"""
InfraGuard AI
Computer Vision — Model Evaluation

Purpose:
    Evaluate the production YOLOv8 model against the held-out TEST split
    and persist all artefacts required for reporting and downstream analysis.

Input:
    weights/best.pt                   — production model (PRODUCTION_WEIGHTS)
    data/processed/dataset.yaml       — dataset config (DATASET_YAML)
    configs/training_config.yaml      — experiment metadata + thresholds

Output:
    evaluation/metrics/<experiment>.csv          — per-class metrics table
    evaluation/metrics/<experiment>_summary.json — overall + per-class JSON
    evaluation/confusion_matrices/<experiment>_confusion_matrix.png
    evaluation/confusion_matrices/<experiment>_PR_curve.png  (if available)

Responsibilities:
    1. Load and validate the production model.
    2. Run model.val() on the TEST split only — never val or train.
    3. Extract overall and per-class metrics (P, R, mAP50, mAP50-95, F1).
    4. Copy Ultralytics-generated plots to evaluation/.
    5. Write CSV and JSON artefacts using only paths from config.py.
    6. Print a formatted evaluation report.

Execution:
    # From ai/computer_vision/
    python training/evaluate.py

    # Evaluate a specific checkpoint instead of production weights:
    python training/evaluate.py --weights path/to/model.pt
"""

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from configs.config import (
    AI_ROOT,
    CLASS_NAMES,
    DATASET_YAML,
    PRODUCTION_WEIGHTS,
    TRAINING_CONFIG,
)
from utils.utils import create_directory, get_logger, print_section, print_separator

# ---------------------------------------------------------------------------
# Module logger
# ---------------------------------------------------------------------------

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Evaluation output directories — derived from config.py AI_ROOT
# ---------------------------------------------------------------------------

EVAL_DIR: Path = AI_ROOT / "evaluation"
EVAL_METRICS_DIR: Path = EVAL_DIR / "metrics"
EVAL_CONFUSION_DIR: Path = EVAL_DIR / "confusion_matrices"


# ===========================================================================
# Stage 1 — Configuration
# ===========================================================================

