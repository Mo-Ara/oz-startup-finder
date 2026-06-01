from __future__ import annotations

import sys
from pathlib import Path
import sqlite3
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.seed_demo import seed_test_db

DB_PATH = PROJECT_ROOT / "data" / "startups.db"


def pytest_configure(config: object) -> None:  # pragma: no cover
    seed_test_db(DB_PATH)


@pytest.fixture(scope="session")
def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()
