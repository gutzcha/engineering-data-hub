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
