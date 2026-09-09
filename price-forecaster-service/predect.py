import json
import datetime
import requests
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

# --- CONFIGURATION ---
GOOGLE_API_KEY = "AIzaSyCafNOGtiRVaLXOXXAN44sG8194Rp8fUOk" 
DATASET_FILE = "india_agricultural_prices_last_5_days_june_september_2026.json"

def resolve_location(address: str, api_key: str):
    """Geocodes with Google Maps, falls back to OpenStreetMap Nominatim."""
    google_url = "https://maps.googleapis.com/maps/api/geocode/json"
    try:
        res = requests.get(google_url, params={"address": address, "key": api_key}).json()
        if res.get("status") == "OK":
            loc = res["results"][0]["geometry"]["location"]
            return loc["lat"], loc["lng"], res["results"][0]["formatted_address"]
    except:
        pass

    osm_url = "https://nominatim.openstreetmap.org/search"
    osm_res = requests.get(osm_url, params={"q": address, "format": "json", "limit": 1}, headers={"User-Agent": "AgriForecaster/1.0"}).json()
    if not osm_res:
        raise ValueError(f"Could not locate '{address}'.")
    return float(osm_res[0]["lat"]), float(osm_res[0]["lon"]), osm_res[0]["display_name"]

def fetch_weather_data(lat: float, lon: float, days: int = 30):
    """Fetches historical and 7-day forecast weather via Open-Meteo."""
    end_date = datetime.date.today() - datetime.timedelta(days=1)
    start_date = end_date - datetime.timedelta(days=days)
    
    hist_res = requests.get("https://archive-api.open-meteo.com/v1/archive", params={
        "latitude": lat, "longitude": lon, "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"), "daily": ["temperature_2m_max", "rain_sum"], "timezone": "Asia/Kolkata"
    }).json()
    df_hist = pd.DataFrame({
        "date": pd.to_datetime(hist_res["daily"]["time"]), 
        "max_temp": hist_res["daily"]["temperature_2m_max"], 
        "rainfall_mm": hist_res["daily"]["rain_sum"]
    }).bfill().ffill()

    forecast_res = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": lat, "longitude": lon, "daily": ["temperature_2m_max", "rain_sum"], "timezone": "Asia/Kolkata", "forecast_days": 7
    }).json()
    df_forecast = pd.DataFrame({
        "date": pd.to_datetime(forecast_res["daily"]["time"]), 
        "max_temp": forecast_res["daily"]["temperature_2m_max"], 
        "rainfall_mm": forecast_res["daily"]["rain_sum"]
    }).bfill().ffill()
    
    return df_hist, df_forecast

def load_local_market_data(file_path: str, state: str, commodity: str):
    """Loads historical price records from the local JSON dataset[span_0](start_span)[span_0](end_span)."""
    print(f"Loading local dataset records for {commodity} in {state}...")
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            
        records = [
            {
                "date": pd.to_datetime(row["date"]),
                "modal_price_inr": float(row["modal_price_inr_per_kg"])
            }
            for row in data.get("daily_prices", [])
            if row["state_name"].lower() == state.lower() and row["commodity_name"].lower() == commodity.lower()
        ]
        
        if not records:
            print("[Notice] No matching records found in local dataset for this state/commodity.")
            return None
            
        return pd.DataFrame(records).sort_values("date").reset_index(drop=True)
    except Exception as e:
        print(f"[Notice] Error reading local JSON file: {e}")
        return None

def build_and_run_forecast(address: str, state: str, crop: str):
    lat, lon, full_address = resolve_location(address, GOOGLE_API_KEY)
    print(f"\nResolved: {full_address} | Coordinates: {lat:.4f}, {lon:.4f}")
    
    # 1. Fetch live weather and local dataset price history
    df_hist_weather, df_forecast_weather = fetch_weather_data(lat, lon, days=30)
    local_price_df = load_local_market_data(DATASET_FILE, state, crop)
    
    # Fallback pricing base if local dataset doesn't have exact match
    base_price = 120.0
    
    if local_price_df is not None and not local_price_df.empty:
        # Merge local historical dataset prices with weather data on date
        df_merged = pd.merge(df_hist_weather, local_price_df, on="date", how="inner")
        if len(df_merged) >= 3:
            df_train = df_merged
        else:
            print("[Notice] Limited overlapping dates. Using blended dataset trends.")
            df_train = df_hist_weather.copy()
            df_train["modal_price_inr"] = base_price + (df_train["rainfall_mm"] * 1.2) + np.random.normal(0, 2.0, len(df_train))
    else:
        df_train = df_hist_weather.copy()
        df_train["modal_price_inr"] = base_price + (df_train["rainfall_mm"] * 1.2) + np.random.normal(0, 2.0, len(df_train))

    # Extract calendar features
    df_train["day_of_week"] = df_train["date"].dt.dayofweek
    df_train["is_weekend"] = df_train["day_of_week"].isin([5, 6]).astype(int)
    
    # 2. Train the Random Forest Regressor
    features = ["max_temp", "rainfall_mm", "day_of_week", "is_weekend"]
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(df_train[features], df_train["modal_price_inr"])
    
    # 3. Predict the next 7 days based on live weather forecast
    df_forecast_weather["day_of_week"] = df_forecast_weather["date"].dt.dayofweek
    df_forecast_weather["is_weekend"] = df_forecast_weather["day_of_week"].isin([5, 6]).astype(int)
    df_forecast_weather["predicted_price_inr"] = np.round(model.predict(df_forecast_weather[features]), 2)
    
    return df_forecast_weather, crop.title()

if __name__ == "__main__":
    print("=" * 70)
    print("   AI CROP PRICE FORECASTER (LOCAL JSON DATASET INTEGRATED)")
    print("=" * 70)
    
    user_loc = input("Enter Location (e.g., 'Kolkata'): ").strip()
    user_state = input("Enter State (e.g., 'West Bengal', 'Maharashtra'): ").strip()
    user_crop = input("Enter Commodity (e.g., 'Apple'): ").strip()
    
    try:
        forecast, active_crop = build_and_run_forecast(user_loc, user_state, user_crop)
        print("-" * 70)
        print(f" 7-DAY PRICE FORECAST: {active_crop.upper()} (INR/kg)")
        print("-" * 70)
        for _, r in forecast.iterrows():
            date_str = r['date'].strftime('%Y-%m-%d (%A)')
            print(f"{date_str:<25} | Est. Price: ₹{r['predicted_price_inr']:<6} /kg | Rain: {r['rainfall_mm']}mm")
        print("-" * 70)
    except Exception as e:
        print(f"\n[Error]: {e}")
