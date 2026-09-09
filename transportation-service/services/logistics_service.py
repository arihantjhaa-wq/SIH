import math
from datetime import datetime, timedelta
from config import settings
from services.vehicle_service import get_vehicle_config


def calculate_logistics_cost(distance_km: float, vehicle_id: str = "1") -> dict:
    """Calculate fuel, toll, and maintenance costs for a given distance and vehicle."""
    config = get_vehicle_config(vehicle_id)

    # 1. Direct Fuel Cost
    fuel_rate = settings.PETROL_PRICE if config["fuel_type"] == "petrol" else settings.DIESEL_PRICE
    litres_needed = distance_km / config["mileage_kmpl"] if config["mileage_kmpl"] > 0 else 0
    fuel_cost = litres_needed * fuel_rate

    # 2. Highway Tolls (only for distances > 40km)
    toll_cost = (distance_km * config["toll_per_km"]) if distance_km > 40 else 0.0

    # 3. Direct Maintenance & Wear Cost
    maintenance_cost = distance_km * config["maint_per_km"]

    total_cost = round(fuel_cost + toll_cost + maintenance_cost)

    return {
        "vehicle_type": config["name"],
        "fuel_type": config["fuel_type"].capitalize(),
        "fuel_cost_inr": f"₹{round(fuel_cost):,}",
        "fuel_cost_raw": round(fuel_cost),
        "estimated_tolls_inr": f"₹{round(toll_cost):,}",
        "toll_cost_raw": round(toll_cost),
        "maintenance_inr": f"₹{round(maintenance_cost):,}",
        "maintenance_raw": round(maintenance_cost),
        "total_estimated_trip_cost": f"₹{total_cost:,}",
        "total_cost_raw": total_cost,
    }


def format_time_duration(total_minutes: float) -> str:
    """Format duration in minutes to human-readable string."""
    total_mins = int(round(total_minutes))
    if total_mins < 60:
        return f"{total_mins} mins"
    elif total_mins < 1440:
        hours = total_mins // 60
        mins = total_mins % 60
        return f"{hours} hrs {mins} mins ({total_mins} mins total)"
    else:
        days = total_mins // 1440
        remainder_mins = total_mins % 1440
        hours = remainder_mins // 60
        mins = remainder_mins % 60
        return f"{days} day(s) {hours} hrs {mins} mins ({round(total_mins / 60, 1)} hrs total)"


def calculate_transit_time(
    traffic_seconds: int,
    vehicle_id: str = "1",
    departure_dt: datetime = None
) -> dict:
    """
    Calculate transit time including mandatory rest periods.

    Returns:
        Dictionary with:
        - active_travel_minutes: Driving time in minutes
        - layover_minutes: Mandatory rest in minutes
        - layover_hours: Layover in hours
        - layover_days: Number of overnight halts
        - total_transit_minutes: Total transit time in minutes
        - arrival_dt: Estimated arrival datetime
        - All formatted strings
    """
    config = get_vehicle_config(vehicle_id)
    active_travel_minutes = (traffic_seconds / 60.0) * config["speed_factor"]

    # Calculate mandatory rest (12 hours after every 10 hours of driving)
    active_travel_hours = active_travel_minutes / 60.0
    layover_days = math.floor(active_travel_hours / 10.0)
    layover_minutes = layover_days * 12.0 * 60.0

    total_transit_minutes = active_travel_minutes + layover_minutes

    # Calculate arrival
    if departure_dt:
        arrival_dt = departure_dt + timedelta(minutes=total_transit_minutes)
    else:
        arrival_dt = datetime.now() + timedelta(minutes=total_transit_minutes)

    return {
        "active_travel_minutes": active_travel_minutes,
        "active_travel_display": format_time_duration(active_travel_minutes),
        "layover_minutes": layover_minutes,
        "layover_hours": round(layover_minutes / 60),
        "layover_days": layover_days,
        "layover_display": f"{round(layover_minutes / 60)} hrs ({layover_days} night(s))" if layover_days > 0 else "None",
        "total_transit_minutes": total_transit_minutes,
        "total_transit_display": format_time_duration(total_transit_minutes),
        "arrival_dt": arrival_dt,
        "arrival_display": arrival_dt.strftime("%Y-%m-%d %I:%M %p"),
        "departure_display": departure_dt.strftime("%Y-%m-%d %I:%M %p") if departure_dt else None,
    }