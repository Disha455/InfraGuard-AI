"""
InfraGuard AI — Environmental & Historical Maintenance Context Service

Integrates:
    1. Real-time Weather API (Open-Meteo - Free, No API key required):
       Extracts precipitation, temperature, moisture/wetness.
       Wet pavement multiplies pothole hazard (hydroplaning & hidden depth).
       Freeze-thaw cycles accelerate crack progression.
    2. Road & Traffic Classification (OpenStreetMap Nominatim Reverse Geocoding):
       Extracts road name and OSM highway hierarchy.
       High-speed / freight corridors multiply structural road failure risk.
    3. Municipal Road Maintenance Survey Registry:
       Historical survey records, days since last resurfacing,
       Pavement Condition Index (PCI 0-100), and sub-base fatigue penalty.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime, date
from pathlib import Path
from typing import Any

logger = logging.getLogger("infraguard.context")

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_REGISTRY_PATH = _DATA_DIR / "municipal_maintenance_registry.json"


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


class ContextService:
    """Provides real-time weather, traffic/road class, and historical maintenance context."""

    def __init__(self, registry_path: Path = _REGISTRY_PATH) -> None:
        self.registry_path = registry_path
        self._registry_data: dict[str, Any] = self._load_registry()

    def _load_registry(self) -> dict[str, Any]:
        if self.registry_path.exists():
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load maintenance registry: %s", e)
        return {"corridors": []}

    # -----------------------------------------------------------------------
    # 1. Weather API (Open-Meteo)
    # -----------------------------------------------------------------------

    def get_weather(self, lat: float | None, lon: float | None) -> dict[str, Any]:
        """
        Fetch real-time weather for the given GPS coordinates using Open-Meteo.
        Free public API with no API key required.
        """
        if lat is None or lon is None:
            return {
                "temperature_c": 26.0,
                "precipitation_mm": 0.0,
                "condition": "Normal / Dry Pavement",
                "risk_impact": "Neutral — No precipitation reported",
                "multiplier": 1.0,
            }

        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat:.4f}&longitude={lon:.4f}&"
            f"current=temperature_2m,precipitation,rain,weather_code"
        )

        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "InfraGuard-AI/2.0 (RoadSafetyProject)"}
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                current = data.get("current", {})
                temp = _safe_float(current.get("temperature_2m"), 25.0)
                precip = _safe_float(current.get("precipitation"), 0.0)
                rain = _safe_float(current.get("rain"), 0.0)
                weather_code = int(current.get("weather_code", 0))

                # Impact calculation
                is_wet = precip > 0.1 or rain > 0.1
                is_freezing = temp < 1.0

                if is_freezing and is_wet:
                    condition = f"Freeze-Thaw Risk ({temp:.1f}°C, {precip:.1f}mm)"
                    impact = "Critical — Ice expansion actively wedges and widens cracks"
                    multiplier = 1.30
                elif precip > 2.0 or rain > 2.0:
                    condition = f"Active Rain / Saturated ({precip:.1f}mm)"
                    impact = "High — Water-filled potholes conceal depth; high hydroplaning hazard"
                    multiplier = 1.22
                elif is_wet:
                    condition = f"Damp / Light Moisture ({precip:.1f}mm)"
                    impact = "Moderate — Wet surface reduces braking friction by ~30%"
                    multiplier = 1.10
                elif temp > 38.0:
                    condition = f"Extreme Heat Wave ({temp:.1f}°C)"
                    impact = "Moderate — Bitumen bleeding and rutting under heavy wheel loads"
                    multiplier = 1.08
                else:
                    condition = f"Dry & Clear ({temp:.1f}°C)"
                    impact = "Low — Favorable surface traction conditions"
                    multiplier = 1.00

                return {
                    "temperature_c": round(temp, 1),
                    "precipitation_mm": round(precip, 1),
                    "condition": condition,
                    "risk_impact": impact,
                    "multiplier": multiplier,
                }
        except Exception as exc:
            logger.info("Open-Meteo weather fetch skipped/timed out: %s", exc)
            return {
                "temperature_c": 25.0,
                "precipitation_mm": 0.0,
                "condition": "Dry / Seasonal Baseline",
                "risk_impact": "Neutral — Regional weather baseline",
                "multiplier": 1.0,
            }

    # -----------------------------------------------------------------------
    # 2. Road Hierarchy & Traffic API (OpenStreetMap Nominatim)
    # -----------------------------------------------------------------------

    def get_traffic(self, lat: float | None, lon: float | None) -> dict[str, Any]:
        """
        Reverse-geocodes coordinates via OpenStreetMap Nominatim to identify
        road name and highway hierarchy to estimate traffic volume.
        """
        if lat is None or lon is None:
            return {
                "road_name": "Field Survey Zone",
                "road_type": "Secondary Arterial",
                "traffic_volume": "Moderate (Urban Commuter)",
                "risk_impact": "Standard urban vehicle flow",
                "multiplier": 1.05,
            }

        url = (
            f"https://nominatim.openstreetmap.org/reverse?"
            f"lat={lat:.5f}&lon={lon:.5f}&format=json"
        )

        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "InfraGuard-AI/2.0 (RoadSafetyResearch)"}
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                address = data.get("address", {})
                road = (
                    address.get("road")
                    or address.get("highway")
                    or address.get("neighbourhood")
                    or address.get("suburb")
                    or "Municipal Roadway"
                )
                category = data.get("type", "").lower()

                # Traffic classification based on OSM highway tag
                if category in ("motorway", "trunk") or "highway" in road.lower() or "nh" in road.lower():
                    road_type = "High-Speed National Corridor / Trunk"
                    traffic_volume = "Very High (Heavy Freight & Inter-city Logistics)"
                    impact = "Critical — Heavy axle loads rapidly degrade structural sub-base"
                    multiplier = 1.25
                elif category in ("primary", "secondary") or "road" in road.lower() or "arterial" in road.lower():
                    road_type = "Primary / Secondary Arterial"
                    traffic_volume = "High (Commercial & Public Transit)"
                    impact = "High — Frequent bus/truck braking increases shearing stress"
                    multiplier = 1.15
                elif category in ("tertiary", "residential"):
                    road_type = "Tertiary / Residential Link"
                    traffic_volume = "Moderate to Low (Local Access)"
                    impact = "Moderate — Lower speed limits reduce dynamic impact"
                    multiplier = 0.95
                else:
                    road_type = "Urban Collector"
                    traffic_volume = "Moderate (Urban Traffic)"
                    impact = "Standard urban traffic volume"
                    multiplier = 1.05

                return {
                    "road_name": road,
                    "road_type": road_type,
                    "traffic_volume": traffic_volume,
                    "risk_impact": impact,
                    "multiplier": multiplier,
                }
        except Exception as exc:
            logger.info("Nominatim road query skipped/timed out: %s", exc)
            return {
                "road_name": "Regional Survey Corridor",
                "road_type": "Primary Arterial",
                "traffic_volume": "Moderate to High",
                "risk_impact": "Standard regional vehicle flow",
                "multiplier": 1.08,
            }

    # -----------------------------------------------------------------------
    # 3. Municipal Historical Maintenance Survey Records
    # -----------------------------------------------------------------------

    def get_maintenance_record(self, lat: float | None, lon: float | None) -> dict[str, Any]:
        """
        Locates the historical municipal road survey record for the location.
        Computes days elapsed since last maintenance, PCI score, and fatigue risk penalty.
        """
        corridors = self._registry_data.get("corridors", [])
        matched = None

        if lat is not None and lon is not None:
            for c in corridors:
                if (
                    c.get("lat_min", -999) <= lat <= c.get("lat_max", 999)
                    and c.get("lon_min", -999) <= lon <= c.get("lon_max", 999)
                ):
                    matched = c
                    break

        if not matched:
            matched = self._registry_data.get("default_zone_profile", {})

        # Compute days since last maintenance
        last_date_str = matched.get("last_resurfaced_date", "2023-01-01")
        try:
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
            days_elapsed = (date.today() - last_date).days
        except Exception:
            days_elapsed = 650

        pci = _safe_float(matched.get("pci_score"), 55.0)
        penalty = _safe_float(matched.get("risk_penalty"), 5.0)

        # Dynamic aging modifier: if > 2 years (730 days) since maintenance, escalate penalty
        if days_elapsed > 1000:
            penalty = max(penalty, 16.0)
            status = "CRITICALLY OVERDUE FOR RECONSTRUCTION"
        elif days_elapsed > 600:
            penalty = max(penalty, 10.0)
            status = "OVERDUE FOR RESURFACING"
        elif days_elapsed > 365:
            penalty = max(penalty, 5.0)
            status = "DUE FOR SCHEDULED RESURFACING"
        else:
            status = matched.get("maintenance_status", "SATISFACTORY")

        return {
            "corridor_id": matched.get("segment_id", "MUNI-COR-DEFAULT"),
            "road_name": matched.get("road_name", "Municipal Survey Corridor"),
            "last_resurfaced_date": last_date_str,
            "days_since_maintenance": days_elapsed,
            "pci_score": round(pci, 1),
            "maintenance_status": status,
            "risk_adjustment": round(penalty, 1),
            "notes": matched.get(
                "inspector_notes",
                f"Surveyed {days_elapsed} days ago. Base layer fatigue increasing risk.",
            ),
        }

    # -----------------------------------------------------------------------
    # 4. Master Context Aggregator
    # -----------------------------------------------------------------------

    def get_context(self, lat: float | None, lon: float | None) -> dict[str, Any]:
        """Gathers all three contextual sources and returns structured results."""
        weather = self.get_weather(lat, lon)
        traffic = self.get_traffic(lat, lon)
        maintenance = self.get_maintenance_record(lat, lon)

        return {
            "weather": weather,
            "traffic": traffic,
            "maintenance": maintenance,
            "combined_multiplier": round(weather["multiplier"] * traffic["multiplier"], 3),
            "maintenance_points": maintenance["risk_adjustment"],
        }
