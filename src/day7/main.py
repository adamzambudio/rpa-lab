# src/day7/main.py
import argparse
import time
from pathlib import Path
import pandas as pd
from .utils import setup_logger, DATA_DIR
from .processor import run_scraper_for_city, read_client_row, create_personal_excel, send_email_with_attachment, capture_error

logger = setup_logger("day7.main")


def process_client_row(row: dict, dry_run: bool):
    start = time.time()
    client_name = row.get("name") or row.get("Nombre")
    city = row.get("city") or row.get("Ciudad")
    result = {"name": client_name, "city": city, "status": "ok", "notes": "", "time_s": 0.0}
    try:
        csv_path = run_scraper_for_city(city)
        client_data = read_client_row(city, csv_path)
        client_data["name"] = client_name
        client_data["email"] = row.get("email")
        out = create_personal_excel(client_data, DATA_DIR)
        if not dry_run:
            subject = f"Informe para {client_name} - {city}"
            body = f"<p>Hola {client_name},</p><p>Adjunto informe con datos para {city}.</p>"
            send_email_with_attachment(subject, body, out)
        result["time_s"] = time.time() - start
    except Exception as e:
        result["status"] = "error"
        result["notes"] = str(e)
        cap = capture_error(client_name or "error")
        if cap:
            result["screenshot"] = str(cap)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--clients", required=True, help="Ruta al CSV de clientes")
    parser.add_argument("--dry-run", action="store_true", help="No envía emails, solo simula")
    args = parser.parse_args(argv)

    df = pd.read_csv(args.clients)
    results = []
    for _, row in df.iterrows():
        res = process_client_row(row.to_dict(), args.dry_run)
        results.append(res)

    # crear report.md
    report_lines = [
        "# Reporte ejecucion day7", "",
        "| name | city | status | time_s | notes |",
        "|---|---|---|---:|---|"
    ]
    for r in results:
        report_lines.append(f"| {r.get('name')} | {r.get('city')} | {r.get('status')} | {r.get('time_s'):.2f} | {r.get('notes')} |")
    Path("report.md").write_text("\n".join(report_lines), encoding="utf-8")
    logger.info("Report generado: report.md")


if __name__ == "__main__":
    main()
