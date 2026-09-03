"""
Generate High-Quality Synthetic Demo Fixtures for AgriDirect Pricing Engine MVP.
Produces data/demo/mandi_prices.csv and data/demo/weather.csv with >= 130 days of observations.
"""
import math
import random
from datetime import date, timedelta
from pathlib import Path
import pandas as pd

random.seed(42)

BASE_DIR = Path(__file__).resolve().parent.parent
DEMO_DIR = BASE_DIR / "data" / "demo"
DEMO_DIR.mkdir(parents=True, exist_ok=True)

MANDIS = [
    {"name": "Pune", "district": "Pune", "code": "MH_PUNE", "lat": 18.520430, "lon": 73.856744, "base_mult": 1.02},
    {"name": "Nashik", "district": "Nashik", "code": "MH_NASHIK", "lat": 19.997453, "lon": 73.789802, "base_mult": 0.96},
    {"name": "Lasalgaon", "district": "Nashik", "code": "MH_LASALGAON", "lat": 20.147222, "lon": 74.228611, "base_mult": 0.93},  # Major onion hub
    {"name": "Vashi", "district": "Thane", "code": "MH_VASHI", "lat": 19.077065, "lon": 72.998604, "base_mult": 1.08},  # Urban terminal market
    {"name": "Nagpur", "district": "Nagpur", "code": "MH_NAGPUR", "lat": 21.145800, "lon": 79.088155, "base_mult": 0.99},
    {"name": "Kolhapur", "district": "Kolhapur", "code": "MH_KOLHAPUR", "lat": 16.704987, "lon": 74.243253, "base_mult": 0.97},
    {"name": "Ahmednagar", "district": "Ahmednagar", "code": "MH_AHMEDNAGAR", "lat": 19.094829, "lon": 74.747979, "base_mult": 0.95},
]

CROPS = [
    {
        "name": "Tomato",
        "category": "fruit_veg",
        "base_price": 2200.0,  # ₹/quintal (i.e. ₹22/kg)
        "volatility": 120.0,
        "trend_cycle": 28,  # Short crop cycle, high seasonality
        "shelf_life": 7
    },
    {
        "name": "Onion",
        "category": "fruit_veg",
        "base_price": 2400.0,  # ₹/quintal (i.e. ₹24/kg)
        "volatility": 85.0,
        "trend_cycle": 45,
        "shelf_life": 30
    },
    {
        "name": "Potato",
        "category": "root",
        "base_price": 1450.0,  # ₹/quintal (i.e. ₹14.5/kg)
        "volatility": 40.0,
        "trend_cycle": 60,
        "shelf_life": 60
    },
    {
        "name": "Rice",
        "category": "grain",
        "base_price": 3300.0,  # ₹/quintal (i.e. ₹33/kg)
        "volatility": 25.0,
        "trend_cycle": 90,
        "shelf_life": 365
    },
    {
        "name": "Wheat",
        "category": "grain",
        "base_price": 2650.0,  # ₹/quintal (i.e. ₹26.5/kg)
        "volatility": 20.0,
        "trend_cycle": 90,
        "shelf_life": 365
    },
    {
        "name": "Maize",
        "category": "grain",
        "base_price": 1800.0,  # ₹/quintal (i.e. ₹18/kg)
        "volatility": 60.0,
        "trend_cycle": 60,
        "shelf_life": 180
    },
    {
        "name": "Groundnut",
        "category": "oilseed",
        "base_price": 5500.0,  # ₹/quintal (i.e. ₹55/kg)
        "volatility": 120.0,
        "trend_cycle": 75,
        "shelf_life": 120
    },
    {
        "name": "Soybean",
        "category": "oilseed",
        "base_price": 4200.0,  # ₹/quintal (i.e. ₹42/kg)
        "volatility": 100.0,
        "trend_cycle": 60,
        "shelf_life": 120
    },
    {
        "name": "Mustard",
        "category": "oilseed",
        "base_price": 5000.0,  # ₹/quintal (i.e. ₹50/kg)
        "volatility": 150.0,
        "trend_cycle": 90,
        "shelf_life": 180
    },
    {
        "name": "Gram",
        "category": "pulse",
        "base_price": 5200.0,  # ₹/quintal (i.e. ₹52/kg)
        "volatility": 100.0,
        "trend_cycle": 90,
        "shelf_life": 180
    },
    {
        "name": "Lentil",
        "category": "pulse",
        "base_price": 5500.0,  # ₹/quintal (i.e. ₹55/kg)
        "volatility": 120.0,
        "trend_cycle": 90,
        "shelf_life": 180
    },
    {
        "name": "Pigeon Pea",
        "category": "pulse",
        "base_price": 6500.0,  # ₹/quintal (i.e. ₹65/kg)
        "volatility": 200.0,
        "trend_cycle": 75,
        "shelf_life": 180
    },
    {
        "name": "Cabbage",
        "category": "vegetable",
        "base_price": 1200.0,  # ₹/quintal (i.e. ₹12/kg)
        "volatility": 80.0,
        "trend_cycle": 21,
        "shelf_life": 14
    },
    {
        "name": "Cauliflower",
        "category": "vegetable",
        "base_price": 1500.0,  # ₹/quintal (i.e. ₹15/kg)
        "volatility": 100.0,
        "trend_cycle": 21,
        "shelf_life": 14
    },
    {
        "name": "Green Chilli",
        "category": "vegetable",
        "base_price": 3500.0,  # ₹/quintal (i.e. ₹35/kg)
        "volatility": 300.0,
        "trend_cycle": 14,
        "shelf_life": 7
    },
    {
        "name": "Brinjal",
        "category": "vegetable",
        "base_price": 1800.0,  # ₹/quintal (i.e. ₹18/kg)
        "volatility": 100.0,
        "trend_cycle": 30,
        "shelf_life": 10
    },
    {
        "name": "Mango",
        "category": "fruit",
        "base_price": 3000.0,  # ₹/quintal (i.e. ₹30/kg)
        "volatility": 250.0,
        "trend_cycle": 60,
        "shelf_life": 10
    },
    {
        "name": "Banana",
        "category": "fruit",
        "base_price": 2000.0,  # ₹/quintal (i.e. ₹20/kg)
        "volatility": 80.0,
        "trend_cycle": 30,
        "shelf_life": 14
    },
    {
        "name": "Orange",
        "category": "fruit",
        "base_price": 2500.0,  # ₹/quintal (i.e. ₹25/kg)
        "volatility": 150.0,
        "trend_cycle": 45,
        "shelf_life": 21
    },
    {
        "name": "Apple",
        "category": "fruit",
        "base_price": 8000.0,  # ₹/quintal (i.e. ₹80/kg)
        "volatility": 300.0,
        "trend_cycle": 60,
        "shelf_life": 30
    },
]

