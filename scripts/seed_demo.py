from __future__ import annotations

import sqlite3
import csv
import tempfile
from pathlib import Path

from scripts.build_knowledge_base import build_knowledge_base


SEED_DATA = [
    {
        "company_name": "Acme AI",
        "company_website": "https://acme-ai.example.com",
        "company_linkedin": "https://linkedin.example.com/company/acme-ai",
        "company_number_of_employees": "11-50",
        "company_description": "Acme AI builds autonomous code review agents for enterprise engineering teams.",
        "industry": "Developer Tools",
        "company_city": "Sydney",
        "company_logo_url": "https://acme-ai.example.com/logo.png",
    },
    {
        "company_name": "QuantumLedger",
        "company_website": "https://quantumledger.example.com",
        "company_linkedin": "https://linkedin.example.com/company/quantumledger",
        "company_number_of_employees": "1-10",
        "company_description": "QuantumLedger provides immutable audit trails for regulated industries using distributed ledger technology.",
        "industry": "Fintech",
        "company_city": "Melbourne",
        "company_logo_url": "https://quantumledger.example.com/logo.png",
    },
    {
        "company_name": "GreenGrid",
        "company_website": "https://greengrid.example.com",
        "company_linkedin": "https://linkedin.example.com/company/greengrid",
        "company_number_of_employees": "51-200",
        "company_description": "GreenGrid optimises energy consumption for commercial buildings using IoT sensors and forecasting models.",
        "industry": "CleanTech",
        "company_city": "Brisbane",
        "company_logo_url": "https://greengrid.example.com/logo.png",
    },
    {
        "company_name": "MediScan",
        "company_website": "https://mediscan.example.com",
        "company_linkedin": "https://linkedin.example.com/company/mediscan",
        "company_number_of_employees": "11-50",
        "company_description": "MediScan uses computer vision to detect early signs of diabetic retinopathy from retinal scans.",
        "industry": "HealthTech",
        "company_city": "Sydney",
        "company_logo_url": "https://mediscan.example.com/logo.png",
    },
    {
        "company_name": "Shipwise",
        "company_website": "https://shipwise.example.com",
        "company_linkedin": "https://linkedin.example.com/company/shipwise",
        "company_number_of_employees": "51-200",
        "company_description": "Shipwise streamlines last-mile logistics for e-commerce businesses.",
        "industry": "Logistics",
        "company_city": "Melbourne",
        "company_logo_url": "https://shipwise.example.com/logo.png",
    },
]


def seed_test_db(db_path: Path | None = None) -> Path:
    target = db_path or Path("data") / "startups.db"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", newline="")
    writer = csv.DictWriter(tmp, fieldnames=list(SEED_DATA[0].keys()))
    writer.writeheader()
    writer.writerows(SEED_DATA)
    tmp.close()

    build_knowledge_base(Path(tmp.name), target)
    Path(tmp.name).unlink(missing_ok=True)
    return target
