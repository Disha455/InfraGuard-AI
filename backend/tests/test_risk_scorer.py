"""
InfraGuard AI — Risk Scorer Tests

Focused unit tests for :class:`backend.risk.scorer.RiskScorer`.

All expected values are derived from the constants in
``backend.risk.constants`` and cross-verified by hand.  No magic
numbers appear in the assertions; every computation is annotated with
the formula step it is testing.

Test organisation:
    TestZeroDetections          — empty input fast-path
    TestSingleDetection         — one detection, various classes / confs
    TestMultipleDetections      — aggregation, dominant damage, sorting
    TestNormalisedArea          — bbox area with and without image dims
    TestImageDimensionEdgeCases — None, zero, invalid dims
    TestScoreClamping           — raw > 100 must be clamped to 100
    TestRiskLevelBoundaries     — exact boundary values for all four levels
    TestDominantDamage          — highest-score detection is dominant
"""

import pytest

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
from backend.risk.scorer import DetectionInput, RiskScorer
from backend.schemas.risk import RiskLevel

# ---------------------------------------------------------------------------
# Shared scorer instance — stateless, safe to reuse across all tests
# ---------------------------------------------------------------------------

scorer = RiskScorer()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _det(
    class_name: str = "pothole",
    confidence: float = 0.80,
    x1: float = 0.0,
    y1: float = 0.0,
    x2: float = 100.0,
    y2: float = 100.0,
) -> DetectionInput:
    """Convenience factory for DetectionInput with sensible defaults."""
    return DetectionInput(
        class_name=class_name,
        confidence=confidence,
        bbox_x1=x1,
        bbox_y1=y1,
        bbox_x2=x2,
        bbox_y2=y2,
    )


# ===========================================================================
# TestZeroDetections
# ===========================================================================

class TestZeroDetections:
    """Empty detection list must produce score=0, level=LOW, no dominant."""

    def test_score_is_zero(self):
        result = scorer.score_inspection([])
        assert result.score == 0.0

    def test_level_is_low(self):
        result = scorer.score_inspection([])
        assert result.level == RiskLevel.LOW

    def test_dominant_damage_is_none(self):
        result = scorer.score_inspection([])
        assert result.dominant_damage is None

    def test_detection_risks_is_empty(self):
        result = scorer.score_inspection([])
        assert result.detection_risks == []

    def test_score_breakdown_all_zeros(self):
        result = scorer.score_inspection([])
        bd = result.score_breakdown
        assert bd["anchor_score"] == 0.0
        assert bd["breadth_bonus"] == 0.0
        assert bd["final_score"] == 0.0
        assert bd["detection_count"] == 0.0

    def test_recommendation_is_no_damage(self):
        result = scorer.score_inspection([])
        assert result.recommendation == RECOMMENDATIONS["NO_DAMAGE"]

    def test_methodology_note_present(self):
        result = scorer.score_inspection([])
        assert result.methodology_note == METHODOLOGY_NOTE

    def test_image_dims_ignored_for_zero_detections(self):
        """Passing image dims with zero detections must still return 0/LOW."""
        result = scorer.score_inspection([], image_dims=(640, 480))
        assert result.score == 0.0
        assert result.level == RiskLevel.LOW


# ===========================================================================
# TestSingleDetection
# ===========================================================================

