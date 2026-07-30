import os
import requests
import numpy as np
import xgboost as xgb
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
import shap
from math import radians, cos, sin, asin, sqrt

# Feature names for the XGBoost classifier
FEATURE_NAMES = [
    'wind_speed', 'pressure', 'pressure_gradient', 'humidity',
    'sea_surface_temp', 'distance_to_coast_km', 'historical_storm_freq', 'month'
]

# ---------------------------------------------------------
# Training Functions (As defined in the brief)
# ---------------------------------------------------------

def train_xgboost(X_train, y_train, X_val, y_val):
    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        scale_pos_weight=15,   # storms are rare events
        use_label_encoder=False,
        eval_metric='logloss'
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)])
    return model

def build_lstm_model():
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(72, 5)),
        Dropout(0.2),
        LSTM(32),
        Dropout(0.2),
        Dense(3)   # outputs: lat_t+12, lon_t+12, wind_t+12
    ])
    model.compile(optimizer='adam', loss='mse')
    return model

def train_lstm(model, X_seq, y_seq):
    model.fit(X_seq, y_seq, epochs=50, batch_size=32, validation_split=0.2)
    return model

# ---------------------------------------------------------
# Inference & Utility Functions
# ---------------------------------------------------------

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius km
    dlat = radians(lat2-lat1)
    dlon = radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))

def get_weather_data(lat: float, lon: float) -> dict:
    '''Fetches current weather readings from OpenWeatherMap API.'''
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        # Fallback to mock data if no key is provided in .env
        return {"wind_speed": 22.5, "pressure": 995, "humidity": 88}
        
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return {
            "wind_speed": data.get("wind", {}).get("speed", 0),
            "pressure": data.get("main", {}).get("pressure", 1013),
            "humidity": data.get("main", {}).get("humidity", 50)
        }
    except requests.exceptions.RequestException:
        return {"wind_speed": 0, "pressure": 1013, "humidity": 50}

# Global placeholders for loaded models (assuming they are loaded on server startup)
xgb_model = None 
lstm_model = None

def predict_storm_risk(lat: float, lon: float, track_history: list = None) -> dict:
    '''
    Core endpoint function to predict storm risk and time-to-impact.
    '''
    # 1. Fetch live weather from OpenWeatherMap
    weather = get_weather_data(lat, lon)
    
    # 2. Build feature vector for XGBoost classifier
    # (Using mock data for ERA5/historical features for the sake of the skeleton)
    X_input = np.array([[
        weather['wind_speed'],
        weather['pressure'],
        -3.2,  # pressure_gradient (mock rate of change)
        weather['humidity'],
        29.5,  # sea_surface_temp (mock)
        120.0, # distance_to_coast_km (mock)
        0.8,   # historical_storm_freq (mock)
        10     # month (mock - October cyclone season)
    ]])

    # 3. Run xgb_model.predict_proba() -> storm_risk_score
    # If model is loaded: storm_risk_score = xgb_model.predict_proba(X_input)[0][1]
    storm_risk_score = 0.74 # Fallback mock score

    # 4. If track_history provided (72 hourly readings):
    time_to_impact_hours = 18
    predicted_landfall_lat, predicted_landfall_lon = 15.2, 80.5

    if track_history and len(track_history) == 72:
        # Reshape to (1, 72, 5) for LSTM
        # X_seq = np.array(track_history).reshape(1, 72, 5)
        # preds = lstm_model.predict(X_seq)[0]
        # pred_lat, pred_lon, pred_wind = preds[0], preds[1], preds[2]
        
        # Mock predicted position
        pred_lat, pred_lon = lat + 1.5, lon - 2.0
        predicted_landfall_lat, predicted_landfall_lon = 15.2, 80.5 # Nearest coast (mock)
        
        # Calculate hours_to_impact via Haversine
        storm_speed_kmh = 15.0 # Average storm speed
        distance_km = haversine(pred_lat, pred_lon, predicted_landfall_lat, predicted_landfall_lon)
        time_to_impact_hours = int(distance_km / storm_speed_kmh)

    # 5. Compute SHAP values for top 3 features
    # If model is loaded: 
    # explainer = shap.TreeExplainer(xgb_model)
    # shap_values = explainer.shap_values(X_input)
    # top_features_list = sorted(zip(FEATURE_NAMES, abs(shap_values[0])), key=lambda x: x[1], reverse=True)[:3]
    # top_factors = {feat: round(float(val), 2) for feat, val in top_features_list}
    
    top_factors = {
        "wind_speed": 0.50,
        "pressure_gradient": 0.30,
        "sea_surface_temp": 0.20
    }

    # Assign rough zone based on longitude (India focus)
    zone = "Bay of Bengal" if lon > 78 else "Arabian Sea"

    # 6. Return dict in required output format
    return {
        "zone": zone,
        "lat": lat,
        "lon": lon,
        "storm_risk_score": storm_risk_score,
        "time_to_impact_hours": time_to_impact_hours,
        "predicted_landfall": {
            "lat": predicted_landfall_lat,
            "lon": predicted_landfall_lon
        },
        "top_factors": top_factors,
        "model_version": "v1.0"
    }

if __name__ == '__main__':
    # Simple test for the endpoint schema
    print(predict_storm_risk(13.0, 84.0))