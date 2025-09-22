import logging
import os

# Crear carpeta logs si no existe
os.makedirs(os.path.join(os.getcwd(), 'logs'), exist_ok=True)

logging.basicConfig(
    filename=os.path.join('logs', 'app.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logging.info("Iniciando procesamiento de ficheros")


import unicodedata

def limpiar_texto(texto):
    texto = texto.strip()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto)
                    if unicodedata.category(c) != 'Mn')
    return texto

def contar_palabras(texto):
    return len(texto.split())


import csv

def procesar_txt(file_path):
    logging.info(f"Procesando TXT: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        lineas = f.readlines()

    lineas_limpias = [limpiar_texto(linea) for linea in lineas]
    total_palabras = sum(contar_palabras(linea) for linea in lineas_limpias)

    return lineas_limpias, total_palabras

def procesar_csv(file_path):
    logging.info(f"Procesando CSV: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        filas = [[limpiar_texto(cell) for cell in row] for row in reader]
    return filas, len(filas)


def guardar_resultados_csv(filas, output_path):
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(filas)
    logging.info(f"Archivo CSV guardado: {output_path}")

def guardar_reporte(txt, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(txt)
    logging.info(f"Reporte guardado: {output_path}")


def main():
    txt_file = 'data/ejemplo.txt'
    csv_file = 'data/ejemplo.csv'

    # Procesar TXT
    lineas, total_palabras = procesar_txt(txt_file)
    reporte_txt = f"Total líneas: {len(lineas)}\nTotal palabras: {total_palabras}"
    guardar_reporte(reporte_txt, 'data/reporte.txt')

    # Procesar CSV
    filas, total_filas = procesar_csv(csv_file)
    guardar_resultados_csv(filas, 'data/resultado.csv')

    logging.info("Procesamiento completado")

if __name__ == '__main__':
    main()
