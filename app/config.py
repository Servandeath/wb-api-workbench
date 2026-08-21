from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
IMPORTS_DIR = DATA_DIR / "imports"
CACHE_DIR = DATA_DIR / "cache"
SECURE_DIR = DATA_DIR / "secure"

DATABASE_URL = f"sqlite:///{DATA_DIR / 'wb_workbench.db'}"

APP_NAME = "WB API Workbench"
APP_VERSION = "0.1.0"
USERS_FILE = DATA_DIR / "users.json"
SESSION_FILE = DATA_DIR / "session.json"
