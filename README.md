# 🚧 InfraGuard-AI: Intelligent Road Infrastructure Inspection & Risk Analytics

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Flutter](https://img.shields.io/badge/Flutter-3.29+-02569B.svg?logo=flutter&logoColor=white)](https://flutter.dev)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF.svg?logo=ultralytics&logoColor=black)](https://github.com/ultralytics/ultralytics)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C.svg?logo=pytorch&logoColor=white)](https://pytorch.org)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Tests-123%20Passing-brightgreen.svg)]()

**InfraGuard-AI** is an enterprise-grade automated road infrastructure inspection and multi-factor risk assessment platform. It bridges deep learning computer vision (YOLOv8 and ResNet50) with live geospatial data, real-time meteorological conditions (Open-Meteo), and municipal road survey registries (ASTM D6433) to provide continuous, actionable road health intelligence.

---

## 🌟 Core Highlights & Capabilities

### 1. Dual AI Vision Architecture
- **Object Detection (YOLOv8)**: Detects, classifies, and annotates localized surface distress into 4 primary municipal classes:
  - **Potholes & Depressions**
  - **Alligator / Fatigue Cracks**
  - **Longitudinal Cracks**
  - **Transverse Cracks**
- **Severity Classification (ResNet50)**: Evaluates deep structural degradation probabilities (Low, Moderate, High, Critical).

### 2. Multi-Factor Contextual Risk Intelligence Engine
Unlike standard visual-only apps, InfraGuard-AI scores structural road risk from **0 to 100** by combining:
- **Visual AI Detections & Severities** (Weighted base score).
- **Live Meteorological Hazards (Open-Meteo API)**: Wet pavement detection and rain conditions increase risk by **+22%** due to hydroplaning hazards and rapid water-induced erosion.
- **Road Hierarchy & Traffic Volumes (OpenStreetMap Nominatim API)**: Reverse geocodes coordinates to road names and assigns traffic multipliers (1.00x for local lanes up to 1.35x for major arterial corridors).
- **Municipal Pavement Management History (ASTM D6433 Standard)**: Integrates municipal GIS records tracking Pavement Condition Index (PCI) and days elapsed since last asphalt resurfacing.

### 3. Persistent SQLite Database & Real-Time Sync
- **Engine**: SQLite 3 (`backend/data/infraguard.db`) running with Write-Ahead Logging (WAL).
- **Zero Data Loss**: Inspections are persisted to disk immediately with GPS coordinates, defect taxonomy, risk scores, and annotated outputs.
- **Automatic Client Synchronization**: Re-opening or refreshing the mobile app auto-syncs all historical records and displays network thumbnails directly from the server.

### 4. Administrator Analytics Dashboard
- **Live Real-Time KPIs**: Total inspections, defect rate percentage, critical high-risk hotspots, and pending maintenance actions.
- **Interactive Visualizations**:
  - **Damage Category Pie Chart**: Proportional distribution across all distress categories.
  - **Severity Bar Chart**: Visual count breakdown across Low, Moderate, High, and Critical severities.
  - **Recent Inspections Log**: Chronological live feed with direct drill-down into detailed inspection reports.

### 5. Dynamic In-App Server IP Configuration & Wireless Operation
- **One-Tap Wi-Fi Switcher**: In-app Wi-Fi settings icon in the top AppBar allows entering new server addresses with real-time connectivity testing against `/health`.
- **Completely Wireless**: Disconnect the USB cable after initial install; field inspectors and admins can use the app anywhere on Wi-Fi or mobile hotspot.

---

## 🏛️ System Architecture

```
                                  MOBILE APP (Flutter)
                     ┌──────────────────────────────────────────────┐
                     │ • Inspector Mode: Camera, Gallery, GPS Fix   │
                     │ • Admin Mode: Live Analytics & Charts        │
                     │ • Dynamic Server IP Switcher & History Sync  │
                     └──────────────────────┬───────────────────────┘
                                            │ HTTP Multipart & REST
                                            ▼
                                   FASTAPI BACKEND
                     ┌──────────────────────────────────────────────┐
                     │ • POST /predict/ (Image + GPS Telemetry)     │
                     │ • GET /api/admin/analytics (Live Stats)      │
                     │ • GET /api/inspections (Historical Records)  │
                     │ • Static Mount: /outputs (Annotated Artifact)│
                     └──────┬───────────────────┬───────────────────┘
                            │                   │
             ┌──────────────┴───────┐    ┌──────┴───────────────────┐
             │   AI Inference Core  │    │  External Services & GIS │
             │ • YOLOv8 Detection   │    │ • Open-Meteo Weather API │
             │ • ResNet50 Severity  │    │ • OSM Nominatim Geocoding│
             └──────────────┬───────┘    │ • ASTM D6433 Registry    │
                            │            └──────────────────────────┘
                            ▼
             ┌──────────────────────────────────────────────────────┐
             │           PERSISTENT SQLITE DATABASE                 │
             │           backend/data/infraguard.db                 │
             └──────────────────────────────────────────────────────┘
```

---

## 🗄️ Database Architecture & Schema

The relational database is stored at `backend/data/infraguard.db` with the primary `inspections` table:

```sql
CREATE TABLE inspections (
    run_id TEXT PRIMARY KEY,               -- Unique run identifier (e.g. run_20261026_182114)
    timestamp TEXT NOT NULL,               -- ISO-8601 UTC timestamp
    location_name TEXT NOT NULL,           -- Reverse-geocoded road name (e.g. "Vinayaka Layout")
    coordinates TEXT,                      -- Display coordinates ("13.1088° N, 77.5788° E")
    latitude REAL,                         -- WGS84 decimal latitude
    longitude REAL,                        -- WGS84 decimal longitude
    dominant_damage TEXT NOT NULL,         -- Primary distress class (Pothole, Alligator Crack, etc.)
    total_detections INTEGER NOT NULL,     -- Total bounding boxes detected
    risk_score REAL NOT NULL,              -- Weighted multi-factor score (0 - 100)
    risk_level TEXT NOT NULL,              -- Categorical severity: LOW, MODERATE, HIGH, CRITICAL
    status TEXT NOT NULL,                  -- Municipal action status
    weather_summary TEXT,                  -- Live atmospheric condition & road wetness
    traffic_level TEXT,                    -- Road hierarchy classification & multiplier
    maintenance_status TEXT,               -- Municipal survey record & days since resurfacing
    detections_json TEXT,                  -- Serialized bounding boxes and confidences
    image_url TEXT                         -- Output path to annotated inspection artifact
);
```

---

## 🌐 External APIs & Standards Integrated

1. **Open-Meteo Weather API**:
   - **Documentation**: [https://open-meteo.com/en/docs](https://open-meteo.com/en/docs)
   - **Endpoint**: `https://api.open-meteo.com/v1/forecast`
   - **Parameters**: `temperature_2m`, `precipitation`, `weather_code`, `rain`
   - **Authentication**: Free open-source tier, no API key required.
2. **OpenStreetMap Nominatim Reverse Geocoding API**:
   - **Documentation**: [https://nominatim.org/release-docs/latest/api/Reverse/](https://nominatim.org/release-docs/latest/api/Reverse/)
   - **Endpoint**: `https://nominatim.openstreetmap.org/reverse`
   - **Role**: Geocodes latitude/longitude into road names and highway classification tags.
3. **Municipal Road Survey Registry (ASTM D6433 Standard)**:
   - **Standard Reference**: [ASTM D6433 - Pavement Condition Index Surveys](https://www.astm.org/d6433-20.html)
   - **File**: `backend/data/municipal_maintenance_registry.json`
   - **Metrics**: Pavement Condition Index (PCI 0-100), last resurfacing date, days elapsed, and reconstruction status.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.13)
- Flutter SDK 3.24+ (Channel stable)
- Android Studio / Android Device with Developer Mode enabled

### 2. Backend Setup
```bash
# Clone the repository
git clone https://github.com/Disha455/InfraGuard-AI.git
cd InfraGuard-AI

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API docs will be live at: `http://localhost:8000/docs`

### 3. Mobile App Setup
```bash
cd mobile_app
flutter pub get
flutter run
```

---

## 🧪 Automated Testing & Verification

InfraGuard-AI maintains a rigorous automated testing pipeline with **123 tests total**:

- **Flutter Mobile Suite (71 Tests Passing)**:
  ```bash
  cd mobile_app
  flutter analyze   # 0 issues found
  flutter test      # 71 / 71 passed
  ```
  Covers role selection, AI viewfinder HUD, image picking, GPS telemetry resolution, location permission denial edge-cases, single-score risk card formatting, history caching, and backend synchronization.

- **Backend Pytest Suite (52 Tests Passing)**:
  ```bash
  .\.venv\Scripts\python -m pytest backend/tests
  ```
  Covers multi-factor risk assessment mathematics, weather friction modifiers, OSM road classification multipliers, SQLite persistence and transactions, real-time analytics aggregation, and API contract compliance.

---

## 👥 Contributors & Maintainers
- **Disha** (Team Lead & Full-Stack / Mobile Lead)
- InfraGuard-AI Engineering Team