class TestSingleDetection:
    """One detection — verifies per-detection formula and aggregation."""

    def test_pothole_high_confidence_no_dims(self):
        """
        pothole, conf=0.80, no dims → no area boost.

        Formula: 1.0 × 0.80 × (1 + 0.5×0) × 100 = 80.0
        anchor=80.0, breadth_bonus=0, final=80.0, level=CRITICAL
        """
        result = scorer.score_inspection([_det("pothole", 0.80)])

        assert result.score == pytest.approx(80.0, abs=1e-3)
        assert result.level == RiskLevel.CRITICAL
        assert result.dominant_damage == "pothole"
        assert len(result.detection_risks) == 1

        dr = result.detection_risks[0]
        assert dr.class_name == "pothole"
        assert dr.severity_weight == CLASS_SEVERITY_WEIGHTS["pothole"]
        assert dr.confidence == pytest.approx(0.80, abs=1e-6)
        assert dr.normalised_area == 0.0
        assert dr.detection_score == pytest.approx(80.0, abs=1e-3)

    def test_longitudinal_crack_moderate_confidence(self):
        """
        longitudinal_crack, conf=0.50, no dims.

        Formula: 0.50 × 0.50 × 1.0 × 100 = 25.0 → MODERATE
        """
        result = scorer.score_inspection([_det("longitudinal_crack", 0.50)])

        assert result.score == pytest.approx(25.0, abs=1e-3)
        assert result.level == RiskLevel.MODERATE

    def test_alligator_crack_score(self):
        """
        alligator_crack, conf=0.70, no dims.

        Formula: 0.85 × 0.70 × 1.0 × 100 = 59.5 → HIGH
        """
        expected = CLASS_SEVERITY_WEIGHTS["alligator_crack"] * 0.70 * 1.0 * 100
        result = scorer.score_inspection([_det("alligator_crack", 0.70)])

        assert result.score == pytest.approx(expected, abs=1e-3)
        assert result.level == RiskLevel.HIGH

    def test_transverse_crack_score(self):
        """
        transverse_crack, conf=0.60, no dims.

        Formula: 0.65 × 0.60 × 1.0 × 100 = 39.0 → MODERATE
        """
        expected = CLASS_SEVERITY_WEIGHTS["transverse_crack"] * 0.60 * 1.0 * 100
        result = scorer.score_inspection([_det("transverse_crack", 0.60)])

        assert result.score == pytest.approx(expected, abs=1e-3)
        assert result.level == RiskLevel.MODERATE

    def test_single_detection_breadth_bonus_is_zero(self):
        """One detection → n_extra=0 → breadth_bonus=0."""
        result = scorer.score_inspection([_det("pothole", 0.80)])
        assert result.score_breakdown["breadth_bonus"] == 0.0

    def test_single_detection_score_breakdown_keys(self):
        result = scorer.score_inspection([_det("pothole", 0.50)])
        bd = result.score_breakdown
        assert set(bd.keys()) == {"anchor_score", "breadth_bonus", "final_score", "detection_count"}
        assert bd["detection_count"] == 1.0

    def test_unknown_class_uses_default_weight(self):
        """
        An unlisted class name must use DEFAULT_SEVERITY_WEIGHT, not 0.

        Formula: 0.65 × 0.80 × 1.0 × 100 = 52.0 → HIGH
        """
        expected = DEFAULT_SEVERITY_WEIGHT * 0.80 * 1.0 * 100
        result = scorer.score_inspection([_det("road_collapse", 0.80)])

        assert result.score == pytest.approx(expected, abs=1e-3)
        assert result.detection_risks[0].severity_weight == DEFAULT_SEVERITY_WEIGHT


# ===========================================================================
# TestMultipleDetections
# ===========================================================================

class TestMultipleDetections:
    """Aggregation logic, breadth bonus, and cap at 100."""

    def test_two_detections_breadth_bonus(self):
        """
        pothole(0.80)=80.0 + alligator_crack(0.90)=76.5

        anchor=80.0, n_extra=1
        breadth_bonus = 1 × 0.08 × 80.0 = 6.4
        final = min(80.0 + 6.4, 100) = 86.4 → CRITICAL
        """
        detections = [
            _det("pothole", 0.80),
            _det("alligator_crack", 0.90),
        ]
        result = scorer.score_inspection(detections)

        alligator_score = CLASS_SEVERITY_WEIGHTS["alligator_crack"] * 0.90 * 100
        anchor = 80.0          # pothole wins
        bonus  = 1 * BREADTH_FACTOR * anchor
        expected_final = anchor + bonus

        assert result.score == pytest.approx(expected_final, abs=1e-3)
        assert result.level == RiskLevel.CRITICAL
        assert result.score_breakdown["anchor_score"] == pytest.approx(anchor, abs=1e-3)
        assert result.score_breakdown["breadth_bonus"] == pytest.approx(bonus, abs=1e-3)

    def test_three_detections_aggregation(self):
        """
        Three longitudinal_cracks at conf=0.60 each.

        each_score = 0.50 × 0.60 × 100 = 30.0
        anchor=30.0, n_extra=2
        bonus = 2 × 0.08 × 30.0 = 4.8
        final = 34.8 → MODERATE
        """
        detections = [_det("longitudinal_crack", 0.60)] * 3
        result = scorer.score_inspection(detections)

        anchor = CLASS_SEVERITY_WEIGHTS["longitudinal_crack"] * 0.60 * 100
        bonus  = 2 * BREADTH_FACTOR * anchor
        expected = anchor + bonus

        assert result.score == pytest.approx(expected, abs=1e-3)
        assert result.level == RiskLevel.MODERATE
        assert result.score_breakdown["detection_count"] == 3.0

    def test_breadth_bonus_capped_at_100(self):
        """
        20 potholes at conf=0.90 — breadth bonus overflows 100.

        anchor=90.0, n_extra=19
        raw_final = 90 + 19×0.08×90 = 90 + 136.8 = 226.8 → capped at 100.0
        """
        detections = [_det("pothole", 0.90)] * 20
        result = scorer.score_inspection(detections)

        assert result.score == pytest.approx(100.0, abs=1e-3)
        assert result.level == RiskLevel.CRITICAL

    def test_detection_risks_sorted_descending(self):
        """detection_risks must be sorted by detection_score descending."""
        detections = [
            _det("longitudinal_crack", 0.60),  # 0.50×0.60×100=30
            _det("pothole",            0.80),  # 1.00×0.80×100=80
            _det("transverse_crack",   0.40),  # 0.65×0.40×100=26
        ]
        result = scorer.score_inspection(detections)
        scores = [dr.detection_score for dr in result.detection_risks]
        assert scores == sorted(scores, reverse=True)

    def test_dominant_damage_is_highest_score(self):
        """dominant_damage must be the class with the highest detection_score."""
        detections = [
            _det("longitudinal_crack", 0.99),  # 0.50×0.99×100=49.5
            _det("pothole",            0.51),  # 1.00×0.51×100=51.0  ← wins
        ]
        result = scorer.score_inspection(detections)
        assert result.dominant_damage == "pothole"


