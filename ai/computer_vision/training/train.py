"""
InfraGuard AI
Computer Vision — Training Entry-Point

Purpose:
    Single script that drives the complete YOLOv8 training run from
    configuration load through to production weight promotion.

Input:
    configs/training_config.yaml  — all hyperparameters and experiment metadata

Output:
    models/<experiment_name>/          — Ultralytics run artefacts
    weights/best.pt                    — promoted production model
    weights/archive/best_<ts>.pt       — archived previous production model
    logs/training/<experiment>/epoch_log.csv
    logs/training/<experiment>/val_metrics.csv
    logs/runs/<experiment>/summary.json

Execution:
    # From ai/computer_vision/
    python training/train.py

    # With a custom config path:
    python training/train.py --config path/to/training_config.yaml
"""

import argparse
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from configs.config import (
    CLASS_NAMES,
    DATASET_YAML,
    EXPERIMENTS_DIR,
    LOGS_RUNS_DIR,
    LOGS_TENSORBOARD_DIR,
    LOGS_TRAINING_DIR,
    MODELS_DIR,
    PRODUCTION_WEIGHTS,
    TRAINING_CONFIG,
    WEIGHTS_ARCHIVE_DIR,
    WEIGHTS_DIR,
)
from training.callbacks import register_callbacks
from utils.utils import create_directory, ensure_directories, get_logger, print_section, print_separator

# ---------------------------------------------------------------------------
# Module logger
# ---------------------------------------------------------------------------

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Valid Ultralytics YOLOv8 architectures for detect task
# ---------------------------------------------------------------------------

VALID_ARCHITECTURES: frozenset[str] = frozenset(
    {"yolov8n", "yolov8s", "yolov8m", "yolov8l", "yolov8x"}
)


# ===========================================================================
# Stage 1 — Configuration
# ===========================================================================

def load_config(config_path: Path) -> dict[str, Any]:
    """
    Load and parse training_config.yaml.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Parsed configuration as a nested dict.

    Raises:
        FileNotFoundError: If *config_path* does not exist.
        ValueError:        If the file cannot be parsed as valid YAML.
    """
    if not config_path.exists():
        raise FileNotFoundError(
            f"Training config not found: '{config_path}'\n"
            f"Expected location: {TRAINING_CONFIG}"
        )

    try:
        with config_path.open("r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"Failed to parse training config '{config_path}': {exc}"
        ) from exc

    if not isinstance(cfg, dict):
        raise ValueError(
            f"Training config must be a YAML mapping, got {type(cfg).__name__}."
        )

    logger.info("Configuration loaded from: %s", config_path)
    return cfg


def validate_config(cfg: dict[str, Any]) -> None:
    """
    Run pre-flight checks on the parsed configuration.

    Validates six conditions and raises ``ValueError`` on the first
    failure with a clear, actionable message.

    Checks:
        1. experiment.name is a non-empty string.
        2. model.architecture is a recognised YOLOv8 variant.
        3. dataset.yaml path resolves to an existing file.
        4. dataset.num_classes matches len(CLASS_NAMES) from config.py.
        5. training.epochs is a positive integer.
        6. training.batch_size is a positive integer.

    Args:
        cfg: Parsed training_config.yaml dict.

    Raises:
        ValueError: On any validation failure.
    """
    errors: list[str] = []

    # --- Check 1: experiment name -------------------------------------------
    exp_name: str = cfg.get("experiment", {}).get("name", "").strip()
    if not exp_name:
        errors.append(
            "experiment.name is empty.  "
            "Set a unique name like 'yolov8n_rdd2022_baseline_v1'."
        )

    # --- Check 2: architecture ----------------------------------------------
    arch: str = cfg.get("model", {}).get("architecture", "").strip()
    if arch not in VALID_ARCHITECTURES:
        errors.append(
            f"model.architecture '{arch}' is not valid.  "
            f"Choose one of: {sorted(VALID_ARCHITECTURES)}"
        )

    # --- Check 3: dataset.yaml exists ---------------------------------------
    # Always use the canonical DATASET_YAML from config.py as the source of
    # truth; the value in training_config.yaml is documentation only.
    if not DATASET_YAML.exists():
        errors.append(
            f"dataset.yaml not found at '{DATASET_YAML}'.\n"
            "  Run prepare_dataset.py first to generate it."
        )

    # --- Check 4: class count consistency -----------------------------------
    cfg_nc: int = cfg.get("dataset", {}).get("num_classes", -1)
    expected_nc: int = len(CLASS_NAMES)
    if cfg_nc != expected_nc:
        errors.append(
            f"dataset.num_classes={cfg_nc} does not match "
            f"len(CLASS_NAMES)={expected_nc} in config.py.  "
            "These must be identical."
        )

    # --- Check 5: epochs is positive ----------------------------------------
    epochs: Any = cfg.get("training", {}).get("epochs", 0)
    try:
        if int(epochs) <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors.append(
            f"training.epochs must be a positive integer, got: {epochs!r}"
        )

    # --- Check 6: batch_size is positive ------------------------------------
    batch: Any = cfg.get("training", {}).get("batch_size", 0)
    try:
        if int(batch) <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors.append(
            f"training.batch_size must be a positive integer, got: {batch!r}"
        )

    if errors:
        msg = "\n".join(f"  [{i+1}] {e}" for i, e in enumerate(errors))
        raise ValueError(f"Configuration validation failed:\n{msg}")

    logger.info("Configuration validated successfully.")


