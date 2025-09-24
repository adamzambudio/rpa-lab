import logging
import sys
import os
import csv
import re
import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape
import argparse

# ---------------- Rutas ----------------
BASE_DIR = Path.cwd()
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "app.log"

# ---------------- Configuración de logging garantizado ----------------
# Limpiar handlers existentes
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Consola
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# Archivo
file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(console_formatter)
logger.addHandler(file_handler)

logging.info("Logging inicializado ✅")

# ---------------- Cargar .env ----------------
load_dotenv(BASE_DIR / ".env")
SMTP_SERVER = os.getenv("SMTP_SERVER", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASS = os.getenv("EMAIL_PASS", "")
DEFAULT_FROM = os.getenv("EMAIL_FROM", EMAIL_USER)

# ---------------- Jinja2 ----------------
env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(['html', 'xml'])
)

def _simple_text_from_html(html: str) -> str:
    """Genera un fallback de texto plano."""
    text = re.sub('<[^<]+?>', '', html)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _attach_file_to_msg(msg: EmailMessage, path: Path):
    """Adjunta un archivo al mensaje de email."""
    if not path.exists():
        logging.warning(f"Adjunto no encontrado: {path}")
        return
    ctype, encoding = mimetypes.guess_type(str(path))
    if ctype is None:
        maintype, subtype = "application", "octet-stream"
    else:
        maintype, subtype = ctype.split("/", 1)

    with open(path, "rb") as f:
        data = f.read()
    msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=path.name)
    logging.debug(f"Adjunto agregado: {path.name}")

# ---------------- Función de envío ----------------
def send_mail(to: str, subject: str, html_body: str, attachments: List[Path] = None,
              from_addr: str = None, dry_run: bool = False) -> bool:
    if attachments is None:
        attachments = []
    from_addr = from_addr or DEFAULT_FROM
    if not from_addr:
        raise ValueError("No hay dirección remitente configurada")

    logging.info(f"{'[DRY-RUN] ' if dry_run else ''}Preparando correo a: {to} | Asunto: {subject}")

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject

    plain = _simple_text_from_html(html_body)
    msg.set_content(plain)
    msg.add_alternative(html_body, subtype="html")

    for a in attachments:
        _attach_file_to_msg(msg, Path(a))

    if dry_run:
        logging.info(f"[DRY-RUN] Mensaje preparado (no enviado) a: {to}, adjuntos: {[p.name for p in attachments]}")
        logging.debug(f"[DRY-RUN] Contenido HTML:\n{html_body[:400]}...")
        return True

    try:
        logging.info("Conectando al servidor SMTP...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=60) as server:
            server.ehlo()
            try:
                server.starttls()
                server.ehlo()
            except Exception:
                logging.debug("starttls() no disponible o no requerido")
            if EMAIL_USER and EMAIL_PASS:
                server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        logging.info(f"Correo enviado a {to}")
        return True
    except Exception:
        logging.exception(f"Fallo enviando correo a {to}")
        return False

# ---------------- Envío masivo ----------------
def is_valid_email(addr: str) -> bool:
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", (addr or "").strip()))

def send_bulk_from_csv(clientes_csv: Path, template_name: str, subject_template: str,
                       attachment_paths: List[Path] = None, dry_run: bool = False,
                       limit: int = None, test_email: str = None):
    if attachment_paths is None:
        attachment_paths = []

    if not clientes_csv.exists():
        logging.error(f"No existe fichero de clientes: {clientes_csv}")
        return

    tmpl = env.get_template(template_name)
    sent = failed = processed = 0

    with open(clientes_csv, newline='', encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if limit is not None and processed >= limit:
                break
            nombre = (row.get("nombre") or "").strip()
            email = (row.get("email") or "").strip()
            processed += 1

            if not nombre or not email or not is_valid_email(email):
                logging.warning(f"Registro inválido: {row}")
                failed += 1
                continue

            target = test_email if test_email else email
            html_body = tmpl.render(nombre=nombre)
            subject = subject_template.format(nombre=nombre)

            ok = send_mail(target, subject, html_body, attachments=attachment_paths, dry_run=dry_run)
            if ok:
                sent += 1
            else:
                failed += 1

    logging.info(f"Envío completo. Procesados: {processed}, enviados: {sent}, fallidos: {failed}")

# ---------------- CLI ----------------
def main():
    parser = argparse.ArgumentParser(description="Mailer parametrizable (Día 3)")
    parser.add_argument("--dry-run", action="store_true", help="No envía correos, solo muestra")
    parser.add_argument("--clientes", type=str, default=str(DATA_DIR / "clientes.csv"))
    parser.add_argument("--template", type=str, default="email.html")
    parser.add_argument("--subject", type=str, default="Informe de ventas - {nombre}")
    parser.add_argument("--attach", type=str, nargs="*", default=[str(DATA_DIR / "informe.xlsx")])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--test-email", type=str, default=None)
    args = parser.parse_args()

    logging.info(f"Modo dry-run: {args.dry_run}")
    logging.info(f"Servidor SMTP: {SMTP_SERVER}:{SMTP_PORT} | Usuario: {EMAIL_USER or '(no configurado)'}")
    logging.info(f"Clientes: {args.clientes} | Template: {args.template} | Adjuntos: {args.attach}")

    send_bulk_from_csv(Path(args.clientes), args.template, args.subject,
                       [Path(p) for p in args.attach],
                       dry_run=args.dry_run, limit=args.limit,
                       test_email=args.test_email)

if __name__ == "__main__":
    main()
