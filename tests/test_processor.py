# tests/test_processor.py
from pathlib import Path
from src.day7.processor import create_personal_excel
import pandas as pd
import tempfile

def test_create_personal_excel(tmp_path):
    client = {"name":"Test User","email":"t@example.com","city":"Nowhere","Temperatura":"20°C"}
    out = create_personal_excel(client, tmp_path)
    assert Path(out).exists()
    # check content
    df = pd.read_excel(out)
    assert df.loc[0, "name"] == "Test User"
