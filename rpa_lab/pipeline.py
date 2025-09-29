# rpa_lab/pipeline.py
import argparse
import logging
import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime
import pandas as pd
import smtplib
from email.message import EmailMessage

from tenacity import retry, wait_exponential, stop_after_attempt, RetryError
from dotenv import load_dotenv

# ---------------- Paths ----------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # rpa_lab/ -> parent = repo root
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
LOG_FILE = LOGS_DIR / "pipeline.log"

SCRAPER_SCRIPT = PROJECT_ROOT / "src" / "day5" / "scraper.py"  # se ejecuta por subprocess

# ---------------- Logging ----------------
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # File handler (UTF-8)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console handler (simple, sin emojis para evitar errores en Windows)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

setup_logging()

# ---------------- Utils / retries factory ----------------
def make_retry_decorator(retries: int):
    return retry(
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(retries),
        reraise=True,
    )

# ---------------- Scraper runner ----------------
def _scraper_impl(city: str):
    if not SCRAPER_SCRIPT.exists():
        raise FileNotFoundError(f"Scraper script not found at {SCRAPER_SCRIPT}")

    env = os.environ.copy()
    env["CITY"] = city  # si el scraper lo soporta, lo recibirá; si no, se ignora
    logging.info(f"Ejecutando scraper (script): {SCRAPER_SCRIPT}  city={city}")

    # Usamos el mismo intérprete (sys.executable) para ejecutar el script
    res = subprocess.run([sys.executable, str(SCRAPER_SCRIPT)], env=env, cwd=str(PROJECT_ROOT),
                         capture_output=True, text=True)
    if res.returncode != 0:
        logging.error("Scraper stderr: %s", res.stderr)
        raise RuntimeError(f"Scraper failed (code {res.returncode})")
    logging.info("Scraper finalizado correctamente")

# ---------------- Email sender impl ----------------
def _send_email_impl(subject: str, body: str, attachment_path: Path):
    # cargar .env
    load_dotenv(PROJECT_ROOT / ".env")

    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")
    EMAIL_TO = os.getenv("EMAIL_TO", SMTP_USER)

    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        raise RuntimeError("Faltan variables SMTP en .env (SMTP_HOST/SMTP_USER/SMTP_PASS)")

    logging.info("Conectando a SMTP %s:%s (usuario=%s)", SMTP_HOST, SMTP_PORT, SMTP_USER)
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject
    msg.set_content(body)

    with open(attachment_path, "rb") as f:
        data = f.read()
        maintype = "application"
        subtype = "octet-stream"
        if attachment_path.suffix.lower() == ".xlsx":
            subtype = "vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=attachment_path.name)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    logging.info("Correo enviado a %s", EMAIL_TO)

# ---------------- CLI main ----------------
def main(argv=None):
    parser = argparse.ArgumentParser(prog="rpa_lab pipeline", description="Pipeline E2E: scraping -> excel -> email")
    parser.add_argument("--city", "-c", default="Madrid", help="Ciudad a consultar")
    parser.add_argument("--send", action="store_true", help="Enviar el informe por email")
    parser.add_argument("--dry-run", action="store_true", help="No enviar correo, sólo simular")
    parser.add_argument("--retries", type=int, default=3, help="Intentos para reintentos (scrape/email)")
    parser.add_argument("--force-scrape", action="store_true", help="Forzar ejecución del scraper (aunque haya CSV)")
    args = parser.parse_args(argv)

    logging.info("Pipeline iniciado (city=%s, send=%s, dry_run=%s)", args.city, args.send, args.dry_run)

    # crear decoradores de retry con el número de intentos solicitado
    retry_decorator = make_retry_decorator(args.retries)
    run_scraper = retry_decorator(_scraper_impl)
    send_email = retry_decorator(_send_email_impl)

    # ---------- 1) Scrape (genera data/webdata.csv) ----------
    csv_path = DATA_DIR / "webdata.csv"
    try:
        if args.force_scrape or not csv_path.exists():
            run_scraper(args.city)
            # esperar un pequeño tiempo para que el script termine de escribir el CSV
            time.sleep(1)
        else:
            logging.info("CSV ya existe en %s (use --force-scrape para regenerar)", csv_path)
    except RetryError as e:
        logging.exception("Scraper falló después de reintentos: %s", str(e))
        return 2
    except Exception:
        logging.exception("Error ejecutando scraper")
        return 3

    # ---------- 2) Leer CSV y generar Excel ----------
    if not csv_path.exists():
        logging.error("No se encontró %s después de ejecutar el scraper", csv_path)
        return 4

    try:
        df = pd.read_csv(csv_path)
        logging.info("CSV leído con %d filas", len(df))
    except Exception:
        logging.exception("Error leyendo CSV %s", csv_path)
        return 5

    # Buscar fila por ciudad (si existe columna 'Ciudad'), caso contrario tomar última fila
    row_df = None
    if "Ciudad" in df.columns:
        matches = df[df["Ciudad"].astype(str).str.lower() == args.city.lower()]
        if not matches.empty:
            row_df = matches
        else:
            logging.warning("No se encontró entrada para la ciudad %s en CSV, se usará la última fila", args.city)
    if row_df is None:
        row_df = df.tail(1)

    excel_path = DATA_DIR / "informe_web.xlsx"
    try:
        # Guardar informe (sobrescribe/crea)
        row_df.to_excel(excel_path, index=False)
        logging.info("Informe guardado en Excel: %s", excel_path)
    except Exception:
        logging.exception("Error generando Excel %s", excel_path)
        return 6

    # ---------- 3) Envío de email (si se solicita) ----------
    if args.send:
        subject = f"Informe web - {args.city} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        body = f"Adjunto informe automático para {args.city} generado el {datetime.now().isoformat()}.\n\n(Generado por rpa_lab pipeline)"
        if args.dry_run:
            logging.info("[DRY-RUN] Se habría enviado el correo con asunto: %s y adjunto %s", subject, excel_path)
        else:
            try:
                send_email(subject, body, excel_path)
            except RetryError as e:
                logging.exception("Envio de email falló después de reintentos: %s", str(e))
                return 7
            except Exception:
                logging.exception("Error enviando email")
                return 8

    logging.info("Pipeline completado correctamente")
    return 0

if __name__ == "__main__":
    sys.exit(main())