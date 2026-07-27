"""
InfraGuard AI
Computer Vision — Dataset Download

Purpose:
    Download the RDD2022 dataset from Kaggle and extract it into
    data/raw/ ready for inspection and filtering.

Input:
    Kaggle credentials — either ~/.kaggle/kaggle.json
    or environment variables KAGGLE_USERNAME and KAGGLE_KEY.

Output:
    data/raw/<split>/images/   — original road images
    data/raw/<split>/labels/   — original YOLO annotations (5 classes)

Responsibilities:
    1. Authenticate with the Kaggle API.
    2. Download the dataset archive (skip if already present).
    3. Extract the archive (skip if already extracted).
    4. Optionally delete the zip after extraction (controlled by KEEP_ZIP).
    5. Never modify any extracted file.

Execution:
    # From ai/computer_vision/
    python -m preprocessing.download_dataset
"""

import logging
import zipfile
from pathlib import Path

from configs.config import (
    DATASET_NAME,
    KAGGLE_DATASET_SLUG,
    RAW_DATASET,
    SPLITS,
)
from utils.utils import create_directory, get_logger, print_section, print_separator

# ---------------------------------------------------------------------------
# Module-level configuration
# ---------------------------------------------------------------------------

# Set to True to keep the downloaded .zip after extraction.
# Useful when disk space allows and you may need to re-extract.
KEEP_ZIP: bool = False

logger: logging.Logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _kaggle_api():
    """
    Import and authenticate the Kaggle API client.

    Returns:
        Authenticated ``KaggleApi`` instance.

    Raises:
        ImportError: If the ``kaggle`` package is not installed.
        OSError:     If credentials cannot be located.
    """
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "The 'kaggle' package is not installed.\n"
            "Run:  pip install kaggle"
        ) from exc

    api = KaggleApi()
    api.authenticate()
    return api


def _is_extracted(destination: Path) -> bool:
    """
    Return ``True`` if the dataset has already been extracted into *destination*.

    Extraction is considered complete when at least one recognised split
    directory (train / val / test) exists inside *destination* or one
    level deeper (handles Kaggle sub-folder extraction).

    Args:
        destination: The configured ``RAW_DATASET`` path.

    Returns:
        Boolean — ``True`` means skip extraction.
    """
    # Check destination directly
    if any((destination / s).exists() for s in SPLITS):
        return True
    # Check one level down (Kaggle sometimes wraps in a sub-folder)
    if destination.exists():
        for child in destination.iterdir():
            if child.is_dir() and any((child / s).exists() for s in SPLITS):
                return True
    return False


def _extract_zip(zip_path: Path, destination: Path) -> None:
    """
    Extract *zip_path* into *destination* with progress logging.

    Args:
        zip_path:    Path to the downloaded ``.zip`` archive.
        destination: Target extraction directory.

    Raises:
        zipfile.BadZipFile: If the archive is corrupt.
    """
    logger.info("Extracting archive …")
    logger.info("  Source      : %s  (%.1f MB)",
                zip_path.name, zip_path.stat().st_size / 1_048_576)
    logger.info("  Destination : %s", destination)

    with zipfile.ZipFile(zip_path, "r") as zf:
        member_count = len(zf.namelist())
        logger.info("  Entries     : %d files", member_count)
        zf.extractall(destination)

    logger.info("Extraction complete.")


