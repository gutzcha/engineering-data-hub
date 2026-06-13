# ===
# File Summary
# Path: backend\apps\imports\mapping.py
# Type: python
# Purpose: Imports domain for parser/mapping workflows and linked entity updates.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: map_excel_row, mapped_rows
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

def map_excel_row(row_values, mapping):
    columns = (mapping or {}).get("columns", {})
    code = ""
    data = {}
    for source_column, target_field in columns.items():
        value = row_values.get(source_column, "")
        if target_field == "code":
            code = str(value).strip() if value is not None else ""
        elif target_field:
            data[target_field] = value
    return {"code": code, "data": data}


def mapped_rows(parsed_rows, mapping):
    return [
        {
            "row_number": row["row_number"],
            **map_excel_row(row["values"], mapping),
        }
        for row in parsed_rows
    ]

