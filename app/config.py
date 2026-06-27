import os
from pathlib import Path
from typing import TypedDict

class Settings(TypedDict):
    TEMPLATE_STORE_READ_ENABLED: bool
    TEMPLATE_STORE_KEY: str
    TEMPLATE_STORE_DB_PATH: Path
    FLASK_SECRET_KEY: str

def _str2bool(v: str) -> bool:
    return v.lower() in {"1", "true", "yes", "on"}

_SETTINGS: Settings = {
    "TEMPLATE_STORE_READ_ENABLED": _str2bool(os.getenv("QM_TEMPLATE_STORE_READ_ENABLED", "1")),
    "TEMPLATE_STORE_KEY": os.getenv("QM_TEMPLATE_STORE_KEY", "builder_beta"),    "TEMPLATE_STORE_DB_PATH": Path(
        os.getenv(
            "QM_TEMPLATE_STORE_PATH",
            Path(__file__).resolve().parent / "template_store.sqlite3",
        )
    ),
    "FLASK_SECRET_KEY": os.getenv("FLASK_SECRET_KEY", "dev-secret-key-CHANGE-ME"),
}

# Export constants for easy import elsewhere
TEMPLATE_STORE_READ_ENABLED = _SETTINGS["TEMPLATE_STORE_READ_ENABLED"]
TEMPLATE_STORE_KEY = _SETTINGS["TEMPLATE_STORE_KEY"]
TEMPLATE_STORE_DB_PATH = _SETTINGS["TEMPLATE_STORE_DB_PATH"]
FLASK_SECRET_KEY = _SETTINGS["FLASK_SECRET_KEY"]
