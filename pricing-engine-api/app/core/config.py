import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://agridirect:agridirect@localhost:5432/agridirect"
)

# Application Mode
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes")

# External APIs
AGMARKNET_API_KEY = os.getenv("AGMARKNET_API_KEY", "")
AGMARKNET_BASE_URL = os.getenv(
    "AGMARKNET_BASE_URL",
    "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
)
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")

# Service configuration
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Config and Data File Paths
CONFIGS_DIR = BASE_DIR / "configs"
CROPS_CONFIG_PATH = CONFIGS_DIR / "crops.yaml"
MANDIS_CONFIG_PATH = CONFIGS_DIR / "mandis.yaml"

DATA_DIR = BASE_DIR / "data"
DEMO_DATA_DIR = DATA_DIR / "demo"
DEMO_MANDI_PRICES_PATH = DEMO_DATA_DIR / "mandi_prices.csv"
DEMO_WEATHER_PATH = DEMO_DATA_DIR / "weather.csv"
