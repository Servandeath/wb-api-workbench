from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL


engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def init_db(bind_engine=engine) -> None:
    # Local import: models.py must be imported so its classes register on
    # Base.metadata before create_all runs. Importing here (instead of at
    # module level) avoids a database <-> models circular import, and means
    # callers of init_db() don't need to remember to import models.py first.
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=bind_engine)
