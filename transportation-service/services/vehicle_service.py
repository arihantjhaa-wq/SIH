from typing import Optional
from config import settings


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


def select_vehicle(quantity_kg: float) -> str:
    """
    Automatically select the smallest suitable vehicle based on quantity.

    Args:
        quantity_kg: Total weight of goods in kg

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

    for vehicle_id, config in sorted_vehicles:
        if quantity_kg <= config["capacity_kg"]:
            return vehicle_id

    # If we reach here, quantity exceeds the largest vehicle
    max_capacity = VEHICLE_CONFIGS["4"]["capacity_kg"]
    raise VehicleCapacityError(
        f"Order quantity ({quantity_kg:.1f} kg) exceeds the largest supported "
        f"vehicle capacity ({max_capacity} kg). Please split your order into "
        f"smaller shipments."
    )