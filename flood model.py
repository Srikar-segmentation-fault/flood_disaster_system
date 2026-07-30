"""
FloodSense AI — Flood Risk ML Model
Backend Development Brief — Colleague 1

Exposes predict_flood_risk(lat, lon) -> dict, called by POST /predict/flood
in alert-server.py every 60s per zone.

Env vars required (see shared .env):
    OPENWEATHER_API_KEY
"""

import os
import json
import pickle
from datetime import datetime, timedelta

import numpy as np
import requests
import shap
from sklearn.ensemble import RandomForestClassifier

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------

OWM_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
OWM_URL = "https://api.openweathermap.org/data/2.5/weather"
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
SRTM_URL = "https://api.opentopodata.org/v1/srtm30m"

MODEL_PATH = os.path.join(os.path.dirname(__file__), "flood_rf_model.pkl")
MODEL_VERSION = "v1.0"

FEATURE_NAMES = [
    "rainfall_1h",
    "rainfall_3h",
    "humidity",
    "wind_speed",
    "soil_moisture",
    "elevation",
    "river_proximity_km",
    "coastal_proximity_km",
    "flood_freq_index",
]

# Static lookup table for zone-level features that don't come from a live
# API (river/coastal proximity, historical flood frequency). In production
# this should be replaced with a proper geospatial lookup (e.g. a
# precomputed raster/GeoJSON join), and expanded with real EM-DAT /
# HDX FloodScan derived values.
STATIC_FEATURE_LOOKUP = {
    "default": {
        "river_proximity_km": 25.0,
        "coastal_proximity_km": 50.0,
        "flood_freq_index": 0.2,
    },
}


# ----------------------------------------------------------------------
# Live data fetchers
# ----------------------------------------------------------------------