# ===========================================================================
# TestNormalisedArea
# ===========================================================================

class TestNormalisedArea:
    """Bbox area calculation with valid image dimensions."""

    def test_area_boost_with_half_image_coverage(self):
        """
        Image: h=480, w=640 → area=307200
        BBox:  x1=0,y1=0, x2=320,y2=240 → area=76800
        norm_area = 76800/307200 = 0.25

        pothole, conf=0.80:
        raw = 1.0 × 0.80 × (1 + 0.5×0.25) × 100 = 0.80 × 1.125 × 100 = 90.0
        """
        det = DetectionInput(
            class_name="pothole", confidence=0.80,
            bbox_x1=0.0, bbox_y1=0.0, bbox_x2=320.0, bbox_y2=240.0,
        )
        result = scorer.score_inspection([det], image_dims=(480, 640))

        expected_norm = 76800.0 / 307200.0   # = 0.25
        expected_score = 1.0 * 0.80 * (1.0 + AREA_BOOST * expected_norm) * 100.0

        assert result.detection_risks[0].normalised_area == pytest.approx(expected_norm, abs=1e-6)
        assert result.detection_risks[0].detection_score == pytest.approx(expected_score, abs=1e-3)

    def test_full_image_coverage_clamped_to_1(self):
        """
        BBox exactly matches image dimensions → norm_area = 1.0
        (or infinitesimally above due to float, clamped to 1.0).

        pothole, conf=1.0:
        raw = 1.0 × 1.0 × (1 + 0.5×1.0) × 100 = 150.0 → clamped to 100.0
        """
        det = DetectionInput(
            class_name="pothole", confidence=1.0,
            bbox_x1=0.0, bbox_y1=0.0, bbox_x2=640.0, bbox_y2=480.0,
        )
        result = scorer.score_inspection([det], image_dims=(480, 640))

        assert result.detection_risks[0].normalised_area == pytest.approx(1.0, abs=1e-6)
        assert result.detection_risks[0].detection_score == pytest.approx(100.0, abs=1e-3)

    def test_no_dims_produces_zero_norm_area(self):
        """Without image dimensions, norm_area must be exactly 0.0."""
        result = scorer.score_inspection([_det("pothole", 0.80)], image_dims=None)
        assert result.detection_risks[0].normalised_area == 0.0

    def test_area_boost_increases_score_vs_no_dims(self):
        """Score with valid dims must be >= score without dims."""
        det = DetectionInput(
            class_name="pothole", confidence=0.80,
            bbox_x1=0.0, bbox_y1=0.0, bbox_x2=300.0, bbox_y2=200.0,
        )
        score_with_dims    = scorer.score_inspection([det], image_dims=(480, 640)).score
        score_without_dims = scorer.score_inspection([det], image_dims=None).score
        assert score_with_dims >= score_without_dims


# ===========================================================================
# TestImageDimensionEdgeCases
# ===========================================================================

