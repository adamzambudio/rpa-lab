# src/day7/processor.py
from pathlib import Path
import subprocess
import os
import time
import pandas as pd
from tenacity import retry, wait_exponential, stop_after_attempt
from dotenv import load_dotenv
from .utils import setup_logger, DATA_DIR, filename_for_client, capture_error

logger = setup_logger("day7.processor")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRAPER_SCRIPT = PROJECT_ROOT / "src" / "day5" / "scraper.py"

# retry decorator
retry_decorator = retry(wait=wait_exponential(multiplier=1, min=2, max=20), stop=stop_after_attempt(3), reraise=True)

@retry_decorator
def run_scraper_for_city(city: str):
    """Llama al scraper (script) para que escriba data/webdata.csv"""
    if not SCRAPER_SCRIPT.exists():
        raise FileNotFoundError(f"Scraper missing: {SCRAPER_SCRIPT}")
    env = os.environ.copy()
    env["CITY"] = city
    logger.info("Running scraper for city=%s", city)
    res = subprocess.run([os.sys.executable, str(SCRAPER_SCRIPT)], env=env, cwd=str(PROJECT_ROOT),
                         capture_output=True, text=True)
    if res.returncode != 0:
        logger.error("Scraper failed: %s", res.stderr)
        raise RuntimeError("Scraper failed")
    # small wait to ensure file written
    time.sleep(1)
    return DATA_DIR / "webdata.csv"

def read_client_row(city: str, csv_path: Path):
    df = pd.read_csv(csv_path)
    if "Ciudad" in df.columns:
        matches = df[df["Ciudad"].astype(str).str.lower() == city.lower()]
        if not matches.empty:
            return matches.iloc[-1].to_dict()
    # fallback to last row
    return df.iloc[-1].to_dict()

def create_personal_excel(client: dict, out_dir: Path):
    """Crea un Excel personalizado para un cliente; devuelve path."""
    name = client.get("name") or client.get("Nombre") or "client"
    fname = filename_for_client(name)
    path = out_dir / fname
    # construir un DataFrame simple con la info
    df = pd.DataFrame([client])
    df.to_excel(path, index=False)
    logger.info("Excel creado: %s", path)
    return path

@retry_decorator
def send_email_with_attachment(subject: str, body: str, attachment_path: Path):
    """Implementa envío reintentable; carga .env para credenciales."""
    load_dotenv(PROJECT_ROOT / ".env")
    import smtplib
    from email.message import EmailMessage
    SMTP_HOST = os.getenv("SMTP_HOST") or os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER") or os.getenv("EMAIL_USER")
    SMTP_PASS = os.getenv("SMTP_PASS") or os.getenv("EMAIL_PASS")
    EMAIL_FROM = os.getenv("EMAIL_FROM") or SMTP_USER
    EMAIL_TO = os.getenv("EMAIL_TO") or SMTP_USER

    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        logger.error("No SMTP config found in .env")
        raise RuntimeError("Missing SMTP config")

    msg = EmailMessage()
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject
    msg.set_content(body, subtype="html")

    with open(attachment_path, "rb") as f:
        data = f.read()
        msg.add_attachment(data, maintype="application", subtype="octet-stream", filename=attachment_path.name)

    logger.info("Connecting SMTP %s", SMTP_HOST)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    logger.info("Email enviado con adjunto %s", attachment_path)
