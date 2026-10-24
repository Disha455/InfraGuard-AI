"""
InfraGuard AI — Risk Assessment Package

Exposes the public API for the CV-based inspection risk scoring engine:

    from backend.risk import RiskScorer
    from backend.risk.constants import CLASS_SEVERITY_WEIGHTS

Internal modules:
    constants.py  — all named constants; no logic
    scorer.py     — RiskScorer class; no FastAPI or Flutter dependencies
"""

from backend.risk.scorer import RiskScorer

__all__ = ["RiskScorer"]
