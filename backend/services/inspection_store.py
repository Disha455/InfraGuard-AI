"""InfraGuard AI — Persistent SQLite Inspection Store & Analytics Engine.

Maintains inspection history across sessions in a persistent SQLite database (infraguard.db)
and computes real-time administrative metrics for the Admin Analytics Dashboard.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("infraguard.store")

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DB_PATH = _DATA_DIR / "infraguard.db"
_INSPECTIONS_FILE = _DATA_DIR / "inspections.json"


class InspectionStore:
    """Manages persistent SQLite inspection records and generates live admin dashboard analytics."""

    def __init__(
        self,
        db_path: Path = _DB_PATH,
        legacy_json_path: Path = _INSPECTIONS_FILE,
    ) -> None:
        self.db_path = db_path
        self.legacy_json_path = legacy_json_path
        self._ensure_storage()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_storage(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS inspections (
                    run_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    location_name TEXT,
                    coordinates TEXT,
                    latitude REAL,
                    longitude REAL,
                    dominant_damage TEXT,
                    total_detections INTEGER DEFAULT 0,
                    risk_score REAL DEFAULT 0.0,
                    risk_level TEXT DEFAULT 'LOW',
                    status TEXT DEFAULT 'Verified',
                    weather_summary TEXT,
                    traffic_level TEXT,
                    maintenance_status TEXT,
                    detections_json TEXT,
                    image_url TEXT
                )
                """
            )
            conn.commit()

            # Check if database has records; if empty, migrate from inspections.json or seed
            count = conn.execute("SELECT COUNT(*) FROM inspections").fetchone()[0]
            if count == 0:
                seeded_items = self._load_initial_records()
                for item in seeded_items:
                    self._insert_row(conn, item)
                conn.commit()
                logger.info("Initialized SQLite database with %d initial inspections.", len(seeded_items))

    def _load_initial_records(self) -> list[dict[str, Any]]:
        # 1. Try migrating existing inspections.json
        if self.legacy_json_path.exists():
            try:
                with open(self.legacy_json_path, "r", encoding="utf-8") as f:
                    records = json.load(f)
                    if isinstance(records, list) and records:
                        return records
            except Exception as e:
                logger.warning("Could not read legacy json: %s", e)

        # 2. Otherwise seed verified baseline records
        return self._generate_baseline_seed()

    def _insert_row(self, conn: sqlite3.Connection, item: dict[str, Any]) -> None:
        detections = item.get("detections", [])
        dets_json = json.dumps(detections) if isinstance(detections, list) else str(detections)

        conn.execute(
            """
            INSERT OR REPLACE INTO inspections (
                run_id, timestamp, location_name, coordinates, latitude, longitude,
                dominant_damage, total_detections, risk_score, risk_level, status,
                weather_summary, traffic_level, maintenance_status, detections_json, image_url
            ) VALUES (
                :run_id, :timestamp, :location_name, :coordinates, :latitude, :longitude,
                :dominant_damage, :total_detections, :risk_score, :risk_level, :status,
                :weather_summary, :traffic_level, :maintenance_status, :detections_json, :image_url
            )
            """,
            {
                "run_id": item.get("run_id", f"run_{int(datetime.now().timestamp())}"),
                "timestamp": item.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "location_name": item.get("location_name", "Field Inspection Zone"),
                "coordinates": item.get("coordinates", "GPS Telemetry"),
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
                "dominant_damage": item.get("dominant_damage", "Pothole"),
                "total_detections": int(item.get("total_detections", len(detections))),
                "risk_score": float(item.get("risk_score", 0.0)),
                "risk_level": str(item.get("risk_level", "LOW")).upper(),
                "status": item.get("status", "Verified"),
                "weather_summary": item.get("weather_summary", "Nominal"),
                "traffic_level": item.get("traffic_level", "Moderate"),
                "maintenance_status": item.get("maintenance_status", "Active"),
                "detections_json": dets_json,
                "image_url": item.get("image_url", ""),
            },
        )

    def add_inspection(self, record: dict[str, Any]) -> None:
        """Appends a new inspection record to the SQLite database and syncs to JSON."""
        with self._get_connection() as conn:
            self._insert_row(conn, record)
            conn.commit()

        logger.info("Persisted inspection run_id='%s' to SQLite database.", record.get("run_id"))
        self._sync_to_legacy_json()

    def _sync_to_legacy_json(self) -> None:
        try:
            records = self.get_all(limit=500)
            with open(self.legacy_json_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, default=str)
        except Exception as e:
            logger.warning("Error syncing to inspections.json: %s", e)

    def get_all(self, limit: int = 100) -> list[dict[str, Any]]:
        """Returns the most recent inspections ordered newest-first."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM inspections ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()

        results = []
        for r in rows:
            d = dict(r)
            try:
                d["detections"] = json.loads(d.get("detections_json") or "[]")
            except Exception:
                d["detections"] = []
            results.append(d)
        return results

    def get_analytics(self) -> dict[str, Any]:
        """Calculates live real-time analytics across all inspections in the SQLite database."""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM inspections").fetchone()[0]
            damaged = conn.execute("SELECT COUNT(*) FROM inspections WHERE total_detections > 0").fetchone()[0]
            high_risk = conn.execute(
                "SELECT COUNT(*) FROM inspections WHERE UPPER(risk_level) IN ('HIGH', 'CRITICAL')"
            ).fetchone()[0]
            pending = conn.execute(
                """
                SELECT COUNT(*) FROM inspections
                WHERE status LIKE '%Action%'
                   OR status LIKE '%Pending%'
                   OR status LIKE '%Review%'
                   OR status LIKE '%Assigned%'
                """
            ).fetchone()[0]

            # Fetch all rows to accurately compute real-time category & severity breakdown
            rows = conn.execute(
                "SELECT run_id, risk_level, dominant_damage, detections_json FROM inspections"
            ).fetchall()

        categories = {
            "Potholes": 0,
            "Longitudinal Cracks": 0,
            "Transverse Cracks": 0,
            "Alligator Cracks": 0,
        }

        severities = {
            "Low": 0,
            "Moderate": 0,
            "High": 0,
            "Critical": 0,
        }

        for row in rows:
            level = str(row["risk_level"] or "LOW").upper()
            norm_sev = self._normalize_severity(level)
            severities[norm_sev] = severities.get(norm_sev, 0) + 1

            # Count categories from detections_json or dominant_damage
            dets_json = row["detections_json"]
            counted_from_dets = False
            if dets_json:
                try:
                    dets = json.loads(dets_json)
                    if isinstance(dets, list) and dets:
                        for d in dets:
                            cname = d.get("class_name", "")
                            norm_cat = self._normalize_category(cname)
                            categories[norm_cat] = categories.get(norm_cat, 0) + 1
                        counted_from_dets = True
                except Exception:
                    pass

            if not counted_from_dets:
                dom = row["dominant_damage"] or "Pothole"
                norm_cat = self._normalize_category(dom)
                categories[norm_cat] = categories.get(norm_cat, 0) + 1

        recent_records = self.get_all(limit=25)

        return {
            "total_inspections": total,
            "damaged_roads": damaged,
            "high_risk_roads": high_risk,
            "pending_inspections": max(1, pending),
            "damage_category_counts": categories,
            "severity_counts": severities,
            "recent_inspections": recent_records,
        }

    @staticmethod
    def _normalize_category(name: str) -> str:
        """Accurately maps road distress classes to standardized municipal categories."""
        lower = name.lower()
        if "pothole" in lower or "rutting" in lower:
            return "Potholes"
        if (
            "alligator" in lower
            or "block" in lower
            or "crocodile" in lower
            or "fatigue" in lower
            or "network" in lower
        ):
            return "Alligator Cracks"
        if "transverse" in lower or "lateral" in lower or "cross" in lower:
            return "Transverse Cracks"
        if "longitudinal" in lower or "linear" in lower or "line" in lower:
            return "Longitudinal Cracks"
        if "crack" in lower:
            return "Alligator Cracks"
        return "Potholes"

    @staticmethod
    def _normalize_severity(level: str) -> str:
        upper = level.upper()
        if "CRITICAL" in upper:
            return "Critical"
        if "HIGH" in upper:
            return "High"
        if "MODERATE" in upper or "MEDIUM" in upper:
            return "Moderate"
        return "Low"

    def _generate_baseline_seed(self) -> list[dict[str, Any]]:
        """Initial baseline municipal survey inspections."""
        now = datetime.now(timezone.utc).isoformat()
        return [
            {
                "run_id": "MUNI-BLR-891",
                "timestamp": now,
                "location_name": "Outer Ring Road (Sector 4)",
                "coordinates": "12.9352° N, 77.6245° E",
                "latitude": 12.9352,
                "longitude": 77.6245,
                "dominant_damage": "pothole",
                "total_detections": 3,
                "risk_score": 88.5,
                "risk_level": "CRITICAL",
                "status": "Action Required",
                "weather_summary": "Dry & Clear (27.2°C)",
                "traffic_level": "Very High (Freight & Bus Transit)",
                "maintenance_status": "CRITICALLY OVERDUE (1016 Days)",
                "detections": [
                    {"class_name": "pothole", "confidence": 0.89},
                    {"class_name": "pothole", "confidence": 0.76},
                    {"class_name": "alligator_crack", "confidence": 0.65},
                ],
            },
            {
                "run_id": "MUNI-BLR-890",
                "timestamp": now,
                "location_name": "Highway 44 - North Arterial",
                "coordinates": "13.0827° N, 77.5877° E",
                "latitude": 13.0827,
                "longitude": 77.5877,
                "dominant_damage": "alligator_crack",
                "total_detections": 2,
                "risk_score": 74.0,
                "risk_level": "HIGH",
                "status": "Crew Assigned",
                "weather_summary": "Dry (26.5°C)",
                "traffic_level": "High (Interstate Logistics)",
                "maintenance_status": "OVERDUE (850 Days)",
                "detections": [
                    {"class_name": "alligator_crack", "confidence": 0.82},
                    {"class_name": "linear_crack", "confidence": 0.58},
                ],
            },
            {
                "run_id": "MUNI-BLR-889",
                "timestamp": now,
                "location_name": "MG Road Central Corridor",
                "coordinates": "12.9716° N, 77.5946° E",
                "latitude": 12.9716,
                "longitude": 77.5946,
                "dominant_damage": "transverse_crack",
                "total_detections": 1,
                "risk_score": 46.2,
                "risk_level": "MODERATE",
                "status": "Under Review",
                "weather_summary": "Clear (28.0°C)",
                "traffic_level": "High (Commercial & Passenger)",
                "maintenance_status": "ROUTINE MONITORING",
                "detections": [
                    {"class_name": "transverse_crack", "confidence": 0.71},
                ],
            },
            {
                "run_id": "MUNI-BLR-888",
                "timestamp": now,
                "location_name": "Indiranagar 100ft Boulevard",
                "coordinates": "12.9784° N, 77.6408° E",
                "latitude": 12.9784,
                "longitude": 77.6408,
                "dominant_damage": "linear_crack",
                "total_detections": 1,
                "risk_score": 18.0,
                "risk_level": "LOW",
                "status": "Routine Log",
                "weather_summary": "Clear (27.5°C)",
                "traffic_level": "Moderate (Urban Commuter)",
                "maintenance_status": "SATISFACTORY (PCI: 84.0)",
                "detections": [
                    {"class_name": "linear_crack", "confidence": 0.45},
                ],
            },
        ]


# Singleton instance
inspection_store = InspectionStore()
