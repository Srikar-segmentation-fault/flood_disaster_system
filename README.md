# 🌊 FloodSense AI — Smart Multi-Hazard Prediction System

> **FloodSense AI** is a real-time flood risk monitoring and alert system powered by compound ML models, LSTM forecasting, SHAP explainability, and live weather data. It sends SMS alerts via Twilio, displays flood risks on an interactive 3D globe using CesiumJS, and now includes dedicated **Analytics Dashboards** for deep Flood and Storm analysis.

---

## 🌐 Live Deployment

| Service | URL | Notes |
|---------|-----|-------|
| **Frontend (3D Globe + Dashboards)** | [flood-disaster-system-1.onrender.com](https://flood-disaster-system-1.onrender.com/) | Static site — open this to use the app |
| **Backend (FastAPI API)** | [flood-disaster-system.onrender.com](https://flood-disaster-system.onrender.com) | API only — no frontend UI, used internally by the site above |

---

## 📁 Project Structure

```text
flood system/
├── alert-server.py       # FastAPI backend server
├── index.html            # Frontend Single-Page App (Cesium 3D Globe + React Dashboards)
├── dashboard.html        # Original Dashboard file (now integrated into index.html)
├── datasets/             # ✨ NEW: Historical datasets (rainfall, storm tracks, etc.) for ML models
├── storm_model.py        # Storm prediction model (XGBoost + LSTM)
├── flood model.py        # Flood compound ML model
├── model-versions.json   # ML model version history
├── spa_merge.py          # Script used to merge views into a Single-Page App
├── .env                  # Environment variables (API keys)
└── README.md             # This file
```


---

## 🖥️ Frontend Pages (Single-Page Application)

We have recently migrated the interface into a **Single-Page Application (SPA)** architecture. This means the 3D Globe and the Analytics Dashboards are now unified under a single navigation bar, allowing instant switching between views without reloading the heavy Cesium globe.

### 🌐 3D Globe — `index.html`

The primary real-time monitoring interface:
- **CesiumJS 3D Globe** with live risk zone markers
- **Multi-hazard layers**: Flood, Storm, Earthquake (USGS), Wildfire, Cyclone Tracks
- **Real-time compound risk feed** with LSTM 48h forecasts
- **Farmer Module**: Register fields, get personalized SMS digest
- **Historical Replay**: Replay past disasters (Amphan, Fani, Tauktae...)
- **SHAP Explainability** in click-through tooltips

### 📊 Analytics Dashboards *(Integrated)*

A full React-powered analytics interface accessible directly from the unified top navbar:

#### 🌍 Overview Dashboard
- Global hazard activity doughnut chart
- FloodSense AI vs Traditional NWP radar comparison
- Real-time alert feed (all hazard types)
- ML model version summary & API health status

#### 🌊 Flood Intelligence Dashboard
- **Monthly Rainfall Distribution** — Monsoon cycle bar chart (2018–2025 avg)
- **Monthly Flood Risk Index** — Compound model line chart (0–100%)
- **LSTM 48h Flood Risk Forecast** — With 95% confidence bands
- **River Gauge Levels (Last 30 Days)** — Krishna & Brahmaputra multi-line
- **Year-on-Year Events & Impact** — Mixed bar+line chart
- **SHAP Feature Attribution** — Top 5 risk drivers visualized
- **Regional Risk Score Chart** — 8 Indian river basins ranked
- **Zone Monitoring Table** — Risk level, affected population, mini risk bars

#### 🌀 Storm Intelligence Dashboard
- **72h Wind Speed Track** — Current active storm history
- **Central Pressure History** — Inverted axis (lower = stronger storm)
- **Monthly Cyclone Frequency** — Climatological distribution (1990–2025)
- **Yearly Intensity Distribution** — Stacked bar by IMD category (Cat 1–5)
- **72h Forecast Wind Bars** — Color-coded by cyclone intensity class
- **SHAP Storm Feature Attribution** — XGBoost top risk factors
- **Regional Storm Risk** — Ocean basin horizontal bar chart
- **Historic Cyclone Table** — Amphan, Biparjoy, Mocha, Fani, Tauktae, Gaja

---

## ⚙️ Prerequisites

Make sure you have the following installed:

- **Python 3.9+** — [Download](https://www.python.org/downloads/)
- **pip** — comes with Python

---

## 🔧 Installation

### 1. Create and activate a virtual environment

```bash
# Create virtual environment
python -m venv .venv

# Activate on Windows
.venv\Scripts\activate

# Activate on macOS/Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install fastapi uvicorn python-dotenv twilio httpx pydantic
```

---

## 🔑 Environment Variables

Edit the `.env` file and fill in your credentials:

```env
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_FROM_NUMBER=+1your_twilio_number

OPENWEATHER_API_KEY=your_openweather_api_key
CESIUM_ION_TOKEN=your_cesium_ion_token

ALERT_PHONE_LOCATION_1=+91xxxxxxxxxx   # Primary alert recipient
ALERT_PHONE_LOCATION_2=+91xxxxxxxxxx   # Secondary alert recipient

# SMS abuse protection (since /send-alert has no auth) — optional, defaults shown
MAX_ALERTS_PER_IP_PER_HOUR=5           # Max alert requests from one IP per rolling hour
MAX_ALERTS_PER_DAY_TOTAL=50            # Hard cap on total SMS sent per day, across all clients

# Farmer endpoint abuse protection (since /farmers has no auth) — optional, defaults shown
MAX_FARMER_REGS_PER_IP_PER_HOUR=10     # Max farmer registrations from one IP per rolling hour
MAX_FARMER_REGS_PER_DAY_TOTAL=200      # Hard cap on total farmer registrations per day
MAX_FARMER_DELETES_PER_IP_PER_HOUR=10  # Max farmer deletions from one IP per rolling hour
```

> ⚠️ **Never commit your `.env` file to version control.**

---

## 🚀 Start Commands

### ▶️ Start the Backend Server

Activate the virtual environment first, then run:

```bash
# Option 1 — Run directly
python alert-server.py

# Option 2 — Run with uvicorn (with hot-reload)
uvicorn alert-server:app --host 0.0.0.0 --port 8000 --reload
```

The server will start at: **http://localhost:8000**

---

### 🌐 Serve the Frontend (Port 5500)

Use Python's built-in HTTP server to serve `index.html` on port **5500**:

```bash
# Using Python (recommended — no install needed)
python -m http.server 5500
```

Then open your browser and go to:
- **3D Globe** → **http://localhost:5500/index.html**
- **Analytics Dashboard** → **http://localhost:5500/dashboard.html** ✨

Alternatively, if you have Node.js installed:

```bash
# Using npx serve
npx serve -p 5500

# Using live-server (with auto-reload)
npx live-server --port=5500
```

> ✅ Make sure the backend server is running at **http://localhost:8000** before opening the frontend.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/health` | Server health check |
| `GET`  | `/config` | Frontend config (tokens) |
| `POST` | `/send-alert` | Trigger Twilio SMS flood alert |
| `GET`  | `/earthquakes` | Proxied USGS earthquake feed |
| `GET`  | `/farmers` | List all registered farmer records |
| `POST` | `/farmers` | Register a new farmer field |
| `DELETE` | `/farmers/{id}` | Remove a farmer record |
| `POST` | `/farmer-feedback` | Log farmer action feedback |
| `GET`  | `/farmer-digest/{id}` | Personalized daily risk digest |
| `GET`  | `/model-versions` | ML model version history |

---

## 🤖 ML Models

### Flood Compound Model (v3)
| Version | Date | Accuracy | Notes |
|---------|------|----------|-------|
| v1.0 | 2024-01-15 | 72% | Initial tabular model |
| v2.0 | 2024-04-20 | 78% | Added soil & coastal features |
| v3.0 | 2024-12-01 | 86% | Compound meta-model + LSTM + SHAP |

### Storm XGBoost + LSTM (v1)
- **XGBoost Classifier** — Storm risk probability from 8 meteorological features
- **LSTM Track Predictor** — 72h track (lat/lon/wind) from 72-hour history
- **SHAP Explainer** — Top 3 risk factors: wind speed, pressure gradient, SST
- **Features**: Wind speed, pressure, pressure gradient, humidity, SST, distance to coast, historical storm frequency, month

### Key Performance
| Metric | Value |
|--------|-------|
| Flood Model Accuracy | 86% |
| Storm Risk Score | 74% |
| LSTM Forecast (48h flood) | 91% |
| Advance Warning Lead Time | 34h |
| Traditional NWP Lead Time | 6–8h |

---

## 🔔 SMS Alert Format

When a flood risk is detected, alerts are sent in this format:

```
🔴 FLOODSENSE AI ALERT v3
Zone: Krishna Delta (Andhra Pradesh)
Risk: Critical (87%) — Compound Model
Rain: 45mm | Wind: 12m/s | Humidity: 95%
⚠ Take protective action immediately.
Time: 2024-12-01 14:30
```

---

## 🧪 Test the Server

After starting the server, open your browser and go to:

- **Health Check** → http://localhost:8000/health
- **Interactive API Docs** → http://localhost:8000/docs
- **ReDoc API Docs** → http://localhost:8000/redoc

---

## 📊 Dashboard Tech Stack

The new `dashboard.html` uses:

| Technology | Purpose |
|-----------|---------|
| **React 18** (CDN) | Component-based UI, page routing |
| **Babel Standalone** | JSX transpilation (no build step) |
| **Chart.js 4** | All charts (bar, line, doughnut, radar) |
| **chartjs-plugin-annotation** | Threshold reference lines |
| **Google Fonts** | Inter + JetBrains Mono |
| **Vanilla CSS** | Dark glassmorphism design system |

No build step or npm install required — just open `dashboard.html` in a browser or serve via HTTP server.

---

## 🛠️ Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | Run `pip install fastapi uvicorn python-dotenv twilio httpx pydantic` |
| `Port already in use` | Change port: `uvicorn alert-server:app --port 8001` |
| SMS not sending | Check `.env` — ensure all `TWILIO_*` variables are set |
| Cesium globe blank | Verify `CESIUM_ION_TOKEN` in `.env` is valid |
| CORS errors | Make sure the backend is running at `http://localhost:8000` |
| Dashboard charts blank | Open via HTTP server (not `file://`), requires CDN access |

---

## 📜 License

This project is for educational and research purposes.

---

> Built with ❤️ using FastAPI, React, Chart.js, CesiumJS, Twilio, OpenWeatherMap & USGS data.
