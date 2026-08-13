import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import init_db
from app.db.request_log_repository import add_request_log, list_request_logs


@pytest.fixture
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    init_db(bind_engine=engine)

    session_factory = sessionmaker(bind=engine)
    db_session = session_factory()

    yield db_session

    db_session.close()


def test_add_request_log(session):
    log = add_request_log(
        session,
        method_name="GetOrders",
        endpoint="/api/v3/orders",
        mode="test",
        status_code=200,
    )

    assert log.id is not None
    assert log.method_name == "GetOrders"
    assert log.endpoint == "/api/v3/orders"
    assert log.mode == "test"
    assert log.status_code == 200


def test_add_request_log_defaults_mode_to_test(session):
    log = add_request_log(session, method_name="GetOrders", endpoint="/api/v3/orders")

    assert log.mode == "test"


def test_list_request_logs_empty(session):
    assert list_request_logs(session) == []


def test_list_request_logs_orders_newest_first(session):
    add_request_log(session, method_name="First", endpoint="/a")
    add_request_log(session, method_name="Second", endpoint="/b")

    logs = list_request_logs(session)

    assert [log.method_name for log in logs] == ["Second", "First"]


def test_list_request_logs_respects_limit(session):
    for i in range(5):
        add_request_log(session, method_name=f"m{i}", endpoint="/x")

    logs = list_request_logs(session, limit=2)

    assert len(logs) == 2
