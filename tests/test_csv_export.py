from __future__ import annotations

from shared.tools.csv_export import validate_row, build_safe_csv


VALID_ROW = {
    "company_name": "Acme AI",
    "company_website": "https://acme-ai.example.com",
    "company_linkedin": "https://linkedin.example.com/company/acme-ai",
    "company_number_of_employees": "11-50",
    "industry": "Developer Tools",
    "company_city": "Sydney",
    "company_logo_url": "https://acme-ai.example.com/logo.png",
}


def test_validate_row_returns_true_for_complete_row():
    assert validate_row(VALID_ROW) is True


def test_validate_row_returns_false_for_missing_field():
    row = dict(VALID_ROW)
    del row["company_website"]
    assert validate_row(row) is False


def test_build_safe_csv_contains_header_and_one_row():
    csv_text = build_safe_csv([VALID_ROW])
    assert "company_name" in csv_text
    assert "Acme AI" in csv_text
    assert "company_description" not in csv_text  # safety: no description column


def test_build_safe_csv_drops_extra_fields():
    row = dict(VALID_ROW)
    row["company_description"] = "this should not appear in output"
    row["extra_field"] = "also not allowed"
    csv_text = build_safe_csv([row])
    assert "this should not appear in output" not in csv_text
    assert "extra_field" not in csv_text
