import json
from pathlib import Path


STARTER_CONFIGURATION_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "plastic_engineering_v1.json"
)


def starter_configuration_data():
    return json.loads(STARTER_CONFIGURATION_PATH.read_text(encoding="utf-8"))
