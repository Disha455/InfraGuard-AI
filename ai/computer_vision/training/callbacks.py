"""
InfraGuard AI
Computer Vision — Training Callbacks

Purpose:
    Provide reusable Ultralytics callback hooks that instrument the YOLOv8
    training loop without coupling any logging logic to train.py.

    train.py's only responsibility regarding logging is a single call:

        from training.callbacks import register_callbacks
        register_callbacks(trainer, cfg)

    Everything else — file creation, CSV writing, JSON summary — is
    handled entirely inside this module.

Input:
    trainer : Ultralytics BaseTrainer instance (passed automatically by the
              Ultralytics callback system)
    cfg     : dict loaded from configs/training_config.yaml

Output:
    logs/training/<experiment_name>/epoch_log.csv   — one row per epoch
    logs/training/<experiment_name>/val_metrics.csv — validation metrics per epoch
    logs/runs/<experiment_name>/summary.json        — full run summary on completion

Callbacks implemented:
    on_train_start    — log config, record start timestamp
    on_fit_epoch_end  — append epoch metrics row to epoch_log.csv
    on_val_end        — append validation metrics row to val_metrics.csv
    on_train_end      — write summary.json, log final results

Public API:
    register_callbacks(trainer, cfg) — attach all enabled callbacks to trainer

Execution:
    Not run directly.  Imported and called by training/train.py.
"""

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from configs.config import LOGS_RUNS_DIR, LOGS_TRAINING_DIR, TRAINING_CONFIG
from utils.utils import create_directory, get_logger

# ---------------------------------------------------------------------------
# Module logger
# ---------------------------------------------------------------------------

logger: logging.Logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# CSV field definitions
# ---------------------------------------------------------------------------

# Column names written to epoch_log.csv — order is fixed and must not change
# between runs so that files from different sessions can be concatenated.
EPOCH_LOG_FIELDS: tuple[str, ...] = (
    "epoch",
    "train_box_loss",
    "train_cls_loss",
    "train_dfl_loss",
    "val_box_loss",
    "val_cls_loss",
    "val_dfl_loss",
    "precision",
    "recall",
    "mAP50",
    "mAP50_95",
    "lr",
)

# Column names written to val_metrics.csv
VAL_METRICS_FIELDS: tuple[str, ...] = (
    "epoch",
    "precision",
    "recall",
    "mAP50",
    "mAP50_95",
)

# ---------------------------------------------------------------------------
# Module-level run state
# ---------------------------------------------------------------------------
# Stores transient data that must survive across callback invocations during
# a single training run.  Reset completely at on_train_start so that
# back-to-back training runs in the same process do not share state.

_run_state: dict[str, Any] = {
    "experiment_name": "",
    "start_dt": None,           # datetime object (UTC)
    "start_utc_str": "",        # ISO-8601 string for JSON serialisation
    "epoch_log_path": None,     # Path to epoch_log.csv
    "val_metrics_path": None,   # Path to val_metrics.csv
    "cfg": {},                  # Full parsed training_config dict
    "epoch_log_initialised": False,
    "val_metrics_initialised": False,
}


# ---------------------------------------------------------------------------
# Internal helpers — metric extraction
# ---------------------------------------------------------------------------

def _get_metric(
    metrics: dict[str, Any],
    *keys: str,
    default: float = 0.0,
) -> float:
    """
    Return the first value found in *metrics* for any of the given *keys*.

    Ultralytics metric key names differ slightly across versions
    (e.g. ``"metrics/mAP50(B)"`` vs ``"mAP_0.5"``).  Passing multiple
    candidate keys makes the callbacks resilient to version differences
    without requiring try/except blocks at every call site.

    Args:
        metrics: Flat dict of metric name → float from trainer.metrics.
        *keys:   Candidate key names, tried left to right.
        default: Value returned when no key is found (default 0.0).

    Returns:
        Float metric value, or *default* if none of the keys are present.
    """
    for key in keys:
        if key in metrics:
            val = metrics[key]
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return default


