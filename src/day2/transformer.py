import logging
import sys
import pandas as pd
from pathlib import Path

# ---------------- Configuración de rutas ----------------
DATA_DIR = Path("data")
OUTPUT_EXCEL = DATA_DIR / "informe.xlsx"
RECHAZADAS = DATA_DIR / "rechazadas.csv"
INPUT_CSV = DATA_DIR / "ventas.csv"

LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "app.log"

# ---------------- Configuración de logging ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),           # imprime en consola
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")  # guarda en logs/app.log
    ]
)

# ---------------- Lógica principal ----------------
# Cargar CSV en un DataFrame
logging.info(f"Leyendo CSV: {INPUT_CSV}")
df = pd.read_csv(INPUT_CSV, sep=",", encoding="utf-8", engine="python") # forzar separador y encoding

# Validar tipos: precio y cantidad deben ser numéricos
logging.info("Validando tipos de columnas numéricas")
df['precio'] = pd.to_numeric(df['precio'], errors='coerce')
df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce')

# Detectar filas inválidas (valores nulos en columnas clave)
logging.info("Separando filas válidas e inválidas")
invalid_rows = df[df[['fecha','categoria','producto','precio','cantidad']].isnull().any(axis=1)]
valid_rows = df.dropna(subset=['fecha','categoria','producto','precio','cantidad'])

# Guardar filas rechazadas
if not invalid_rows.empty:
    logging.info(f"Guardando filas rechazadas en: {RECHAZADAS}")
    invalid_rows.to_csv(RECHAZADAS, index=False)
else:
    logging.info("No se encontraron filas inválidas")

# Normalización de textos
valid_rows['categoria'] = valid_rows['categoria'].str.strip().str.title()
valid_rows['producto'] = valid_rows['producto'].str.strip().str.title()

# Agregación por fecha/categoría
logging.info("Generando resumen de ventas")
resumen = (
    valid_rows
    .groupby(['fecha','categoria'])
    .agg(total_ingresos=('precio', lambda x: (x * valid_rows.loc[x.index,'cantidad']).sum()),
         total_unidades=('cantidad','sum'))
    .reset_index()
)

# Exportar a Excel
logging.info(f"Exportando informe a Excel: {OUTPUT_EXCEL}")
with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
    valid_rows.to_excel(writer, sheet_name="Datos", index=False)
    resumen.to_excel(writer, sheet_name="Resumen", index=False)

def main():
    logging.info("Transformación completada con éxito ✅")
    print("Transformación completada.")
    print(f"Informe generado en: {OUTPUT_EXCEL}")
    print(f"Rechazadas guardadas en: {RECHAZADAS}")

if __name__ == "__main__":
    main()
