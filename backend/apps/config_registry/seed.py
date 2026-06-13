# ===
# File Summary
# Path: backend\apps\config_registry\seed.py
# Type: python
# Purpose: Configuration registry service for dynamic schemas, publishing, and config governance.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: starter_configuration_data
# Inputs:
# - Downstream and upstream interactions in the same domain.
# Outputs:
# - API payloads, records, side effects, or UI views depending on file role.
# Dependencies:
# - Shared runtime services and adjacent domain modules.
# Known risks:
# - Validate behavior after migrations, dependency upgrades, or contract changes.
# ===
# 

import json
from pathlib import Path


STARTER_CONFIGURATION_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "plastic_engineering_v1.json"
)


def starter_configuration_data():
    return json.loads(STARTER_CONFIGURATION_PATH.read_text(encoding="utf-8"))

