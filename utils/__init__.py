from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PATH_DB_FILE    = PROJECT_ROOT / "data" / "teachable.duckdb"
PATH_BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
PATH_SILVER_DIR = PROJECT_ROOT / "data" / "silver"
PATH_GOLD_DIR   = PROJECT_ROOT / "data" / "gold"