def fetch_weather(lat: float, lon: float) -> dict:
    """Fetch rainfall, humidity, wind speed from OpenWeatherMap."""
    try:
        resp = requests.get(
            OWM_URL,
            params={"lat": lat, "lon": lon, "appid": OWM_API_KEY, "units": "metric"},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        rain = data.get("rain", {})
        return {
            "rainfall_1h": rain.get("1h", 0.0),
            "rainfall_3h": rain.get("3h", 0.0),
            "humidity": data.get("main", {}).get("humidity", 0.0),
            "wind_speed": data.get("wind", {}).get("speed", 0.0),
        }
    except requests.RequestException as e:
        print(f"[flood_model] OpenWeatherMap fetch failed: {e}")
        return {"rainfall_1h": 0.0, "rainfall_3h": 0.0, "humidity": 50.0, "wind_speed": 0.0}


def fetch_soil_moisture(lat: float, lon: float) -> dict:
    """Fetch soil moisture / evapotranspiration from NASA POWER."""
    try:
        end = datetime.utcnow().date()
        start = end - timedelta(days=1)
        resp = requests.get(
            NASA_POWER_URL,
            params={
                "parameters": "GWETPROF,EVPTRNS",
                "community": "AG",
                "longitude": lon,
                "latitude": lat,
                "start": start.strftime("%Y%m%d"),
                "end": end.strftime("%Y%m%d"),
                "format": "JSON",
            },
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        params = data.get("properties", {}).get("parameter", {})
        soil_series = params.get("GWETPROF", {})
        soil_moisture = list(soil_series.values())[-1] if soil_series else 0.3
        return {"soil_moisture": max(0.0, min(1.0, float(soil_moisture)))}
    except (requests.RequestException, ValueError, IndexError) as e:
        print(f"[flood_model] NASA POWER fetch failed: {e}")
        return {"soil_moisture": 0.3}


def fetch_elevation(lat: float, lon: float) -> dict:
    """Fetch terrain elevation from SRTM via OpenTopoData."""
    try:
        resp = requests.get(
            SRTM_URL, params={"locations": f"{lat},{lon}"}, timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
        elevation = data["results"][0]["elevation"]
        return {"elevation": float(elevation)}
    except (requests.RequestException, KeyError, IndexError) as e:
        print(f"[flood_model] SRTM fetch failed: {e}")
        return {"elevation": 100.0}


def get_static_features(lat: float, lon: float) -> dict:
    """Look up river proximity, coastal proximity, historical flood freq.
    Replace with a real geospatial join against EM-DAT / HDX data."""
    return dict(STATIC_FEATURE_LOOKUP["default"])


# ----------------------------------------------------------------------
# Feature vector assembly
# ----------------------------------------------------------------------

def build_feature_vector(lat: float, lon: float) -> np.ndarray:
    features = {}
    features.update(fetch_weather(lat, lon))
    features.update(fetch_soil_moisture(lat, lon))
    features.update(fetch_elevation(lat, lon))
    features.update(get_static_features(lat, lon))

    vector = [features[name] for name in FEATURE_NAMES]
    return np.array(vector).reshape(1, -1), features


# ----------------------------------------------------------------------
# Model loading / training
# ----------------------------------------------------------------------

def _train_placeholder_model() -> RandomForestClassifier:
    """Train a Random Forest on synthetic data as a placeholder until
    real EM-DAT-labeled historical data is wired in. Replace this with
    actual training on historical flood records before production use.
    """
    rng = np.random.RandomState(42)
    n_samples = 2000

    rainfall_1h = rng.exponential(5, n_samples)
    rainfall_3h = rainfall_1h * rng.uniform(1.5, 3.0, n_samples)
    humidity = rng.uniform(30, 100, n_samples)
    wind_speed = rng.exponential(4, n_samples)
    soil_moisture = rng.uniform(0, 1, n_samples)
    elevation = rng.exponential(150, n_samples)
    river_proximity = rng.exponential(20, n_samples)
    coastal_proximity = rng.exponential(60, n_samples)
    flood_freq = rng.uniform(0, 1, n_samples)

    X = np.column_stack(
        [rainfall_1h, rainfall_3h, humidity, wind_speed, soil_moisture,
         elevation, river_proximity, coastal_proximity, flood_freq]
    )

    risk_score = (
        0.30 * (rainfall_1h / rainfall_1h.max())
        + 0.20 * soil_moisture
        + 0.15 * (1 - elevation / elevation.max())
        + 0.15 * flood_freq
        + 0.10 * (1 - river_proximity / river_proximity.max())
        + 0.10 * humidity / 100
    )
    y = (risk_score > np.percentile(risk_score, 85)).astype(int)

    model = RandomForestClassifier(n_estimators=200, max_depth=12, random_state=42)
    model.fit(X, y)
    return model


def load_model() -> RandomForestClassifier:
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)

    model = _train_placeholder_model()
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    return model


_MODEL = load_model()
_EXPLAINER = shap.TreeExplainer(_MODEL)


# ----------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------

def predict_flood_risk(lat: float, lon: float) -> dict:
    X_input, feature_dict = build_feature_vector(lat, lon)

    flood_risk_score = float(_MODEL.predict_proba(X_input)[0][1])

    shap_values = _compute_shap_values(X_input)

    abs_shap = np.abs(shap_values[0])
    ranked = sorted(zip(FEATURE_NAMES, abs_shap), key=lambda x: x[1], reverse=True)
    top_3 = ranked[:3]

    total = sum(v for _, v in top_3) or 1.0
    top_factors = {
        _friendly_name(name): round(float(v) / total, 2) for name, v in top_3
    }

    return {
        "zone": f"{lat:.2f},{lon:.2f}",
        "lat": lat,
        "lon": lon,
        "flood_risk_score": round(flood_risk_score, 2),
        "top_factors": top_factors,
        "model_version": MODEL_VERSION,
    }


def _compute_shap_values(X_input):
    """Compute SHAP values for the input, handling both binary-classifier
    output shapes (list of arrays vs single array) across shap versions."""
    shap_values = _EXPLAINER.shap_values(X_input)
    if isinstance(shap_values, list):
        # shap_values[1] = contributions toward the positive (flood) class
        return shap_values[1]
    return shap_values


def _friendly_name(feature_name: str) -> str:
    mapping = {
        "rainfall_1h": "rainfall",
        "rainfall_3h": "rainfall",
        "humidity": "humidity",
        "wind_speed": "wind",
        "soil_moisture": "soil_moisture",
        "elevation": "elevation",
        "river_proximity_km": "river_proximity",
        "coastal_proximity_km": "coastal_proximity",
        "flood_freq_index": "flood_history",
    }
    return mapping.get(feature_name, feature_name)


if __name__ == "__main__":
    result = predict_flood_risk(16.5, 81.0)
    print(json.dumps(result, indent=2))