# ===========================================================================
# Stage 2 — Directory preparation + experiment guard
# ===========================================================================

def check_experiment_directory(experiment_name: str, resume: bool) -> None:
    """
    Enforce explicit control over the experiment output directory.

    Ultralytics silently appends a numeric suffix (experiment2, experiment3 …)
    when the target directory already exists.  This breaks ``locate_best_pt()``
    and produces orphaned run folders.  This function prevents that by
    failing fast with a clear, actionable message whenever a conflict is
    detected.

    Rules:
        - Directory does NOT exist → always OK (fresh run).
        - Directory DOES exist AND ``resume=True`` → OK (will write into it).
        - Directory DOES exist AND ``resume=False`` → hard error.

    Args:
        experiment_name: Value of ``experiment.name`` from config.
        resume:          Whether the pipeline intends to resume training.

    Raises:
        FileExistsError: If the experiment directory already exists and
                         ``resume`` is ``False``.
    """
    exp_dir = MODELS_DIR / experiment_name

    if not exp_dir.exists():
        # Fresh run — directory will be created by Ultralytics
        logger.info("Experiment directory: new  → %s", exp_dir)
        return

    if resume:
        logger.info(
            "Experiment directory: exists (resume mode) → %s", exp_dir
        )
        return

    # Directory exists, resume is off → hard stop
    last_pt = exp_dir / "weights" / "last.pt"
    resume_hint = (
        "\n  Option A — Resume the existing run:"
        "\n              Set checkpointing.resume: true in training_config.yaml"
        "\n              and re-run train.py."
        "\n  Option B — Start a new experiment:"
        f"\n              Change experiment.name in training_config.yaml"
        f"\n              (current: '{experiment_name}')"
    )
    raise FileExistsError(
        f"Experiment directory already exists: '{exp_dir}'\n"
        f"resume=false is set, so a fresh run cannot write here.\n"
        f"{'last.pt found — run can be resumed.' if last_pt.exists() else 'No last.pt found.'}"
        f"{resume_hint}"
    )


def prepare_output_dirs() -> None:
    """
    Create all output directories required by the training pipeline.

    Uses constants from config.py exclusively — no paths are constructed
    here.  Safe to call multiple times (all calls are idempotent).
    """
    ensure_directories(
        MODELS_DIR,
        WEIGHTS_DIR,
        WEIGHTS_ARCHIVE_DIR,
        EXPERIMENTS_DIR,
        LOGS_TRAINING_DIR,
        LOGS_RUNS_DIR,
        LOGS_TENSORBOARD_DIR,
    )
    logger.info("Output directories ready.")


# ===========================================================================
# Stage 3 — Model construction
# ===========================================================================

