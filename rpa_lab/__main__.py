# rpa_lab/__main__.py
import sys
from . import pipeline

def _usage():
    print("Uso: python -m rpa_lab pipeline [--city CITY] [--send] [--dry-run]")
    print("Ejemplo: python -m rpa_lab pipeline --city Madrid --send")

if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "pipeline":
        # pasar solo los args tras 'pipeline' a pipeline.main
        sys.exit(pipeline.main(sys.argv[2:]))
    else:
        _usage()