class TestImageDimensionEdgeCases:
    """Malformed or missing image dimensions must not fail the prediction."""

    def test_none_dims_no_crash(self):
        result = scorer.score_inspection([_det()], image_dims=None)
        assert result.score > 0.0

    def test_zero_height_dims_treated_as_unavailable(self):
        """(0, 640) → area=0 → no area boost → same as None."""
        result_bad  = scorer.score_inspection([_det("pothole", 0.80)], image_dims=(0, 640))
        result_none = scorer.score_inspection([_det("pothole", 0.80)], image_dims=None)
        assert result_bad.score == pytest.approx(result_none.score, abs=1e-6)

    def test_zero_width_dims_treated_as_unavailable(self):
        result_bad  = scorer.score_inspection([_det("pothole", 0.80)], image_dims=(480, 0))
        result_none = scorer.score_inspection([_det("pothole", 0.80)], image_dims=None)
        assert result_bad.score == pytest.approx(result_none.score, abs=1e-6)

    def test_negative_dims_treated_as_unavailable(self):
        """Negative dimensions produce non-positive area → no boost."""
        result_bad  = scorer.score_inspection([_det("pothole", 0.80)], image_dims=(-480, 640))
        result_none = scorer.score_inspection([_det("pothole", 0.80)], image_dims=None)
        assert result_bad.score == pytest.approx(result_none.score, abs=1e-6)

    def test_zero_bbox_area_no_boost(self):
        """Degenerate bbox (x1==x2) produces zero area → norm_area=0."""
        det = DetectionInput(
            class_name="pothole", confidence=0.80,
            bbox_x1=100.0, bbox_y1=100.0, bbox_x2=100.0, bbox_y2=200.0,
        )
        result = scorer.score_inspection([det], image_dims=(480, 640))
        assert result.detection_risks[0].normalised_area == 0.0


# ===========================================================================
# TestScoreClamping
# ===========================================================================

class TestScoreClamping:
    """Per-detection score must never exceed 100, even at maximum inputs."""

    def test_max_inputs_per_detection_clamped(self):
        """
        sw=1.0, conf=1.0, norm_area=1.0
        raw = 1.0 × 1.0 × (1 + 0.5×1.0) × 100 = 150.0 → must be clamped to 100.0
        """
        det = DetectionInput(
            class_name="pothole", confidence=1.0,
            bbox_x1=0.0, bbox_y1=0.0, bbox_x2=640.0, bbox_y2=480.0,
        )
        result = scorer.score_inspection([det], image_dims=(480, 640))
        assert result.detection_risks[0].detection_score <= 100.0
        assert result.detection_risks[0].detection_score == pytest.approx(100.0, abs=1e-3)

    def test_final_score_never_exceeds_100(self):
        """Many detections with max inputs must not produce final > 100."""
        detections = [
            DetectionInput(
                class_name="pothole", confidence=1.0,
                bbox_x1=0.0, bbox_y1=0.0, bbox_x2=640.0, bbox_y2=480.0,
            )
        ] * 50
        result = scorer.score_inspection(detections, image_dims=(480, 640))
        assert result.score <= 100.0

    def test_score_and_breakdown_agree(self):
        """result.score must equal score_breakdown['final_score']."""
        result = scorer.score_inspection([_det("pothole", 0.75)])
        assert result.score == pytest.approx(result.score_breakdown["final_score"], abs=1e-9)


# ===========================================================================
# TestRiskLevelBoundaries
# ===========================================================================