def resolve_model_weights(cfg: dict[str, Any]) -> str:
    """
    Return the weight specification string that Ultralytics accepts.

    When ``model.pretrained`` is ``True``, return ``"<arch>.pt"`` so
    Ultralytics downloads COCO-pretrained weights.  When ``False``,
    return ``"<arch>.yaml"`` to initialise from scratch.

    Args:
        cfg: Parsed training_config.yaml dict.

    Returns:
        String accepted by ``YOLO(weight_spec)``.
    """
    arch: str = cfg["model"]["architecture"]
    pretrained: bool = bool(cfg["model"].get("pretrained", True))
    weight_spec = f"{arch}.pt" if pretrained else f"{arch}.yaml"
    logger.info(
        "Model weight spec: '%s'  (pretrained=%s)", weight_spec, pretrained
    )
    return weight_spec


def build_model(weight_spec: str) -> Any:
    """
    Instantiate a YOLO model from *weight_spec*.

    Args:
        weight_spec: Value returned by :func:`resolve_model_weights`.

    Returns:
        Ultralytics ``YOLO`` model instance.

    Raises:
        ImportError:  If ``ultralytics`` is not installed.
        ValueError:   If Ultralytics rejects the weight specification.
        RuntimeError: If model construction fails for any other reason.
    """
    try:
        from ultralytics import YOLO  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "The 'ultralytics' package is not installed.\n"
            "Run: pip install ultralytics"
        ) from exc

    try:
        model = YOLO(weight_spec)
    except Exception as exc:
        raise ValueError(
            f"Failed to load YOLO model from '{weight_spec}': {exc}\n"
            f"Valid architectures: {sorted(VALID_ARCHITECTURES)}"
        ) from exc

    logger.info("Model loaded: %s", weight_spec)
    return model


# ===========================================================================
# Stage 4 — Resume detection
# ===========================================================================

def check_resume(cfg: dict[str, Any], experiment_name: str) -> tuple[bool, Path | None]:
    """
    Determine whether to resume training from a previous checkpoint.

    Resuming is only attempted when:
        - ``checkpointing.resume`` is ``True`` in the config, AND
        - ``last.pt`` exists in the experiment's Ultralytics output directory.

    Args:
        cfg:             Parsed training_config.yaml dict.
        experiment_name: Current experiment name string.

    Returns:
        ``(True, last_pt_path)``  if resume conditions are met.
        ``(False, None)``         otherwise.
    """
    resume_enabled: bool = bool(
        cfg.get("checkpointing", {}).get("resume", True)
    )

    if not resume_enabled:
        logger.info("Resume: disabled in config (checkpointing.resume: false).")
        return False, None

    last_pt = MODELS_DIR / experiment_name / "weights" / "last.pt"

    if last_pt.exists():
        logger.info("Resume: last.pt found — training will resume from: %s", last_pt)
        return True, last_pt

    logger.info("Resume: enabled in config but no last.pt found — starting fresh.")
    return False, None


