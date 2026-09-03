"""Live API verification script for all 5 crops after unit normalization fix."""
import httpx
import json
import sys
import time

BASE_URL = "http://localhost:8000/api/v1/pricing/estimate"

# Each commodity maps to a specific mandi in the API route
# Use locations that map to mandis with data
COMMODITY_TESTS = [
    {
        "crop": "Tomato",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Onion",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Potato",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Rice",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Wheat",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Maize",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Groundnut",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Soybean",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Mustard",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Gram",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Lentil",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Pigeon Pea",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Cabbage",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Cauliflower",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Green Chilli",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Brinjal",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Mango",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Banana",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Orange",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
    {
        "crop": "Apple",
        "farmer_lat": 18.5204,
        "farmer_lon": 73.8567,
        "buyer_lat": 19.0760,
        "buyer_lon": 72.8777,
    },
]


def check_crop(test):
    """Test one crop and return the result."""
    body = {
        "commodity": test["crop"],
        "quantity_kg": 500.0,
        "farmer_location": {"lat": test["farmer_lat"], "lon": test["farmer_lon"]},
        "buyer_location": {"lat": test["buyer_lat"], "lon": test["buyer_lon"]},
        "farmer_declared_minimum": 10.0,
        "platform_fee_pct": 0.05,
    }

    try:
        resp = httpx.post(BASE_URL, json=body, timeout=10.0)
        return resp.status_code, resp.json()
    except Exception as e:
        return 0, {"error": str(e)}


def main():
    print("=" * 72)
    print("LIVE API VERIFICATION — POST NORMALIZATION FIX")
    print("=" * 72)
    print()

    all_ok = True
    results = []

    for test in COMMODITY_TESTS:
        crop = test["crop"]
        status_code, data = check_crop(test)

        if status_code == 200:
            bp = data.get("baseline_price_per_kg")
            fp = data.get("fair_price_per_kg")
            pp = data.get("farmer_payout_per_kg")
            pf = data.get("protected_floor")
            lc = data.get("logistics_cost_per_kg")
            plf = data.get("platform_fee_per_kg")
            byp = data.get("buyer_price_per_kg")
            bt = data.get("buyer_total")
            ft = data.get("farmer_total")
            fb = data.get("floor_blocked")
            rs = data.get("reliability_score")
            ma = data.get("ml_available")

            # Check invariant: buyer = farmer + logistics + platform
            recomputed = round((pp or 0) + (lc or 0) + (plf or 0), 2)
            invariant_ok = abs(recomputed - (byp or 0)) < 0.02

            # Check all prices are in plausible per-kg range
            in_range = all(
                5 <= (v or 0) <= 60
                for v in [bp, fp, pp, pf, byp]
            )

            results.append({
                "crop": crop,
                "baseline": bp,
                "fair_price": fp,
                "farmer_payout": pp,
                "floor": pf,
                "logistics": lc,
                "platform_fee": plf,
                "buyer_price": byp,
                "buyer_total": bt,
                "farmer_total": ft,
                "floor_blocked": fb,
                "reliability": rs,
                "invariant_ok": invariant_ok,
                "in_range": in_range,
            })

            status_icon = "OK" if (invariant_ok and in_range) else "WARN"
            if not (invariant_ok and in_range):
                all_ok = False

            print(f"  {crop:8s} | baseline={bp:6.2f} fair={fp:6.2f} farmer={pp:6.2f} "
                  f"floor={pf:6.2f} logistics={lc:5.2f} platform={plf:5.2f} "
                  f"buyer={byp:6.2f} | invariant={'OK' if invariant_ok else 'FAIL':3s} "
                  f"range={'OK' if in_range else 'FAIL':3s} [{status_icon}]")
        else:
            detail = data.get("detail", data)
            results.append({"crop": crop, "error": detail, "invariant_ok": False, "in_range": False})
            all_ok = False
            print(f"  {crop:8s} | HTTP {status_code} - {json.dumps(detail)[:100]}")

    print()
    print("-" * 72)

    # Summary table
    print()
    print(f"{'Crop':8s} | {'Baseline':>8s} | {'Fair':>8s} | {'Farmer':>8s} | {'Floor':>8s} | "
          f"{'Logistic':>8s} | {'Platform':>8s} | {'Buyer':>8s} | {'Buyer Total':>11s}")
    print("-" * 90)
    for r in results:
        if "error" in r:
            print(f"{r['crop']:8s} | {'ERROR':>8s}")
        else:
            print(f"{r['crop']:8s} | {r['baseline']:8.2f} | {r['fair_price']:8.2f} | "
                  f"{r['farmer_payout']:8.2f} | {r['floor']:8.2f} | "
                  f"{r['logistics']:8.2f} | {r['platform_fee']:8.2f} | "
                  f"{r['buyer_price']:8.2f} | {r['buyer_total']:11.2f}")

    print()

    # Verify all prices are NOT in quintal range (would indicate 100x bug)
    quintal_check = True
    for r in results:
        if "error" not in r:
            for key in ["baseline", "fair_price", "farmer_payout", "floor", "buyer_price"]:
                if (r.get(key) or 0) > 100:
                    print(f"  ALERT: {r['crop']} {key}={r[key]} is in quintal range — 100x BUG PRESENT")
                    quintal_check = False
                    all_ok = False

    if quintal_check:
        print("  All prices confirmed in per-kg range (< 100) — no 100x inflation detected.")

    # Mathematical consistency checks
    print()
    print("  MATHEMATICAL CONSISTENCY CHECKS:")
    for r in results:
        if "error" not in r:
            # buyer = farmer + logistics + platform
            expected = r["farmer_payout"] + r["logistics"] + r["platform_fee"]
            actual = r["buyer_price"]
            ok = abs(expected - actual) < 0.02
            print(f"    {r['crop']:8s} farmer({r['farmer_payout']:.2f}) + logistics({r['logistics']:.2f}) "
                  f"+ platform({r['platform_fee']:.2f}) = {expected:.2f} vs buyer({actual:.2f}) {'OK' if ok else 'FAIL'}")

    print()
    if all_ok:
        print("  ALL CHECKS PASSED")
    else:
        print("  SOME CHECKS FAILED — review above output")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
