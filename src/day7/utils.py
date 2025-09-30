# src/day7/utils.py
from pathlib import Path
import logging
import sys
from datetime import datetime
import pyautogui

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CAPTURES_DIR = PROJECT_ROOT / "captures"
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_DIR.mkdir(exist_ok=True)
CAPTURES_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

LOG_FILE = LOGS_DIR / "day7.log"

def setup_logger(name: str = None):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

def filename_for_client(name: str) -> str:
    safe = "".join(c if c.isalnum() else "_" for c in name).strip("_")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{safe}_{ts}.xlsx"

def capture_error(tag: str):
    """Toma screenshot y devuelve path (requiere entorno gráfico)."""
    p = CAPTURES_DIR / f"{tag}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    try:
        img = pyautogui.screenshot(str(p))
        return p
    except Exception:
        # si no hay entorno gráfico, no fallamos la ejecución
        return None