def _get_lr(trainer: Any) -> float:
    """
    Extract the current learning rate from the trainer's optimizer.

    Reads the first parameter group's learning rate, which corresponds to
    the backbone / feature extractor layers (pg0 in Ultralytics terminology).

    Args:
        trainer: Ultralytics BaseTrainer instance.

    Returns:
        Current learning rate as a float, or 0.0 if unavailable.
    """
    try:
        return float(trainer.optimizer.param_groups[0]["lr"])
    except (AttributeError, IndexError, KeyError, TypeError):
        return 0.0


def _format_duration(total_seconds: float) -> str:
    """
    Convert *total_seconds* into a human-readable string.

    Args:
        total_seconds: Elapsed time in seconds.

    Returns:
        String in the form ``"11h 32m 43s"``, ``"45m 12s"``, or ``"38s"``.
    """
    total_seconds = max(0.0, total_seconds)
    h = int(total_seconds // 3600)
    m = int((total_seconds % 3600) // 60)
    s = int(total_seconds % 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


# ---------------------------------------------------------------------------
# Internal helpers — file I/O
# ---------------------------------------------------------------------------

def _resolve_log_paths(experiment_name: str) -> tuple[Path, Path, Path]:
    """
    Build and create all log file paths for *experiment_name*.

    Args:
        experiment_name: Value of cfg["experiment"]["name"].

    Returns:
        Tuple of (epoch_log_path, val_metrics_path, summary_dir).
    """
    training_dir = LOGS_TRAINING_DIR / experiment_name
    runs_dir = LOGS_RUNS_DIR / experiment_name

    create_directory(training_dir)
    create_directory(runs_dir)

    epoch_log_path = training_dir / "epoch_log.csv"
    val_metrics_path = training_dir / "val_metrics.csv"

    return epoch_log_path, val_metrics_path, runs_dir


def _write_csv_row(
    csv_path: Path,
    fields: tuple[str, ...],
    row: dict[str, Any],
    *,
    write_header: bool,
) -> None:
    """
    Append one row to a CSV file, optionally writing the header first.

    Opens in append mode so this is O(1) per call regardless of file size.

    Args:
        csv_path:     Destination CSV file path.
        fields:       Ordered column names (defines both header and row order).
        row:          Mapping of field name → value for this row.
        write_header: If True, write the header row before the data row.
                      Should only be True on the first call for a given file.
    """
    create_directory(csv_path.parent)
    mode = "a"
    with csv_path.open(mode, newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        if write_header:
            writer.writeheader()
        # Fill any missing fields with empty string rather than raising KeyError
        safe_row = {f: row.get(f, "") for f in fields}
        writer.writerow(safe_row)


# ---------------------------------------------------------------------------
# Callback 1 — on_train_start
# ---------------------------------------------------------------------------

def on_train_start(trainer: Any) -> None:
    """
    Fires once immediately before the first training epoch.

    Responsibilities:
        - Reset module-level run state.
        - Record the UTC start timestamp.
        - Resolve and create log file paths.
        - Emit structured log lines covering the full training configuration.

    Args:
        trainer: Ultralytics BaseTrainer instance.
    """
    cfg: dict = _run_state.get("cfg", {})
    exp_cfg = cfg.get("experiment", {})
    train_cfg = cfg.get("training", {})
    model_cfg = cfg.get("model", {})
    dataset_cfg = cfg.get("dataset", {})
    log_cfg = cfg.get("logging", {})

    experiment_name: str = exp_cfg.get("name", "unknown_experiment")
    start_dt = datetime.now(tz=timezone.utc)

    # Resolve paths and create directories
    epoch_log_path, val_metrics_path, _ = _resolve_log_paths(experiment_name)

    # Reset run state
    _run_state.update({
        "experiment_name": experiment_name,
        "start_dt": start_dt,
        "start_utc_str": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "epoch_log_path": epoch_log_path,
        "val_metrics_path": val_metrics_path,
        "epoch_log_initialised": False,
        "val_metrics_initialised": False,
    })

    # ------------------------------------------------------------------
    # Structured log output
    # ------------------------------------------------------------------
    from utils.utils import print_section, print_separator  # local import avoids circular at module level

    print_section("Training Started")
    logger.info("Experiment       : %s", experiment_name)
    logger.info("Description      : %s", exp_cfg.get("description", "").strip())
    logger.info("Author           : %s", exp_cfg.get("author", ""))
    logger.info("Version          : %s", exp_cfg.get("version", ""))
    print_separator("-", 60)
    logger.info("Architecture     : %s", model_cfg.get("architecture", ""))
    logger.info("Pretrained       : %s", model_cfg.get("pretrained", True))
    logger.info("Task             : %s", model_cfg.get("task", "detect"))
    print_separator("-", 60)
    logger.info("Dataset YAML     : %s", dataset_cfg.get("yaml", ""))
    logger.info("Classes (%d)      : %s",
                dataset_cfg.get("num_classes", 0),
                dataset_cfg.get("class_names", []))
    print_separator("-", 60)
    logger.info("Epochs           : %s", train_cfg.get("epochs", ""))
    logger.info("Batch size       : %s", train_cfg.get("batch_size", ""))
    logger.info("Image size       : %s", train_cfg.get("image_size", ""))
    logger.info("Device           : %s", train_cfg.get("device", ""))
    logger.info("Workers          : %s", train_cfg.get("workers", ""))
    logger.info("Seed             : %s", train_cfg.get("seed", ""))
    print_separator("-", 60)
    logger.info("Start time (UTC) : %s", _run_state["start_utc_str"])
    logger.info("Epoch log        : %s", epoch_log_path)
    logger.info("Val metrics log  : %s", val_metrics_path)
    logger.info("Config file      : %s", TRAINING_CONFIG)
    print_separator()

    if log_cfg.get("csv_logging", True):
        logger.info("CSV logging      : ENABLED")
    else:
        logger.info("CSV logging      : DISABLED  (set logging.csv_logging: true to enable)")

    if log_cfg.get("json_summary", True):
        logger.info("JSON summary     : ENABLED")
    else:
        logger.info("JSON summary     : DISABLED  (set logging.json_summary: true to enable)")


# ---------------------------------------------------------------------------
# Callback 2 — on_fit_epoch_end
# ---------------------------------------------------------------------------

def on_fit_epoch_end(trainer: Any) -> None:
    """
    Fires after every epoch once both training and validation are complete.

    Appends one row to epoch_log.csv containing all training and validation
    losses, mAP metrics, precision, recall, and the current learning rate.

    The CSV header is written automatically on the first epoch.

    Args:
        trainer: Ultralytics BaseTrainer instance with trainer.metrics populated.
    """
    cfg: dict = _run_state.get("cfg", {})
    if not cfg.get("logging", {}).get("csv_logging", True):
        return

    metrics = getattr(trainer, "metrics", {}) or {}

    # 1-indexed epoch number for human readability
    epoch = (getattr(trainer, "epoch", 0) or 0) + 1

    row: dict[str, Any] = {
        "epoch": epoch,
        # Training losses
        "train_box_loss": _get_metric(
            metrics,
            "train/box_loss", "train/box_om", "box_loss",
        ),
        "train_cls_loss": _get_metric(
            metrics,
            "train/cls_loss", "cls_loss",
        ),
        "train_dfl_loss": _get_metric(
            metrics,
            "train/dfl_loss", "dfl_loss",
        ),
        # Validation losses
        "val_box_loss": _get_metric(
            metrics,
            "val/box_loss", "val/box_om",
        ),
        "val_cls_loss": _get_metric(
            metrics,
            "val/cls_loss",
        ),
        "val_dfl_loss": _get_metric(
            metrics,
            "val/dfl_loss",
        ),
        # Detection metrics
        "precision": _get_metric(
            metrics,
            "metrics/precision(B)", "precision",
        ),
        "recall": _get_metric(
            metrics,
            "metrics/recall(B)", "recall",
        ),
        "mAP50": _get_metric(
            metrics,
            "metrics/mAP50(B)", "mAP_0.5", "mAP50",
        ),
        "mAP50_95": _get_metric(
            metrics,
            "metrics/mAP50-95(B)", "mAP_0.5:0.95", "mAP50-95",
        ),
        # Learning rate
        "lr": _get_lr(trainer),
    }

    csv_path: Path = _run_state["epoch_log_path"]
    write_header = not _run_state["epoch_log_initialised"]

    try:
        _write_csv_row(csv_path, EPOCH_LOG_FIELDS, row, write_header=write_header)
        _run_state["epoch_log_initialised"] = True
        logger.debug(
            "Epoch %d — mAP50: %.4f  mAP50-95: %.4f  P: %.4f  R: %.4f  LR: %.6f",
            epoch,
            row["mAP50"],
            row["mAP50_95"],
            row["precision"],
            row["recall"],
            row["lr"],
        )
    except OSError as exc:
        logger.error("Failed to write epoch log row for epoch %d: %s", epoch, exc)


# ---------------------------------------------------------------------------
# Callback 3 — on_val_end
# ---------------------------------------------------------------------------

def on_val_end(validator: Any) -> None:
    """
    Fires after each validation pass (during training or standalone val).

    Appends one row to val_metrics.csv containing only the validation
    detection metrics (precision, recall, mAP50, mAP50-95).

    This file is intentionally separate from epoch_log.csv so that
    validation results can be analysed in isolation without parsing the
    full combined log.

    Args:
        validator: Ultralytics BaseValidator instance with validator.metrics
                   populated.
    """
    cfg: dict = _run_state.get("cfg", {})
    if not cfg.get("logging", {}).get("csv_logging", True):
        return

    # validator.metrics may be a Metrics object rather than a plain dict
    raw_metrics = getattr(validator, "metrics", None)
    if raw_metrics is None:
        return

    # Normalise to dict — Ultralytics Metrics objects support .results_dict
    if hasattr(raw_metrics, "results_dict"):
        metrics: dict[str, Any] = raw_metrics.results_dict
    elif isinstance(raw_metrics, dict):
        metrics = raw_metrics
    else:
        return

    # Derive epoch from the trainer attached to the validator (if available)
    trainer = getattr(validator, "trainer", None)
    epoch = ((getattr(trainer, "epoch", 0) or 0) + 1) if trainer is not None else 0

    row: dict[str, Any] = {
        "epoch": epoch,
        "precision": _get_metric(
            metrics,
            "metrics/precision(B)", "precision",
        ),
        "recall": _get_metric(
            metrics,
            "metrics/recall(B)", "recall",
        ),
        "mAP50": _get_metric(
            metrics,
            "metrics/mAP50(B)", "mAP_0.5", "mAP50",
        ),
        "mAP50_95": _get_metric(
            metrics,
            "metrics/mAP50-95(B)", "mAP_0.5:0.95", "mAP50-95",
        ),
    }

    csv_path: Path = _run_state["val_metrics_path"]
    write_header = not _run_state["val_metrics_initialised"]

    try:
        _write_csv_row(csv_path, VAL_METRICS_FIELDS, row, write_header=write_header)
        _run_state["val_metrics_initialised"] = True
    except OSError as exc:
        logger.error("Failed to write val_metrics row: %s", exc)


# ---------------------------------------------------------------------------
# Callback 4 — on_train_end
# ---------------------------------------------------------------------------

def on_train_end(trainer: Any) -> None:
    """
    Fires once after the final epoch or after early stopping completes.

    Responsibilities:
        - Compute total training duration.
        - Collect final metrics from trainer.
        - Write summary.json to logs/runs/<experiment_name>/.
        - Emit a final console summary.

    Args:
        trainer: Ultralytics BaseTrainer instance.
    """
    cfg: dict = _run_state.get("cfg", {})
    log_cfg = cfg.get("logging", {})
    exp_cfg = cfg.get("experiment", {})
    train_cfg = cfg.get("training", {})
    model_cfg = cfg.get("model", {})
    dataset_cfg = cfg.get("dataset", {})
    opt_cfg = cfg.get("optimizer", {})

    experiment_name: str = _run_state.get("experiment_name", "unknown_experiment")

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------
    start_dt: datetime | None = _run_state.get("start_dt")
    end_dt = datetime.now(tz=timezone.utc)
    end_utc_str = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    if start_dt is not None:
        duration_seconds = (end_dt - start_dt).total_seconds()
    else:
        duration_seconds = 0.0

    duration_human = _format_duration(duration_seconds)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------
    metrics = getattr(trainer, "metrics", {}) or {}
    best_fitness = float(getattr(trainer, "best_fitness", 0.0) or 0.0)

    # Ultralytics stores the best epoch index (0-based) in trainer.best
    # for some versions, or it can be inferred from trainer.stopper.best_epoch
    best_epoch_raw = (
        getattr(trainer, "best_epoch", None)
        or getattr(getattr(trainer, "stopper", None), "best_epoch", None)
    )
    best_epoch: int = (int(best_epoch_raw) + 1) if best_epoch_raw is not None else 0
    epochs_completed: int = (getattr(trainer, "epoch", 0) or 0) + 1

    final_map50 = _get_metric(
        metrics, "metrics/mAP50(B)", "mAP_0.5", "mAP50",
    )
    final_map50_95 = _get_metric(
        metrics, "metrics/mAP50-95(B)", "mAP_0.5:0.95", "mAP50-95",
    )
    final_precision = _get_metric(
        metrics, "metrics/precision(B)", "precision",
    )
    final_recall = _get_metric(
        metrics, "metrics/recall(B)", "recall",
    )

    # ------------------------------------------------------------------
    # Build best.pt path (Ultralytics save_dir)
    # ------------------------------------------------------------------
    save_dir: Path = Path(getattr(trainer, "save_dir", ""))
    best_pt_path = save_dir / "weights" / "best.pt"

    # ------------------------------------------------------------------
    # Log file paths (relative for portability in JSON)
    # ------------------------------------------------------------------
    epoch_log_path: Path = _run_state.get("epoch_log_path") or Path("")
    val_metrics_path: Path = _run_state.get("val_metrics_path") or Path("")
    runs_dir = LOGS_RUNS_DIR / experiment_name
    summary_path = runs_dir / "summary.json"

    # ------------------------------------------------------------------
    # Build summary dict
    # ------------------------------------------------------------------
    summary: dict[str, Any] = {
        "experiment": {
            "name": experiment_name,
            "description": exp_cfg.get("description", "").strip(),
            "version": str(exp_cfg.get("version", "")),
            "author": exp_cfg.get("author", ""),
            "notes": exp_cfg.get("notes", ""),
        },
        "config": {
            "architecture": model_cfg.get("architecture", ""),
            "pretrained": model_cfg.get("pretrained", True),
            "task": model_cfg.get("task", "detect"),
            "epochs_planned": train_cfg.get("epochs", 0),
            "epochs_completed": epochs_completed,
            "batch_size": train_cfg.get("batch_size", 0),
            "image_size": train_cfg.get("image_size", 640),
            "device": str(train_cfg.get("device", "")),
            "seed": train_cfg.get("seed", 0),
            "optimizer": opt_cfg.get("type", ""),
            "lr0": opt_cfg.get("lr0", 0.0),
            "lrf": opt_cfg.get("lrf", 0.0),
            "momentum": opt_cfg.get("momentum", 0.0),
            "weight_decay": opt_cfg.get("weight_decay", 0.0),
            "dataset_yaml": dataset_cfg.get("yaml", ""),
            "num_classes": dataset_cfg.get("num_classes", 0),
            "class_names": dataset_cfg.get("class_names", []),
        },
        "results": {
            "best_epoch": best_epoch,
            "best_fitness": round(best_fitness, 6),
            "final_mAP50": round(final_map50, 6),
            "final_mAP50_95": round(final_map50_95, 6),
            "final_precision": round(final_precision, 6),
            "final_recall": round(final_recall, 6),
        },
        "paths": {
            "best_pt_ultralytics": str(best_pt_path),
            "epoch_log_csv": str(epoch_log_path),
            "val_metrics_csv": str(val_metrics_path),
            "summary_json": str(summary_path),
        },
        "timing": {
            "start_utc": _run_state.get("start_utc_str", ""),
            "end_utc": end_utc_str,
            "duration_seconds": round(duration_seconds, 1),
            "duration_human": duration_human,
        },
    }

    # ------------------------------------------------------------------
    # Write summary.json
    # ------------------------------------------------------------------
    if log_cfg.get("json_summary", True):
        try:
            create_directory(runs_dir)
            with summary_path.open("w", encoding="utf-8") as fh:
                json.dump(summary, fh, indent=2, ensure_ascii=False)
            logger.info("Run summary written → %s", summary_path)
        except OSError as exc:
            logger.error("Failed to write summary.json: %s", exc)

    # ------------------------------------------------------------------
    # Final console output
    # ------------------------------------------------------------------
    from utils.utils import print_section, print_separator  # local import

    print_section("Training Complete")
    logger.info("Experiment       : %s", experiment_name)
    logger.info("Epochs completed : %d / %d",
                epochs_completed, train_cfg.get("epochs", 0))
    logger.info("Best epoch       : %d", best_epoch)
    logger.info("Best fitness     : %.4f", best_fitness)
    print_separator("-", 60)
    logger.info("Final mAP50      : %.4f", final_map50)
    logger.info("Final mAP50-95   : %.4f", final_map50_95)
    logger.info("Final Precision  : %.4f", final_precision)
    logger.info("Final Recall     : %.4f", final_recall)
    print_separator("-", 60)
    logger.info("Duration         : %s", duration_human)
    logger.info("best.pt          : %s", best_pt_path)
    if log_cfg.get("json_summary", True):
        logger.info("Summary JSON     : %s", summary_path)
    if log_cfg.get("csv_logging", True):
        logger.info("Epoch log CSV    : %s", epoch_log_path)
    print_separator()


# ---------------------------------------------------------------------------
# Public API — register_callbacks
# ---------------------------------------------------------------------------

def register_callbacks(trainer: Any, cfg: dict[str, Any]) -> None:
    """
    Attach all enabled InfraGuard callbacks to *trainer*.

    This is the only function train.py needs to call.  It reads the
    ``logging`` section of *cfg* to decide which callbacks to register,
    then injects the config into module-level state so every callback
    has access to it without needing it passed as a parameter (which the
    Ultralytics callback signature does not support).

    Callback registration is additive — Ultralytics stores a list of
    functions per event and calls all of them in order.  Registering
    callbacks multiple times (e.g. in a Jupyter notebook that re-runs
    a cell) would cause duplicate writes.  The function guards against
    this by checking whether its own callbacks are already registered.

    Args:
        trainer: Ultralytics BaseTrainer instance (before training starts).
        cfg:     Parsed training_config.yaml as a nested dict.

    Example::

        from training.callbacks import register_callbacks
        register_callbacks(trainer, cfg)
        trainer.train()
    """
    # Store the full config in run state so callbacks can access it
    # without needing it passed as an argument (Ultralytics callback
    # functions receive only the trainer/validator object).
    _run_state["cfg"] = cfg

    log_cfg: dict = cfg.get("logging", {})

    # ------------------------------------------------------------------
    # Guard against duplicate registration (notebook re-run safety)
    # ------------------------------------------------------------------
    existing: list = trainer.callbacks.get("on_train_start", [])
    if any(cb is on_train_start for cb in existing):
        logger.warning(
            "InfraGuard callbacks already registered on this trainer — skipping."
        )
        return

    # ------------------------------------------------------------------
    # on_train_start — always registered (pure logging, no file I/O risk)
    # ------------------------------------------------------------------
    trainer.add_callback("on_train_start", on_train_start)
    logger.debug("Registered: on_train_start")

    # ------------------------------------------------------------------
    # on_fit_epoch_end — registered when csv_logging is enabled
    # ------------------------------------------------------------------
    if log_cfg.get("csv_logging", True):
        trainer.add_callback("on_fit_epoch_end", on_fit_epoch_end)
        logger.debug("Registered: on_fit_epoch_end  (epoch_log.csv)")

    # ------------------------------------------------------------------
    # on_val_end — registered when csv_logging is enabled
    # ------------------------------------------------------------------
    if log_cfg.get("csv_logging", True):
        trainer.add_callback("on_val_end", on_val_end)
        logger.debug("Registered: on_val_end  (val_metrics.csv)")

    # ------------------------------------------------------------------
    # on_train_end — registered when json_summary is enabled
    # ------------------------------------------------------------------
    if log_cfg.get("json_summary", True):
        trainer.add_callback("on_train_end", on_train_end)
        logger.debug("Registered: on_train_end  (summary.json)")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    experiment_name: str = cfg.get("experiment", {}).get("name", "unknown")
    logger.info(
        "Callbacks registered for experiment '%s'  "
        "(csv=%s  json=%s)",
        experiment_name,
        log_cfg.get("csv_logging", True),
        log_cfg.get("json_summary", True),
    )