def validate_checkpoint_compatibility(
    last_pt: Path,
    cfg: dict[str, Any],
) -> None:
    """
    Verify that *last_pt* is compatible with the current configuration.

    Reads the PyTorch checkpoint metadata embedded in ``last.pt`` and
    cross-checks three dimensions against the active training config:

        1. Architecture — the model type stored in the checkpoint must
           match ``model.architecture`` from training_config.yaml.
        2. Number of classes — ``nc`` from the checkpoint must match
           ``dataset.num_classes`` from training_config.yaml.
        3. Experiment directory — the checkpoint's parent directory name
           must match the configured ``experiment.name`` so that a user
           who renames the experiment is alerted immediately.

    All checks emit ``logger.warning`` for non-critical mismatches
    that are recoverable, and raise ``ValueError`` for incompatibilities
    that would silently corrupt training state.

    Args:
        last_pt: Path to ``last.pt`` to inspect.
        cfg:     Parsed training_config.yaml dict.

    Raises:
        ValueError: If a hard incompatibility is detected.
        RuntimeError: If the checkpoint file cannot be read.
    """
    import torch  # type: ignore  — available wherever ultralytics is installed

    cfg_arch: str = cfg.get("model", {}).get("architecture", "").strip()
    cfg_nc: int = int(cfg.get("dataset", {}).get("num_classes", -1))
    cfg_exp: str = cfg.get("experiment", {}).get("name", "").strip()

    # ------------------------------------------------------------------
    # Check 3 — Experiment directory name
    # The checkpoint should live at models/<experiment_name>/weights/last.pt.
    # If the grandparent folder name doesn't match the configured name the
    # user has likely changed experiment.name without disabling resume.
    # ------------------------------------------------------------------
    checkpoint_exp = last_pt.parent.parent.name   # weights/ → <exp_name>
    if checkpoint_exp != cfg_exp:
        raise ValueError(
            f"Resume checkpoint belongs to experiment '{checkpoint_exp}' "
            f"but training_config.yaml targets '{cfg_exp}'.\n"
            f"  Checkpoint : {last_pt}\n"
            f"  Options:\n"
            f"    A) Restore experiment.name to '{checkpoint_exp}'\n"
            f"    B) Set checkpointing.resume: false to start a new run"
        )

    # ------------------------------------------------------------------
    # Read checkpoint metadata (CPU-safe, does not load weights onto GPU)
    # ------------------------------------------------------------------
    try:
        ckpt: dict = torch.load(str(last_pt), map_location="cpu", weights_only=False)
    except Exception as exc:
        raise RuntimeError(
            f"Cannot read checkpoint '{last_pt}': {exc}\n"
            "The file may be corrupted.  Delete it and start a fresh run."
        ) from exc

    # ------------------------------------------------------------------
    # Check 1 — Architecture
    # Ultralytics stores the model yaml path in ckpt["train_args"]["model"]
    # for modern versions (8.x), or in ckpt["model"].yaml_file for older.
    # We try both and fall back gracefully if neither is present.
    # ------------------------------------------------------------------
    ckpt_arch: str | None = None

    train_args_in_ckpt: dict = ckpt.get("train_args", {}) or {}
    model_field: str = str(train_args_in_ckpt.get("model", ""))
    if model_field:
        # Strip path and extension: "yolov8n.pt" → "yolov8n"
        ckpt_arch = Path(model_field).stem

    if ckpt_arch is None:
        # Fallback: read from the model object's yaml_file attribute
        model_obj = ckpt.get("model")
        yaml_file = getattr(model_obj, "yaml_file", None) or getattr(
            getattr(model_obj, "model", None), "yaml_file", None
        )
        if yaml_file:
            ckpt_arch = Path(str(yaml_file)).stem

    if ckpt_arch is not None and ckpt_arch != cfg_arch:
        raise ValueError(
            f"Checkpoint architecture '{ckpt_arch}' does not match "
            f"configured architecture '{cfg_arch}'.\n"
            f"  Checkpoint : {last_pt}\n"
            f"  Options:\n"
            f"    A) Set model.architecture: {ckpt_arch} to resume correctly\n"
            f"    B) Set checkpointing.resume: false to train '{cfg_arch}' fresh"
        )

    if ckpt_arch is None:
        logger.warning(
            "Checkpoint compatibility: could not read architecture from '%s' "
            "— proceeding without architecture check.",
            last_pt.name,
        )
    else:
        logger.info(
            "Checkpoint compatibility: architecture '%s' matches config.", ckpt_arch
        )

    # ------------------------------------------------------------------
    # Check 2 — Number of classes
    # Ultralytics stores nc in ckpt["train_args"] or in the model's nc attr.
    # ------------------------------------------------------------------
    ckpt_nc: int | None = None

    nc_from_args = train_args_in_ckpt.get("nc") or train_args_in_ckpt.get("num_classes")
    if nc_from_args is not None:
        try:
            ckpt_nc = int(nc_from_args)
        except (TypeError, ValueError):
            pass

    if ckpt_nc is None:
        model_obj = ckpt.get("model")
        nc_attr = getattr(model_obj, "nc", None) or getattr(
            getattr(model_obj, "model", None), "nc", None
        )
        if nc_attr is not None:
            try:
                ckpt_nc = int(nc_attr)
            except (TypeError, ValueError):
                pass

    if ckpt_nc is not None and ckpt_nc != cfg_nc:
        raise ValueError(
            f"Checkpoint has nc={ckpt_nc} classes but config expects nc={cfg_nc}.\n"
            f"  Checkpoint : {last_pt}\n"
            f"  The dataset was likely changed after training started.\n"
            f"  Set checkpointing.resume: false and start a new run."
        )

    if ckpt_nc is None:
        logger.warning(
            "Checkpoint compatibility: could not read nc from '%s' "
            "— proceeding without class count check.",
            last_pt.name,
        )
    else:
        logger.info(
            "Checkpoint compatibility: nc=%d matches config.", ckpt_nc
        )

    logger.info("Checkpoint compatibility check passed: %s", last_pt.name)


