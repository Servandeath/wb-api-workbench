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


def test_init_db_adds_missing_columns_to_existing_table(tmp_path):
    """
    Regression test for the no-Alembic mini-migration in init_db(): a user
    who ran the app before last_check_status/last_check_detail existed has
    an api_keys table on disk without them. create_all() alone would not
    add the columns (it only creates missing TABLES) — init_db() must also
    backfill missing columns on tables that already exist.
    """
    db_path = tmp_path / "old_schema.db"

    from sqlalchemy import create_engine

    old_engine = create_engine(f"sqlite:///{db_path}")
    with old_engine.connect() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE api_keys (
                id INTEGER PRIMARY KEY,
                name VARCHAR UNIQUE NOT NULL,
                marketplace VARCHAR NOT NULL,
                key_kind VARCHAR NOT NULL,
                masked_token VARCHAR NOT NULL,
                storage_type VARCHAR NOT NULL,
                is_active BOOLEAN,
                created_at DATETIME,
                last_used_at DATETIME
            )
            """
        )
        connection.exec_driver_sql(
            "INSERT INTO api_keys (name, marketplace, key_kind, masked_token, "
            "storage_type, is_active) VALUES ('a', 'WB', 'jwt', 'x...y', "
            "'encrypted_file', 0)"
        )
        connection.commit()
    old_engine.dispose()

    from app.db.database import init_db
    from app.db.key_repository import get_api_key_by_name
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(f"sqlite:///{db_path}")
    init_db(bind_engine=engine)

    session = sessionmaker(bind=engine)()
    try:
        key = get_api_key_by_name(session, "a")
        assert key is not None
        assert key.last_check_status is None
        assert key.last_check_detail is None
    finally:
        session.close()
