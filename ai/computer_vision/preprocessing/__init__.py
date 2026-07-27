"""
InfraGuard AI
Computer Vision — Preprocessing Package

Exposes the public entry-point function from each pipeline stage so
callers can import directly from the package:

    from preprocessing import download_dataset
    from preprocessing import inspect_dataset
    from preprocessing import filter_classes
    from preprocessing import verify_dataset

Pipeline order:
    1. download_dataset   — fetch RDD2022 from Kaggle → data/raw/
    2. inspect_dataset    — read-only report on raw data
    3. filter_classes     — remove other_corruption, remap IDs → data/processed/
    4. verify_dataset     — integrity checks on processed labels

Use prepare_dataset.py to run the full pipeline in one command.
"""

from preprocessing.download_dataset import download_dataset
from preprocessing.inspect_dataset import inspect_dataset
from preprocessing.filter_classes import filter_classes
from preprocessing.verify_dataset import verify_dataset

__all__ = [
    "download_dataset",
    "inspect_dataset",
    "filter_classes",
    "verify_dataset",
]