# ===========================================================================
# Stage 5 — Training argument assembly
# ===========================================================================

def build_train_args(
    cfg: dict[str, Any],
    dataset_yaml: Path,
    resume: bool,
    last_pt: Path | None,
) -> dict[str, Any]:
    """
    Assemble the complete keyword-argument dict for ``model.train()``.

    Every value comes from *cfg* or from config.py path constants.
    Nothing is hardcoded in this function.

    Args:
        cfg:         Parsed training_config.yaml dict.
        dataset_yaml: Resolved path to dataset.yaml.
        resume:      Whether to resume from a previous checkpoint.
        last_pt:     Path to ``last.pt`` when resuming, else ``None``.

    Returns:
        Dict of keyword arguments passed directly to ``model.train()``.
    """
    t_cfg = cfg.get("training", {})
    o_cfg = cfg.get("optimizer", {})
    s_cfg = cfg.get("scheduler", {})
    a_cfg = cfg.get("augmentation", {})
    v_cfg = cfg.get("validation", {})
    c_cfg = cfg.get("checkpointing", {})
    l_cfg = cfg.get("logging", {})
    e_cfg = cfg.get("experiment", {})

    experiment_name: str = e_cfg.get("name", "experiment")

    train_args: dict[str, Any] = {
        # ---- Dataset -------------------------------------------------------
        "data": str(dataset_yaml),

        # ---- Output directories --------------------------------------------
        "project": str(MODELS_DIR),
        "name": experiment_name,
        "exist_ok": resume,   # True = write into existing dir; False = error on conflict

        # ---- Core training -------------------------------------------------
        "epochs": int(t_cfg.get("epochs", 100)),
        "batch": int(t_cfg.get("batch_size", 16)),
        "imgsz": int(t_cfg.get("image_size", 640)),
        "workers": int(t_cfg.get("workers", 2)),
        "device": t_cfg.get("device", 0),
        "seed": int(t_cfg.get("seed", 42)),
        "deterministic": bool(t_cfg.get("deterministic", True)),

        # ---- Optimizer -----------------------------------------------------
        "optimizer": str(o_cfg.get("type", "SGD")),
        "lr0": float(o_cfg.get("lr0", 0.01)),
        "lrf": float(o_cfg.get("lrf", 0.01)),
        "momentum": float(o_cfg.get("momentum", 0.937)),
        "weight_decay": float(o_cfg.get("weight_decay", 0.0005)),
        "warmup_epochs": float(o_cfg.get("warmup_epochs", 3)),
        "warmup_momentum": float(o_cfg.get("warmup_momentum", 0.8)),
        "warmup_bias_lr": float(o_cfg.get("warmup_bias_lr", 0.1)),

        # ---- Scheduler -----------------------------------------------------
        "cos_lr": bool(s_cfg.get("cos_lr", True)),
        "close_mosaic": int(s_cfg.get("close_mosaic_epochs", 10)),

        # ---- Augmentation --------------------------------------------------
        "hsv_h": float(a_cfg.get("hsv_h", 0.015)),
        "hsv_s": float(a_cfg.get("hsv_s", 0.7)),
        "hsv_v": float(a_cfg.get("hsv_v", 0.4)),
        "degrees": float(a_cfg.get("degrees", 0.0)),
        "translate": float(a_cfg.get("translate", 0.1)),
        "scale": float(a_cfg.get("scale", 0.5)),
        "flipud": float(a_cfg.get("flipud", 0.0)),
        "fliplr": float(a_cfg.get("fliplr", 0.5)),
        "perspective": float(a_cfg.get("perspective", 0.0)),
        "shear": float(a_cfg.get("shear", 0.0)),
        "mosaic": float(a_cfg.get("mosaic", 1.0)),
        "mixup": float(a_cfg.get("mixup", 0.1)),
        "copy_paste": float(a_cfg.get("copy_paste", 0.0)),

        # ---- Validation ----------------------------------------------------
        "conf": float(v_cfg.get("conf_threshold", 0.25)),
        "iou": float(v_cfg.get("iou_threshold", 0.7)),
        "val": True,
        "max_det": int(v_cfg.get("max_det", 300)),

        # ---- Checkpointing -------------------------------------------------
        "save_period": int(c_cfg.get("save_period", 10)),
        "patience": int(c_cfg.get("patience", 50)),
        "save": bool(c_cfg.get("save_best", True)),

        # ---- Logging -------------------------------------------------------
        "plots": bool(l_cfg.get("save_plots", True)),
        "verbose": bool(l_cfg.get("verbose", True)),

        # ---- Resume --------------------------------------------------------
        "resume": resume,
    }

    # When resuming, Ultralytics expects the path to last.pt as the
    # model argument, not the standard weight spec.  train.py handles
    # this by passing last_pt back to the caller for use in run_training().
    # The "resume" key in train_args is still needed to tell Ultralytics
    # not to reset the epoch counter.

    return train_args


