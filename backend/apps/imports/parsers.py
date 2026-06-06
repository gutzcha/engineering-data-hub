from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException


class XlsxParseError(ValueError):
    pass


def parse_xlsx_rows(source_file):
    if not source_file:
        raise XlsxParseError("Import file must be a valid .xlsx workbook.")

    source_file.open("rb")
    try:
        try:
            workbook = load_workbook(source_file, data_only=True)
        except (BadZipFile, InvalidFileException, OSError, ValueError) as error:
            raise XlsxParseError("Import file must be a valid .xlsx workbook.") from error
    finally:
        source_file.close()
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise XlsxParseError("Import file must contain a header row.")

    headers = [_cell_to_value(value) for value in rows[0]]
    if not any(headers):
        raise XlsxParseError("Import file must contain a header row.")
    parsed = []
    for index, row in enumerate(rows[1:], start=2):
        if all(value is None or value == "" for value in row):
            continue
        parsed.append(
            {
                "row_number": index,
                "values": {
                    header: _cell_to_value(row[column_index])
                    for column_index, header in enumerate(headers)
                    if header
                },
            }
        )
    return parsed


def _cell_to_value(value):
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
