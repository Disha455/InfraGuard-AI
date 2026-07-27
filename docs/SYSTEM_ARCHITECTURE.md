# System Architecture
## InfraGuard AI

> This document explains the complete software architecture of InfraGuard AI and how every module communicates with one another.

---

# Table of Contents

- Overall Architecture
- Component Architecture
- Data Flow
- AI Architecture
- Backend Architecture
- Mobile Application Architecture
- Database Architecture
- Deployment Architecture
- Design Decisions

---

# 1. Overall Architecture

InfraGuard AI follows a modular architecture.

Each module has a single responsibility and communicates through well-defined APIs.

```mermaid
flowchart TB

User([User])

Flutter["Flutter Mobile App"]

FastAPI["FastAPI Backend"]

YOLO["YOLOv8 Detection Engine"]

Risk["XGBoost Risk Prediction"]

Weather["Weather API"]

Database[(PostgreSQL)]

User --> Flutter

Flutter --> FastAPI

FastAPI --> YOLO

YOLO --> Risk

Weather --> Risk

Risk --> Database

Database --> FastAPI

FastAPI --> Flutter
```

---

# 2. High-Level Component Diagram

```mermaid
graph LR

subgraph Client
A[Flutter]
end

subgraph Server
B[FastAPI]
C[Authentication]
D[Prediction API]
E[History API]
end

subgraph AI
F[YOLOv8]
G[XGBoost]
H[SHAP]
end

subgraph Storage
I[(PostgreSQL)]
end

A --> B

B --> C

B --> D

B --> E

D --> F

F --> G

G --> H

D --> I

E --> I
```

---

# 3. Data Flow

```mermaid
flowchart LR

RoadImage

RoadImage --> Upload

Upload --> API

API --> YOLO

YOLO --> DamageDetection

DamageDetection --> FeatureExtraction

FeatureExtraction --> RiskPrediction

RiskPrediction --> Database

Database --> Dashboard
```

---

# 4. Image Prediction Flow

```mermaid
sequenceDiagram

participant User

participant Flutter

participant Backend

participant YOLO

participant Risk

participant DB

User->>Flutter: Upload Image

Flutter->>Backend: POST /predict

Backend->>YOLO: Detect Damage

YOLO-->>Backend: Damage Classes

Backend->>Risk: Risk Prediction

Risk-->>Backend: Risk Score

Backend->>DB: Save Result

Backend-->>Flutter: Prediction
```

---

# 5. AI Architecture

```mermaid
flowchart TB

RDD2022

RDD2022 --> Inspection

Inspection --> Filtering

Filtering --> Training

Training --> best.pt

best.pt --> Inference

Inference --> FeatureExtraction

FeatureExtraction --> XGBoost

XGBoost --> SHAP

SHAP --> RiskReport
```

---

# 6. Backend Architecture

```mermaid
flowchart TD

Flutter

Flutter --> UploadAPI

Flutter --> HistoryAPI

Flutter --> LoginAPI

UploadAPI --> PredictionService

PredictionService --> YOLO

PredictionService --> RiskModel

PredictionService --> Database

HistoryAPI --> Database
```

---

# 7. Mobile Architecture

```mermaid
flowchart TD

Login

Home

Camera

Gallery

Prediction

History

Profile

Login --> Home

Home --> Camera

Home --> Gallery

Camera --> Prediction

Gallery --> Prediction

Prediction --> History

History --> Profile
```

---

# 8. Database Architecture

```mermaid
erDiagram

USER ||--o{ PREDICTION : creates

PREDICTION ||--o{ DAMAGE : contains

ROAD ||--o{ PREDICTION : has
```

---

# 9. Deployment Architecture

```mermaid
flowchart LR

Developer

Developer --> GitHub

GitHub --> Colab

Colab --> GoogleDrive

GoogleDrive --> Backend

Backend --> Flutter
```

---

# 10. Why This Architecture?

| Decision | Reason |
|-----------|--------|
| Flutter | Cross-platform mobile app |
| FastAPI | Lightweight, fast REST API |
| YOLOv8 | State-of-the-art object detection |
| XGBoost | Excellent tabular ML performance |
| PostgreSQL | Reliable relational database |
| Google Colab | Free GPU for training |
| Google Drive | Model and dataset storage |

---

# 11. Advantages

- Modular Design
- Easy to Extend
- Independent AI Module
- Independent Backend
- Reusable Components
- Better Testing
- Easy Deployment
- Maintainable Codebase

---

# Related Documents

- PROJECT_MASTER.md
- AI_MODULE.md
- APPLICATION_MODULE.md
- DEVELOPMENT_WORKFLOW.md
