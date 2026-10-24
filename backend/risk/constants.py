"""
InfraGuard AI — Risk Assessment Constants

Single source of truth for every named constant used by the CV-based
inspection risk scoring engine.  No scoring logic lives here.

IMPORTANT — EPISTEMOLOGICAL NOTE
----------------------------------
The values in this file are HEURISTIC ENGINEERING JUDGEMENTS, not
measured probabilities of structural failure.  They encode inspection
priority order based on how each damage type affects road serviceability
and how quickly it typically progresses without intervention, as
described in the RDD2022 dataset documentation.

They are deliberately separate from the scorer so they can be revised
by domain experts without reading Python logic.  A comment explaining
the rationale accompanies every value.

Future factors (traffic density, weather, road age, etc.) should be
added as new named constants in this file, not as inline literals
in scorer.py.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Class severity weights
#
# Scale: 0.0 (no concern) → 1.0 (highest inspection priority).
#
# Rationale for each class:
#
#   pothole (1.00)
#       Discrete surface depression.  Immediate safety risk to vehicles
#       and cyclists; high liability exposure.  Assigned the maximum
#       inspection priority weight.
#
#   alligator_crack (0.85)
#       Interconnected fatigue-crack network indicating base-layer or
#       sub-grade failure.  Rapid progression under traffic loading;
#       high risk of pothole formation.
#
#   transverse_crack (0.65)
#       Crack oriented perpendicular to the travel direction.  Structural
#       crack often caused by thermal cycling; medium-to-high progression
#       risk depending on width and depth (not measurable from imagery).
#
#   longitudinal_crack (0.50)
#       Crack oriented parallel to the travel direction.  Typically
#       slower to progress than transverse cracks; medium priority.
#
# Unlisted class names fall back to a DEFAULT weight so unknown detections
# do not silently produce a zero score.
# ---------------------------------------------------------------------------

CLASS_SEVERITY_WEIGHTS: dict[str, float] = {
    "pothole":            1.00,
    "alligator_crack":    0.85,
    "transverse_crack":   0.65,
    "longitudinal_crack": 0.50,
}

# Fallback weight applied to any class name not in CLASS_SEVERITY_WEIGHTS.
# Set to the median of the known values so an unknown class is not treated
# as either negligible or maximally urgent.
DEFAULT_SEVERITY_WEIGHT: float = 0.65


# ---------------------------------------------------------------------------
# Bounding-box area boost
#
# A normalised bounding-box area of 1.0 (detection covering the entire
# image) multiplies the base score by (1 + AREA_BOOST).
# A normalised area of 0.0 contributes no boost.
#
# Rationale: a larger detected region suggests greater spatial extent of
# the damage within the captured frame, which is weakly correlated with
# physical size.  The relationship is noisy (camera height, zoom, and
# distance all vary) so the boost is kept small (0.5 max amplification)
# and requires valid image dimensions to apply.
# ---------------------------------------------------------------------------

AREA_BOOST: float = 0.5


# ---------------------------------------------------------------------------
# Breadth factor for multi-detection aggregation
#
# Each additional detection beyond the first adds
#   BREADTH_FACTOR × base_score
# to the total, capped at 100.
#
# Rationale: multiple independent damage instances in one inspection frame
# indicate a broader maintenance problem than a single instance.  Using a
# fractional factor rather than simple summation prevents the count from
# dominating the severity signal.
# ---------------------------------------------------------------------------

BREADTH_FACTOR: float = 0.08


# ---------------------------------------------------------------------------
# Risk level score thresholds
#
# Thresholds are LOWER BOUNDS (inclusive) for each level except LOW,
# which applies to everything below MODERATE_THRESHOLD.
#
# Boundary rule: score > threshold → next level.
# Example: score == 20 → LOW; score == 20.001 → MODERATE.
#
# Expressed as a sorted list of (lower_bound_exclusive, RiskLevel) pairs
# so the scorer can iterate without embedding level names as strings.
# ---------------------------------------------------------------------------

# These are imported as plain floats so callers don't need to import
# the RiskLevel enum from the schema just to read a threshold.
LOW_MAX:      float = 20.0   # score ∈ [0, 20]   → LOW
MODERATE_MAX: float = 45.0   # score ∈ (20, 45]  → MODERATE
HIGH_MAX:     float = 70.0   # score ∈ (45, 70]  → HIGH
                              # score ∈ (70, 100] → CRITICAL


# ---------------------------------------------------------------------------
# Recommendation strings
#
# Keyed by risk level name (string) so scorer.py does not need to
# import the enum to look up text.
#
# Wording describes MAINTENANCE PRIORITY, not guaranteed structural
# failure.  Automatic road closure is never recommended solely on the
# basis of this CV-only score.
# ---------------------------------------------------------------------------

RECOMMENDATIONS: dict[str, str] = {
    "LOW": (
        "Continue routine monitoring and reassess during the "
        "next scheduled inspection."
    ),
    "MODERATE": (
        "Schedule a maintenance review within 30–60 days and "
        "document the detected damage."
    ),
    "HIGH": (
        "Prioritize a field inspection and schedule maintenance "
        "within 7–14 days."
    ),
    "CRITICAL": (
        "Prioritize immediate field inspection and escalate for "
        "urgent maintenance assessment."
    ),
    "NO_DAMAGE": (
        "No damage detected above the confidence threshold.  "
        "Continue routine monitoring."
    ),
}


# ---------------------------------------------------------------------------
# Methodology note
#
# Emitted verbatim in every RiskAssessmentOut response so downstream
# consumers (UI, reports, APIs) always carry the scoring limitation.
# ---------------------------------------------------------------------------

METHODOLOGY_NOTE: str = (
    "CV-based inspection risk assessment v1.  This heuristic score uses "
    "detected damage type, model confidence, and normalised bounding-box "
    "coverage.  It is intended for inspection prioritisation and does not "
    "represent a probability of infrastructure failure or a structural "
    "engineering assessment."
)
