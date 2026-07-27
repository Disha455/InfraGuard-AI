"""
InfraGuard AI
Computer Vision — Model Export

Purpose:
    Convert the production YOLO model (weights/best.pt) into the deployment
    formats requested in training_config.yaml export section.

Input:
    weights/best.pt                    — production model (PRODUCTION_WEIGHTS)
    configs/training_config.yaml       — export flags and format parameters

Output:
    exports/<experiment_name>/<experiment_name>.pt       — PyTorch copy
    exports/<experiment_name>/<experiment_name>.onnx     — ONNX (if enabled)
    exports/<experiment_name>/<experiment_name>.engine   — TensorRT (if enabled)
    exports/<experiment_name>/<experiment_name>.tflite   — TFLite (if enabled)

Responsibilities:
    1. Validate weights/best.pt exists before attempting any export.
    2. Read the export section of training_config.yaml.
    3. Export only the formats explicitly set to true.
    4. Isolate each format — one format failing must not abort the rest.
    5. Write all outputs to EXPORTS_DIR/<experiment_name>/ from config.py.
    6. Print a summary table of all outcomes.

Execution:
    # From ai/computer_vision/
    python training/export.py

    # Export a specific checkpoint:
    python training/export.py --weights weights/archive/best_20260726_191422.pt

    # Use a custom config:
    python training/export.py --config configs/training_config.yaml
"""

import argparse
import json
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from configs.config import EXPORTS_DIR, PRODUCTION_WEIGHTS, TRAINING_CONFIG
from training.evaluate import (
    load_eval_config,
    resolve_experiment_name,
    validate_model_exists,
)
from utils.utils import create_directory, get_logger, print_section, print_separator

# ---------------------------------------------------------------------------
# Module logger
# ---------------------------------------------------------------------------

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Supported export formats — canonical names map to Ultralytics format strings
# ---------------------------------------------------------------------------

# Maps config key → Ultralytics format= argument
# "pytorch" is handled separately (copy, not model.export)
_FORMAT_TO_ULTRALYTICS: dict[str, str] = {
    "onnx":      "onnx",
    "tensorrt":  "engine",
    "tflite":    "tflite",
}

# Maps format key → expected output file extension (for locating the output)
_FORMAT_TO_EXTENSION: dict[str, str] = {
    "pytorch":  ".pt",
    "onnx":     ".onnx",
    "tensorrt": ".engine",
    "tflite":   ".tflite",
}


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class ExportResult:
    """
    Records the outcome of a single format export attempt.

    Attributes:
        fmt:     Format name key (e.g. ``"onnx"``).
        enabled: Whether this format was requested in config.
        success: Whether the export completed without error.
        path:    Path to the exported file, or ``None`` on failure.
        size_mb: File size in megabytes, or 0.0 if unavailable.
        error:   Error message string on failure, or ``""`` on success.
        elapsed: Wall-clock seconds taken for this export.
    """
    fmt: str
    enabled: bool
    success: bool = False
    path: Path | None = None
    size_mb: float = 0.0
    error: str = ""
    elapsed: float = 0.0


# ===========================================================================
# Stage 1 — Configuration
# ===========================================================================

def load_export_config(config_path: Path) -> dict[str, Any]:
    """
    Load the ``export`` section from training_config.yaml.

    Delegates full YAML loading to :func:`training.evaluate.load_eval_config`
    (no duplication) and then extracts only the export section.

    Args:
        config_path: Path to training_config.yaml.

    Returns:
        The ``export`` sub-dict, or sensible defaults if absent.
        Keys: ``pytorch``, ``onnx``, ``onnx_opset``, ``onnx_simplify``,
        ``tensorrt``, ``tensorrt_fp16``, ``tflite``, ``export_image_size``.
    """
    cfg = load_eval_config(config_path)
    export_cfg: dict[str, Any] = cfg.get("export", {})

    # Apply defaults for any keys absent from the YAML
    defaults: dict[str, Any] = {
        "pytorch":          True,
        "onnx":             False,
        "onnx_opset":       17,
        "onnx_simplify":    True,
        "tensorrt":         False,
        "tensorrt_fp16":    True,
        "tflite":           False,
        "export_image_size": 640,
    }
    for k, v in defaults.items():
        export_cfg.setdefault(k, v)

    return export_cfg


