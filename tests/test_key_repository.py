import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.marketplace import KeyKind, Marketplace
from app.db.database import init_db
from app.db.key_repository import (
    activate_api_key,
    add_api_key,
    deactivate_api_key,
    delete_api_key,
    get_api_key_by_name,
    list_api_keys,
    record_check_result,
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


def _add_wb_key(session, name="a", masked_token="x", storage_type="keyring"):
    return add_api_key(
        session,
        name=name,
        marketplace=Marketplace.WB,
        key_kind=KeyKind.JWT,
        masked_token=masked_token,
        storage_type=storage_type,
    )


def test_add_api_key(session):
    api_key = add_api_key(
        session,
        name="cab1",
        marketplace=Marketplace.WB,
        key_kind=KeyKind.JWT,
        masked_token="abc...xyz",
        storage_type="encrypted_file",
    )

    assert api_key.id is not None
    assert api_key.name == "cab1"
    assert api_key.marketplace == "WB"
    assert api_key.key_kind == "jwt"
    assert api_key.masked_token == "abc...xyz"
    assert api_key.storage_type == "encrypted_file"
    assert api_key.is_active is False
    assert api_key.last_used_at is None


def test_add_api_key_stores_ozon_marketplace_and_kind(session):
    api_key = add_api_key(
        session,
        name="ozon-seller-1",
        marketplace=Marketplace.OZON,
        key_kind=KeyKind.SELLER,
        masked_token="cid...key",
        storage_type="encrypted_file",
    )

    assert api_key.marketplace == "OZON"
    assert api_key.key_kind == "seller"


def test_get_api_key_by_name(session):
    _add_wb_key(session, name="cab1", masked_token="abc")

    found = get_api_key_by_name(session, "cab1")

    assert found is not None
    assert found.name == "cab1"


def test_get_api_key_by_name_missing_returns_none(session):
    assert get_api_key_by_name(session, "missing") is None


def test_list_api_keys_empty(session):
    assert list_api_keys(session) == []


def test_list_api_keys_returns_all(session):
    _add_wb_key(session, name="a", masked_token="x")
    _add_wb_key(session, name="b", masked_token="y")

    names = {key.name for key in list_api_keys(session)}

    assert names == {"a", "b"}


def test_touch_api_key_last_used_sets_timestamp(session):
    _add_wb_key(session)

    updated = touch_api_key_last_used(session, "a")

    assert updated.last_used_at is not None


def test_touch_api_key_last_used_missing_returns_none(session):
    assert touch_api_key_last_used(session, "missing") is None


def test_activate_api_key(session):
    _add_wb_key(session)

    updated = activate_api_key(session, "a")

    assert updated.is_active is True


def test_deactivate_api_key(session):
    _add_wb_key(session)
    activate_api_key(session, "a")

    updated = deactivate_api_key(session, "a")

    assert updated.is_active is False


def test_delete_api_key(session):
    _add_wb_key(session)

    assert delete_api_key(session, "a") is True
    assert get_api_key_by_name(session, "a") is None


def test_delete_api_key_missing_returns_false(session):
    assert delete_api_key(session, "missing") is False


def test_record_check_result_ok_activates_and_stores_status(session):
    _add_wb_key(session)

    updated = record_check_result(session, "a", "OK", "Content: 200\nAnalytics: 200")

    assert updated.is_active is True
    assert updated.last_check_status == "OK"
    assert updated.last_check_detail == "Content: 200\nAnalytics: 200"
    assert updated.last_used_at is not None


def test_record_check_result_non_ok_deactivates(session):
    _add_wb_key(session)
    record_check_result(session, "a", "OK")

    updated = record_check_result(session, "a", "MIXED", "Content: 200\nAnalytics: 401")

    assert updated.is_active is False
    assert updated.last_check_status == "MIXED"


def test_record_check_result_without_detail(session):
    _add_wb_key(session)

    updated = record_check_result(session, "a", "OK")

    assert updated.last_check_detail is None


def test_record_check_result_missing_returns_none(session):
    assert record_check_result(session, "missing", "OK") is None
