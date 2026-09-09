import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    GOOGLE_MAPS_API_KEY: str
    PORT: int = 8001
    HOST: str = "0.0.0.0"

    # Fuel rate baselines (INR/Litre)
    DIESEL_PRICE: float = 94.0
    PETROL_PRICE: float = 104.0

    # Vehicle capacity limits (kg) - used for automatic vehicle selection
    VEHICLE_CAPACITIES: dict = {
        "1": 150,       # Two-Wheeler / Bike: 150 kg max
        "2": 1500,      # Light Mini-Truck: 1.5T = 1500 kg
        "3": 7000,      # Medium Truck: 4-7 Ton = 7000 kg
        "4": 25000,     # Heavy Freight: 16T-25T = 25000 kg
    }

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()