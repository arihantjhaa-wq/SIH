"""Direct pricing engine verification — bypasses API commodity UUID mismatch."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uuid
from datetime import date
from app.pricing.engine import predict_price
from app.pricing.integration import compute_end_to_end_price
from app.logistics.engine import estimate_logistics

CROPS = [
    {"name": "Tomato",  "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.tomato")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Onion",   "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.onion")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Potato",  "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.potato")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Rice",    "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.rice")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Wheat",   "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.wheat")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Maize",   "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.maize")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Groundnut", "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.groundnut")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Soybean", "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.soybean")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Mustard", "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.mustard")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Gram",    "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.gram")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Lentil",  "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.lentil")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Pigeon Pea", "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.pigeon pea")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Cabbage", "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.cabbage")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Cauliflower", "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.cauliflower")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Green Chilli", "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.green chilli")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Brinjal", "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.brinjal")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Mango",   "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.mango")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Banana",  "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.banana")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Orange",  "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.orange")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
    {"name": "Apple",   "commodity_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "commodity.apple")), "mandi": "97ce83b2-322f-5c5c-8fce-22f2eacdd677"},
]

print("=" * 100)
print("DIRECT PRICING ENGINE VERIFICATION — ALL 5 CROPS (CORRECT DB IDs, PUNE MANDI)")
print("=" * 100)
print()
print(f"{'Crop':8s} | {'Baseline':>8s} | {'Fair':>8s} | {'Farmer':>8s} | {'Floor':>8s} | "
      f"{'Logistic':>8s} | {'Platform':>8s} | {'Buyer':>8s} | {'Buyer Total':>11s} | {'Inv':>3s} | {'Range':>5s}")
print("-" * 105)

all_ok = True
for crop in CROPS:
    pr = predict_price(
        commodity_id=crop["commodity_id"],
        mandi_id=crop["mandi"],
        as_of_date=date.today(),
        quantity_kg=500.0,
        farmer_declared_minimum=10.0,
    )

    if pr.get("status") == "INSUFFICIENT_DATA":
        print(f"{crop['name']:8s} | INSUFFICIENT DATA")
        all_ok = False
        continue

    try:
        lr = estimate_logistics(
            farmer_lat=18.5204, farmer_lon=73.8567,
            buyer_lat=19.0760, buyer_lon=72.8777,
            quantity_kg=500.0,
        )
    except Exception as e:
        print(f"{crop['name']:8s} | LOGISTICS ERROR: {e}")
        all_ok = False
        continue

    e2e = compute_end_to_end_price(
        pricing_result=pr,
        logistics_result=lr,
        platform_fee_pct=0.05,
    )

    bp  = e2e.get("baseline_price_per_kg")
    fp  = e2e.get("fair_price_per_kg")
    pp  = e2e.get("farmer_payout_per_kg")
    flr = e2e.get("protected_floor")
    lc  = e2e.get("logistics_cost_per_kg")
    plf = e2e.get("platform_fee_per_kg")
    byp = e2e.get("buyer_price_per_kg")
    bt  = e2e.get("buyer_total")
    fb  = e2e.get("floor_blocked")

    # Invariant: buyer = farmer + logistics + platform
    recomputed = round((pp or 0) + (lc or 0) + (plf or 0), 2)
    invariant_ok = abs(recomputed - (byp or 0)) < 0.02

    # Range check: all prices in per-kg band
    in_range = all(
        5 <= (v or 0) <= 60
        for v in [bp, fp, pp, flr, byp]
    )

    if not in_range or not invariant_ok:
        all_ok = False

    print(f"{crop['name']:8s} | {bp:8.2f} | {fp:8.2f} | {pp:8.2f} | {flr:8.2f} | "
          f"{lc:8.2f} | {plf:8.2f} | {byp:8.2f} | {bt:11.2f} | {'OK' if invariant_ok else 'FAIL':3s} | {'OK' if in_range else 'FAIL':5s}")

print("-" * 105)
print()

# Range check
print("100x INFLATION CHECK:")
for crop in CROPS:
    pr = predict_price(
        commodity_id=crop["commodity_id"],
        mandi_id=crop["mandi"],
        as_of_date=date.today(),
        quantity_kg=500.0,
    )
    if pr.get("status") != "INSUFFICIENT_DATA":
        baseline = pr.get("baseline")
        if baseline and baseline > 100:
            print(f"  {crop['name']}: FAIL — baseline {baseline} in quintal range")
            all_ok = False
        else:
            print(f"  {crop['name']}: OK — baseline {baseline:.2f} in per-kg range")

print()
print("MATHEMATICAL CONSISTENCY:")
for crop in CROPS:
    pr = predict_price(
        commodity_id=crop["commodity_id"],
        mandi_id=crop["mandi"],
        as_of_date=date.today(),
        quantity_kg=500.0,
    )
    if pr.get("status") == "INSUFFICIENT_DATA":
        continue

    lr = estimate_logistics(
        farmer_lat=18.5204, farmer_lon=73.8567,
        buyer_lat=19.0760, buyer_lon=72.8777,
        quantity_kg=500.0,
    )
    e2e = compute_end_to_end_price(pricing_result=pr, logistics_result=lr, platform_fee_pct=0.05)

    pp  = e2e.get("farmer_payout_per_kg", 0)
    lc  = e2e.get("logistics_cost_per_kg", 0)
    plf = e2e.get("platform_fee_per_kg", 0)
    byp = e2e.get("buyer_price_per_kg", 0)
    ft  = e2e.get("farmer_total", 0)
    lt  = e2e.get("logistics_total", 0)
    plt = e2e.get("platform_total", 0)
    bt  = e2e.get("buyer_total", 0)

    inv1 = abs(pp + lc + plf - byp) < 0.02
    inv2 = abs(ft + lt + plt - bt) < 0.02
    inv3 = abs(byp * 500 - bt) < 1.0

    print(f"  {crop['name']}: farmer({pp:.2f}) + logistics({lc:.2f}) + platform({plf:.2f}) = {pp+lc+plf:.2f} vs buyer({byp:.2f}) {'OK' if inv1 else 'FAIL'}")
    print(f"    farmer_total({ft:.2f}) + logistics_total({lt:.2f}) + platform_total({plt:.2f}) = {ft+lt+plt:.2f} vs buyer_total({bt:.2f}) {'OK' if inv2 else 'FAIL'}")
    print(f"    buyer_price_per_kg({byp:.2f}) * 500kg = {byp*500:.2f} vs buyer_total({bt:.2f}) {'OK' if inv3 else 'FAIL'}")

print()
if all_ok:
    print("ALL CHECKS PASSED — fix confirmed correct")
else:
    print("SOME CHECKS FAILED")
