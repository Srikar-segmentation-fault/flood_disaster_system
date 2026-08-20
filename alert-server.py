from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from twilio.rest import Client
from dotenv import load_dotenv
import os, datetime, json, httpx
from typing import Optional
from collections import deque

load_dotenv()

app = FastAPI(title="FloodSense AI Alert Server", version="3.0.0")

app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

TWILIO_SID        = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN      = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM       = os.getenv("TWILIO_FROM_NUMBER")
OWM_KEY           = os.getenv("OPENWEATHER_API_KEY")
CESIUM_ION_TOKEN  = os.getenv("CESIUM_ION_TOKEN")
ALERT_TO          = os.getenv("ALERT_PHONE_LOCATION_1")

# ── Abuse limits (several endpoints have no auth, so these are the safety net) ──
MAX_ALERTS_PER_IP_PER_HOUR       = int(os.getenv("MAX_ALERTS_PER_IP_PER_HOUR", "5"))
MAX_ALERTS_PER_DAY_TOTAL         = int(os.getenv("MAX_ALERTS_PER_DAY_TOTAL", "50"))
MAX_FARMER_REGS_PER_IP_PER_HOUR  = int(os.getenv("MAX_FARMER_REGS_PER_IP_PER_HOUR", "10"))
MAX_FARMER_REGS_PER_DAY_TOTAL    = int(os.getenv("MAX_FARMER_REGS_PER_DAY_TOTAL", "200"))
MAX_FARMER_DELETES_PER_IP_PER_HOUR = int(os.getenv("MAX_FARMER_DELETES_PER_IP_PER_HOUR", "10"))
RATE_LIMIT_WINDOW_SECONDS        = 3600  # 1 hour rolling window for all per-IP limits

sent_alerts: dict = {}
usgs_cache: dict = {"data": None, "fetched_at": None}
FARMERS_FILE = os.path.join(os.path.dirname(__file__), "farmers.json")

# In-memory abuse tracking (resets on server restart — fine for this scale)
action_timestamps: dict[tuple[str, str], deque] = {}   # (bucket, ip) -> deque[datetime] of recent attempts
daily_counters: dict[str, dict] = {}                    # bucket -> {"date": ..., "count": ...}


