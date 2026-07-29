"""
InfraGuard AI
Computer Vision — Class Filter, Label Remap & Dataset Layout

Purpose:
    Remove the "other_corruption" class from RDD2022 labels, remap the
    remaining class IDs to the contiguous 0-3 scheme used by InfraGuard AI,
    and write a standard YOLO dataset layout that Ultralytics can consume
    directly without any path tricks.

Input:
    data/raw/<split>/images/   — original images (never modified)
    data/raw/<split>/labels/   — original RDD2022 YOLO annotations

Output:
    data/processed/
    ├── train/
    │   ├── images/   ← symlinks to raw images (copy fallback on Windows)
    │   └── labels/   ← filtered + remapped annotations
    ├── val/
    │   ├── images/
    │   └── labels/
    ├── test/
    │   ├── images/
    │   └── labels/
    └── dataset.yaml  ← Ultralytics config using relative paths

Why this layout?
    Ultralytics resolves label paths from image paths by replacing the
    ``images`` path component with ``labels``.  Both directories must
    therefore share the same split parent.  A dataset.yaml that points
    images at raw/ but labels at processed/ causes Ultralytics to silently
    load the *original* unfiltered labels, making the filter step invisible
    to training.  Placing symlinked images alongside filtered labels in
    processed/ fixes this with zero extra disk usage on Linux / Colab.

Responsibilities:
    1. Remove annotations whose class ID is in REMOVED_CLASS_IDS.
    2. Remap surviving class IDs via CLASS_REMAP.
    3. Skip images whose label has no remaining valid annotations.
    4. Write filtered labels to   processed/<split>/labels/.
    5. Link (or copy) images to   processed/<split>/images/.
    6. Write dataset.yaml with relative split paths so the file is
       portable regardless of where the project is mounted.

Execution:
    # From ai/computer_vision/
    python -m preprocessing.filter_classes
"""

import logging
import os
import shutil
from pathlib import Path

import yaml  # PyYAML — already in requirements.txt

from configs.config import (
    CLASS_NAMES,
    CLASS_REMAP,
    DATASET_YAML,
    PROCESSED_DATASET,
    RAW_DATASET,
    REMOVED_CLASS_IDS,
    SPLITS,
)
from utils.utils import (
    create_directory,
    get_logger,
    list_images,
    parse_yolo_label,
    print_section,
    print_separator,
)

# ---------------------------------------------------------------------------
# Module logger
# ---------------------------------------------------------------------------

logger: logging.Logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper: directory creation
# ---------------------------------------------------------------------------

def ensure_dir(path: Path) -> None:
    """
    Create *path* and any missing parents.  No-op if it already exists.

    Args:
        path: Directory to create.
    """
    create_directory(path)


# ---------------------------------------------------------------------------
# Helper: image linking
# ---------------------------------------------------------------------------

def create_image_link(src: Path, dst: Path) -> None:
    """
    Create a filesystem link from *src* to *dst*.

    Attempts ``os.symlink`` first (zero extra disk usage on Linux / Colab).
    Falls back to ``shutil.copy2`` when symlinks are not supported (Windows
    without elevated privileges, some network file systems).

    If *dst* already exists the call is a no-op — the link/copy was already
    created by a previous run.

    Args:
        src: Absolute path to the source image in raw/.
        dst: Desired path in processed/<split>/images/.
    """
    if dst.exists() or dst.is_symlink():
        return  # idempotent

    ensure_dir(dst.parent)

    try:
        os.symlink(src.resolve(), dst)
    except (OSError, NotImplementedError):
        shutil.copy2(src, dst)


# ---------------------------------------------------------------------------
# Helper: label filtering + remapping
# ---------------------------------------------------------------------------

def process_label(src_label: Path, dst_label: Path) -> tuple[int, int]:
    """
    Filter and remap one YOLO ``.txt`` label file.

    Reads *src_label*, drops every row whose class ID is in
    ``REMOVED_CLASS_IDS``, remaps the remaining IDs through ``CLASS_REMAP``,
    and writes the result to *dst_label*.

    An image whose every annotation is dropped produces an empty *dst_label*
    file.  The caller (:func:`process_split`) checks for this and skips the
    corresponding image link.

    Args:
        src_label: Source annotation file (original RDD2022 label).
        dst_label: Destination annotation file (processed label).

    Returns:
        ``(kept, dropped)`` — counts of annotation rows kept and dropped.

    Raises:
        ValueError: Propagated from :func:`parse_yolo_label` on malformed input.
        OSError:    If *dst_label* cannot be written.
    """
    rows = parse_yolo_label(src_label)
    kept_lines: list[str] = []
    dropped = 0

    for row in rows:
        class_id = int(row[0])

        if class_id in REMOVED_CLASS_IDS:
            dropped += 1
            continue

        if class_id not in CLASS_REMAP:
            logger.warning(
                "Unexpected class ID %d in '%s' — skipping row.",
                class_id,
                src_label,
            )
            dropped += 1
            continue

        remapped_id = CLASS_REMAP[class_id]
        coord_str = " ".join(f"{v:.6f}" for v in row[1:])
        kept_lines.append(f"{remapped_id} {coord_str}")

    ensure_dir(dst_label.parent)
    with dst_label.open("w", encoding="utf-8") as fh:
        if kept_lines:
            fh.write("\n".join(kept_lines) + "\n")

    return len(kept_lines), dropped


