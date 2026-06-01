from __future__ import annotations

import sqlite3
import csv
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "startups.db"


def build_knowledge_base(csv_path: Path, db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("""
            CREATE TABLE companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                company_website TEXT,
                company_linkedin TEXT,
                company_number_of_employees TEXT,
                company_description TEXT,
                industry TEXT,
                company_city TEXT,
                company_logo_url TEXT
            )
        """)

        conn.execute("""
            CREATE VIRTUAL TABLE companies_fts USING fts5(
                company_name,
                industry,
                company_city,
                company_description,
                content=companies,
                content_rowid=id
            )
        """)

        conn.execute("""
            CREATE TRIGGER companies_ai AFTER INSERT ON companies BEGIN
                INSERT INTO companies_fts(rowid, company_name, industry, company_city, company_description)
                VALUES (new.id, new.company_name, new.industry, new.company_city, new.company_description);
            END
        """)

        conn.execute("""
            CREATE TRIGGER companies_ad AFTER DELETE ON companies BEGIN
                INSERT INTO companies_fts(companies_fts, rowid, company_name, industry, company_city, company_description)
                VALUES ('delete', old.id, old.company_name, old.industry, old.company_city, old.company_description);
            END
        """)

        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        conn.executemany(
            """
            INSERT INTO companies (
                company_name, company_website, company_linkedin,
                company_number_of_employees, company_description,
                industry, company_city, company_logo_url
            ) VALUES (:company_name, :company_website, :company_linkedin,
                      :company_number_of_employees, :company_description,
                      :industry, :company_city, :company_logo_url)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()
