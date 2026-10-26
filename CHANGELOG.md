# Changelog

All notable changes to the **InfraGuard-AI** platform are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2.1.0] - October 2026

### 🎨 UI/UX & Visual Design Overhaul
- **Executive Pastel Palette**: Replaced flat glaring pure white backgrounds with a soothing, high-clarity ambient pastel mesh gradient (`#E8EEF5` -> `#F1F5F9` -> `#EDE8F5`) for eye comfort during field inspections.
- **Luminous Gradient Headers**: Styled AppBars across Welcome, Home, Admin Dashboard, History, and Result pages with a cohesive midnight-to-sapphire executive gradient (`#0A2239` -> `#133E68` -> `#1D5A8F`).
- **Modern AI Viewfinder HUD**: Replaced empty camera icon with an active targeting viewfinder containing corner precision brackets and dual Camera/Gallery action buttons.
- **Gradient Action Buttons**: Upgraded primary call-to-actions ("Analyze Image") with royal steel gradients and subtle depth elevations.
- **Decluttered Interface**: Removed prototype debug text, redundant status banners, and duplicate strings across all pages for a clean, presentation-ready look.

### 🌐 Network & Wireless Architecture
- **In-App Dynamic Server IP Switcher**: Created `ServerConfigDialog` accessible via a dedicated Wi-Fi icon in the top AppBar across all pages. Users can test connectivity with one tap and switch backend host addresses dynamically without editing code or rebuilding.
- **Untethered Wireless Phone Operation**: Clarified workflow for running the app on physical mobile devices completely untethered from the development USB cable over local Wi-Fi or mobile hotspots.

### 🖼️ Inspection History & Image Persistence
- **Annotated Image Storage**: Updated backend predictor service to store relative artifact URLs (`/outputs/{run_id}/annotated.jpg`) upon inference completion.
- **Dynamic Thumbnail Resolver**: Enhanced `_Thumbnail` in `history_page.dart` to automatically resolve relative and server paths against the active `ApiEndpoints.baseUrl`, displaying sharp annotated road thumbnails on all historical inspection cards.
- **Database Backfill**: Migrated and linked all legacy inspection records with their respective annotated image outputs on disk.

### 🗄️ Relational Database & Real-Time Sync
- **Persistent SQLite Engine**: Implemented `InspectionStore` with SQLite 3 (`backend/data/infraguard.db`) running with Write-Ahead Logging (WAL) and automatic JSON sync for complete persistence across server and device restarts.
- **Normalized Defect Taxonomy**: Implemented robust normalization mapping YOLO and ResNet distress classes (`pothole`, `block_crack`, `linear_crack`) to standard municipal categories (Potholes, Alligator Cracks, Longitudinal Cracks, Transverse Cracks).
- **Client Synchronization**: Added `syncWithBackend()` in `InspectionHistoryService` to automatically recover and merge all database records when opening the inspection history screen.

### 📊 Real-Time Administrator Analytics
- **Live Aggregated Metrics**: Admin Dashboard now computes live counts directly from SQLite:
  - Total Inspections
  - Damaged Roads & Defect Rate Percentage
  - High-Risk Critical Hotspots
  - Pending Municipal Action Items
- **Live Dynamic Charts**: Damage distribution pie chart and severity bar chart dynamically render from central database rows with 0 hardcoded values.
- **Recent Inspections Feed**: Connected live real-time inspection log displaying timestamp, road location, dominant distress, and risk badge with direct drill-down to full results.

### 🌍 Multi-Modal Environmental & Municipal Risk Engine
- **Open-Meteo Weather Integration**: Real-time atmospheric API integration querying current temperature, precipitation, and rain codes at GPS coordinates. Applies a **+22%** hazard multiplier on wet pavement.
- **OpenStreetMap Nominatim Geocoding**: Reverse geocodes coordinates to street names and detects highway hierarchy tags (motorway, primary, secondary, residential) to calculate traffic multipliers (1.00x to 1.35x).
- **ASTM D6433 Municipal Registry**: Models municipal GIS records tracking Pavement Condition Index (PCI 0-100), days since last resurfacing, and maintenance status with structural penalty scoring.
- **Unified Risk Assessment**: Unified conflicting scores into a single authoritative risk metric (0-100) categorized into LOW, MODERATE, HIGH, and CRITICAL with automated action recommendations.

### 🧪 Quality Assurance & Test Automation
- **71 Flutter Automated Tests**: Full test suite passing with 0 errors across widget rendering, role navigation, location capture, history storage, risk model parsing, and server config dialogs.
- **52 Backend Pytest Tests**: Comprehensive test suite passing with 0 errors across risk scorer algorithms, SQLite transactions, API routes, and analytics calculations.

---

## [1.0.0] - August 2026

### Added
- Core mobile app using Flutter (Camera, Gallery, Image Validation).
- FastAPI backend serving YOLOv8 inference.
- Output generation for annotated images and detection JSONs.
- Local in-memory inspection history.
- Result screen displaying bounding boxes and damage confidence.