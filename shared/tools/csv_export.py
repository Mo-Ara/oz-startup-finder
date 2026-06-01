from __future__ import annotations

import csv
import io
from typing import Any

REQUIRED_COLUMNS = [
    "company_name",
    "company_website",
    "company_linkedin",
    "company_number_of_employees",
    "industry",
    "company_city",
    "company_state",
    "company_logo_url",
]


def validate_row(row: dict[str, str]) -> bool:
    return all(row.get(col) for col in REQUIRED_COLUMNS)


def build_safe_csv(rows: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=REQUIRED_COLUMNS, strict=True)
    writer.writeheader()
    for row in rows:
        writer.writerow({col: row.get(col, "") for col in REQUIRED_COLUMNS})
    return buffer.getvalue()


def leads_to_csv(leads: list[dict[str, Any]]) -> str:
    return build_safe_csv(leads)
