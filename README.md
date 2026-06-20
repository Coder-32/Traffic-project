<div align="center">

# 🚦 TrafficSense — Bengaluru Live Incident Command

**AI-powered real-time traffic incident prediction, management, and resource deployment platform for Bengaluru**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python)](https://python.org)
[![NGBoost](https://img.shields.io/badge/Model-NGBoost-orange?style=flat-square)](https://stanfordmlgroup.github.io/ngboost/)
[![Gemini](https://img.shields.io/badge/LLM-Gemini%201.5-4285F4?style=flat-square&logo=google)](https://aistudio.google.com)
[![Leaflet](https://img.shields.io/badge/Maps-Leaflet.js-199900?style=flat-square&logo=leaflet)](https://leafletjs.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

![TrafficSense Dashboard](https://raw.githubusercontent.com/Coder-32/Traffic-project/main/docs/screenshot.png)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [API Reference](#-api-reference)
- [ML Model](#-ml-model)
- [Dataset](#-dataset)
- [Frontend Tabs](#-frontend-tabs)
- [Configuration](#-configuration)
- [Contributing](#-contributing)

---

## 🌟 Overview

TrafficSense is a full-stack **Traffic Incident Command System** built for Bengaluru's urban traffic management. It combines:

- **NGBoost ML model** trained on the ASTRAM traffic dataset to predict incident duration and severity
- **Google Gemini LLM** for natural-language incident analysis and contextual briefings
- **Real-time WebSocket** stream for live incident feeds across all clients
- **Interactive Leaflet.js map** for geospatial incident visualization with routing
- **5-tab dashboard** covering Live Map, Event Forecast, Deployment Plan, Analytics, and Resource Management

The system allows traffic control operators to:
1. Report new incidents (with AI-predicted severity, duration, and officer requirements)
2. View live incidents on an interactive map
3. Forecast impact of scheduled events (IPL matches, concerts, rallies)
4. Manage and deploy field resources (personnel, vehicles, equipment)
5. Review historical analytics with Chart.js visualizations

---

## ✨ Features

### 🗺️ Live Incident Map
- Real-time Leaflet.js map centered on Bengaluru
- Color-coded incident markers (High / Medium / Low priority)
- Sliding incident detail drawer with full prediction metadata
- **Smart Route Planner**: Calculates alternative routes avoiding active incidents using Leaflet Routing Machine
- Live congestion hotspot overlay (GeoJSON polygon clusters)
- Risk timeline bar showing predicted peak hours

### 📅 Event Forecast
- Submit upcoming events (venue, crowd size, time window)
- AI pipeline (NGBoost + Gemini) generates:
  - Predicted jam duration and radius
  - LLM severity score (0–1)
  - Affected junctions and corrridors
  - Operational mitigation recommendations
- Mini-map preview of predicted affected zones

### 📋 Deployment Plan
- Full officer roster with live assignment status
- Confirm / release resource allocations per incident
- Visual deployment map showing officer positions
- Export deployment plan as text file

### 📊 Analytics
- **KPI Cards**: Total incidents, avg predicted duration, most affected junction, peak hour
- **Charts** (Chart.js):
  - Incidents by Event Cause (horizontal bar)
  - Incident Timeline (30-day line chart)
  - Congestion Heatmap by Hour (bar with colour gradient)
  - Model Performance: Predicted vs Actual (canvas line chart)
- **Post-Event Review Table**: Paginated, sortable, filterable incident history from backend

### 📦 Resource Management
- Inventory grouped by **Personnel / Vehicles / Equipment**
- Availability progress bars (green → amber → red)
- Inline editing of resource totals (PATCH API)
- Add new resources via modal form
- Active deployment tracker per incident
- City-wide resource summary stats

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        FRONTEND  (Vanilla HTML/CSS/JS)             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────┐  ┌────────┐  │
│  │ Live Map │  │Forecast  │  │Deployment│  │Anal- │  │Resour- │  │
│  │(Leaflet) │  │(LLM Form)│  │  Plan    │  │ytics │  │  ces   │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──┬───┘  └───┬────┘  │
│       │             │             │            │          │       │
│       └─────────────┴─────────────┴────────────┴──────────┘       │
│                         REST API  +  WebSocket                     │
└──────────────────────────────────┬─────────────────────────────────┘
                                   │ HTTP / WS
┌──────────────────────────────────▼─────────────────────────────────┐
│                     BACKEND  (FastAPI + Python)                    │
│  ┌─────────────┐  ┌────────────┐  ┌──────────┐  ┌─────────────┐  │
│  │  /incidents │  │  /predict  │  │/analytics│  │  /resources │  │
│  └─────────────┘  └─────┬──────┘  └────┬─────┘  └─────────────┘  │
│                         │              │                           │
│  ┌──────────────────┐   │   ┌──────────▼──────────┐               │
│  │  NGBoost Model   │◄──┘   │   SQLite Database   │               │
│  │  (.pkl files)    │       │   (SQLAlchemy ORM)  │               │
│  └──────────────────┘       └─────────────────────┘               │
│                                                                    │
│  ┌──────────────────┐  ┌───────────────────────────┐              │
│  │  Gemini LLM API  │  │  WebSocket Broadcast Mgr  │              │
│  │  (llm_agent.py)  │  │  (websocket_manager.py)   │              │
│  └──────────────────┘  └───────────────────────────┘              │
└────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend Framework** | FastAPI 0.111+ |
| **ML Model** | NGBoost (Probabilistic Gradient Boosting) |
| **Spatial Index** | NumPy vectorised Haversine over ASTRAM dataset |
| **LLM Integration** | Google Gemini 1.5 Flash (`google-generativeai`) |
| **Database** | SQLite via SQLAlchemy ORM |
| **Real-time** | WebSockets (native FastAPI) |
| **Frontend** | Vanilla HTML5 + CSS3 + JavaScript (ES2022) |
| **Maps** | Leaflet.js 1.9.4 + Leaflet Routing Machine 3.2.12 |
| **Charts** | Chart.js (CDN) |
| **Fonts** | Google Fonts – Inter |
| **Model Serialization** | Joblib |

---

## 📂 Project Structure

```
traffic-project/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── database.py                # SQLAlchemy engine & session
│   ├── db_models.py               # ORM models + seeding
│   ├── schemas.py                 # Pydantic request/response models
│   ├── model.py                   # NGBoost loader + spatial resolver
│   ├── llm_agent.py               # Gemini LLM integration
│   ├── websocket_manager.py       # WebSocket broadcast manager
│   ├── requirements.txt
│   ├── .env.example               # Environment variable template
│   ├── traffic.db                 # SQLite database (auto-created)
│   ├── models/
│   │   ├── ngboost_traffic_model.pkl   # Trained NGBoost model (~1.4 MB)
│   │   ├── label_encoder_cause.pkl     # LabelEncoder for event_cause
│   │   └── label_encoder_priority.pkl  # LabelEncoder for priority
│   ├── data/
│   │   ├── processed_astram_with_graph_AND_history.csv   # Spatial index (~5.6 MB)
│   │   ├── hotspots.json          # GeoJSON cluster hotspots
│   │   └── risk_table.json        # Pre-computed risk timeline
│   └── routers/
│       ├── __init__.py
│       ├── incidents.py           # Report / resolve / list incidents
│       ├── predict.py             # Full prediction pipeline
│       ├── analytics.py           # Summary stats, charts, timeline
│       ├── resources.py           # Resource inventory & allocation
│       ├── routing.py             # Smart route calculation
│       └── predictions.py        # Legacy predictions endpoint
│
└── frontend/
    ├── index.html                 # Main dashboard (all 5 tabs, self-contained)
    ├── index.css                  # Global stylesheet
    ├── app.js                     # Auxiliary dashboard logic
    ├── livemap.html               # Standalone live map page
    ├── livemap.css                # Livemap styles
    └── livemap.js                 # Livemap logic
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- `pip` package manager
- Google Gemini API key ([get one free here](https://aistudio.google.com/app/apikey))

### 1. Clone the Repository

```bash
git clone https://github.com/Coder-32/Traffic-project.git
cd Traffic-project
```

### 2. Set Up the Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy the template
cp .env.example .env

# Edit .env and add your Gemini API key
# GEMINI_API_KEY=your_real_key_here
```

### 4. Start the Backend Server

```bash
# From the backend/ directory
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

### 5. Open the Frontend

Simply open `frontend/index.html` in your browser:
```bash
# Windows
start frontend/index.html

# macOS
open frontend/index.html

# Or serve with Python
python -m http.server 8080 --directory frontend
# Then visit http://localhost:8080
```

> **Note:** The frontend connects to `http://localhost:8000` by default. Ensure the backend is running before opening the frontend.

---

## 📡 API Reference

### Incidents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/incidents/report` | Report a new incident (triggers AI prediction) |
| `GET` | `/incidents/active` | List all currently active incidents |
| `GET` | `/incidents/history` | Paginated incident history with filters |
| `POST` | `/incidents/resolve/{id}` | Resolve an incident and release its resources |

### Predictions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/predict/event` | Full event-impact forecast (NGBoost + Gemini) |
| `POST` | `/predict/batch` | Batch duration prediction |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/analytics/summary` | KPI summary (total incidents, peak hour, etc.) |
| `GET` | `/analytics/by_cause` | Incident counts grouped by event cause |
| `GET` | `/analytics/by_hour` | Incident counts by hour of day (0-23) |
| `GET` | `/analytics/incidents_timeline` | 30-day incident count timeline |
| `GET` | `/analytics/hotspots` | GeoJSON hotspot clusters |
| `GET` | `/analytics/risk_timeline` | Risk table by cause × hour |

### Resources

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/resources` | All resources grouped by category |
| `POST` | `/resources` | Create a new resource |
| `PATCH` | `/resources/{id}` | Update resource total count |
| `POST` | `/resources/allocate` | Allocate resources to an incident |
| `POST` | `/resources/release` | Release allocated resources |
| `GET` | `/resources/summary` | City-wide resource summary stats |
| `GET` | `/resources/active-deployments` | All active resource allocations |

### Routing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/routing/smart` | Calculate smart route avoiding incidents |
| `GET` | `/routing/context/{junction}` | Get resource context for a junction |

---

## 🤖 ML Model

### NGBoost Traffic Duration Predictor

The model predicts **jam duration (minutes)** for a traffic incident.

**Input Features (21 total):**

| # | Feature | Description |
|---|---------|-------------|
| 1 | `event_cause_enc` | Label-encoded incident cause |
| 2 | `priority_enc` | Label-encoded priority level |
| 3 | `hour_of_day` | Hour when incident was reported (0–23) |
| 4–19 | `spatial_emb_0` to `spatial_emb_15` | 16-dim spatial embedding from ASTRAM spatial index |
| 20 | `historical_incident_count` | Historical incident count at nearest junction |
| 21 | `historical_median_duration` | Historical median duration at nearest junction |

**Spatial Resolution Pipeline:**
1. Incoming incident coordinates → vectorised Haversine distance to all 26,000+ ASTRAM rows
2. If nearest point ≤ 500m → exact match embeddings
3. If nearest point 500m–1000m → proximity-averaged embeddings
4. If no point within 1km → global average embeddings

**Supported Event Causes:**
- `vehicle_breakdown` · `accident` · `tree_fall` · `public_event` · `waterlogging` · `road_works` · `signal_failure` · `others`

**Supported Priorities:** `High` · `Medium` · `Low`

---

## 📊 Dataset

### ASTRAM Traffic Dataset (`processed_astram_with_graph_AND_history.csv`)

The dataset is a processed version of the **ASTRAM (Advanced Signal Traffic and Road Management)** Bengaluru dataset enriched with:
- 16-dimensional graph-based spatial embeddings per junction
- Historical incident count and median duration per location
- Latitude/longitude of ~26,000+ data points across Bengaluru

**Key columns used:**

| Column | Type | Description |
|--------|------|-------------|
| `latitude` / `longitude` | float | Geographic coordinates |
| `junction` | string | Junction/area name |
| `spatial_emb_0` … `spatial_emb_15` | float | Graph neural embedding features |
| `historical_incident_count` | int | Past incidents at this location |
| `historical_median_duration` | float | Historical median jam duration (mins) |

---

## 🖥️ Frontend Tabs

| Tab | ID | Description |
|-----|----|-------------|
| 🗺️ **Live Incident Map** | `viewLiveMap` | Leaflet map with real-time incident markers, incident drawer, routing, hotspot overlay |
| 📅 **Event Forecast** | `viewForecast` | Event impact form → AI prediction results with gauge and junction list |
| 📋 **Deployment Plan** | `viewDeployment` | Officer assignment table, deployment map, resource allocation confirm/release |
| 📊 **Analytics** | `viewAnalytics` | KPI cards + 4 Chart.js charts + sortable post-event review table |
| 📦 **Resources** | `viewResources` | Inventory management + active deployments + city-wide summary |

---

## ⚙️ Configuration

### Backend Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | ✅ Yes | — | Google Gemini API key for LLM analysis |
| `PORT` | ❌ No | `8000` | Port for uvicorn server |

### Frontend Configuration

The frontend reads from `BASE_URL` defined at the top of the inline `<script>` in `index.html`:

```javascript
const BASE_URL = 'http://localhost:8000';
```

Change this to your deployed backend URL for production.

---

## 🗄️ Database

SQLite is used with SQLAlchemy. The database (`traffic.db`) is automatically created and seeded with default resources on first startup.

**Tables:**
- `incidents` — All reported traffic incidents with predictions
- `resources` — Resource inventory (personnel, vehicles, equipment)
- `allocations` — Resource allocation tracking per incident

To reset the database:
```bash
rm backend/traffic.db
# Restart the server — it will recreate and re-seed automatically
```

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ❤️ for Bengaluru's traffic management  
**NGBoost × Gemini × FastAPI × Leaflet.js**

</div>
