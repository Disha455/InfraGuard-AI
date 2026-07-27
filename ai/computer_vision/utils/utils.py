"""
InfraGuard AI
Computer Vision — Shared Utilities

Provides helpers used across the entire preprocessing pipeline:
  - Directory creation
  - Logging configuration
  - File enumeration
  - YOLO label parsing and validation
  - Console formatting
"""

import logging
import sys
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Console / Separator Helpers
# ---------------------------------------------------------------------------

def print_separator(char: str = "=", width: int = 60) -> None:
    """Print a visual separator line to stdout."""
    print(char * width)


def print_section(title: str, char: str = "=", width: int = 60) -> None:
    """Print a titled section separator."""
    print_separator(char, width)
    print(f"  {title}")
    print_separator(char, width)


# ---------------------------------------------------------------------------
# Directory Helpers
# ---------------------------------------------------------------------------

def create_directory(path: Path) -> None:
    """
    Create *path* (and any missing parents) if it does not already exist.

    Args:
        path: Target directory path.
    """
    path.mkdir(parents=True, exist_ok=True)


def ensure_directories(*paths: Path) -> None:
    """
    Create multiple directories in one call.

    Args:
        *paths: Any number of Path objects to create.
    """
    for path in paths:
        create_directory(path)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def get_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """
    Return a named logger with a consistent format.

    The logger writes to stdout by default.  If *log_file* is supplied a
    FileHandler is added in addition to the StreamHandler so that every
    message is persisted to disk.

    Args:
        name:     Logger name — typically ``__name__`` of the calling module.
        level:    Logging level (default: INFO).
        log_file: Optional path to a ``.log`` file.

    Returns:
        Configured :class:`logging.Logger` instance.
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers when the function is called multiple
    # times in the same process (e.g. during interactive notebook sessions).
    if logger.handlers:
        return logger

    logger.setLevel(level)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Stream handler — always present
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)
    logger.addHandler(stream_handler)

    # Optional file handler
    if log_file is not None:
        create_directory(log_file.parent)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger


# ---------------------------------------------------------------------------
# File Enumeration
# ---------------------------------------------------------------------------

IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
)

LABEL_EXTENSION: str = ".txt"


def count_files(directory: Path, extensions: frozenset[str]) -> int:
    """
    Recursively count files whose suffix is in *extensions*.

    Args:
        directory:  Root directory to search.
        extensions: Set of lowercase file extensions including the dot,
                    e.g. ``{".jpg", ".png"}``.

    Returns:
        Integer count of matching files.
    """
    if not directory.exists():
        return 0
    return sum(
        1 for f in directory.rglob("*")
        if f.is_file() and f.suffix.lower() in extensions
    )


def count_images(directory: Path) -> int:
    """Return the number of image files inside *directory* (recursive)."""
    return count_files(directory, IMAGE_EXTENSIONS)


def count_labels(directory: Path) -> int:
    """Return the number of ``.txt`` label files inside *directory* (recursive)."""
    return count_files(directory, frozenset({LABEL_EXTENSION}))


def list_images(directory: Path) -> list[Path]:
    """
    Return a sorted list of all image paths under *directory*.

    Args:
        directory: Root directory to search.

    Returns:
        Sorted list of :class:`pathlib.Path` objects.
    """
    if not directory.exists():
        return []
    return sorted(
        f for f in directory.rglob("*")
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )


def list_labels(directory: Path) -> list[Path]:
    """
    Return a sorted list of all ``.txt`` label paths under *directory*.

    Args:
        directory: Root directory to search.

    Returns:
        Sorted list of :class:`pathlib.Path` objects.
    """
    if not directory.exists():
        return []
    return sorted(
        f for f in directory.rglob("*")
        if f.is_file() and f.suffix.lower() == LABEL_EXTENSION
    )


# ---------------------------------------------------------------------------
# YOLO Label Helpers
# ---------------------------------------------------------------------------

def parse_yolo_label(label_path: Path) -> list[list[float]]:
    """
    Parse a YOLO-format ``.txt`` annotation file.

    Each line has the form::

        <class_id> <cx> <cy> <w> <h>

    Blank lines and lines starting with ``#`` are silently ignored.

    Args:
        label_path: Path to the annotation file.

    Returns:
        List of rows, where each row is
        ``[class_id, cx, cy, w, h]`` as floats.

    Raises:
        ValueError: If a line cannot be parsed as five space-separated numbers.
    """
    rows: list[list[float]] = []
    with label_path.open("r", encoding="utf-8") as fh:
        for line_no, raw_line in enumerate(fh, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) != 5:
                raise ValueError(
                    f"{label_path}:{line_no} — expected 5 fields, got {len(parts)}: '{line}'"
                )
            rows.append([float(p) for p in parts])
    return rows


def label_contains_class(label_path: Path, class_id: int) -> bool:
    """
    Return ``True`` if *label_path* contains at least one annotation for
    the given *class_id*.

    Args:
        label_path: Path to a YOLO ``.txt`` annotation file.
        class_id:   Integer class index to search for.

    Returns:
        Boolean indicating presence of the class.
    """
    try:
        rows = parse_yolo_label(label_path)
    except (ValueError, OSError):
        return False
    return any(int(row[0]) == class_id for row in rows)


def get_class_ids(label_path: Path) -> set[int]:
    """
    Return the set of unique class IDs present in *label_path*.

    Args:
        label_path: Path to a YOLO ``.txt`` annotation file.

    Returns:
        Set of integer class IDs.  Empty set if the file is empty or
        cannot be read.
    """
    try:
        rows = parse_yolo_label(label_path)
    except (ValueError, OSError):
        return set()
    return {int(row[0]) for row in rows}


def find_label_for_image(image_path: Path) -> Optional[Path]:
    """
    Derive the expected label path from an image path.

    Assumes the standard YOLO layout where ``images/`` and ``labels/``
    are sibling directories::

        split/images/img.jpg  →  split/labels/img.txt

    Args:
        image_path: Path to an image file.

    Returns:
        Expected :class:`pathlib.Path` for the label file, or ``None``
        if the image is not inside an ``images/`` directory.
    """
    parts = image_path.parts
    try:
        images_idx = len(parts) - 1 - parts[::-1].index("images")
    except ValueError:
        return None
    label_parts = parts[:images_idx] + ("labels",) + parts[images_idx + 1 :]
    label_path = Path(*label_parts).with_suffix(LABEL_EXTENSION)
    return label_path
