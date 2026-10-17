import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.getenv("INCOMEGEN_SECRET_KEY", "local-development-only-change-me")
    DATABASE = os.getenv("INCOMEGEN_DATABASE", str(BASE_DIR / "instance" / "incomegen.db"))
    REQUEST_TIMEOUT = int(os.getenv("INCOMEGEN_REQUEST_TIMEOUT", "20"))
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024

