from pathlib import Path

APP_NAME = "STOCK AI ANALYST - PRO EDITION"
APP_VERSION = "2.0.0"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"
CACHE_DIR = BASE_DIR / "cache"
DB_PATH = DATA_DIR / "stock_data_v2.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SYMBOLS = ["HPG", "FPT", "VIC", "SSI", "MWG", "TCB"]
DEFAULT_PERIOD = "3Y"
DEFAULT_CACHE_TTL_MINUTES = 60