def resolve_export_targets(export_cfg: dict[str, Any]) -> list[str]:
    """
    Return the ordered list of format names that are enabled in config.

    Formats are returned in a stable order: pytorch → onnx → tensorrt → tflite.
    This ensures the console output and summary JSON are always consistent.

    Args:
        export_cfg: The export sub-dict from :func:`load_export_config`.

    Returns:
        List of enabled format name strings.  May be empty if all are false.
    """
    ordered: list[str] = ["pytorch", "onnx", "tensorrt", "tflite"]
    return [fmt for fmt in ordered if bool(export_cfg.get(fmt, False))]


# ===========================================================================
# Stage 2 — Model loading
# ===========================================================================

def load_model_for_export(weights_path: Path) -> Any:
    """
    Load a YOLO model for export.

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

    logger.info("Model loaded for export: %s", weights_path.name)
    return model


# ===========================================================================
# Stage 3 — Per-format export handlers
# ===========================================================================

def _resolve_output_path(
    export_dir: Path,
    experiment_name: str,
    extension: str,
) -> Path:
    """
    Build the destination file path for a single exported artefact.

    All exports land in ``exports/<experiment_name>/`` with the filename
    ``<experiment_name><extension>``.

    Args:
        export_dir:      Root exports directory (``EXPORTS_DIR``).
        experiment_name: Current experiment identifier string.
        extension:       File extension including the dot (e.g. ``".onnx"``).

    Returns:
        Full destination :class:`~pathlib.Path`.
    """
    dest_dir = export_dir / experiment_name
    create_directory(dest_dir)
    return dest_dir / f"{experiment_name}{extension}"


def _file_size_mb(path: Path) -> float:
    """Return file size in megabytes, or 0.0 if the path does not exist."""
    try:
        return round(path.stat().st_size / 1_048_576, 2)
    except OSError:
        return 0.0


def _export_pytorch(
    weights_path: Path,
    export_dir: Path,
    experiment_name: str,
) -> Path:
    """
    Copy the source ``.pt`` file into the exports directory.

    PyTorch format is already present as ``weights/best.pt``.  This step
    copies it into the experiment sub-folder so all exported artefacts
    live in one place.

    Args:
        weights_path:    Source ``.pt`` file (PRODUCTION_WEIGHTS).
        export_dir:      Root exports directory.
        experiment_name: Experiment identifier used for the filename.

    Returns:
        Path to the copied ``.pt`` file.

    Raises:
        OSError: If the copy operation fails.
    """
    dst = _resolve_output_path(export_dir, experiment_name, ".pt")
    shutil.copy2(weights_path, dst)
    logger.info("PyTorch export: copied → %s  (%.1f MB)", dst.name, _file_size_mb(dst))
    return dst


def _export_onnx(
    model: Any,
    export_dir: Path,
    experiment_name: str,
    export_cfg: dict[str, Any],
) -> Path:
    """
    Export the model to ONNX format via Ultralytics.

    Uses opset and simplify settings from the config export section.
    Ultralytics places the ``.onnx`` file next to ``best.pt`` in the
    weights directory; this function then moves it to the exports folder.

    Args:
        model:           Loaded Ultralytics YOLO model.
        export_dir:      Root exports directory.
        experiment_name: Experiment identifier used for the filename.
        export_cfg:      Export section dict from training_config.yaml.

    Returns:
        Final destination Path of the ``.onnx`` file.

    Raises:
        RuntimeError: If ``model.export()`` fails.
    """
    imgsz: int = int(export_cfg.get("export_image_size", 640))
    opset: int = int(export_cfg.get("onnx_opset", 17))
    simplify: bool = bool(export_cfg.get("onnx_simplify", True))

    logger.info(
        "ONNX export: imgsz=%d  opset=%d  simplify=%s", imgsz, opset, simplify
    )

    try:
        result_path = model.export(
            format="onnx",
            imgsz=imgsz,
            opset=opset,
            simplify=simplify,
            dynamic=False,
        )
    except Exception as exc:
        raise RuntimeError(f"ONNX export failed: {exc}") from exc

    src = Path(str(result_path))
    dst = _resolve_output_path(export_dir, experiment_name, ".onnx")

    if src.exists() and src != dst:
        shutil.move(str(src), dst)
    elif not dst.exists():
        raise RuntimeError(
            f"ONNX export appeared to succeed but output not found at '{src}'."
        )

    logger.info("ONNX export: done → %s  (%.1f MB)", dst.name, _file_size_mb(dst))
    return dst


def _export_tensorrt(
    model: Any,
    export_dir: Path,
    experiment_name: str,
    export_cfg: dict[str, Any],
) -> Path:
    """
    Export the model to a TensorRT engine via Ultralytics.

    Requires TensorRT to be installed in the current environment.  On
    Colab free tier this will fail — the exception is caught by the
    dispatcher and logged as a warning so other formats continue.

    Args:
        model:           Loaded Ultralytics YOLO model.
        export_dir:      Root exports directory.
        experiment_name: Experiment identifier used for the filename.
        export_cfg:      Export section dict from training_config.yaml.

    Returns:
        Final destination Path of the ``.engine`` file.

    Raises:
        RuntimeError: If ``model.export()`` fails (e.g. TensorRT not installed).
    """
    imgsz: int = int(export_cfg.get("export_image_size", 640))
    fp16: bool = bool(export_cfg.get("tensorrt_fp16", True))

    logger.info("TensorRT export: imgsz=%d  fp16=%s", imgsz, fp16)

    try:
        result_path = model.export(
            format="engine",
            imgsz=imgsz,
            half=fp16,
            dynamic=False,
        )
    except Exception as exc:
        raise RuntimeError(
            f"TensorRT export failed: {exc}\n"
            "  Ensure TensorRT is installed: https://docs.nvidia.com/deeplearning/tensorrt/"
        ) from exc

    src = Path(str(result_path))
    dst = _resolve_output_path(export_dir, experiment_name, ".engine")

    if src.exists() and src != dst:
        shutil.move(str(src), dst)
    elif not dst.exists():
        raise RuntimeError(
            f"TensorRT export appeared to succeed but output not found at '{src}'."
        )

    logger.info(
        "TensorRT export: done → %s  (%.1f MB)", dst.name, _file_size_mb(dst)
    )
    return dst


def _export_tflite(
    model: Any,
    export_dir: Path,
    experiment_name: str,
    export_cfg: dict[str, Any],
) -> Path:
    """
    Export the model to TFLite format via Ultralytics.

    Required for on-device inference on Android (Flutter mobile app).
    Requires TensorFlow to be installed.

    Args:
        model:           Loaded Ultralytics YOLO model.
        export_dir:      Root exports directory.
        experiment_name: Experiment identifier used for the filename.
        export_cfg:      Export section dict from training_config.yaml.

    Returns:
        Final destination Path of the ``.tflite`` file.

    Raises:
        RuntimeError: If ``model.export()`` fails.
    """
    imgsz: int = int(export_cfg.get("export_image_size", 640))

    logger.info("TFLite export: imgsz=%d", imgsz)

    try:
        result_path = model.export(
            format="tflite",
            imgsz=imgsz,
        )
    except Exception as exc:
        raise RuntimeError(
            f"TFLite export failed: {exc}\n"
            "  Ensure TensorFlow is installed: pip install tensorflow"
        ) from exc

    # Ultralytics may return a directory or a file path for TFLite
    src = Path(str(result_path))

    # If a directory was returned, locate the .tflite file inside it
    if src.is_dir():
        candidates = list(src.glob("*.tflite"))
        if not candidates:
            raise RuntimeError(
                f"TFLite export returned a directory but no .tflite "
                f"file was found inside: '{src}'"
            )
        src = candidates[0]

    dst = _resolve_output_path(export_dir, experiment_name, ".tflite")

    if src.exists() and src != dst:
        shutil.move(str(src), dst)
    elif not dst.exists():
        raise RuntimeError(
            f"TFLite export appeared to succeed but output not found at '{src}'."
        )

    logger.info(
        "TFLite export: done → %s  (%.1f MB)", dst.name, _file_size_mb(dst)
    )
    return dst


def _dispatch_export(
    fmt: str,
    model: Any,
    weights_path: Path,
    export_dir: Path,
    experiment_name: str,
    export_cfg: dict[str, Any],
) -> ExportResult:
    """
    Attempt a single format export and return an :class:`ExportResult`.

    This function is the sole caller of all ``_export_*`` handlers.
    It catches every exception so that a failure in one format can never
    abort the remaining exports.

    Args:
        fmt:             Format name key (``"pytorch"``, ``"onnx"``, etc.).
        model:           Loaded Ultralytics YOLO model.
        weights_path:    Path to the source ``.pt`` weights file.
        export_dir:      Root exports directory (``EXPORTS_DIR``).
        experiment_name: Experiment identifier string.
        export_cfg:      Export section dict from training_config.yaml.

    Returns:
        :class:`ExportResult` populated with outcome details.
    """
    t_start = time.time()
    result = ExportResult(fmt=fmt, enabled=True)

    logger.info("─" * 50)
    logger.info("Exporting format: %s", fmt.upper())

    try:
        if fmt == "pytorch":
            output_path = _export_pytorch(weights_path, export_dir, experiment_name)
        elif fmt == "onnx":
            output_path = _export_onnx(model, export_dir, experiment_name, export_cfg)
        elif fmt == "tensorrt":
            output_path = _export_tensorrt(
                model, export_dir, experiment_name, export_cfg
            )
        elif fmt == "tflite":
            output_path = _export_tflite(
                model, export_dir, experiment_name, export_cfg
            )
        else:
            raise ValueError(f"Unknown export format: '{fmt}'")

        result.success = True
        result.path = output_path
        result.size_mb = _file_size_mb(output_path)

    except Exception as exc:
        result.success = False
        result.error = str(exc)
        logger.warning(
            "Format '%s' export FAILED — continuing with remaining formats.\n"
            "  Reason: %s",
            fmt,
            exc,
        )

    result.elapsed = round(time.time() - t_start, 2)
    return result


# ===========================================================================
# Stage 4 — Orchestrator (public API)
# ===========================================================================

def export_all(
    weights_path: Path = PRODUCTION_WEIGHTS,
    config_path: Path = TRAINING_CONFIG,
) -> dict[str, ExportResult]:
    """
    Run the complete export pipeline end-to-end.

    Stages:
        1. Load the export section from training_config.yaml.
        2. Resolve which formats are enabled.
        3. Validate the source weights file exists (hard stop if missing).
        4. Load the YOLO model once — reused across all formats.
        5. Dispatch each enabled format through :func:`_dispatch_export`.
        6. Persist an export manifest JSON to the experiment export dir.
        7. Print a summary table of all outcomes.

    Each format is attempted independently.  A failure in one format
    logs a warning and continues — the pipeline never aborts mid-run
    due to a single format error.  The only hard stop is a missing
    ``weights_path`` (step 3).

    Args:
        weights_path: Path to the ``.pt`` model to export.
                      Defaults to ``PRODUCTION_WEIGHTS`` from config.py.
        config_path:  Path to training_config.yaml.
                      Defaults to ``TRAINING_CONFIG`` from config.py.

    Returns:
        Dict mapping format name → :class:`ExportResult`.
        Keys present for every *enabled* format, regardless of success.
        Returns an empty dict ``{}`` if the weights file is missing or
        the model cannot be loaded.

    Example::

        from training.export import export_all
        results = export_all()
        for fmt, r in results.items():
            print(fmt, "OK" if r.success else r.error)
    """
    wall_start = time.time()

    print_section("InfraGuard AI — Model Export")
    logger.info("Weights : %s", weights_path)
    logger.info("Config  : %s", config_path)
    print_separator()

    # ------------------------------------------------------------------
    # Stage 1 — Load export config
    # ------------------------------------------------------------------
    export_cfg = load_export_config(config_path)

    # Resolve experiment name from the full config for directory naming
    full_cfg = load_eval_config(config_path)
    experiment_name = resolve_experiment_name(full_cfg)
    logger.info("Experiment : %s", experiment_name)

    # ------------------------------------------------------------------
    # Stage 2 — Resolve enabled formats
    # ------------------------------------------------------------------
    targets = resolve_export_targets(export_cfg)

    if not targets:
        logger.warning(
            "No export formats are enabled in training_config.yaml.\n"
            "Set at least one format to true under the 'export:' section."
        )
        return {}

    logger.info(
        "Formats enabled (%d): %s", len(targets), ", ".join(targets)
    )

    # ------------------------------------------------------------------
    # Stage 3 — Validate source weights (hard stop)
    # ------------------------------------------------------------------
    try:
        validate_model_exists(weights_path)
    except FileNotFoundError as exc:
        logger.error(
            "Export aborted — production model not found.\n%s", exc
        )
        return {}

    # ------------------------------------------------------------------
    # Stage 4 — Load model once (reused for all non-pytorch formats)
    # ------------------------------------------------------------------
    try:
        model = load_model_for_export(weights_path)
    except (ImportError, ValueError) as exc:
        logger.error("Export aborted — model could not be loaded: %s", exc)
        return {}

    # ------------------------------------------------------------------
    # Stage 5 — Dispatch each enabled format
    # ------------------------------------------------------------------
    results: dict[str, ExportResult] = {}

    for fmt in targets:
        result = _dispatch_export(
            fmt=fmt,
            model=model,
            weights_path=weights_path,
            export_dir=EXPORTS_DIR,
            experiment_name=experiment_name,
            export_cfg=export_cfg,
        )
        results[fmt] = result

    # ------------------------------------------------------------------
    # Stage 6 — Persist export manifest
    # ------------------------------------------------------------------
    elapsed = round(time.time() - wall_start, 2)
    save_export_manifest(results, experiment_name, weights_path, elapsed)

    # ------------------------------------------------------------------
    # Stage 7 — Console summary
    # ------------------------------------------------------------------
    print_export_summary(results, elapsed)

    return results


# ===========================================================================
# Stage 5 — Reporting and persistence
# ===========================================================================

def print_export_summary(
    results: dict[str, ExportResult],
    elapsed: float,
) -> None:
    """
    Print a formatted summary table of all export outcomes.

    Columns: Format | Status | Size (MB) | Duration | Output path

    Args:
        results: Dict returned by :func:`export_all`.
        elapsed: Total wall-clock seconds for the full export run.
    """
    h = int(elapsed // 3600)
    m = int((elapsed % 3600) // 60)
    s = int(elapsed % 60)
    elapsed_str = (
        f"{h}h {m}m {s}s" if h > 0
        else f"{m}m {s}s" if m > 0
        else f"{s}s"
    )

    print_section("Export Summary")

    # Column widths
    w_fmt    = 12
    w_status = 8
    w_size   = 10
    w_dur    = 10

    header = (
        f"  {'Format':<{w_fmt}}"
        f"{'Status':<{w_status}}"
        f"{'Size MB':>{w_size}}"
        f"{'Time (s)':>{w_dur}}"
        f"  Output"
    )
    print_separator("-", 78)
    print(header)
    print_separator("-", 78)

    succeeded = 0
    failed = 0

    for fmt, result in results.items():
        status = "OK" if result.success else "FAILED"
        size   = f"{result.size_mb:.1f}" if result.success else "—"
        dur    = f"{result.elapsed:.1f}"
        out    = result.path.name if result.path else result.error[:48]

        print(
            f"  {fmt.upper():<{w_fmt}}"
            f"{status:<{w_status}}"
            f"{size:>{w_size}}"
            f"{dur:>{w_dur}}"
            f"  {out}"
        )

        if result.success:
            succeeded += 1
        else:
            failed += 1

    print_separator("-", 78)
    print(
        f"  {succeeded} succeeded  |  {failed} failed  |  "
        f"Total time: {elapsed_str}"
    )
    print_separator()

    if failed > 0:
        logger.warning(
            "%d format(s) failed — check messages above for details.", failed
        )
    else:
        logger.info("All %d export(s) completed successfully.", succeeded)


def save_export_manifest(
    results: dict[str, ExportResult],
    experiment_name: str,
    weights_path: Path,
    elapsed: float,
) -> Path:
    """
    Write a JSON manifest of the export run to the experiment export dir.

    The manifest records which formats were attempted, whether each
    succeeded, output paths, file sizes, and timing.  It serves as a
    machine-readable receipt that other pipeline stages can query.

    Args:
        results:         Dict returned by :func:`export_all`.
        experiment_name: Experiment identifier string.
        weights_path:    Source weights file path.
        elapsed:         Total wall-clock seconds for the export run.

    Returns:
        Path to the written manifest JSON file.
    """
    dest_dir = EXPORTS_DIR / experiment_name
    create_directory(dest_dir)
    manifest_path = dest_dir / "export_manifest.json"

    h = int(elapsed // 3600)
    m_val = int((elapsed % 3600) // 60)
    s = int(elapsed % 60)
    duration_human = (
        f"{h}h {m_val}m {s}s" if h > 0
        else f"{m_val}m {s}s" if m_val > 0
        else f"{s}s"
    )

    formats_data: list[dict[str, Any]] = []
    for fmt, result in results.items():
        formats_data.append({
            "format":   fmt,
            "enabled":  result.enabled,
            "success":  result.success,
            "path":     str(result.path) if result.path else None,
            "size_mb":  result.size_mb,
            "elapsed_s": result.elapsed,
            "error":    result.error if not result.success else None,
        })

    manifest: dict[str, Any] = {
        "experiment":      experiment_name,
        "exported_at_utc": datetime.now(tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "source_weights":  str(weights_path),
        "export_dir":      str(EXPORTS_DIR / experiment_name),
        "formats":         formats_data,
        "timing": {
            "total_seconds": elapsed,
            "duration_human": duration_human,
        },
    }

    with manifest_path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    logger.info("Export manifest written → %s", manifest_path)
    return manifest_path


# ===========================================================================
# CLI entry-point
# ===========================================================================

def _parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for standalone export runs.

    Returns:
        Parsed :class:`argparse.Namespace` with attributes:
            ``weights`` — Path to the ``.pt`` source model.
            ``config``  — Path to training_config.yaml.
    """
    parser = argparse.ArgumentParser(
        description="InfraGuard AI — YOLOv8 model export",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Export production weights using default config\n"
            "  python training/export.py\n"
            "\n"
            "  # Export a specific checkpoint\n"
            "  python training/export.py"
            " --weights weights/archive/best_20260726_191422.pt\n"
            "\n"
            "  # Use a custom config path\n"
            "  python training/export.py"
            " --config configs/training_config.yaml\n"
        ),
    )
    parser.add_argument(
        "--weights",
        type=Path,
        default=PRODUCTION_WEIGHTS,
        help=(
            "Path to the .pt model weights to export. "
            f"Default: {PRODUCTION_WEIGHTS}"
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=TRAINING_CONFIG,
        help=(
            "Path to training_config.yaml. "
            f"Default: {TRAINING_CONFIG}"
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    output = export_all(
        weights_path=args.weights,
        config_path=args.config,
    )
    # Exit 1 if nothing was exported or every enabled format failed
    any_success = any(r.success for r in output.values()) if output else False
    sys.exit(0 if any_success else 1)
