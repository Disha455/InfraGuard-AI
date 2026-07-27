"""
InfraGuard AI
Computer Vision — Dataset Inspection

Purpose:
    Produce a human-readable report of the raw RDD2022 dataset so the
    team can confirm the download is intact before any filtering is applied.

Input:
    data/raw/<split>/images/   — original images
    data/raw/<split>/labels/   — original YOLO annotations (5 classes)

Output:
    Console report only — nothing is written to disk.
    Returns a dict of per-split statistics for programmatic use.

Responsibilities:
    1. Locate the dataset root inside data/raw/ (handles Kaggle sub-folder).
    2. Count images and labels per split.
    3. Compute class frequency distribution per split and overall.
    4. Print sample annotation lines for a visual sanity-check.
    5. Never modify any file.

Execution:
    # From ai/computer_vision/
    python -m preprocessing.inspect_dataset
"""

import logging
from collections import Counter
from pathlib import Path
from typing import Optional

from configs.config import CLASS_NAMES, RAW_DATASET, SPLITS
from utils.utils import (
    get_logger,
    list_images,
    list_labels,
    parse_yolo_label,
    print_section,
    print_separator,
)

# ---------------------------------------------------------------------------
# Module logger
# ---------------------------------------------------------------------------

logger: logging.Logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _class_label(class_id: int, names: list[str]) -> str:
    """Return a display string for *class_id*."""
    try:
        return f"{class_id} ({names[class_id]})"
    except IndexError:
        return f"{class_id} (unknown)"


def _inspect_split(
    split_dir: Path,
    class_names: list[str],
    sample_count: int = 3,
) -> dict:
    """
    Collect statistics for a single dataset split directory.

    Args:
        split_dir:    Path to e.g. ``data/raw/rdd2022/train/``.
        class_names:  Ordered list of class name strings.
        sample_count: Number of sample label lines to include in the report.

    Returns:
        Dictionary with keys:
            ``split``, ``images_dir``, ``labels_dir``,
            ``image_count``, ``label_count``,
            ``class_counter``, ``samples``, ``errors``.
    """
    images_dir = split_dir / "images"
    labels_dir = split_dir / "labels"

    images = list_images(images_dir)
    labels = list_labels(labels_dir)

    class_counter: Counter[int] = Counter()
    errors: list[str] = []
    samples: list[str] = []

    for label_path in labels:
        try:
            rows = parse_yolo_label(label_path)
            for row in rows:
                class_counter[int(row[0])] += 1
        except ValueError as exc:
            errors.append(str(exc))

    # Collect a few raw annotation lines as sample output
    for label_path in labels[:sample_count]:
        try:
            with label_path.open("r", encoding="utf-8") as fh:
                first_line = fh.readline().strip()
            samples.append(f"  {label_path.name}: {first_line}")
        except OSError:
            pass

    return {
        "split": split_dir.name,
        "images_dir": images_dir,
        "labels_dir": labels_dir,
        "image_count": len(images),
        "label_count": len(labels),
        "class_counter": class_counter,
        "samples": samples,
        "errors": errors,
    }


def _find_dataset_root(raw_dir: Path) -> Optional[Path]:
    """
    Locate the actual dataset root inside *raw_dir*.

    Kaggle may extract into a sub-folder (e.g. ``raw/rdd2022/``).
    This function checks whether *raw_dir* itself or any immediate
    child contains a recognised split directory.

    Args:
        raw_dir: The configured RAW_DATASET path.

    Returns:
        Resolved dataset root path, or ``None`` if not found.
    """
    # Check raw_dir directly first
    if any((raw_dir / s).exists() for s in SPLITS):
        return raw_dir

    # Check one level down
    for candidate in sorted(raw_dir.iterdir()):
        if candidate.is_dir() and any((candidate / s).exists() for s in SPLITS):
            return candidate

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def inspect_dataset(
    raw_dir: Path = RAW_DATASET,
    class_names: list[str] = CLASS_NAMES,
) -> dict:
    """
    Inspect the raw RDD2022 dataset directory and print a summary report.

    Args:
        raw_dir:      Root directory containing the extracted dataset.
                      Defaults to the path defined in ``config.py``.
        class_names:  Ordered list of class name strings used to label
                      class IDs in the report.

    Returns:
        Dictionary keyed by split name (``"train"``, ``"val"``, ``"test"``)
        containing the per-split statistics dictionaries produced by
        :func:`_inspect_split`.  Useful for programmatic access to counts.

    Raises:
        FileNotFoundError: If *raw_dir* does not exist or no split directories
                           are found inside it.
    """
    print_section("Dataset Inspection Report")

    if not raw_dir.exists():
        raise FileNotFoundError(
            f"Raw dataset directory not found: '{raw_dir}'\n"
            "Run download_dataset.py first."
        )

    dataset_root = _find_dataset_root(raw_dir)
    if dataset_root is None:
        raise FileNotFoundError(
            f"Could not find train/val/test splits inside '{raw_dir}'.\n"
            "Expected folder layout:  <root>/<split>/images/  and  <root>/<split>/labels/"
        )

    logger.info("Dataset root resolved to: %s", dataset_root)

    # ------------------------------------------------------------------
    # Per-split stats
    # ------------------------------------------------------------------
    results: dict[str, dict] = {}
    overall_classes: Counter[int] = Counter()

    for split_name in SPLITS:
        split_dir = dataset_root / split_name
        if not split_dir.exists():
            logger.warning("Split directory not found: '%s' — skipping.", split_dir)
            continue

        stats = _inspect_split(split_dir, class_names)
        results[split_name] = stats
        overall_classes.update(stats["class_counter"])

        # Print split summary
        print_separator("-", 60)
        print(f"  Split : {split_name.upper()}")
        print_separator("-", 60)
        print(f"  Images dir  : {stats['images_dir']}")
        print(f"  Labels dir  : {stats['labels_dir']}")
        print(f"  Image count : {stats['image_count']:,}")
        print(f"  Label count : {stats['label_count']:,}")

        if stats["class_counter"]:
            print("\n  Class Distribution:")
            for cid, count in sorted(stats["class_counter"].items()):
                print(f"    {_class_label(cid, class_names):<35} {count:>8,}")
        else:
            print("\n  No annotations found in this split.")

        if stats["samples"]:
            print("\n  Sample Annotations:")
            for sample in stats["samples"]:
                print(sample)

        if stats["errors"]:
            logger.warning(
                "%d parse error(s) in split '%s'.",
                len(stats["errors"]), split_name,
            )
            for err in stats["errors"][:5]:  # cap output
                logger.warning("  %s", err)

        print()

    # ------------------------------------------------------------------
    # Overall summary
    # ------------------------------------------------------------------
    print_section("Overall Class Distribution (All Splits)")

    total_annotations = sum(overall_classes.values())
    print(f"  Total annotations: {total_annotations:,}\n")

    for cid, count in sorted(overall_classes.items()):
        pct = (count / total_annotations * 100) if total_annotations else 0.0
        print(f"  {_class_label(cid, class_names):<35} {count:>8,}  ({pct:5.1f}%)")

    print()
    logger.info("Inspection complete.")

    return results


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    inspect_dataset()
