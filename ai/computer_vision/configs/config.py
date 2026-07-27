"""
InfraGuard AI
Computer Vision — Configuration

Central source of truth for all project paths and dataset constants.
Every preprocessing, training, and inference script imports from here.
No paths are hardcoded anywhere else in the codebase.

Directory layout produced by the preprocessing pipeline:

    data/
    ├── raw/                  ← extracted Kaggle dataset (images + original labels)
    │   ├── train/
    │   │   ├── images/
    │   │   └── labels/
    │   ├── val/
    │   └── test/
    ├── processed/            ← filtered & remapped labels only (no image copies)
    │   ├── train/labels/
    │   ├── val/labels/
    │   ├── test/labels/
    │   └── dataset.yaml      ← Ultralytics training config (images → raw/, labels → processed/)
    └── (no yolo/ subdirectory — images are never duplicated)
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Project Root
# ---------------------------------------------------------------------------

PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------------------
# AI Module Root
# ---------------------------------------------------------------------------

AI_ROOT: Path = PROJECT_ROOT / "ai" / "computer_vision"

# ---------------------------------------------------------------------------
# Dataset Directories
# ---------------------------------------------------------------------------

DATASET_ROOT: Path = AI_ROOT / "data"

# Raw extracted dataset — never modified after download
RAW_DATASET: Path = DATASET_ROOT / "raw"

# Filtered + remapped labels (labels only — images stay in raw/)
PROCESSED_DATASET: Path = DATASET_ROOT / "processed"

# Ultralytics dataset.yaml — written into processed/ by filter_classes.py
DATASET_YAML: Path = PROCESSED_DATASET / "dataset.yaml"

# ---------------------------------------------------------------------------
# Model & Output Directories
# ---------------------------------------------------------------------------

# Ultralytics writes all run artefacts here (weights, results.csv, TensorBoard
# events).  train.py passes this as project=MODELS_DIR to model.train().
MODELS_DIR: Path = AI_ROOT / "models"

# Human-authored experiment notes (Markdown).  One sub-folder per named run.
# Keeps decisions and observations alongside the artefacts that produced them.
EXPERIMENTS_DIR: Path = AI_ROOT / "experiments"

# Trained model weights — stable production path consumed by FastAPI.
# train.py copies models/<name>/weights/best.pt here after every run.
# inference/predictor.py loads from this path.  Both sides reference this
# constant so the path is defined exactly once.
WEIGHTS_DIR: Path = AI_ROOT / "weights"
PRODUCTION_WEIGHTS: Path = WEIGHTS_DIR / "best.pt"

# Archived previous best weights — train.py moves the old PRODUCTION_WEIGHTS
# here before promoting a new model, so no trained model is ever silently lost.
WEIGHTS_ARCHIVE_DIR: Path = WEIGHTS_DIR / "archive"

EXPORTS_DIR: Path = AI_ROOT / "exports"

# Log sub-directories consumed by callbacks.py and train.py
LOGS_DIR: Path = AI_ROOT / "logs"
LOGS_TENSORBOARD_DIR: Path = LOGS_DIR / "tensorboard"
LOGS_TRAINING_DIR: Path = LOGS_DIR / "training"
LOGS_RUNS_DIR: Path = LOGS_DIR / "runs"

# ---------------------------------------------------------------------------
# Training Configuration
# ---------------------------------------------------------------------------

# Path to the YAML file that drives every training run.
# train.py reads this; changing experiments means editing this file, not code.
TRAINING_CONFIG: Path = AI_ROOT / "configs" / "training_config.yaml"

# ---------------------------------------------------------------------------
# Dataset Metadata
# ---------------------------------------------------------------------------

DATASET_NAME: str = "RDD2022"

# Kaggle dataset identifier used by download_dataset.py
KAGGLE_DATASET_SLUG: str = "aliabdelmenam/rdd-2022"

# Ordered class names after filtering.
# Index matches the remapped class ID written into processed/labels/.
#   0 → pothole
#   1 → longitudinal_crack
#   2 → transverse_crack
#   3 → alligator_crack
CLASS_NAMES: list[str] = [
    "pothole",
    "longitudinal_crack",
    "transverse_crack",
    "alligator_crack",
]

# Original RDD2022 class IDs that are removed during filtering
REMOVED_CLASS_IDS: frozenset[int] = frozenset({3})  # other_corruption

# Mapping: original RDD2022 class ID → InfraGuard class ID
# Must stay consistent with CLASS_NAMES order above
CLASS_REMAP: dict[int, int] = {
    4: 0,  # Pothole            → pothole
    0: 1,  # longitudinal_crack → longitudinal_crack
    1: 2,  # transverse_crack   → transverse_crack
    2: 3,  # alligator_crack    → alligator_crack
}

# Split names — matches Kaggle RDD2022 folder structure
SPLITS: tuple[str, ...] = ("train", "val", "test")
