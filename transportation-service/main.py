"""
AgriDirect Transportation Service — FastAPI

Converts the transportation algorithm from a CLI script into an automatic
backend service integrated into the marketplace flow.

Endpoints:
  GET  /api/v1/health          — Health check
  POST /api/v1/transport/route — Transportation quote

The service:
  1. Auto-selects vehicle based on quantity_kg (no manual selection)
  2. Calls Google Maps Directions API for route + polyline
  3. Calculates logistics costs (fuel, toll, maintenance)
  4. Calculates transit time and ETA

Google Maps API key is READ from .env — never exposed to frontend.
"""

import os
import sys
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import uvicorn
from dotenv import load_dotenv

# Load environment variables before importing config
load_dotenv()

from config import settings
from services.vehicle_service import (
    select_vehicle,
    get_vehicle_config,
    VehicleCapacityError,
    VEHICLE_CONFIGS,
)
from services.routing_service import (
    get_route_from_google_maps,
    GoogleMapsError,
)
from services.logistics_service import (
    calculate_logistics_cost,
    calculate_transit_time,
    format_time_duration,
)


# ==============================================================================
# FastAPI App
# ==============================================================================

app = FastAPI(
    title="AgriDirect Transportation Service",
    description="Automatic transportation scheduling for AgriDirect marketplace",
    version="1.0.0",
)

# CORS — allow marketplace backend (port 7200) to call this service
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Marketplace backend is internal; allow for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================================================
# Request / Response Models
# ==========================================================================

class TransportRouteRequest(BaseModel):
    origin_address: str = Field(
        ..., description="Farmer/origin address (resolved server-side from product ownership)"
    )
    destination_address: str = Field(
        ..., description="Consumer/destination address (from authenticated consumer record)"
    )
    quantity_kg: float = Field(
        ..., gt=0, description="Total quantity in kg for vehicle selection"
    )
    departure_datetime: Optional[str] = Field(
        None, description="ISO 8601 departure timestamp; defaults to server time if omitted"
    )

    @validator("origin_address", "destination_address")
    def validate_address(cls, v):
        if not v or not v.strip():
            raise ValueError("Address cannot be empty")
        return v.strip()


class TransportRouteResponse(BaseModel):
    # Addresses
    origin_address: str
    destination_address: str

    # Vehicle
    vehicle: dict

    # Route
    distance_km: float
    distance_display: str
    route_polyline: str
    route_points: list

    # Timing
    active_travel_minutes: float
    active_travel_display: str
    layover_minutes: float
    layover_display: str
    layover_hours: int
    layover_days: int
    total_transit_minutes: float
    total_transit_display: str
    scheduled_departure: str
    scheduled_departure_display: str
    estimated_arrival: str
    estimated_arrival_display: str

    # Costs
    fuel_type: str
    fuel_cost: int
    fuel_cost_display: str
    toll_cost: int
    toll_cost_display: str
    maintenance_cost: int
    maintenance_cost_display: str
    total_transportation_cost: int
    total_transportation_cost_display: str


# ==========================================================================
# Routes
# ==========================================================================

@app.get("/")
def root():
    return {"service": "AgriDirect Transportation Service", "version": "1.0.0"}


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": "transportation-service",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/v1/transport/route", response_model=TransportRouteResponse)
def calculate_transport_route(request: TransportRouteRequest):
    """
    Calculate automated transportation quote.

    The marketplace backend (NOT the frontend) calls this endpoint after
    resolving trusted origin (farmer address), destination (consumer address),
    quantity, and departure time server-side.
    """
    # Validate quantity
    if request.quantity_kg <= 0 or request.quantity_kg > 1000000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid quantity. Must be between 0 and 1,000,000 kg.",
        )

    # Parse departure time (server time if not provided)
    departure_dt: datetime
    if request.departure_datetime:
        try:
            departure_dt = datetime.fromisoformat(request.departure_datetime.replace("Z", "+00:00"))
            # Keep timezone info so .timestamp() computes correct UTC seconds.
            # Stripping tzinfo caused Python to interpret UTC values as local time,
            # shifting the Unix timestamp backward by the local UTC offset.
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid departure_datetime format: {request.departure_datetime}. Expected ISO 8601 (e.g. 2026-09-08T15:35:00).",
            )
    else:
        departure_dt = datetime.now()

    # 1. Automatic vehicle selection
    try:
        vehicle_id = select_vehicle(request.quantity_kg)
    except VehicleCapacityError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    vehicle_config = get_vehicle_config(vehicle_id)

    # 2. Call Google Maps Directions API
    try:
        route_data = get_route_from_google_maps(
            request.origin_address, request.destination_address, departure_dt
        )
    except GoogleMapsError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Route calculation failed: {str(e)}",
        )

    distance_km = route_data["distance_km"]
    traffic_seconds = route_data["duration_seconds"]

    # 3. Calculate logistics costs
    cost_data = calculate_logistics_cost(distance_km, vehicle_id)

    # 4. Calculate transit time (including mandatory rest)
    transit_data = calculate_transit_time(traffic_seconds, vehicle_id, departure_dt)

    # 5. Build response
    return TransportRouteResponse(
        # Addresses (normalized by Google)
        origin_address=route_data["origin_address"],
        destination_address=route_data["destination_address"],
        # Vehicle
        vehicle={
            "id": vehicle_id,
            "name": vehicle_config["name"],
            "fuel_type": cost_data["fuel_type"],
            "mileage_kmpl": vehicle_config["mileage_kmpl"],
            "capacity_kg": vehicle_config["capacity_kg"],
        },
        # Route
        distance_km=round(distance_km, 1),
        distance_display=f"{distance_km:.1f} km",
        route_polyline=route_data["route_polyline"],
        route_points=route_data["route_points"],
        # Timing
        active_travel_minutes=round(transit_data["active_travel_minutes"], 1),
        active_travel_display=transit_data["active_travel_display"],
        layover_minutes=transit_data["layover_minutes"],
        layover_display=transit_data["layover_display"],
        layover_hours=transit_data["layover_hours"],
        layover_days=transit_data["layover_days"],
        total_transit_minutes=round(transit_data["total_transit_minutes"], 1),
        total_transit_display=transit_data["total_transit_display"],
        scheduled_departure=departure_dt.isoformat(),
        scheduled_departure_display=transit_data["departure_display"],
        estimated_arrival=transit_data["arrival_dt"].isoformat(),
        estimated_arrival_display=transit_data["arrival_display"],
        # Costs
        fuel_type=cost_data["fuel_type"],
        fuel_cost=cost_data["fuel_cost_raw"],
        fuel_cost_display=cost_data["fuel_cost_inr"],
        toll_cost=cost_data["toll_cost_raw"],
        toll_cost_display=cost_data["estimated_tolls_inr"],
        maintenance_cost=cost_data["maintenance_raw"],
        maintenance_cost_display=cost_data["maintenance_inr"],
        total_transportation_cost=cost_data["total_cost_raw"],
        total_transportation_cost_display=cost_data["total_estimated_trip_cost"],
    )


