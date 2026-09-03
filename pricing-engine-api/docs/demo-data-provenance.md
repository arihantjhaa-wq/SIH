# Demo Data Provenance & Methodology

## 1. Overview
The datasets located in `data/demo/mandi_prices.csv` and `data/demo/weather.csv` are **synthetic demo fixtures** designed to enable offline development, rigorous testing, and reliable live demonstration of the AgriDirect Pricing Engine MVP.

In compliance with the project's credibility guidelines:
- Every record originating from these files is explicitly tagged with `source = "demo_fixture"`.
- The dashboard and API responses derived from these records will display a clear **DEMO DATA** badge.
- Synthetic data is never represented as verified live market data.

## 2. Market Price Dataset (`mandi_prices.csv`)

### Parameters & Structure
- **Geography:** State of Maharashtra (7 mandis: Pune, Nashik, Lasalgaon, Vashi, Nagpur, Kolhapur, Ahmednagar).
- **Crops:** All 20 demo crops (Tomato, Onion, Potato, Rice, Wheat, Maize, Groundnut, Soybean, Mustard, Gram, Lentil, Pigeon Pea, Cabbage, Cauliflower, Green Chilli, Brinjal, Mango, Banana, Orange, Apple).
- **Time Horizon:** 140 days (April 14, 2026 to September 1, 2026), exceeding the 120-day requirement.
- **Total Records:** 19,605 daily observations.
- **Price Units:** Stored in canonical ₹/quintal (matching Agmarknet format). Converted to ₹/kg via `app.data.quality.to_kg()` for internal engine operations.

### Crop Volatility & Price Characteristics
| Crop | Category | Base Price (₹/quintal) | Base Price (₹/kg) | Volatility Model | Perishability / Shelf Life |
|---|---|---|---|---|---|
| Tomato | `fruit_veg` | ₹2,200 | ₹22.00 | High volatility ($\sigma=120$), 28-day cyclical harvest wave | 7 days |
| Onion | `fruit_veg` | ₹2,400 | ₹24.00 | Moderate volatility ($\sigma=85$), 45-day cycle | 30 days |
| Potato | `root` | ₹1,450 | ₹14.50 | Low volatility ($\sigma=40$), 60-day cycle | 60 days |
| Rice | `grain` | ₹3,300 | ₹33.00 | Very low volatility ($\sigma=25$), staple baseline | 365 days |
| Wheat | `grain` | ₹2,650 | ₹26.50 | Very low volatility ($\sigma=20$), staple baseline | 365 days |
| Maize | `grain` | ₹1,800 | ₹18.00 | Low volatility ($\sigma=60$), 60-day cycle | 180 days |
| Groundnut | `oilseed` | ₹5,500 | ₹55.00 | Moderate volatility ($\sigma=120$), 75-day cycle | 120 days |
| Soybean | `oilseed` | ₹4,200 | ₹42.00 | Moderate volatility ($\sigma=100$), 60-day cycle | 120 days |
| Mustard | `oilseed` | ₹5,000 | ₹50.00 | Moderate volatility ($\sigma=150$), 90-day cycle | 180 days |
| Gram | `pulse` | ₹5,200 | ₹52.00 | Moderate volatility ($\sigma=100$), 90-day cycle | 180 days |
| Lentil | `pulse` | ₹5,500 | ₹55.00 | Moderate volatility ($\sigma=120$), 90-day cycle | 180 days |
| Pigeon Pea | `pulse` | ₹6,500 | ₹65.00 | High volatility ($\sigma=200$), 75-day cycle | 180 days |
| Cabbage | `vegetable` | ₹1,200 | ₹12.00 | Low volatility ($\sigma=80$), 21-day cycle | 14 days |
| Cauliflower | `vegetable` | ₹1,500 | ₹15.00 | Moderate volatility ($\sigma=100$), 21-day cycle | 14 days |
| Green Chilli | `vegetable` | ₹3,500 | ₹35.00 | Very high volatility ($\sigma=300$), 14-day cycle | 7 days |
| Brinjal | `vegetable` | ₹1,800 | ₹18.00 | Moderate volatility ($\sigma=100$), 30-day cycle | 10 days |
| Mango | `fruit` | ₹3,000 | ₹30.00 | High volatility ($\sigma=250$), 60-day cycle | 10 days |
| Banana | `fruit` | ₹2,000 | ₹20.00 | Low volatility ($\sigma=80$), 30-day cycle | 14 days |
| Orange | `fruit` | ₹2,500 | ₹25.00 | Moderate volatility ($\sigma=150$), 45-day cycle | 21 days |
| Apple | `fruit` | ₹8,000 | ₹80.00 | Very high volatility ($\sigma=300$), 60-day cycle | 30 days |

### Regional Multipliers
- **Lasalgaon (0.93×):** Major agricultural production & onion hub.
- **Ahmednagar (0.95×), Nashik (0.96×), Kolhapur (0.97×), Nagpur (0.99×):** Regional collection and distribution mandis.
- **Pune (1.02×):** Major metropolitan consumption market.
- **Vashi (1.08×):** Mumbai terminal consumption market.

### Embedded Edge Cases for Quality Validation
The fixture includes deliberate edge cases on April 14, 2026:
1. **Missing Modal Price (Pune / Tomato):** `min_price = 2000`, `max_price = 2400`, `modal_price = NULL` $\rightarrow$ derives ₹2,200 and flags `is_derived_modal = True`.
2. **Inverted Min/Max (Nashik / Onion):** `min_price = 2600`, `max_price = 2200` $\rightarrow$ swap-corrects to min ₹2,200 / max ₹2,600.
3. **Non-Positive Price (Nagpur / Potato):** `modal_price = 0.0` $\rightarrow$ flags `is_flagged_outlier = True` and retains record in database while excluding it from training sets.
4. **Missing Modal Price (Pune / Cabbage):** `min_price = 1100`, `max_price = 1300`, `modal_price = NULL` $\rightarrow$ derives ₹1,200 for new crop validation.
5. **Inverted Min/Max (Nashik / Brinjal):** `min_price = 2000`, `max_price = 1600` $\rightarrow$ swap-corrects to min ₹1,600 / max ₹2,000.

---

## 3. Weather Dataset (`weather.csv`)
- **Total Records:** 980 daily observations across 7 mandis and 140 days.
- **Variables:** `rainfall_mm` (0 to 45 mm, reflecting monsoon dynamics in June/July/August) and `temp_max_c` (25°C to 38°C).
- **Source Tag:** `demo_fixture`.
