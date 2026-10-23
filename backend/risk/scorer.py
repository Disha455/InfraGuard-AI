"""
InfraGuard AI — Risk Scorer

Pure Python scoring engine for the CV-based inspection risk assessment.

This module has NO dependencies on FastAPI, Ultralytics, or Flutter.
It accepts plain Python data structures and returns a
:class:`~backend.schemas.risk.RiskAssessmentOut` instance.

The scorer is intentionally stateless — every call to
:meth:`RiskScorer.score_inspection` is independent and thread-safe.

Scoring formula (per detection)
---------------------------------
    detection_score =
        CLASS_SEVERITY_WEIGHT[class_name]        # damage-priority weight
        × confidence                              # model trust multiplier
        × (1 + AREA_BOOST × normalised_area)     # optional size amplifier
        × 100                                     # scale to [0, 100]
    clamped to [0, 100]

Confidence is treated as a MODEL TRUST MULTIPLIER, not as physical
damage severity.  A 0.45-confidence pothole is not a "less severe"
pothole; it is a pothole the model is 45% confident it found.

Aggregation (across all detections in one inspection)
-------------------------------------------------------
    base_score    = max(detection_scores)
    breadth_bonus = (N - 1) × BREADTH_FACTOR × base_score
    final_score   = min(base_score + breadth_bonus, 100)

Risk level bucketing
---------------------
    score ∈ [0, 20]     → LOW
    score ∈ (20, 45]    → MODERATE
    score ∈ (45, 70]    → HIGH
    score ∈ (70, 100]   → CRITICAL

All threshold values and weights are defined in constants.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from backend.risk.constants import (
    AREA_BOOST,
    BREADTH_FACTOR,
    CLASS_SEVERITY_WEIGHTS,
    DEFAULT_SEVERITY_WEIGHT,
    HIGH_MAX,
    LOW_MAX,
    METHODOLOGY_NOTE,
    MODERATE_MAX,
    RECOMMENDATIONS,
)
from backend.schemas.risk import DetectionRiskOut, RiskAssessmentOut, RiskLevel

logger = logging.getLogger("infraguard.risk.scorer")


# ---------------------------------------------------------------------------
# Internal detection input type
# ---------------------------------------------------------------------------

@dataclass
class _DetectionInput:
    """
    Minimal detection data consumed by the scorer.

    The scorer never imports Ultralytics or inference-layer types.
    The service layer extracts these fields from its own Detection objects
    and passes them here.
    """

    class_name:   str
    confidence:   float
    bbox_x1:      float
    bbox_y1:      float
    bbox_x2:      float
    bbox_y2:      float


# ---------------------------------------------------------------------------
# Image dimension type alias
# ---------------------------------------------------------------------------

# (height, width) in pixels — matches Ultralytics orig_shape convention.
# None means dimensions are not available for this request.
ImageDimensions = tuple[int, int] | None


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

class RiskScorer:
    """
    Stateless CV-based inspection risk scoring engine.

    No constructor arguments are required.  All configuration is read
    from :mod:`backend.risk.constants` at call time so constants can be
    patched in tests without subclassing.

    Usage::

        scorer = RiskScorer()
        result = scorer.score_inspection(detections, image_dims)
    """

    # ------------------------------------------------------------------
    # Public entry-point
    # ------------------------------------------------------------------

    def score_inspection(
        self,
        detections: list[_DetectionInput],
        image_dims: ImageDimensions = None,
    ) -> RiskAssessmentOut:
        """
        Score a complete inspection run from its detection list.

        Args:
            detections:  List of :class:`_DetectionInput` instances, one
                         per YOLO detection.  Empty list → score 0, LOW.
            image_dims:  ``(height, width)`` in pixels as returned by
                         Ultralytics ``result.orig_shape``.  Pass ``None``
                         when unavailable — normalised_area will be 0.0
                         for all detections and the area boost is skipped
                         without failing the prediction.

        Returns:
            Fully populated :class:`~backend.schemas.risk.RiskAssessmentOut`.
        """
        # ── Zero-detection fast path ──────────────────────────────────────
        if not detections:
            return self._zero_detection_result()

        # ── Per-detection scores ──────────────────────────────────────────
        img_area = self._safe_image_area(image_dims)
        detection_risks: list[DetectionRiskOut] = []

        for det in detections:
            dr = self._score_detection(det, img_area)
            detection_risks.append(dr)

        # Sort by individual score descending — dominant damage is first
        detection_risks.sort(key=lambda d: d.detection_score, reverse=True)

        # ── Aggregation ───────────────────────────────────────────────────
        anchor_score  = detection_risks[0].detection_score
        n_extra        = len(detection_risks) - 1
        breadth_bonus  = round(n_extra * BREADTH_FACTOR * anchor_score, 4)
        final_score    = round(min(anchor_score + breadth_bonus, 100.0), 4)

        # ── Risk level and recommendation ────────────────────────────────
        level          = self._level_for_score(final_score)
        recommendation = RECOMMENDATIONS[level.value]
        dominant       = detection_risks[0].class_name

        score_breakdown: dict[str, float] = {
            "anchor_score":    round(anchor_score, 4),
            "breadth_bonus":   round(breadth_bonus, 4),
            "final_score":     round(final_score, 4),
            "detection_count": float(len(detections)),
        }

        logger.debug(
            "score_inspection: detections=%d  anchor=%.2f  breadth=%.2f  "
            "final=%.2f  level=%s",
            len(detections), anchor_score, breadth_bonus, final_score, level.value,
        )

        return RiskAssessmentOut(
            score=final_score,
            level=level,
            detection_risks=detection_risks,
            dominant_damage=dominant,
            score_breakdown=score_breakdown,
            recommendation=recommendation,
            methodology_note=METHODOLOGY_NOTE,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _zero_detection_result() -> RiskAssessmentOut:
        """Return the canonical result when no detections are present."""
        return RiskAssessmentOut(
            score=0.0,
            level=RiskLevel.LOW,
            detection_risks=[],
            dominant_damage=None,
            score_breakdown={
                "anchor_score":    0.0,
                "breadth_bonus":   0.0,
                "final_score":     0.0,
                "detection_count": 0.0,
            },
            recommendation=RECOMMENDATIONS["NO_DAMAGE"],
            methodology_note=METHODOLOGY_NOTE,
        )

    @staticmethod
    def _safe_image_area(image_dims: ImageDimensions) -> float | None:
        """
        Return the image area in square pixels, or ``None`` when dimensions
        are absent or invalid.

        Args:
            image_dims: ``(height, width)`` tuple or ``None``.

        Returns:
            Positive float, or ``None`` when the area cannot be computed.
        """
        if image_dims is None:
            return None

        try:
            h, w = image_dims
            area = float(h) * float(w)
        except (TypeError, ValueError):
            logger.warning(
                "RiskScorer: invalid image_dims %r — area boost disabled.",
                image_dims,
            )
            return None

        if area <= 0.0:
            logger.warning(
                "RiskScorer: non-positive image area %.1f — area boost disabled.",
                area,
            )
            return None

        return area

    @staticmethod
    def _normalised_area(
        det: _DetectionInput,
        img_area: float | None,
    ) -> float:
        """
        Compute bounding-box area normalised by image area.

        Returns ``0.0`` (no area boost) when:
          - *img_area* is ``None`` (dimensions unavailable / invalid)
          - the bounding box produces a non-positive area
          - any arithmetic error occurs

        The result is clamped to ``[0.0, 1.0]``.

        Args:
            det:      Detection input containing bbox coordinates.
            img_area: Pre-computed image area, or ``None``.

        Returns:
            Normalised area in ``[0.0, 1.0]``.
        """
        if img_area is None:
            return 0.0

        try:
            bbox_area = (det.bbox_x2 - det.bbox_x1) * (det.bbox_y2 - det.bbox_y1)
        except (TypeError, ValueError):
            return 0.0

        if bbox_area <= 0.0:
            return 0.0

        raw = bbox_area / img_area
        # Clamp: a detection should never exceed full-image coverage, but
        # floating-point rounding can produce values infinitesimally above 1.
        return max(0.0, min(raw, 1.0))

    @classmethod
    def _score_detection(
        cls,
        det: _DetectionInput,
        img_area: float | None,
    ) -> DetectionRiskOut:
        """
        Compute the risk contribution of a single detection.

        Formula::

            detection_score =
                severity_weight
                × confidence             ← MODEL TRUST, not physical severity
                × (1 + AREA_BOOST × normalised_area)
                × 100
            clamped to [0, 100]

        Args:
            det:      Detection input.
            img_area: Pre-computed image area (or ``None``).

        Returns:
            Populated :class:`~backend.schemas.risk.DetectionRiskOut`.
        """
        severity_weight = CLASS_SEVERITY_WEIGHTS.get(
            det.class_name, DEFAULT_SEVERITY_WEIGHT
        )
        norm_area       = cls._normalised_area(det, img_area)

        raw_score = (
            severity_weight
            * det.confidence
            * (1.0 + AREA_BOOST * norm_area)
            * 100.0
        )
        # Clamp: by construction the max is 1.0 × 1.0 × (1 + 0.5×1.0) × 100 = 150,
        # but we cap at 100 to keep the per-detection score on the same 0–100 scale.
        clamped_score = round(max(0.0, min(raw_score, 100.0)), 4)

        return DetectionRiskOut(
            class_name=det.class_name,
            severity_weight=severity_weight,
            confidence=round(det.confidence, 6),
            normalised_area=round(norm_area, 6),
            detection_score=clamped_score,
        )

    @staticmethod
    def _level_for_score(score: float) -> RiskLevel:
        """
        Map a continuous score to a :class:`~backend.schemas.risk.RiskLevel`.

        Boundary rule: ``score > threshold`` advances to the next level,
        so a score of exactly ``LOW_MAX`` (20.0) stays LOW.

        Args:
            score: Final inspection score in ``[0, 100]``.

        Returns:
            The corresponding :class:`~backend.schemas.risk.RiskLevel`.
        """
        if score > HIGH_MAX:
            return RiskLevel.CRITICAL
        if score > MODERATE_MAX:
            return RiskLevel.HIGH
        if score > LOW_MAX:
            return RiskLevel.MODERATE
        return RiskLevel.LOW


# ---------------------------------------------------------------------------
# Public re-export of the input type so callers can annotate correctly
# ---------------------------------------------------------------------------

DetectionInput = _DetectionInput

__all__ = ["RiskScorer", "DetectionInput", "ImageDimensions"]
