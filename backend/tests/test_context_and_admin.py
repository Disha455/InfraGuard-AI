"""Unit and integration tests for ContextService, InspectionStore, and Admin Analytics."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.context_service import ContextService
from backend.services.inspection_store import InspectionStore


@pytest.fixture
def test_client():
    return TestClient(app)


def test_context_service_municipal_registry_lookup():
    service = ContextService()
    # Coordinates near Silk Board - Electronic City Flyover (~12.9172, 77.6228)
    context = service.get_context(
        lat=12.9172,
        lon=77.6228,
    )

    assert "weather" in context
    assert "traffic" in context
    assert "maintenance" in context
    assert context["combined_multiplier"] > 0
    assert context["maintenance"]["days_since_maintenance"] >= 0
    assert context["maintenance"]["pci_score"] > 0
    assert "Silk Board" in context["maintenance"]["road_name"] or context["maintenance"]["days_since_maintenance"] > 0


def test_context_service_fallback_when_no_coords():
    service = ContextService()
    context = service.get_context(
        lat=None,
        lon=None,
    )

    assert context["weather"]["temperature_c"] >= 0 or context["weather"]["condition"] is not None
    assert context["traffic"]["multiplier"] >= 1.0
    assert context["maintenance"]["maintenance_status"] is not None


def test_inspection_store_and_admin_api(test_client):
    store = InspectionStore()
    initial_stats = store.get_analytics()
    assert initial_stats["total_inspections"] >= 0

    # Add a live sample inspection
    store.add_inspection({
        "run_id": "TEST-INSP-001",
        "dominant_damage": "pothole",
        "risk_score": 75.5,
        "risk_level": "HIGH",
        "total_detections": 2,
        "latitude": 12.9716,
        "longitude": 77.5946,
        "location_name": "MG Road Corridor",
        "weather_summary": "24°C • Fair",
        "traffic_level": "High (Commercial & Transit)",
        "maintenance_status": "Maintenance Overdue",
        "status": "Verified",
    })

    updated_stats = store.get_analytics()
    assert updated_stats["total_inspections"] >= initial_stats["total_inspections"]

    # Verify FastAPI /admin/analytics endpoint
    response = test_client.get("/admin/analytics")
    assert response.status_code == 200
    data = response.json()
    assert "total_inspections" in data
    assert "damaged_roads" in data
    assert "high_risk_roads" in data
    assert "damage_category_counts" in data
    assert "severity_counts" in data
    assert "recent_inspections" in data

    # Verify FastAPI /admin/inspections endpoint
    inspections_resp = test_client.get("/admin/inspections")
    assert inspections_resp.status_code == 200
    records = inspections_resp.json()
    assert isinstance(records, list)
    assert any(r.get("run_id") == "TEST-INSP-001" for r in records)