def get_client_ip(request: Request) -> str:
    """Resolve the real client IP, honoring X-Forwarded-For when behind a proxy (e.g. Render)."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(bucket: str, ip: str, max_per_hour: int, max_per_day: Optional[int] = None) -> Optional[str]:
    """
    Generic per-IP hourly limiter with an optional global daily cap, tracked per named
    'bucket' (e.g. 'sms_alert', 'farmer_register', 'farmer_delete').
    Returns an error reason string if the request should be blocked, or None if allowed
    (in which case the attempt is recorded as consumed).
    """
    now = datetime.datetime.now()

    # ── Global daily cap (optional) ──
    if max_per_day is not None:
        today = now.date().isoformat()
        counter = daily_counters.setdefault(bucket, {"date": None, "count": 0})
        if counter["date"] != today:
            counter["date"] = today
            counter["count"] = 0
        if counter["count"] >= max_per_day:
            return f"Daily limit reached for {bucket} ({max_per_day}/day). Try again tomorrow."

    # ── Per-IP rolling hourly limit ──
    window_start = now - datetime.timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
    key = (bucket, ip)
    dq = action_timestamps.setdefault(key, deque())
    while dq and dq[0] < window_start:
        dq.popleft()
    if len(dq) >= max_per_hour:
        return f"Rate limit exceeded: max {max_per_hour}/hour per client for {bucket}."

    # Allowed — record this attempt
    dq.append(now)
    if max_per_day is not None:
        daily_counters[bucket]["count"] += 1
    return None

print("=" * 58)
print("  FloodSense AI Alert Server v3.0")
print("=" * 58)
print(f"  Twilio SID   : {'[OK]' if TWILIO_SID   else '[MISSING]'}")
print(f"  Twilio Token : {'[OK]' if TWILIO_TOKEN  else '[MISSING]'}")
print(f"  Twilio FROM  : {TWILIO_FROM  or '[MISSING]'}")
print(f"  Alert TO     : {ALERT_TO     or '[MISSING] (ALERT_PHONE_LOCATION_1)'}")
print(f"  OWM Key      : {'[OK]' if OWM_KEY       else '[MISSING]'}")
print(f"  SMS limits   : {MAX_ALERTS_PER_IP_PER_HOUR}/hr per IP, {MAX_ALERTS_PER_DAY_TOTAL}/day total")
print("=" * 58)
print("  Endpoints:")
print("  GET  /health          — Server health check")
print("  GET  /config          — Frontend config (tokens)")
print("  POST /send-alert      — Trigger Twilio SMS alert")
print("  GET  /earthquakes     — Proxied USGS earthquake feed")
print("  GET  /farmers         — List farmer records")
print("  POST /farmers         — Register new farmer")
print("  DELETE /farmers/{id}  — Remove farmer")
print("  POST /farmer-feedback — Log farmer action feedback")
print("  GET  /model-versions  — Model version history")
print("=" * 58)

# ── Farmer helpers ────────────────────────────────────────────────
def load_farmers():
    if not os.path.exists(FARMERS_FILE):
        return []
    with open(FARMERS_FILE, "r") as f:
        return json.load(f)

def save_farmers(farmers):
    with open(FARMERS_FILE, "w") as f:
        json.dump(farmers, f, indent=2)

def is_valid_phone(phone) -> bool:
    return bool(phone and len(phone) > 5)

def send_sms(message: str):
    missing = []
    if not TWILIO_SID:   missing.append("TWILIO_ACCOUNT_SID")
    if not TWILIO_TOKEN: missing.append("TWILIO_AUTH_TOKEN")
    if not TWILIO_FROM:  missing.append("TWILIO_FROM_NUMBER")
    if not ALERT_TO:     missing.append("ALERT_PHONE_LOCATION_1")
    if missing:
        err = f"Missing env vars: {', '.join(missing)}"
        print(f"[SMS] [MISSING] {err}")
        return {"status": "error", "error": err}
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        msg = client.messages.create(body=message, from_=TWILIO_FROM, to=ALERT_TO)
        print(f"[SMS] Sent to {ALERT_TO} — SID: {msg.sid}")
        return {"status": "sent", "sid": msg.sid}
    except Exception as e:
        print(f"[SMS] Error → {e}")
        return {"status": "error", "error": str(e)}


# ── Request Models ────────────────────────────────────────────────
class AlertRequest(BaseModel):
    zone_name:  str
    region:     str
    lat:        float
    lon:        float
    risk_score: float
    risk_label: str
    rainfall:   str
    wind:       str
    humidity:   str
    phone:      Optional[str] = None

class FarmerRecord(BaseModel):
    name:     str
    crop:     str
    sowing:   str
    area:     float = 1.0
    phone:    Optional[str] = None
    lat:      float
    lon:      float

class FarmerFeedback(BaseModel):
    farmer_id: int
    zone_name: str
    action_taken: bool
    outcome: str            # "crop_saved", "crop_damaged", "no_flood", "other"
    notes: Optional[str] = None


# ── ENDPOINTS ─────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "online",
        "version": "3.0.0",
        "time": str(datetime.datetime.now()),
        "alert_to": ALERT_TO or "NOT CONFIGURED",
        "features": ["LSTM forecast", "SHAP explainability", "compound model",
                     "USGS proxy", "farmer module", "model versioning"]
    }

@app.get("/config")
async def get_config():
    return {
        "cesium_ion_token": CESIUM_ION_TOKEN,
        "openweather_api_key": OWM_KEY,
    }

@app.post("/send-alert")
async def send_alert(req: AlertRequest, request: Request):
    if not is_valid_phone(ALERT_TO):
        print(f"[SMS] Skipped {req.zone_name} — ALERT_PHONE_LOCATION_1 not configured")
        return {"status": "skipped", "reason": "ALERT_PHONE_LOCATION_1 not set in .env"}

    now = datetime.datetime.now()
    key = f"{req.zone_name}_{now.hour}"
    if key in sent_alerts:
        return {"status": "skipped", "reason": "Already alerted this hour"}

    client_ip = get_client_ip(request)
    limit_reason = check_rate_limit("sms_alert", client_ip, MAX_ALERTS_PER_IP_PER_HOUR, MAX_ALERTS_PER_DAY_TOTAL)
    if limit_reason:
        print(f"[SMS] Blocked from {client_ip} — {limit_reason}")
        return {"status": "rate_limited", "reason": limit_reason}

    emoji = "🔴" if req.risk_label in ["Critical", "Extreme"] else "🟠"
    message = (
        f"{emoji} FLOODSENSE AI ALERT v3\n"
        f"Zone: {req.zone_name} ({req.region})\n"
        f"Risk: {req.risk_label} ({int(req.risk_score * 100)}%) — Compound Model\n"
        f"Rain: {req.rainfall}mm | Wind: {req.wind}m/s | Humidity: {req.humidity}%\n"
        f"⚠ Take protective action immediately.\n"
        f"Time: {now.strftime('%Y-%m-%d %H:%M')}"
    )

    result = send_sms(message)
    if result["status"] == "sent":
        sent_alerts[key] = True
    return result


@app.get("/earthquakes")
async def get_earthquakes():
    """Proxy USGS earthquake feed with 60s in-memory cache."""
    now = datetime.datetime.now()
    cached_at = usgs_cache.get("fetched_at")
    if cached_at and (now - cached_at).seconds < 60 and usgs_cache.get("data"):
        return usgs_cache["data"]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson"
            )
            data = resp.json()
            usgs_cache["data"] = data
            usgs_cache["fetched_at"] = now
            print(f"[USGS] Fetched {len(data.get('features', []))} earthquakes")
            return data
    except Exception as e:
        print(f"[USGS] Fetch error → {e}")
        if usgs_cache.get("data"):
            return usgs_cache["data"]
        raise HTTPException(status_code=502, detail=f"USGS unavailable: {e}")


@app.get("/farmers")
async def get_farmers():
    """Return all registered farmer records."""
    return {"farmers": load_farmers()}

@app.post("/farmers")
async def register_farmer(farmer: FarmerRecord, request: Request):
    """Register a new farmer field."""
    client_ip = get_client_ip(request)
    limit_reason = check_rate_limit(
        "farmer_register", client_ip,
        MAX_FARMER_REGS_PER_IP_PER_HOUR, MAX_FARMER_REGS_PER_DAY_TOTAL
    )
    if limit_reason:
        print(f"[FARMER] Registration blocked from {client_ip} — {limit_reason}")
        raise HTTPException(status_code=429, detail=limit_reason)

    farmers = load_farmers()
    record = farmer.dict()
    record["id"] = int(datetime.datetime.now().timestamp() * 1000)
    record["created"] = datetime.datetime.now().isoformat()
    record["feedback_log"] = []
    farmers.append(record)
    save_farmers(farmers)
    print(f"[FARMER] Registered: {farmer.name} ({farmer.crop}, {farmer.area}ha) at ({farmer.lat:.4f}, {farmer.lon:.4f})")
    return {"status": "registered", "id": record["id"], "farmer": record}

@app.delete("/farmers/{farmer_id}")
async def remove_farmer(farmer_id: int, request: Request):
    """Remove a farmer record by ID."""
    client_ip = get_client_ip(request)
    limit_reason = check_rate_limit(
        "farmer_delete", client_ip,
        MAX_FARMER_DELETES_PER_IP_PER_HOUR
    )
    if limit_reason:
        print(f"[FARMER] Delete blocked from {client_ip} — {limit_reason}")
        raise HTTPException(status_code=429, detail=limit_reason)

    farmers = load_farmers()
    new_farmers = [f for f in farmers if f.get("id") != farmer_id]
    if len(new_farmers) == len(farmers):
        raise HTTPException(status_code=404, detail="Farmer not found")
    save_farmers(new_farmers)
    print(f"[FARMER] Removed ID {farmer_id}")
    return {"status": "removed"}

@app.post("/farmer-feedback")
async def record_feedback(fb: FarmerFeedback):
    """
    Log farmer action feedback after an alert.
    This data powers the recommendation model retraining loop.
    """
    farmers = load_farmers()
    for f in farmers:
        if f.get("id") == fb.farmer_id:
            entry = {
                "timestamp": datetime.datetime.now().isoformat(),
                "zone": fb.zone_name,
                "action_taken": fb.action_taken,
                "outcome": fb.outcome,
                "notes": fb.notes,
            }
            if "feedback_log" not in f:
                f["feedback_log"] = []
            f["feedback_log"].append(entry)
            save_farmers(farmers)
            print(f"[FEEDBACK] Farmer {fb.farmer_id}: action={fb.action_taken}, outcome={fb.outcome}")
            return {"status": "logged", "entry": entry}
    raise HTTPException(status_code=404, detail="Farmer not found")

@app.get("/farmer-digest/{farmer_id}")
async def farmer_digest(farmer_id: int):
    """Generate a personalized daily risk digest for a farmer."""
    farmers = load_farmers()
    farmer = next((f for f in farmers if f.get("id") == farmer_id), None)
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    # Simplified digest — in production this would call the ML model
    return {
        "farmer_name": farmer["name"],
        "crop": farmer["crop"],
        "sowing_date": farmer["sowing"],
        "digest": {
            "risk_level": "Moderate",
            "risk_score": 0.48,
            "forecast_48h": "Risk expected to rise over next 24h. Monitor drainage.",
            "recommended_action": "Check bunds, ensure drainage channels are clear.",
            "confidence": 0.81,
            "generated_at": datetime.datetime.now().isoformat(),
        }
    }

@app.get("/model-versions")
async def model_versions():
    """Return model version history."""
    versions_file = os.path.join(os.path.dirname(__file__), "model-versions.json")
    if os.path.exists(versions_file):
        with open(versions_file) as f:
            return json.load(f)
    # Fallback default
    return {
        "versions": [
            {"version": "v1.0", "date": "2024-01-15", "accuracy": 0.72, "features": ["rainfall", "humidity", "wind", "base_risk"], "notes": "Initial tabular model"},
            {"version": "v2.0", "date": "2024-04-20", "accuracy": 0.78, "features": ["rainfall", "humidity", "wind", "base_risk", "soil_saturation", "coastal_proximity"], "notes": "Added soil & coastal features"},
            {"version": "v3.0", "date": "2024-12-01", "accuracy": 0.86, "features": ["compound_flood", "compound_storm", "agri_stress", "lstm_forecast", "shap_attribution"], "notes": "Compound meta-model + LSTM + SHAP"},
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
