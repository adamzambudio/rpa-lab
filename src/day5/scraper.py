import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from pathlib import Path

# ---------------- Carpetas y Logging ----------------
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_DIR.mkdir(exist_ok=True)
LOG_FILE = Path("logs/app.log")
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, mode="a"), logging.StreamHandler()]
)

logging.info("Scraper web iniciado")

# ---------------- Configurar WebDriver ----------------
options = Options()
# options.add_argument("--headless")  # opcional, para que no abra ventana
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    ciudad = "Madrid"
    url = f"https://www.accuweather.com/es/es/madrid/308526/weather-forecast/308526"

    driver.get(url)
    logging.info(f"Abriendo página del clima para {ciudad}")

    # ---------------- Espera y extracción ----------------
    time.sleep(3)  # espera para que cargue la página

    # Ejemplo: extraer temperatura actual y estado
    temp_elem = driver.find_element(By.XPATH, "//div[@class='temp']")
    estado_elem = driver.find_element(By.XPATH, "/html/body/div/div[7]/div[1]/div[1]/a[1]/div[2]/div[1]/div[2]/span[1]")

    temperatura = temp_elem.text
    estado = estado_elem.text

    logging.info(f"{ciudad}: {temperatura}, {estado}")

    # ---------------- Guardar en CSV ----------------
    import pandas as pd

    df = pd.DataFrame([{
        "Ciudad": ciudad,
        "Temperatura": temperatura,
        "Estado": estado,
        "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])

    csv_path = DATA_DIR / "webdata.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    logging.info(f"Datos guardados en CSV: {csv_path}")

    # ---------------- Guardar resumen en Excel ----------------
    excel_path = DATA_DIR / "informe_web.xlsx"
    df.to_excel(excel_path, sheet_name="Resumen", index=False)
    logging.info(f"Informe web generado en Excel: {excel_path}")

except Exception as e:
    logging.exception(f"Error durante el scraping: {e}")

finally:
    driver.quit()
    logging.info("WebDriver cerrado")