START_DATE = date(2026, 4, 15)
END_DATE = date(2026, 9, 1)
NUM_DAYS = (END_DATE - START_DATE).days + 1  # 140 days


def generate_data():
    price_records = []
    weather_records = []

    # 1. Generate daily weather observations for each mandi
    for day_idx in range(NUM_DAYS):
        current_date = START_DATE + timedelta(days=day_idx)
        # Seasonal weather variation: Monsoon onset in June/July/August
        is_monsoon = current_date.month in (6, 7, 8)
        base_temp = 32.0 if not is_monsoon else 29.0

        for mandi in MANDIS:
            rain_prob = 0.55 if is_monsoon else 0.15
            has_rain = random.random() < rain_prob
            rainfall_mm = round(random.uniform(2.0, 45.0), 1) if has_rain else 0.0
            temp_max = round(base_temp + random.uniform(-3.5, 4.0), 1)

            weather_records.append({
                "state": "Maharashtra",
                "district": mandi["district"],
                "market": mandi["name"],
                "agmarknet_code": mandi["code"],
                "obs_date": current_date.strftime("%Y-%m-%d"),
                "rainfall_mm": rainfall_mm,
                "temp_max_c": temp_max,
                "data_source": "demo_fixture"
            })

    # 2. Generate daily price observations for each crop and mandi
    for crop in CROPS:
        for mandi in MANDIS:
            current_modal = crop["base_price"] * mandi["base_mult"]
            for day_idx in range(NUM_DAYS):
                current_date = START_DATE + timedelta(days=day_idx)

                # Cyclical wave + random walk
                wave = math.sin(2 * math.pi * day_idx / crop["trend_cycle"]) * (crop["volatility"] * 1.8)
                step = random.gauss(0, crop["volatility"] * 0.3)
                
                # Mean reverting price
                target = (crop["base_price"] * mandi["base_mult"]) + wave
                current_modal = 0.85 * current_modal + 0.15 * target + step

                # Ensure positive sensible price
                current_modal = max(crop["base_price"] * 0.4, current_modal)
                modal_price = round(current_modal, 2)

                spread = random.uniform(0.04, 0.08)
                min_price = round(modal_price * (1.0 - spread), 2)
                max_price = round(modal_price * (1.0 + spread), 2)
                arrival_qty = round(random.uniform(150.0, 950.0), 1)

                price_records.append({
                    "state": "Maharashtra",
                    "district": mandi["district"],
                    "market": mandi["name"],
                    "agmarknet_code": mandi["code"],
                    "commodity": crop["name"],
                    "variety": "Other / Local",
                    "grade": "FAQ",
                    "arrival_date": current_date.strftime("%Y-%m-%d"),
                    "min_price": min_price,
                    "max_price": max_price,
                    "modal_price": modal_price,
                    "arrival_qty": arrival_qty,
                    "data_source": "demo_fixture"
                })

    # Add a few controlled edge-case fixtures at early dates to test quality pipeline
    # Edge case 1: Missing modal price (should derive from min & max)
    price_records.append({
        "state": "Maharashtra",
        "district": "Pune",
        "market": "Pune",
        "agmarknet_code": "MH_PUNE",
        "commodity": "Tomato",
        "variety": "Desi",
        "grade": "Medium",
        "arrival_date": "2026-04-14",
        "min_price": 2000.00,
        "max_price": 2400.00,
        "modal_price": None,  # Missing modal price -> derives 2200.00
        "arrival_qty": 400.0,
        "data_source": "demo_fixture"
    })

    # Edge case 2: Inverted min/max price (should swap correct)
    price_records.append({
        "state": "Maharashtra",
        "district": "Nashik",
        "market": "Nashik",
        "agmarknet_code": "MH_NASHIK",
        "commodity": "Onion",
        "variety": "Red",
        "grade": "FAQ",
        "arrival_date": "2026-04-14",
        "min_price": 2600.00,
        "max_price": 2200.00,  # Min > Max
        "modal_price": 2400.00,
        "arrival_qty": 500.0,
        "data_source": "demo_fixture"
    })

    # Edge case 3: Non-positive price (should flag as outlier)
    price_records.append({
        "state": "Maharashtra",
        "district": "Nagpur",
        "market": "Nagpur",
        "agmarknet_code": "MH_NAGPUR",
        "commodity": "Potato",
        "variety": "Local",
        "grade": "FAQ",
        "arrival_date": "2026-04-14",
        "min_price": 0.00,
        "max_price": 0.00,
        "modal_price": 0.00,  # Zero price
        "arrival_qty": 100.0,
        "data_source": "demo_fixture"
    })

    # Edge case 4: Missing modal price for new crop (Cabbage)
    price_records.append({
        "state": "Maharashtra",
        "district": "Pune",
        "market": "Pune",
        "agmarknet_code": "MH_PUNE",
        "commodity": "Cabbage",
        "variety": "Local",
        "grade": "FAQ",
        "arrival_date": "2026-04-14",
        "min_price": 1100.00,
        "max_price": 1300.00,
        "modal_price": None,  # Missing modal price -> derives 1200.00
        "arrival_qty": 300.0,
        "data_source": "demo_fixture"
    })

    # Edge case 5: Inverted min/max for new crop (Brinjal)
    price_records.append({
        "state": "Maharashtra",
        "district": "Nashik",
        "market": "Nashik",
        "agmarknet_code": "MH_NASHIK",
        "commodity": "Brinjal",
        "variety": "Local",
        "grade": "FAQ",
        "arrival_date": "2026-04-14",
        "min_price": 2000.00,
        "max_price": 1600.00,  # Min > Max
        "modal_price": 1800.00,
        "arrival_qty": 250.0,
        "data_source": "demo_fixture"
    })

    # Save to CSV
    prices_df = pd.DataFrame(price_records)
    weather_df = pd.DataFrame(weather_records)

    prices_path = DEMO_DIR / "mandi_prices.csv"
    weather_path = DEMO_DIR / "weather.csv"

    prices_df.to_csv(prices_path, index=False)
    weather_df.to_csv(weather_path, index=False)

    print(f"Generated {len(prices_df)} price records -> {prices_path}")
    print(f"Generated {len(weather_df)} weather records -> {weather_path}")


if __name__ == "__main__":
    generate_data()