# =============================================================================
# CLI Fallback (for manual testing — NOT used by the integrated marketplace)
# =============================================================================

def _cli_main():
    """
    Legacy CLI is preserved for manual testing only.
    The integrated application uses the FastAPI endpoints exclusively.
    """
    print("=" * 60)
    print("   INDIAN ROUTE, TRAFFIC & TRANSPORTATION COST ENGINE")
    print("   (CLI mode — for manual testing)")
    print("=" * 60)

    orig = input("Enter Origin Address (or PIN): ").strip()
    dest = input("Enter Destination Address (or PIN): ").strip()

    print("\nSelect Vehicle Type:")
    for vid, cfg in VEHICLE_CONFIGS.items():
        print(f"  [{vid}] {cfg['name']} (capacity {cfg['capacity_kg']} kg)")
    choice = input("Enter Choice (1-4) [Default: 1]: ").strip() or "1"

    print("\nSelect Departure Timing:")
    print("  - Press [Enter] for Immediate Departure ('now')")
    print("  - Or enter date/time (Format: YYYY-MM-DD HH:MM, e.g. 2026-09-08 06:00)")
    date_input = input("Departure: ").strip()

    if not date_input:
        departure_time = datetime.now()
    else:
        try:
            departure_time = datetime.strptime(date_input, "%Y-%m-%d %H:%M")
        except ValueError:
            print("Invalid date format. Defaulting to current time.")
            departure_time = datetime.now()

    # Use the FastAPI calculation path for consistency
    req = TransportRouteRequest(
        origin_address=orig,
        destination_address=dest,
        quantity_kg=VEHICLE_CONFIGS.get(choice, VEHICLE_CONFIGS["1"])["capacity_kg"] / 2,
        departure_datetime=departure_time.isoformat(),
    )
    # If CLI choice is explicit, override auto-selected vehicle
    from services.logistics_service import calculate_logistics_cost as calc_cost

    if choice in VEHICLE_CONFIGS:
        route_data = get_route_from_google_maps(orig, dest, departure_time)
        cost_data = calc_cost(route_data["distance_km"], choice)
        transit_data = calculate_transit_time(route_data["duration_seconds"], choice, departure_time)
        print("\n" + "-" * 60)
        print(f"Origin Address              : {route_data['origin_address']}")
        print(f"Destination Address         : {route_data['destination_address']}")
        print(f"Road Distance               : {route_data['distance_km']:.1f} km")
        print(f"Active Travel Time          : {transit_data['active_travel_display']}")
        print(f"Mandatory Rest / Halts      : {transit_data['layover_display']}")
        print(f"Total Transit Time          : {transit_data['total_transit_display']}")
        print(f"Scheduled Departure         : {transit_data['departure_display']}")
        print(f"Estimated Delivery Arrival  : {transit_data['arrival_display']}")
        print(f"\n--- Vehicle Cost Breakdown ---")
        print(f"Vehicle Profile             : {cost_data['vehicle_type']}")
        print(f"Est. {cost_data['fuel_type']} Expense   : {cost_data['fuel_cost_inr']}")
        print(f"Est. FASTag Tolls           : {cost_data['estimated_tolls_inr']}")
        print(f"Maintenance & Servicing     : {cost_data['maintenance_inr']}")
        print(f"Total Transportation Cost   : {cost_data['total_estimated_trip_cost']}")
        print("-" * 60)
    else:
        print(f"[Error]: Invalid vehicle choice: {choice}")


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    # Check if run with --cli flag for manual testing
    if "--cli" in sys.argv:
        _cli_main()
    else:
        port = int(os.getenv("PORT", "8001"))
        print(f"Starting AgriDirect Transportation Service on port {port}...")
        uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)