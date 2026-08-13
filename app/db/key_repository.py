from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import utcnow
from app.db.models import ApiKey


def add_api_key(
    session: Session,
    name: str,
    marketplace: str,
    key_kind: str,
    masked_token: str,
    storage_type: str,
) -> ApiKey:
    api_key = ApiKey(
        name=name,
        marketplace=marketplace,
        key_kind=key_kind,
        masked_token=masked_token,
        storage_type=storage_type,
    )
    session.add(api_key)
    session.commit()
    session.refresh(api_key)

    return api_key


def get_api_key_by_name(session: Session, name: str) -> ApiKey | None:
    stmt = select(ApiKey).where(ApiKey.name == name)
    return session.execute(stmt).scalar_one_or_none()


def list_api_keys(session: Session) -> list[ApiKey]:
    stmt = select(ApiKey).order_by(ApiKey.created_at)
    return list(session.execute(stmt).scalars())


def touch_api_key_last_used(session: Session, name: str) -> ApiKey | None:
    api_key = get_api_key_by_name(session, name)
    if api_key is None:
        return None

    api_key.last_used_at = utcnow()
    session.commit()
    session.refresh(api_key)

    return api_key


def activate_api_key(session: Session, name: str) -> ApiKey | None:
    api_key = get_api_key_by_name(session, name)
    if api_key is None:
        return None

    api_key.is_active = True
    session.commit()
    session.refresh(api_key)

    return api_key


def deactivate_api_key(session: Session, name: str) -> ApiKey | None:
    api_key = get_api_key_by_name(session, name)
    if api_key is None:
        return None

    api_key.is_active = False
    session.commit()
    session.refresh(api_key)

    return api_key


def delete_api_key(session: Session, name: str) -> bool:
    api_key = get_api_key_by_name(session, name)
    if api_key is None:
        return False

    session.delete(api_key)
    session.commit()

    return True