# ---------------------------------------------------------------------------
# Helper: process one split
# ---------------------------------------------------------------------------

def process_split(
    split_name: str,
    src_images_dir: Path,
    src_labels_dir: Path,
    dst_split_dir: Path,
) -> tuple[int, int]:
    """
    Process all images and labels for one dataset split.

    For each image in *src_images_dir*:

    1. Locate the corresponding source label (same stem, ``.txt`` extension).
    2. If the source label does not exist, skip the image silently.
    3. Filter and remap the label via :func:`process_label`.
    4. If the filtered label is empty (all annotations removed), skip.
    5. Write the filtered label to ``dst_split_dir/labels/``.
    6. Link (or copy) the image to ``dst_split_dir/images/``.

    Args:
        split_name:     Human-readable split identifier for log messages.
        src_images_dir: ``raw/<split>/images/`` directory.
        src_labels_dir: ``raw/<split>/labels/`` directory.
        dst_split_dir:  ``processed/<split>/`` destination root.

    Returns:
        ``(processed, skipped)`` — counts of image-label pairs handled
        and skipped (no label or empty after filtering).
    """
    dst_images_dir = dst_split_dir / "images"
    dst_labels_dir = dst_split_dir / "labels"
    ensure_dir(dst_images_dir)
    ensure_dir(dst_labels_dir)

    images = list_images(src_images_dir)
    processed = 0
    skipped = 0

    for src_image in images:
        src_label = src_labels_dir / (src_image.stem + ".txt")

        if not src_label.exists():
            skipped += 1
            continue

        dst_label = dst_labels_dir / (src_image.stem + ".txt")

        try:
            kept, _ = process_label(src_label, dst_label)
        except (ValueError, OSError) as exc:
            logger.error("Failed to process label '%s': %s", src_label, exc)
            skipped += 1
            continue

        if kept == 0:
            # Remove the empty label file so processed/ stays clean
            if dst_label.exists():
                dst_label.unlink()
            skipped += 1
            continue

        create_image_link(src_image, dst_images_dir / src_image.name)
        processed += 1

    return processed, skipped


# ---------------------------------------------------------------------------
# Helper: dataset.yaml
# ---------------------------------------------------------------------------

def write_dataset_yaml(
    processed_dir: Path,
    class_names: list[str],
    yaml_path: Path,
) -> None:
    """
    Write the Ultralytics ``dataset.yaml`` using relative split paths.

    With ``path`` set to the absolute *processed_dir* and the three split
    keys set to relative strings (``train/images``, etc.), Ultralytics
    resolves both images and labels correctly.  Labels are found by
    replacing ``images`` with ``labels`` in each resolved image path —
    which works because :func:`process_split` writes labels alongside images
    inside the same ``processed/<split>/`` parent.

    The file is portable: moving the entire ``processed/`` directory
    requires updating only the ``path`` key.

    Args:
        processed_dir: Absolute path to the processed dataset root.
        class_names:   Ordered list of class name strings.
        yaml_path:     Destination path for the YAML file.
    """
    ensure_dir(yaml_path.parent)

    data: dict = {
        "path":  str(processed_dir.resolve()),
        "train": "train/images",
        "val":   "val/images",
        "test":  "test/images",
        "nc":    len(class_names),
        "names": class_names,
    }

    with yaml_path.open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh, default_flow_style=False, sort_keys=False)

    logger.info("dataset.yaml written → %s", yaml_path)


# ---------------------------------------------------------------------------
# Raw dataset root resolution
# ---------------------------------------------------------------------------