# ===========================================================================
# Stage 6 — Execute training
# ===========================================================================

def run_training(model: Any, train_args: dict[str, Any]) -> Any:
    """
    Execute ``model.train()`` with the assembled argument dict.

    Args:
        model:       Ultralytics YOLO model instance.
        train_args:  Dict returned by :func:`build_train_args`.

    Returns:
        Ultralytics results object returned by ``model.train()``.

    Raises:
        RuntimeError: If ``model.train()`` raises an unexpected exception
                      (re-raised after logging).
    """
    experiment_name: str = train_args.get("name", "experiment")
    epochs: int = int(train_args.get("epochs", 0))

    print_section(f"Starting Training — {experiment_name}")
    logger.info("Epochs     : %d", epochs)
    logger.info("Batch      : %d", train_args.get("batch", 0))
    logger.info("Image size : %d", train_args.get("imgsz", 0))
    logger.info("Device     : %s", train_args.get("device", ""))
    logger.info("Dataset    : %s", train_args.get("data", ""))
    logger.info("Output dir : %s / %s", train_args.get("project", ""), experiment_name)
    if train_args.get("resume"):
        logger.info("Mode       : RESUME from last.pt")
    else:
        logger.info("Mode       : FRESH START")
    print_separator()

    try:
        results = model.train(**train_args)
    except Exception as exc:
        raise RuntimeError(
            f"model.train() failed with: {type(exc).__name__}: {exc}"
        ) from exc

    return results


# ===========================================================================
# Stage 7 — Weight promotion
# ===========================================================================

def locate_best_pt(experiment_name: str) -> Path:
    """
    Locate the ``best.pt`` file produced by Ultralytics.

    Ultralytics writes to ``models/<experiment_name>/weights/best.pt``.

    Args:
        experiment_name: Value of ``experiment.name`` from config.

    Returns:
        Resolved path to the Ultralytics ``best.pt``.

    Raises:
        FileNotFoundError: If the file does not exist after training.
    """
    best_pt = MODELS_DIR / experiment_name / "weights" / "best.pt"

    if not best_pt.exists():
        raise FileNotFoundError(
            f"best.pt not found at expected location: '{best_pt}'\n"
            "Possible causes:\n"
            "  - Training was interrupted before any checkpoint was saved.\n"
            "  - All epochs completed but no improvement was recorded.\n"
            "  - Ultralytics used a different output path.\n"
            f"  Check: {MODELS_DIR / experiment_name}"
        )

    logger.info("Ultralytics best.pt located: %s", best_pt)
    return best_pt


def archive_production_weights() -> Path | None:
    """
    Move the current ``weights/best.pt`` to the archive directory.

    Called before promoting a new model so that the previous production
    weights are never silently overwritten.  The archive filename includes
    a UTC timestamp so the chronological order of experiments is clear.

    Returns:
        Path to the archived file, or ``None`` if no existing file was found.
    """
    if not PRODUCTION_WEIGHTS.exists():
        logger.info("No existing production weights to archive.")
        return None

    create_directory(WEIGHTS_ARCHIVE_DIR)
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_path = WEIGHTS_ARCHIVE_DIR / f"best_{ts}.pt"

    shutil.move(str(PRODUCTION_WEIGHTS), archive_path)
    logger.info("Previous production weights archived → %s", archive_path)
    return archive_path


