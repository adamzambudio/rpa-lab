# rpa-lab
## Día 6 — Orquestación CLI + Logging + Reintentos

Este día construimos un **pipeline ejecutable** que orquesta scraping, generación de Excel y envío de correo.  
El flujo usa **argparse** para parámetros, **logging** para trazabilidad y **tenacity** para reintentos automáticos.

---

### 🚀 Ejecución del pipeline

El pipeline se ejecuta como módulo:

```bash
python -m rpa_lab pipeline --city Madrid --send --dry-run