class TestRiskLevelBoundaries:
    """
    Boundary rule: score > threshold → higher level.
    score == threshold stays at the lower level.
    """

    # ── LOW / MODERATE boundary (LOW_MAX = 20.0) ─────────────────────────

    def test_score_at_low_max_is_low(self):
        """score == 20.0 exactly → LOW (not MODERATE)."""
        # sw=1.0, conf=0.20, no dims → raw=20.0
        result = scorer.score_inspection([_det("pothole", 0.20)])
        assert result.score == pytest.approx(20.0, abs=1e-6)
        assert result.level == RiskLevel.LOW

    def test_score_just_above_low_max_is_moderate(self):
        """score infinitesimally > 20 → MODERATE."""
        # sw=1.0, conf=0.201 → raw=20.1
        result = scorer.score_inspection([_det("pothole", 0.201)])
        assert result.score > LOW_MAX
        assert result.level == RiskLevel.MODERATE

    # ── MODERATE / HIGH boundary (MODERATE_MAX = 45.0) ───────────────────

    def test_score_at_moderate_max_is_moderate(self):
        """score == 45.0 exactly → MODERATE (not HIGH)."""
        # sw=1.0, conf=0.45, no dims → raw=45.0
        result = scorer.score_inspection([_det("pothole", 0.45)])
        assert result.score == pytest.approx(45.0, abs=1e-6)
        assert result.level == RiskLevel.MODERATE

    def test_score_just_above_moderate_max_is_high(self):
        """score infinitesimally > 45 → HIGH."""
        result = scorer.score_inspection([_det("pothole", 0.451)])
        assert result.score > MODERATE_MAX
        assert result.level == RiskLevel.HIGH

    # ── HIGH / CRITICAL boundary (HIGH_MAX = 70.0) ───────────────────────

    def test_score_at_high_max_is_high(self):
        """score == 70.0 exactly → HIGH (not CRITICAL)."""
        # sw=1.0, conf=0.70, no dims → raw=70.0
        result = scorer.score_inspection([_det("pothole", 0.70)])
        assert result.score == pytest.approx(70.0, abs=1e-6)
        assert result.level == RiskLevel.HIGH

    def test_score_just_above_high_max_is_critical(self):
        """score infinitesimally > 70 → CRITICAL."""
        result = scorer.score_inspection([_det("pothole", 0.701)])
        assert result.score > HIGH_MAX
        assert result.level == RiskLevel.CRITICAL

    # ── CRITICAL range ────────────────────────────────────────────────────

    def test_score_100_is_critical(self):
        """Maximum possible score → CRITICAL."""
        result = scorer.score_inspection([_det("pothole", 1.0)])
        # sw=1.0, conf=1.0, no dims → raw=100.0
        assert result.level == RiskLevel.CRITICAL

    # ── Recommendation text matches level ────────────────────────────────

    @pytest.mark.parametrize("conf,expected_level", [
        (0.10, RiskLevel.LOW),
        (0.30, RiskLevel.MODERATE),
        (0.60, RiskLevel.HIGH),
        (0.90, RiskLevel.CRITICAL),
    ])
    def test_recommendation_matches_level(self, conf, expected_level):
        result = scorer.score_inspection([_det("pothole", conf)])
        assert result.level == expected_level
        assert result.recommendation == RECOMMENDATIONS[expected_level.value]


# ===========================================================================
# TestDominantDamage
# ===========================================================================

class TestDominantDamage:
    """dominant_damage must identify the highest-scoring detection's class."""

    def test_dominant_is_highest_score_not_highest_confidence(self):
        """
        A lower-confidence pothole can outrank a higher-confidence longitudinal_crack
        because severity_weight for pothole (1.0) is higher (0.50).

        pothole conf=0.40      → 1.00×0.40×100 = 40.0
        longitudinal conf=0.70 → 0.50×0.70×100 = 35.0

        dominant must be "pothole" despite lower confidence.
        """
        detections = [
            _det("pothole",            0.40),
            _det("longitudinal_crack", 0.70),
        ]
        result = scorer.score_inspection(detections)
        assert result.dominant_damage == "pothole"

    def test_dominant_matches_first_detection_risk_entry(self):
        """detection_risks[0].class_name must equal dominant_damage."""
        detections = [
            _det("alligator_crack",    0.90),
            _det("longitudinal_crack", 0.99),
        ]
        result = scorer.score_inspection(detections)
        assert result.dominant_damage == result.detection_risks[0].class_name

    def test_dominant_none_for_empty_detections(self):
        result = scorer.score_inspection([])
        assert result.dominant_damage is None


# ===========================================================================
# TestSchemaOutput
# ===========================================================================

class TestSchemaOutput:
    """Verify RiskAssessmentOut Pydantic model is valid and JSON-serialisable."""

    def test_result_is_serialisable(self):
        """model_dump() must not raise on any valid result."""
        result = scorer.score_inspection(
            [_det("pothole", 0.80), _det("alligator_crack", 0.60)],
            image_dims=(480, 640),
        )
        d = result.model_dump()
        assert isinstance(d["score"], float)
        assert isinstance(d["level"], str)          # RiskLevel serialises to str
        assert isinstance(d["detection_risks"], list)
        assert isinstance(d["score_breakdown"], dict)
        assert isinstance(d["methodology_note"], str)

    def test_methodology_note_is_verbatim_constant(self):
        """The methodology_note in output must exactly match METHODOLOGY_NOTE."""
        result = scorer.score_inspection([_det()])
        assert result.methodology_note == METHODOLOGY_NOTE

    def test_all_detection_scores_in_range(self):
        """Every detection_score must be in [0, 100]."""
        detections = [
            _det("pothole",            1.0),
            _det("alligator_crack",    0.95),
            _det("transverse_crack",   0.75),
            _det("longitudinal_crack", 0.50),
            _det("unknown_type",       0.80),
        ]
        result = scorer.score_inspection(detections, image_dims=(480, 640))
        for dr in result.detection_risks:
            assert 0.0 <= dr.detection_score <= 100.0