def load_eval_config(config_path: Path) -> dict[str, Any]:
    """
    Load training_config.yaml for evaluation context.

    Only the experiment, dataset, and validation sections are needed.
    Returns an empty dict for missing sections rather than raising so
    that evaluate.py is usable even without a full training config.

    Args:
        config_path: Path to training_config.yaml.

    Returns:
        Parsed config dict, or ``{}`` if the file is absent or unreadable.
    """
    if not config_path.exists():
        logger.warning(
            "Training config not found at '%s' — using defaults.", config_path
        )
        return {}

    try:
        with config_path.open("r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
    except yaml.YAMLError as exc:
        logger.warning("Could not parse training config: %s — using defaults.", exc)
        return {}

    logger.info("Evaluation config loaded from: %s", config_path)
    return cfg


def resolve_experiment_name(cfg: dict[str, Any]) -> str:
    """Return the experiment name from config, falling back to 'unknown'."""
    return cfg.get("experiment", {}).get("name", "unknown").strip() or "unknown"


# ===========================================================================
# Stage 2 — Model validation and loading
# ===========================================================================

def validate_model_exists(weights_path: Path) -> None:
    """
    Confirm the weights file exists before attempting to load it.

    Args:
        weights_path: Path to the ``.pt`` weights file.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not weights_path.exists():
        raise FileNotFoundError(
            f"Model weights not found: '{weights_path}'\n"
            "Possible causes:\n"
            "  - Training has not completed yet.\n"
            "  - train.py did not finish the weight promotion step.\n"
            "  - You are pointing at the wrong path.\n"
            "Run training/train.py first, then re-run evaluate.py."
        )
    logger.info(
        "Model weights found: %s  (%.1f MB)",
        weights_path,
        weights_path.stat().st_size / 1_048_576,
    )


def load_model(weights_path: Path) -> Any:
    """
    Load a YOLO model from *weights_path*.

    Args:
        weights_path: Path to a trained ``.pt`` file.

    Returns:
        Ultralytics ``YOLO`` model instance.

    Raises:
        ImportError: If ``ultralytics`` is not installed.
        ValueError:  If the model cannot be loaded.
    """
    try:
        from ultralytics import YOLO  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "The 'ultralytics' package is not installed.\n"
            "Run: pip install ultralytics"
        ) from exc

    try:
        model = YOLO(str(weights_path))
    except Exception as exc:
        raise ValueError(
            f"Failed to load model from '{weights_path}': {exc}"
        ) from exc

    logger.info("Model loaded for evaluation: %s", weights_path.name)
    return model


# ===========================================================================
# Stage 3 — Run validation on the test split
# ===========================================================================

def run_val(
    model: Any,
    cfg: dict[str, Any],
    weights_path: Path,
) -> Any:
    """
    Execute ``model.val()`` against the TEST split exclusively.

    All thresholds are read from *cfg*. The split is hardcoded to
    ``"test"`` — this function will never evaluate on val or train.

    Args:
        model:        Loaded Ultralytics YOLO model.
        cfg:          Parsed training_config.yaml dict.
        weights_path: Path to the weights being evaluated (used for logging).

    Returns:
        Ultralytics ``Results`` / ``DetMetrics`` object.

    Raises:
        RuntimeError: If ``model.val()`` raises an unexpected exception.
    """
    v_cfg = cfg.get("validation", {})
    t_cfg = cfg.get("training", {})

    conf: float = float(v_cfg.get("conf_threshold", 0.25))
    iou: float = float(v_cfg.get("iou_threshold", 0.7))
    imgsz: int = int(t_cfg.get("image_size", 640))
    max_det: int = int(v_cfg.get("max_det", 300))
    device: Any = t_cfg.get("device", 0)
    workers: int = int(t_cfg.get("workers", 2))

    print_section("Running Evaluation — TEST Split")
    logger.info("Weights      : %s", weights_path.name)
    logger.info("Dataset YAML : %s", DATASET_YAML)
    logger.info("Split        : test")
    logger.info("conf         : %.2f", conf)
    logger.info("iou          : %.2f", iou)
    logger.info("imgsz        : %d", imgsz)
    logger.info("device       : %s", device)
    print_separator()

    try:
        results = model.val(
            data=str(DATASET_YAML),
            split="test",
            conf=conf,
            iou=iou,
            imgsz=imgsz,
            max_det=max_det,
            device=device,
            workers=workers,
            verbose=True,
            plots=True,          # generates confusion matrix + PR curve
            save_json=False,     # not needed for this pipeline
        )
    except Exception as exc:
        raise RuntimeError(
            f"model.val() failed: {type(exc).__name__}: {exc}"
        ) from exc

    return results


# ===========================================================================
# Stage 4 — Metric extraction
# ===========================================================================

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert *value* to float, returning *default* on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _compute_f1(precision: float, recall: float) -> float:
    """
    Compute the F1 score from *precision* and *recall*.

    Returns 0.0 when precision + recall == 0 to avoid division by zero.
    """
    denom = precision + recall
    if denom == 0.0:
        return 0.0
    return round(2.0 * precision * recall / denom, 6)


def extract_overall_metrics(results: Any) -> dict[str, float]:
    """
    Extract overall (macro-averaged) detection metrics from *results*.

    Tries the ``results_dict`` property first (modern Ultralytics ≥ 8.1),
    then falls back to direct attribute access for older versions.

    Args:
        results: Object returned by ``model.val()``.

    Returns:
        Dict with keys: ``mAP50``, ``mAP50_95``, ``precision``,
        ``recall``, ``f1``.
    """
    # Try results_dict (Ultralytics ≥ 8.1)
    rd: dict = {}
    if hasattr(results, "results_dict"):
        rd = results.results_dict or {}

    def _get(*keys: str) -> float:
        for k in keys:
            if k in rd:
                return _safe_float(rd[k])
        return 0.0

    precision = _get("metrics/precision(B)", "precision")
    recall = _get("metrics/recall(B)", "recall")
    map50 = _get("metrics/mAP50(B)", "mAP_0.5", "mAP50")
    map50_95 = _get("metrics/mAP50-95(B)", "mAP_0.5:0.95", "mAP50-95")

    # Fallback: direct attribute access
    if map50 == 0.0 and hasattr(results, "box"):
        box = results.box
        precision = _safe_float(getattr(box, "mp", 0.0))
        recall = _safe_float(getattr(box, "mr", 0.0))
        map50 = _safe_float(getattr(box, "map50", 0.0))
        map50_95 = _safe_float(getattr(box, "map", 0.0))

    return {
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "mAP50": round(map50, 6),
        "mAP50_95": round(map50_95, 6),
        "f1": _compute_f1(precision, recall),
    }


def extract_per_class_metrics(
    results: Any,
    class_names: list[str],
) -> list[dict[str, Any]]:
    """
    Extract per-class detection metrics from the ``results.box`` breakdown.

    Ultralytics exposes per-class arrays via ``results.box.ap_class_index``,
    ``results.box.p``, ``results.box.r``, ``results.box.ap50``,
    and ``results.box.ap``.

    Args:
        results:      Object returned by ``model.val()``.
        class_names:  Ordered list of class name strings from config.py.

    Returns:
        List of dicts, one per class, each with keys:
        ``class_id``, ``class_name``, ``precision``, ``recall``,
        ``mAP50``, ``mAP50_95``, ``f1``.
        Returns empty list if per-class data is unavailable.
    """
    box = getattr(results, "box", None)
    if box is None:
        logger.warning("Per-class metrics unavailable: results.box not found.")
        return []

    try:
        import numpy as np  # type: ignore

        class_indices = getattr(box, "ap_class_index", None)
        p_arr = getattr(box, "p", None)
        r_arr = getattr(box, "r", None)
        ap50_arr = getattr(box, "ap50", None)
        ap_arr = getattr(box, "ap", None)

        if class_indices is None or p_arr is None:
            logger.warning(
                "Per-class metrics unavailable: ap_class_index or p arrays missing."
            )
            return []

        rows: list[dict[str, Any]] = []
        for i, cls_idx in enumerate(class_indices):
            cls_id = int(cls_idx)
            try:
                cls_name = class_names[cls_id]
            except IndexError:
                cls_name = f"class_{cls_id}"

            p = _safe_float(p_arr[i] if p_arr is not None else 0.0)
            r = _safe_float(r_arr[i] if r_arr is not None else 0.0)
            ap50 = _safe_float(ap50_arr[i] if ap50_arr is not None else 0.0)
            ap = _safe_float(ap_arr[i] if ap_arr is not None else 0.0)

            rows.append({
                "class_id": cls_id,
                "class_name": cls_name,
                "precision": round(p, 6),
                "recall": round(r, 6),
                "mAP50": round(ap50, 6),
                "mAP50_95": round(ap, 6),
                "f1": _compute_f1(p, r),
            })

        return rows

    except Exception as exc:
        logger.warning("Could not extract per-class metrics: %s", exc)
        return []


# ===========================================================================
# Stage 5 — Copy Ultralytics plots
# ===========================================================================

def copy_ultralytics_plots(
    results: Any,
    experiment_name: str,
) -> dict[str, Path | None]:
    """
    Copy Ultralytics-generated PNG plots to the evaluation directory.

    Ultralytics saves plots into its run directory
    (``models/<experiment>/``).  This function locates them and copies
    them to ``evaluation/confusion_matrices/`` with a descriptive name.

    Plots copied (when present):
        - confusion_matrix.png        → <experiment>_confusion_matrix.png
        - confusion_matrix_normalized.png → <experiment>_confusion_matrix_normalized.png
        - PR_curve.png                → <experiment>_PR_curve.png
        - P_curve.png                 → <experiment>_P_curve.png
        - R_curve.png                 → <experiment>_R_curve.png
        - F1_curve.png                → <experiment>_F1_curve.png

    Args:
        results:         Object returned by ``model.val()``.
        experiment_name: Used as the filename prefix.

    Returns:
        Dict mapping plot type → destination Path (or None if not found).
    """
    create_directory(EVAL_CONFUSION_DIR)
    copied: dict[str, Path | None] = {}

    # Ultralytics stores the save directory in results.save_dir
    save_dir: Path | None = None
    raw_dir = getattr(results, "save_dir", None)
    if raw_dir is not None:
        save_dir = Path(str(raw_dir))

    if save_dir is None or not save_dir.exists():
        logger.warning(
            "Ultralytics save_dir not found — plots will not be copied."
        )
        return copied

    # Map source filename → destination suffix
    plot_map: dict[str, str] = {
        "confusion_matrix.png":            "confusion_matrix",
        "confusion_matrix_normalized.png": "confusion_matrix_normalized",
        "PR_curve.png":                    "PR_curve",
        "P_curve.png":                     "P_curve",
        "R_curve.png":                     "R_curve",
        "F1_curve.png":                    "F1_curve",
    }

    for src_name, dest_suffix in plot_map.items():
        src = save_dir / src_name
        if src.exists():
            dst = EVAL_CONFUSION_DIR / f"{experiment_name}_{dest_suffix}.png"
            shutil.copy2(src, dst)
            copied[dest_suffix] = dst
            logger.info("Plot copied: %s → %s", src_name, dst.name)
        else:
            copied[dest_suffix] = None

    if not any(v for v in copied.values()):
        logger.warning(
            "No plots found in '%s' — Ultralytics may not have generated them.",
            save_dir,
        )

    return copied


# ===========================================================================
# Stage 6 — Persist artefacts
# ===========================================================================

_CSV_FIELDS: tuple[str, ...] = (
    "class_id",
    "class_name",
    "precision",
    "recall",
    "mAP50",
    "mAP50_95",
    "f1",
)


def save_metrics_csv(
    per_class: list[dict[str, Any]],
    overall: dict[str, float],
    experiment_name: str,
) -> Path:
    """
    Write per-class and overall metrics to a CSV file.

    Overall metrics are written as a final summary row with
    ``class_name="OVERALL"``.

    Args:
        per_class:       List of per-class metric dicts.
        overall:         Overall metric dict.
        experiment_name: Used as the filename stem.

    Returns:
        Path to the written CSV file.
    """
    create_directory(EVAL_METRICS_DIR)
    csv_path = EVAL_METRICS_DIR / f"{experiment_name}.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDS)
        writer.writeheader()

        for row in per_class:
            writer.writerow({f: row.get(f, "") for f in _CSV_FIELDS})

        # Overall summary row
        writer.writerow({
            "class_id": "",
            "class_name": "OVERALL",
            "precision": overall.get("precision", ""),
            "recall": overall.get("recall", ""),
            "mAP50": overall.get("mAP50", ""),
            "mAP50_95": overall.get("mAP50_95", ""),
            "f1": overall.get("f1", ""),
        })

    logger.info("Metrics CSV written → %s", csv_path)
    return csv_path


def save_summary_json(
    overall: dict[str, float],
    per_class: list[dict[str, Any]],
    experiment_name: str,
    weights_path: Path,
    elapsed: float,
) -> Path:
    """
    Write a structured JSON summary of the evaluation run.

    Args:
        overall:         Overall metric dict.
        per_class:       List of per-class metric dicts.
        experiment_name: Used as the filename stem.
        weights_path:    Path to the evaluated weights file.
        elapsed:         Total evaluation wall-clock seconds.

    Returns:
        Path to the written JSON file.
    """
    create_directory(EVAL_METRICS_DIR)
    json_path = EVAL_METRICS_DIR / f"{experiment_name}_summary.json"

    h = int(elapsed // 3600)
    m = int((elapsed % 3600) // 60)
    s = int(elapsed % 60)
    duration_human = (
        f"{h}h {m}m {s}s" if h > 0
        else f"{m}m {s}s" if m > 0
        else f"{s}s"
    )

    summary: dict[str, Any] = {
        "experiment": experiment_name,
        "evaluated_at_utc": datetime.now(tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "weights": str(weights_path),
        "split": "test",
        "dataset_yaml": str(DATASET_YAML),
        "overall": overall,
        "per_class": per_class,
        "timing": {
            "duration_seconds": round(elapsed, 1),
            "duration_human": duration_human,
        },
    }

    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)

    logger.info("Summary JSON written → %s", json_path)
    return json_path


# ===========================================================================
# Stage 7 — Console report
# ===========================================================================

def print_eval_report(
    overall: dict[str, float],
    per_class: list[dict[str, Any]],
    csv_path: Path,
    json_path: Path,
    copied_plots: dict[str, "Path | None"],
    elapsed: float,
) -> None:
    """
    Print a formatted evaluation report to the console.

    Displays:
        - A per-class metrics table (precision, recall, mAP50, mAP50-95, F1)
        - An overall summary row
        - Paths to every artefact that was written to disk
        - Total evaluation duration

    Args:
        overall:       Overall metric dict from :func:`extract_overall_metrics`.
        per_class:     Per-class metric list from :func:`extract_per_class_metrics`.
        csv_path:      Path to the written metrics CSV.
        json_path:     Path to the written summary JSON.
        copied_plots:  Dict returned by :func:`copy_ultralytics_plots`.
        elapsed:       Total wall-clock seconds for the evaluation run.
    """
    h = int(elapsed // 3600)
    m = int((elapsed % 3600) // 60)
    s = int(elapsed % 60)
    elapsed_str = (
        f"{h}h {m}m {s}s" if h > 0
        else f"{m}m {s}s" if m > 0
        else f"{s}s"
    )

    # ------------------------------------------------------------------
    # Per-class metrics table
    # ------------------------------------------------------------------
    print_section("Evaluation Results — TEST Split")

    col_w = 24  # class name column width
    num_w = 10  # numeric column width

    header = (
        f"  {'Class':<{col_w}}"
        f"{'Precision':>{num_w}}"
        f"{'Recall':>{num_w}}"
        f"{'mAP50':>{num_w}}"
        f"{'mAP50-95':>{num_w}}"
        f"{'F1':>{num_w}}"
    )
    print_separator("-", 78)
    print(header)
    print_separator("-", 78)

    if per_class:
        for row in per_class:
            name = str(row.get("class_name", ""))[:col_w]
            print(
                f"  {name:<{col_w}}"
                f"{row.get('precision', 0.0):>{num_w}.4f}"
                f"{row.get('recall', 0.0):>{num_w}.4f}"
                f"{row.get('mAP50', 0.0):>{num_w}.4f}"
                f"{row.get('mAP50_95', 0.0):>{num_w}.4f}"
                f"{row.get('f1', 0.0):>{num_w}.4f}"
            )
    else:
        print("  (per-class breakdown not available)")

    print_separator("-", 78)

    # Overall row
    print(
        f"  {'OVERALL':<{col_w}}"
        f"{overall.get('precision', 0.0):>{num_w}.4f}"
        f"{overall.get('recall', 0.0):>{num_w}.4f}"
        f"{overall.get('mAP50', 0.0):>{num_w}.4f}"
        f"{overall.get('mAP50_95', 0.0):>{num_w}.4f}"
        f"{overall.get('f1', 0.0):>{num_w}.4f}"
    )
    print_separator("-", 78)

    # ------------------------------------------------------------------
    # Key headline metrics (easy to read at a glance)
    # ------------------------------------------------------------------
    print()
    logger.info("mAP50         : %.4f", overall.get("mAP50", 0.0))
    logger.info("mAP50-95      : %.4f", overall.get("mAP50_95", 0.0))
    logger.info("Precision     : %.4f", overall.get("precision", 0.0))
    logger.info("Recall        : %.4f", overall.get("recall", 0.0))
    logger.info("F1            : %.4f", overall.get("f1", 0.0))

    # ------------------------------------------------------------------
    # Output artefact paths
    # ------------------------------------------------------------------
    print_separator("-", 78)
    logger.info("Metrics CSV   : %s", csv_path)
    logger.info("Summary JSON  : %s", json_path)

    for plot_key, plot_path in copied_plots.items():
        if plot_path is not None:
            logger.info("Plot %-20s: %s", plot_key, plot_path.name)

    print_separator("-", 78)
    logger.info("Duration      : %s", elapsed_str)
    print_separator()


# ===========================================================================
# Stage 8 — Orchestrator (public API)
# ===========================================================================

def evaluate(
    weights_path: Path = PRODUCTION_WEIGHTS,
    config_path: Path = TRAINING_CONFIG,
    class_names: list[str] = CLASS_NAMES,
) -> dict[str, Any]:
    """
    Run the complete evaluation pipeline end-to-end.

    Stages:
        1. Load training_config.yaml (gracefully optional).
        2. Validate the weights file exists.
        3. Load the YOLO model.
        4. Run model.val() on the TEST split.
        5. Extract overall and per-class metrics.
        6. Copy Ultralytics-generated plots to evaluation/.
        7. Persist metrics CSV and summary JSON.
        8. Print the formatted evaluation report.

    Args:
        weights_path: Path to the ``.pt`` model to evaluate.
                      Defaults to ``PRODUCTION_WEIGHTS`` from config.py.
        config_path:  Path to training_config.yaml.
                      Defaults to ``TRAINING_CONFIG`` from config.py.
        class_names:  Ordered class name list.
                      Defaults to ``CLASS_NAMES`` from config.py.

    Returns:
        Dict with keys:
            ``overall``         — overall metric dict (mAP50, mAP50-95, P, R, F1)
            ``per_class``       — list of per-class metric dicts
            ``csv_path``        — Path to the written metrics CSV
            ``json_path``       — Path to the written summary JSON
            ``copied_plots``    — dict of plot type → Path (or None)
            ``experiment_name`` — resolved experiment name string
        On failure, returns an empty dict ``{}``.

    Example::

        from training.evaluate import evaluate
        results = evaluate()
        print(results["overall"])
    """
    import time
    wall_start = time.time()

    print_section("InfraGuard AI — Model Evaluation")
    logger.info("Weights : %s", weights_path)
    logger.info("Config  : %s", config_path)
    print_separator()

    # ------------------------------------------------------------------
    # Stage 1 — Load config (non-fatal if absent)
    # ------------------------------------------------------------------
    cfg = load_eval_config(config_path)
    experiment_name = resolve_experiment_name(cfg)
    logger.info("Experiment : %s", experiment_name)

    # ------------------------------------------------------------------
    # Stage 2 — Validate model weights exist
    # ------------------------------------------------------------------
    try:
        validate_model_exists(weights_path)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return {}

    # ------------------------------------------------------------------
    # Stage 3 — Load model
    # ------------------------------------------------------------------
    try:
        model = load_model(weights_path)
    except (ImportError, ValueError) as exc:
        logger.error("Model load failed: %s", exc)
        return {}

    # ------------------------------------------------------------------
    # Stage 4 — Run val on TEST split
    # ------------------------------------------------------------------
    try:
        results = run_val(model, cfg, weights_path)
    except RuntimeError as exc:
        logger.error("%s", exc)
        return {}

    # ------------------------------------------------------------------
    # Stage 5 — Extract metrics
    # ------------------------------------------------------------------
    overall = extract_overall_metrics(results)
    per_class = extract_per_class_metrics(results, class_names)

    logger.info(
        "Metrics extracted — mAP50: %.4f  mAP50-95: %.4f  P: %.4f  R: %.4f",
        overall["mAP50"],
        overall["mAP50_95"],
        overall["precision"],
        overall["recall"],
    )

    # ------------------------------------------------------------------
    # Stage 6 — Copy Ultralytics plots
    # ------------------------------------------------------------------
    copied_plots = copy_ultralytics_plots(results, experiment_name)

    # ------------------------------------------------------------------
    # Stage 7 — Persist artefacts
    # ------------------------------------------------------------------
    try:
        csv_path = save_metrics_csv(per_class, overall, experiment_name)
        json_path = save_summary_json(
            overall,
            per_class,
            experiment_name,
            weights_path,
            elapsed=time.time() - wall_start,
        )
    except OSError as exc:
        logger.error("Failed to write evaluation artefacts: %s", exc)
        return {}

    # ------------------------------------------------------------------
    # Stage 8 — Console report
    # ------------------------------------------------------------------
    elapsed = time.time() - wall_start
    print_eval_report(overall, per_class, csv_path, json_path, copied_plots, elapsed)

    return {
        "overall": overall,
        "per_class": per_class,
        "csv_path": csv_path,
        "json_path": json_path,
        "copied_plots": copied_plots,
        "experiment_name": experiment_name,
    }


# ===========================================================================
# CLI entry-point
# ===========================================================================

def _parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for standalone evaluation runs.

    Returns:
        Parsed :class:`argparse.Namespace` with attributes:
            ``weights``  — Path to the ``.pt`` model file.
            ``config``   — Path to training_config.yaml.
    """
    parser = argparse.ArgumentParser(
        description="InfraGuard AI — YOLOv8 model evaluation (TEST split)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Evaluate production weights (default)\n"
            "  python training/evaluate.py\n"
            "\n"
            "  # Evaluate a specific checkpoint\n"
            "  python training/evaluate.py --weights weights/archive/best_20260726_191422.pt\n"
            "\n"
            "  # Use a custom config\n"
            "  python training/evaluate.py --config configs/training_config.yaml\n"
        ),
    )
    parser.add_argument(
        "--weights",
        type=Path,
        default=PRODUCTION_WEIGHTS,
        help=(
            f"Path to the .pt model weights to evaluate. "
            f"Default: {PRODUCTION_WEIGHTS}"
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=TRAINING_CONFIG,
        help=(
            f"Path to training_config.yaml. "
            f"Default: {TRAINING_CONFIG}"
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    output = evaluate(
        weights_path=args.weights,
        config_path=args.config,
    )
    sys.exit(0 if output else 1)
