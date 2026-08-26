from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL


engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def utcnow() -> datetime:
    """
    Naive UTC datetime, для колонок created_at/last_used_at.

    datetime.utcnow() устарел в самом Python (DeprecationWarning с 3.12+).
    Рекомендованная замена — datetime.now(timezone.utc), но она возвращает
    timezone-aware значение, а колонки здесь на обычном DateTime (naive).
    Отбрасываем tzinfo, чтобы поведение не поменялось.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def init_db(bind_engine=engine) -> None:
    # Local import: models.py must be imported so its classes register on
    # Base.metadata before create_all runs. Importing here (instead of at
    # module level) avoids a database <-> models circular import, and means
    # callers of init_db() don't need to remember to import models.py first.
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=bind_engine)
    _add_missing_columns(bind_engine)


def _add_missing_columns(bind_engine) -> None:
    """
    Мини-миграция без Alembic: create_all() создаёт только отсутствующие
    ТАБЛИЦЫ, но не добавляет новые колонки в уже существующие (у тех, кто
    запускал приложение раньше, api_keys.db уже на диске со старой схемой).
    Для одного sqlite-файла проекта этого достаточно — полноценный Alembic
    был бы избыточен.
    """
    with bind_engine.connect() as connection:
        existing = {
            row[1] for row in connection.exec_driver_sql("PRAGMA table_info(api_keys)")
        }

        if "last_check_status" not in existing:
            connection.exec_driver_sql(
                "ALTER TABLE api_keys ADD COLUMN last_check_status VARCHAR"
            )
        if "last_check_detail" not in existing:
            connection.exec_driver_sql(
                "ALTER TABLE api_keys ADD COLUMN last_check_detail TEXT"
            )

        connection.commit()
