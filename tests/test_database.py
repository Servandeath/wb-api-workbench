import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_init_db_creates_tables_without_prior_models_import(tmp_path):
    """
    Regression test: init_db() must create all tables even when the caller
    never imported app.db.models directly (e.g. GUI startup only imports
    init_db). Runs in a fresh subprocess so no other test's import of
    app.db.models can mask a missing registration.
    """
    db_path = tmp_path / "regression.db"
    script = f"""
from sqlalchemy import create_engine, inspect
from app.db.database import init_db

engine = create_engine("sqlite:///{db_path.as_posix()}")
init_db(bind_engine=engine)

tables = set(inspect(engine).get_table_names())
assert tables == {{"api_keys", "api_request_logs"}}, tables
"""

    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
    )

    assert result.returncode == 0, result.stderr
