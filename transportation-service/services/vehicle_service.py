from typing import Optional  # noqa: F401 - kept for potential future use


# Vehicle configurations with capacity info (extracted from original CLI)
VEHICLE_CONFIGS = {
    "1": {
        "id": "1",
        "name": "Two-Wheeler / Delivery Bike (100cc - 150cc)",
        "fuel_type": "petrol",
        "mileage_kmpl": 45.0,
        "maint_per_km": 0.50,  # ₹0.50/km (Routine lube, brake pads, tire wear)
        "toll_per_km": 0.0,
        "speed_factor": 1.0,
        "capacity_kg": 150,
    },
    "2": {
        "id": "2",
        "name": "Light Mini-Truck (Tata Ace / Bolero - up to 1.5T)",
        "fuel_type": "diesel",
        "mileage_kmpl": 12.0,
        "maint_per_km": 2.00,  # ₹2.00/km (4 tires, oil/filters, basic wear)
        "toll_per_km": 0.8,
        "speed_factor": 1.25,
        "capacity_kg": 1500,
    },
    "3": {
        "id": "3",
        "name": "Medium Duty Truck (14ft - 19ft / 4-7 Ton)",
        "fuel_type": "diesel",
        "mileage_kmpl": 6.5,
        "maint_per_km": 3.50,  # ₹3.50/km (6 heavy tires, chassis grease, brake shoes)
        "toll_per_km": 1.6,
        "speed_factor": 1.35,
        "capacity_kg": 7000,
    },
    "4": {
        "id": "4",
        "name": "Heavy Commercial Vehicle (16T - 25T Multi-Axle)",
        "fuel_type": "diesel",
        "mileage_kmpl": 3.8,
        "maint_per_km": 5.50,  # ₹5.50/km (10-12 radial tires, axle lubricants, air filters)
        "toll_per_km": 2.8,
        "speed_factor": 1.45,
        "capacity_kg": 25000,
    },
}


class VehicleCapacityError(Exception):
    """Raised when order quantity exceeds all vehicle capacities."""
    pass


def get_vehicle_config(vehicle_id: str) -> dict:
    """Get vehicle configuration by ID."""
    return VEHICLE_CONFIGS.get(vehicle_id, VEHICLE_CONFIGS["1"])


def select_vehicle(quantity_kg: float, distance_km: float = None) -> str:
    """
    Automatically select the smallest suitable vehicle based on quantity and distance.

    Args:
        quantity_kg: Total weight of goods in kg
        distance_km: Distance in kilometers (optional, used for bike eligibility)

    Returns:
        Vehicle ID string ("1", "2", "3", or "4")

    Raises:
        VehicleCapacityError: If quantity exceeds all vehicle capacities
    """
    # Sort by capacity to pick smallest suitable
    sorted_vehicles = sorted(
        VEHICLE_CONFIGS.items(),
        key=lambda x: x[1]["capacity_kg"]
    )

    # Determine if distance is available for bike eligibility check
    distance_available = distance_km is not None and isinstance(distance_km, (int, float))

    for vehicle_id, config in sorted_vehicles:
        # Check weight capacity first
        if quantity_kg <= config["capacity_kg"]:
            # Special rule for bike (Two-Wheeler): only eligible if distance < 50 km
            if vehicle_id == "1" and distance_available:
                if distance_km >= 50:
                    # Bike not eligible for 50+ km, skip to next vehicle
                    continue
            # For bike when distance is not available, use safest existing behavior
            # (wait for actual calculated distance before deciding bike eligibility)
            elif vehicle_id == "1" and not distance_available:
                continue
            return vehicle_id

    # If we reach here, quantity exceeds the largest vehicle
    max_capacity = VEHICLE_CONFIGS["4"]["capacity_kg"]
    raise VehicleCapacityError(
        f"Order quantity ({quantity_kg:.1f} kg) exceeds the largest supported "
        f"vehicle capacity ({max_capacity} kg). Please split your order into "
        f"smaller shipments."
    )