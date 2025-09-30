# tests/test_utils.py
from src.day7.utils import filename_for_client
import re

def test_filename_contains_name_and_timestamp():
    name = "Ana Lopez"
    fn = filename_for_client(name)
    assert "Ana_Lopez" in fn or "Ana_Lopez" in fn  # basic check
    assert re.search(r"\d{8}_\d{6}\.xlsx$", fn)
