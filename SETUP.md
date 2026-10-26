# 🛠️ InfraGuard-AI Complete Setup & Operations Guide

This guide walks you through setting up the **FastAPI Backend**, the **Flutter Mobile App**, configuring **wireless physical phone operation**, and running the **automated test suites**.

---

## 1. System Requirements

- **Operating System**: Windows 10/11, macOS, or Linux.
- **Python**: 3.10 to 3.13 (Python virtual environment recommended).
- **Flutter SDK**: 3.24.0 or newer.
- **Android Device**: Physical Android phone (Android 8.0+) with Developer Options & USB Debugging enabled, OR Android Emulator.
- **Network**: Wi-Fi network or Mobile Hotspot connecting both your laptop and phone.

---

## 2. Repository Setup

```bash
git clone https://github.com/Disha455/InfraGuard-AI.git
cd InfraGuard-AI
```

---

## 3. Backend Setup

### A. Create and Activate Virtual Environment

**Windows PowerShell:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

*(Ensure `(.venv)` appears at the beginning of your command prompt.)*

### B. Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### C. Verify Computer Vision Weights
Ensure the YOLOv8 and ResNet weights are present in:
```
ai/
└── computer_vision/
    └── weights/
        └── best.pt
```

### D. Start Backend Server
```powershell
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Model weights verified. Predictor service initialized.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```
- Interactive Swagger API Documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/`

---

## 4. Mobile Application Setup

### A. Install Flutter Dependencies
Open a second terminal:
```bash
cd mobile_app
flutter pub get
```

### B. First-Time Physical Device Installation
1. Connect your Android phone to your laptop using a USB cable.
2. Enable **USB Debugging** on your phone (Settings -> Developer Options -> USB Debugging).
3. Verify your device is recognized:
   ```bash
   flutter devices
   ```
4. Run the app to install it onto your device:
   ```bash
   flutter run
   ```

---

## 5. Wireless Operation (Untethered from USB Cable)

You do **NOT** need to keep your phone connected via USB to perform inspections or view admin analytics.

### How to use the app wirelessly:
1. Make sure your phone and laptop are connected to the same Wi-Fi (or your phone's personal hotspot).
2. **Unplug the USB cable from your phone.**
3. Tap the **InfraGuard AI** icon from your phone's home screen or app drawer.
4. If your laptop's Wi-Fi IP address ever changes:
   - Tap the **Wi-Fi icon (`Icons.wifi_rounded`)** in the top AppBar of the Welcome or Home screen.
   - Enter your laptop's current IP (e.g. `http://192.168.1.50:8000`).
   - Tap **Test Connection** (turns green when verified).
   - Tap **Save & Connect**.
5. You can now walk anywhere, capture road photos with your phone camera, analyze them, and see live results sync to the central database!

---

## 6. How to Never Change IP Again (Zero Maintenance)

To permanently avoid looking up `ipconfig`:

### Option A: Phone Mobile Hotspot (Recommended for project demos & viva)
1. Turn on your phone's personal Wi-Fi hotspot and connect your laptop to it.
2. Under mobile hotspot, your laptop receives a stable private IP (typically `192.168.43.x`).
3. Set this IP once in the app's Wi-Fi Settings. It remains unchanged across college and home networks.

### Option B: Free Cloud Tunnel (Works anywhere, even over 4G/5G mobile data)
1. On your laptop terminal, run:
   ```bash
   npx localtunnel --port 8000
   ```
   *(or `ngrok http 8000`)*
2. It gives you a public HTTPS URL like: `https://infraguard-ai.loca.lt`
3. Enter that URL into the app's Wi-Fi settings once. Your phone can now be anywhere in the world on mobile data and communicate with your backend.

---

## 7. Automated Testing & Verification

Run these commands to verify that all systems are healthy:

### Flutter Mobile App Tests (71 Tests)
```bash
cd mobile_app
flutter analyze     # Verify 0 lint/analyzer issues
flutter test        # Run all 71 unit and widget tests
```

### Backend Pytest Suite (52 Tests)
```powershell
.\.venv\Scripts\python -m pytest backend/tests
```

---

## 8. Common Troubleshooting

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| **Connection Timeout** | Phone cannot reach laptop IP. | 1. Ensure phone and laptop are on same Wi-Fi.<br>2. Check Windows Firewall: allow Python / Uvicorn.<br>3. Tap Wi-Fi icon in app to test connection. |
| **Model returns 503** | `best.pt` model weights not found. | Verify `ai/computer_vision/weights/best.pt` exists. |
| **History images not showing** | Output directory path mismatch. | Server serves `/outputs` statically. Tap the Wi-Fi icon in app to verify backend URL is reachable. |
| **Location unavailable** | GPS permissions denied. | In Android Settings -> Apps -> InfraGuard AI -> Permissions -> Allow Location while using the app. |