import pyautogui
import time
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
import subprocess

# ---------------- Carpetas ----------------
CAPTURES_DIR = Path("captures")
CAPTURES_DIR.mkdir(exist_ok=True)
LOG_FILE = Path("logs/app.log")
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # sube 2 niveles hasta la raíz
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# ---------------- Logging ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logging.info("RPA Bloc de notas iniciado ✅")

# ---------------- Archivo Excel ----------------
INFORME = Path("data/informe.xlsx")
if not INFORME.exists():
    logging.error(f"No se encontró {INFORME}")
    exit(1)

df = pd.read_excel(INFORME, sheet_name="Resumen")
texto = df.to_string(index=False)
logging.info("Informe leído y convertido a texto")

# ---------------- Abrir Bloc de notas ----------------
try:
    subprocess.Popen("notepad.exe")
    time.sleep(2)  # esperar a que se abra
except Exception:
    logging.exception("Error abriendo Bloc de notas")
    exit(1)

# ---------------- Pegar texto ----------------
try:
    pyautogui.FAILSAFE = True  # mover ratón a esquina para detener
    pyautogui.typewrite(texto, interval=0.01)
    logging.info("Texto pegado en Bloc de notas")
except Exception:
    screenshot_file = CAPTURES_DIR / f"error_typewrite_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    pyautogui.screenshot(screenshot_file)
    logging.exception(f"Error pegando texto, screenshot guardado: {screenshot_file}")

# ---------------- Guardar archivo (ruta fija + timestamp) ----------------
try:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"Resumen_{timestamp}.txt"
    full_path = DATA_DIR / filename

    pyautogui.hotkey("ctrl", "g")  # abre diálogo “Guardar como” (según configuración)
    time.sleep(1.5)  # espera a que aparezca la ventana

    pyautogui.typewrite(str(full_path))
    pyautogui.press("enter")  # confirma guardar

    logging.info(f"Archivo guardado en: {full_path}")
except Exception:
    screenshot_file = CAPTURES_DIR / f"error_save_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    pyautogui.screenshot(screenshot_file)
    logging.exception(f"Error guardando archivo, screenshot guardado: {screenshot_file}")

# ---------------- Cerrar Bloc de notas ----------------
try:
    pyautogui.hotkey("alt", "f4")
    logging.info("Bloc de notas cerrado ✅")
except Exception:
    screenshot_file = CAPTURES_DIR / f"error_close_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    pyautogui.screenshot(screenshot_file)
    logging.exception(f"Error cerrando Bloc de notas, screenshot guardado: {screenshot_file}")