def _remove_zip(zip_path: Path) -> None:
    """
    Delete *zip_path* to reclaim disk space.

    Failure is logged as a warning but does not abort the pipeline.

    Args:
        zip_path: Path to the archive file to remove.
    """
    try:
        zip_path.unlink()
        logger.info("Archive removed to free disk space: %s", zip_path.name)
    except OSError as exc:
        logger.warning("Could not remove archive '%s': %s", zip_path.name, exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def download_dataset(
    destination: Path = RAW_DATASET,
    *,
    slug: str = KAGGLE_DATASET_SLUG,
    keep_zip: bool = KEEP_ZIP,
    skip_if_exists: bool = True,
) -> Path:
    """
    Download and extract the RDD2022 dataset from Kaggle.

    The function is idempotent — it checks for existing extracted data
    and an existing archive before triggering any network activity.

    Skip logic:
        1. If split directories already exist in *destination* → skip entirely.
        2. If a ``.zip`` archive already exists in *destination* → skip download,
           go straight to extraction.
        3. If extraction has already been done → skip extraction too.

    Args:
        destination:    Directory that will receive the extracted dataset.
                        Defaults to ``RAW_DATASET`` from ``config.py``.
        slug:           Kaggle dataset identifier (``owner/dataset-name``).
                        Defaults to ``KAGGLE_DATASET_SLUG`` from ``config.py``.
        keep_zip:       Keep the ``.zip`` archive after extraction.
                        Defaults to the module-level ``KEEP_ZIP`` flag.
        skip_if_exists: Skip the entire operation if the dataset appears to
                        be already extracted.  Defaults to ``True``.

    Returns:
        Path to *destination*.

    Raises:
        ImportError:      If the ``kaggle`` package is not installed.
        OSError:          If credentials are missing or a filesystem error occurs.
        FileNotFoundError: If the download succeeds but no archive is found.
        zipfile.BadZipFile: If the downloaded archive is corrupt.
    """
    print_section(f"Downloading {DATASET_NAME} Dataset")

    create_directory(destination)

    # ------------------------------------------------------------------
    # Step 1 — skip entirely if already extracted
    # ------------------------------------------------------------------
    if skip_if_exists and _is_extracted(destination):
        logger.info("Dataset already extracted at '%s' — skipping download.", destination)
        logger.info("Set skip_if_exists=False to force a fresh download.")
        return destination

    # ------------------------------------------------------------------
    # Step 2 — check for an existing zip (e.g. partial previous run)
    # ------------------------------------------------------------------
    existing_zips = list(destination.glob("*.zip"))
    if existing_zips:
        zip_path = existing_zips[0]
        logger.info(
            "Found existing archive '%s' (%.1f MB) — skipping download.",
            zip_path.name, zip_path.stat().st_size / 1_048_576,
        )
    else:
        # ------------------------------------------------------------------
        # Step 3 — authenticate and download
        # ------------------------------------------------------------------
        print_separator("-", 60)
        logger.info("Authenticating with Kaggle API …")
        api = _kaggle_api()
        logger.info("Authentication successful.")

        logger.info("Downloading dataset '%s' …", slug)
        logger.info("Destination: %s", destination)
        print_separator("-", 60)

        api.dataset_download_files(
            dataset=slug,
            path=str(destination),
            unzip=False,    # manual extraction gives better logging
            quiet=False,
            force=False,
        )

        zip_files = list(destination.glob("*.zip"))
        if not zip_files:
            raise FileNotFoundError(
                f"Download appeared to succeed but no .zip found in '{destination}'.\n"
                "Check your Kaggle credentials and available disk space."
            )
        zip_path = zip_files[0]
        logger.info(
            "Download complete: '%s'  (%.1f MB)",
            zip_path.name, zip_path.stat().st_size / 1_048_576,
        )

    # ------------------------------------------------------------------
    # Step 4 — extract (skip if already done)
    # ------------------------------------------------------------------
    if _is_extracted(destination):
        logger.info("Dataset already extracted — skipping extraction.")
    else:
        _extract_zip(zip_path, destination)

    # ------------------------------------------------------------------
    # Step 5 — optionally remove the archive
    # ------------------------------------------------------------------
    if not keep_zip and zip_path.exists():
        _remove_zip(zip_path)
    elif keep_zip:
        logger.info("Keeping archive (KEEP_ZIP=True): %s", zip_path.name)

    # ------------------------------------------------------------------
    # Done
    # ------------------------------------------------------------------
    print_separator("-", 60)
    logger.info("Dataset ready at: %s", destination)
    print_separator()

    return destination


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    download_dataset()