def promote_best_pt(src_best_pt: Path) -> Path:
    """
    Promote *src_best_pt* to the stable production weights path.

    Sequence:
        1. Archive the current ``weights/best.pt`` (if any).
        2. Copy *src_best_pt* → ``weights/best.pt``.

    Using copy rather than move preserves the original Ultralytics run
    artefact inside ``models/`` so the full training run remains intact.

    Args:
        src_best_pt: Path to the Ultralytics-generated ``best.pt``.

    Returns:
        Path to the promoted production weights (``PRODUCTION_WEIGHTS``).

    Raises:
        OSError: If the copy operation fails.
    """
    archive_production_weights()

    create_directory(WEIGHTS_DIR)
    shutil.copy2(src_best_pt, PRODUCTION_WEIGHTS)

    logger.info(
        "best.pt promoted to production: %s  (%.1f MB)",
        PRODUCTION_WEIGHTS,
        PRODUCTION_WEIGHTS.stat().st_size / 1_048_576,
    )
    return PRODUCTION_WEIGHTS


# ===========================================================================
# Stage 8 — Final summary
# ===========================================================================

def print_final_summary(
    cfg: dict[str, Any],
    promoted_path: Path,
    elapsed: float,
) -> None:
    """
    Print the post-training summary block to the console.

    Args:
        cfg:           Parsed training_config.yaml dict.
        promoted_path: Path to the production weights file.
        elapsed:       Total wall-clock seconds for the full run() call.
    """
    exp_name: str = cfg.get("experiment", {}).get("name", "")
    arch: str = cfg.get("model", {}).get("architecture", "")
    epochs: int = int(cfg.get("training", {}).get("epochs", 0))

    h = int(elapsed // 3600)
    m = int((elapsed % 3600) // 60)
    s = int(elapsed % 60)
    if h > 0:
        elapsed_str = f"{h}h {m}m {s}s"
    elif m > 0:
        elapsed_str = f"{m}m {s}s"
    else:
        elapsed_str = f"{s}s"

    summary_json = LOGS_RUNS_DIR / exp_name / "summary.json"
    epoch_log = LOGS_TRAINING_DIR / exp_name / "epoch_log.csv"

    print_section("Run Complete")
    logger.info("Experiment        : %s", exp_name)
    logger.info("Architecture      : %s", arch)
    logger.info("Epochs configured : %d", epochs)
    print_separator("-", 60)
    logger.info("Production model  : %s", promoted_path)
    logger.info("Run artefacts     : %s", MODELS_DIR / exp_name)
    logger.info("Epoch log         : %s", epoch_log)
    logger.info("Summary JSON      : %s", summary_json)
    print_separator("-", 60)
    logger.info("Total wall time   : %s", elapsed_str)
    print_separator()
    logger.info("Next step — run evaluation:")
    logger.info("  python training/evaluate.py")
    print_separator()


# ===========================================================================
# Orchestrator
# ===========================================================================

def run(config_path: Path = TRAINING_CONFIG) -> bool:
    """
    Execute the complete training pipeline end-to-end.

    Stages:
        1.  Load training_config.yaml.
        2.  Validate all configuration values.
        3.  Prepare output directories.
        4.  Resolve model weight specification.
        5.  Build the YOLO model.
        6.  Check for a resumable checkpoint.
        7.  Register InfraGuard callbacks.
        8.  Assemble Ultralytics training arguments.
        9.  Execute model.train().
        10. Locate Ultralytics best.pt.
        11. Archive previous production weights.
        12. Promote new best.pt to weights/best.pt.
        13. Print final summary.

    Args:
        config_path: Path to ``training_config.yaml``.
                     Defaults to ``TRAINING_CONFIG`` from ``config.py``.

    Returns:
        ``True`` if training completed and weights were promoted successfully.
        ``False`` if any stage failed.
    """
    wall_start = time.time()

    print_section("InfraGuard AI — Training Pipeline")
    logger.info("Config: %s", config_path)
    print_separator()

    # ------------------------------------------------------------------
    # Stage 1 — Load config
    # ------------------------------------------------------------------
    try:
        cfg = load_config(config_path)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Failed to load config: %s", exc)
        return False

    # ------------------------------------------------------------------
    # Stage 2 — Validate config
    # ------------------------------------------------------------------
    try:
        validate_config(cfg)
    except ValueError as exc:
        logger.error("%s", exc)
        return False

    experiment_name: str = cfg["experiment"]["name"]

    # ------------------------------------------------------------------
    # Stage 3 — Prepare directories
    # ------------------------------------------------------------------
    prepare_output_dirs()

    # ------------------------------------------------------------------
    # Stage 3b — Guard experiment directory BEFORE building the model.
    # resume is not yet known here; we need check_resume() first.
    # We call check_resume early (read-only) so the directory guard has
    # the correct resume value before any filesystem writes occur.
    # ------------------------------------------------------------------
    resume_early, last_pt_early = check_resume(cfg, experiment_name)

    try:
        check_experiment_directory(experiment_name, resume_early)
    except FileExistsError as exc:
        logger.error("%s", exc)
        return False

    # ------------------------------------------------------------------
    # Stage 4 — Resolve weights spec
    # ------------------------------------------------------------------
    weight_spec = resolve_model_weights(cfg)

    # ------------------------------------------------------------------
    # Stage 5 — Build model
    # ------------------------------------------------------------------
    try:
        model = build_model(weight_spec)
    except (ImportError, ValueError) as exc:
        logger.error("%s", exc)
        return False

    # ------------------------------------------------------------------
    # Stage 6 — Resume detection (already resolved above)
    # ------------------------------------------------------------------
    resume, last_pt = resume_early, last_pt_early

    # When resuming, validate the checkpoint before loading it, then
    # rebuild the model from last.pt so Ultralytics restores full state.
    if resume and last_pt is not None:
        try:
            validate_checkpoint_compatibility(last_pt, cfg)
        except (ValueError, RuntimeError) as exc:
            logger.error("Checkpoint compatibility check failed:\n%s", exc)
            return False

        try:
            model = build_model(str(last_pt))
        except (ImportError, ValueError) as exc:
            logger.error(
                "Could not load last.pt for resume (%s) — aborting.\n"
                "Set checkpointing.resume: false to start a fresh run.",
                exc,
            )
            return False

    # ------------------------------------------------------------------
    # Stage 7 — Register callbacks
    # ------------------------------------------------------------------
    register_callbacks(model, cfg)

    # ------------------------------------------------------------------
    # Stage 8 — Assemble training arguments
    # ------------------------------------------------------------------
    train_args = build_train_args(cfg, DATASET_YAML, resume, last_pt)

    # ------------------------------------------------------------------
    # Stage 9 — Execute training
    # ------------------------------------------------------------------
    try:
        run_training(model, train_args)
    except KeyboardInterrupt:
        logger.warning("Training interrupted by user (KeyboardInterrupt).")
        logger.warning(
            "Checkpoint saved at: %s",
            MODELS_DIR / experiment_name / "weights" / "last.pt",
        )
        logger.warning(
            "To resume: set checkpointing.resume: true in training_config.yaml "
            "and re-run train.py."
        )
        return False
    except RuntimeError as exc:
        logger.error("Training failed: %s", exc)
        return False

    # ------------------------------------------------------------------
    # Stage 10 — Locate best.pt
    # ------------------------------------------------------------------
    try:
        src_best_pt = locate_best_pt(experiment_name)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return False

    # ------------------------------------------------------------------
    # Stages 11–12 — Archive old weights, promote new best.pt
    # ------------------------------------------------------------------
    try:
        promoted = promote_best_pt(src_best_pt)
    except OSError as exc:
        logger.error("Failed to promote best.pt: %s", exc)
        return False

    # ------------------------------------------------------------------
    # Stage 13 — Final summary
    # ------------------------------------------------------------------
    elapsed = time.time() - wall_start
    print_final_summary(cfg, promoted, elapsed)

    return True


# ===========================================================================
# CLI entry-point
# ===========================================================================

def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="InfraGuard AI — YOLOv8 training pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python training/train.py\n"
            "  python training/train.py --config configs/training_config.yaml\n"
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=TRAINING_CONFIG,
        help=f"Path to training_config.yaml  (default: {TRAINING_CONFIG})",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    success = run(config_path=args.config)
    sys.exit(0 if success else 1)
