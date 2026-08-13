import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import init_db
from app.db.key_repository import (
    activate_api_key,
    add_api_key,
    deactivate_api_key,
    delete_api_key,
    get_api_key_by_name,
    list_api_keys,
    touch_api_key_last_used,
)


@pytest.fixture
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    init_db(bind_engine=engine)

    session_factory = sessionmaker(bind=engine)
    db_session = session_factory()

    yield db_session

    db_session.close()


def test_add_api_key(session):
    api_key = add_api_key(session, name="cab1", masked_token="abc...xyz", storage_type="encrypted_file")

    assert api_key.id is not None
    assert api_key.name == "cab1"
    assert api_key.masked_token == "abc...xyz"
    assert api_key.storage_type == "encrypted_file"
    assert api_key.is_active is False
    assert api_key.last_used_at is None


def test_get_api_key_by_name(session):
    add_api_key(session, name="cab1", masked_token="abc", storage_type="keyring")

    found = get_api_key_by_name(session, "cab1")

    assert found is not None
    assert found.name == "cab1"


def test_get_api_key_by_name_missing_returns_none(session):
    assert get_api_key_by_name(session, "missing") is None


def test_list_api_keys_empty(session):
    assert list_api_keys(session) == []


def test_list_api_keys_returns_all(session):
    add_api_key(session, name="a", masked_token="x", storage_type="keyring")
    add_api_key(session, name="b", masked_token="y", storage_type="keyring")

    names = {key.name for key in list_api_keys(session)}

    assert names == {"a", "b"}


def test_touch_api_key_last_used_sets_timestamp(session):
    add_api_key(session, name="a", masked_token="x", storage_type="keyring")

    updated = touch_api_key_last_used(session, "a")

    assert updated.last_used_at is not None


def test_touch_api_key_last_used_missing_returns_none(session):
    assert touch_api_key_last_used(session, "missing") is None


def test_activate_api_key(session):
    add_api_key(session, name="a", masked_token="x", storage_type="keyring")

    updated = activate_api_key(session, "a")

    assert updated.is_active is True


def test_deactivate_api_key(session):
    add_api_key(session, name="a", masked_token="x", storage_type="keyring")
    activate_api_key(session, "a")

    updated = deactivate_api_key(session, "a")

    assert updated.is_active is False


def test_delete_api_key(session):
    add_api_key(session, name="a", masked_token="x", storage_type="keyring")

    assert delete_api_key(session, "a") is True
    assert get_api_key_by_name(session, "a") is None


def test_delete_api_key_missing_returns_false(session):
    assert delete_api_key(session, "missing") is False