def _resolve_raw_root(raw_dir: Path) -> Path:
    """
    Locate the actual split root inside *raw_dir*.

    Kaggle sometimes extracts the archive into a sub-folder (e.g.
    ``raw/RDD_SPLIT/``).  Checks *raw_dir* itself first, then one level
    deeper.

    Args:
        raw_dir: Configured ``RAW_DATASET`` path.

    Returns:
        Resolved dataset root that contains train/val/test.

    Raises:
        FileNotFoundError: If no split directories are found.
    """
    if any((raw_dir / s).exists() for s in SPLITS):
        return raw_dir

    for candidate in sorted(raw_dir.iterdir()):
        if candidate.is_dir() and any(
            (candidate / s).exists() for s in SPLITS
        ):
            return candidate

    raise FileNotFoundError(
        f"Cannot find split directories {SPLITS} inside '{raw_dir}'.\n"
        "Run download_dataset.py first."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def filter_classes(
    raw_dir: Path = RAW_DATASET,
    processed_dir: Path = PROCESSED_DATASET,
    yaml_path: Path = DATASET_YAML,
    *,
    skip_if_exists: bool = True,
) -> Path:
    """
    Filter RDD2022 labels, remap class IDs, and build a YOLO dataset layout.

    Produces a ``processed/`` directory that is immediately usable with::

        model.train(data="data/processed/dataset.yaml")

    For each split (train / val / test) the function:

    * Reads every image in ``raw_dir/<split>/images/``.
    * Reads the corresponding label from ``raw_dir/<split>/labels/``.
    * Drops annotations in :data:`REMOVED_CLASS_IDS` (``other_corruption``).
    * Remaps surviving class IDs via :data:`CLASS_REMAP`.
    * Writes the filtered label to ``processed_dir/<split>/labels/``.
    * Symlinks (or copies) the image to ``processed_dir/<split>/images/``.
    * Skips images with no remaining valid annotations.

    Finishes by writing ``dataset.yaml`` with relative split paths so
    Ultralytics resolves both images and labels from the same split parent.

    Args:
        raw_dir:         Source directory containing the extracted dataset.
                         Defaults to ``RAW_DATASET`` from ``config.py``.
        processed_dir:   Destination for the complete YOLO layout.
                         Defaults to ``PROCESSED_DATASET`` from ``config.py``.
        yaml_path:       Path where ``dataset.yaml`` will be written.
                         Defaults to ``DATASET_YAML`` from ``config.py``.
        skip_if_exists:  When ``True`` and *processed_dir* already contains
                         ``.txt`` files, the entire operation is skipped.
                         Set to ``False`` to force a full re-run.

    Returns:
        Path to *processed_dir*.

    Raises:
        FileNotFoundError: If *raw_dir* does not exist or contains no splits.
    """
    print_section("Filter Classes & Build YOLO Dataset")

    # ------------------------------------------------------------------
    # Guard — raw dataset must exist
    # ------------------------------------------------------------------
    if not raw_dir.exists():
        raise FileNotFoundError(
            f"Raw dataset not found: '{raw_dir}'\n"
            "Run download_dataset.py first."
        )

    # ------------------------------------------------------------------
    # Guard — skip if already processed
    # ------------------------------------------------------------------
    if skip_if_exists and processed_dir.exists() and any(processed_dir.rglob("*.txt")):
        logger.info(
            "Processed dataset already exists in '%s' — skipping.",
            processed_dir,
        )
        logger.info("Set skip_if_exists=False to force re-processing.")
        return processed_dir

    # ------------------------------------------------------------------
    # Resolve actual dataset root (handles Kaggle sub-folder extraction)
    # ------------------------------------------------------------------
    dataset_root = _resolve_raw_root(raw_dir)

    ensure_dir(processed_dir)

    logger.info("Raw dataset root : %s", dataset_root)
    logger.info("Processed dir    : %s", processed_dir)
    logger.info("Removing IDs     : %s  (other_corruption)", sorted(REMOVED_CLASS_IDS))
    logger.info("Remap table      : %s", CLASS_REMAP)
    logger.info("Output classes   : %s", CLASS_NAMES)

    total_processed = 0
    total_skipped = 0

    # ------------------------------------------------------------------
    # Process each split
    # ------------------------------------------------------------------
    for split_name in SPLITS:
        split_src = dataset_root / split_name
        if not split_src.exists():
            logger.warning("Split '%s' not found in raw/ — skipping.", split_name)
            continue

        src_images_dir = split_src / "images"
        src_labels_dir = split_src / "labels"
        dst_split_dir  = processed_dir / split_name

        if not src_images_dir.exists():
            logger.warning(
                "images/ directory missing for split '%s' — skipping.", split_name
            )
            continue

        logger.info("Processing %s ...", split_name)

        n_processed, n_skipped = process_split(
            split_name=split_name,
            src_images_dir=src_images_dir,
            src_labels_dir=src_labels_dir,
            dst_split_dir=dst_split_dir,
        )

        total_processed += n_processed
        total_skipped   += n_skipped

        print_separator("-", 60)
        print(f"  Split            : {split_name}")
        print(f"  Images processed : {n_processed:,}")
        print(f"  Images skipped   : {n_skipped:,}  (no label or empty after filter)")

    # ------------------------------------------------------------------
    # Write dataset.yaml
    # ------------------------------------------------------------------
    write_dataset_yaml(processed_dir, CLASS_NAMES, yaml_path)

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    print_separator()
    print(f"  Total processed  : {total_processed:,} image-label pairs")
    print(f"  Total skipped    : {total_skipped:,}")
    print(f"  Processed dir    : {processed_dir}")
    print(f"  dataset.yaml     : {yaml_path}")
    print_separator()

    logger.info("filter_classes complete.")
    return processed_dir


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    filter_classes()
