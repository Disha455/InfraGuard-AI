# Project Setup Guide

Follow these steps carefully.

---

# Clone Repository

```bash
git clone <repository-url>
```

```bash
cd InfraGuard-AI
```

---

# Backend Setup

## Create Virtual Environment

```bash
python -m venv .venv
```

---

## Activate Environment

### PowerShell

```bash
.venv\Scripts\Activate.ps1
```

### CMD

```bash
.venv\Scripts\activate.bat
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

If ultralytics is missing

```bash
pip install ultralytics
```

---

# AI Model Setup

The trained model is **NOT stored on GitHub** because of its size.

The model file (`best.pt`) will be shared separately.

Place it here:

```
ai/
└── computer_vision/
    └── weights/
        └── best.pt
```

---

# Start Backend

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see

```
Application startup complete.
```

---

# Flutter Setup

Move inside mobile app

```bash
cd mobile_app
```

Install dependencies

```bash
flutter pub get
```

Run

```bash
flutter run
```

---

# Using a Physical Android Phone

Open

```
mobile_app/lib/core/constants/api_endpoints.dart
```

Replace

```dart
http://127.0.0.1:8000
```

with your computer's IPv4 address.

Example

```dart
http://192.168.29.107:8000
```

Find IP

```bash
ipconfig
```

Use the IPv4 Address under Wi-Fi Adapter.

---

# Important

- Laptop and phone must be on the same Wi-Fi.
- Allow Firewall access.
- Backend must be started before Flutter.

---

# Common Errors

## Prediction returns 503

Model not loaded.

Check

```
best.pt
```

exists.

---

## Connection Timeout

Wrong IP address.

Check

```
api_endpoints.dart
```

---

## ModuleNotFoundError

Install missing package.

Example

```bash
pip install ultralytics
```

---

## Flutter Errors

Run

```bash
flutter clean

flutter pub get
```

---

## Backend doesn't start

Ensure virtual environment is activated.

```
(.venv)
```

should appear before the terminal path.