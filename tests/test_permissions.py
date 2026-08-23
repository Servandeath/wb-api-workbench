from app.core.permissions import has_permission
from app.core.settings import UserRole


def test_admin_can_add_key():
    assert has_permission(UserRole.ADMIN, "add_key") is True


def test_viewer_cannot_add_key():
    assert has_permission(UserRole.VIEWER, "add_key") is False


def test_tester_can_check_key_liveness():
    assert has_permission(UserRole.TESTER, "check_key_liveness") is True


def test_viewer_cannot_check_key_liveness():
    assert has_permission(UserRole.VIEWER, "check_key_liveness") is False


def test_tester_cannot_run_test_request():
    # Свободный API Tester (даже Test mode) — не для Tester, только
    # Operator/Admin. Tester проверяет ключи через Check (wb_ping/ozon_ping),
    # не пишет запросы руками.
    assert has_permission(UserRole.TESTER, "run_test_request") is False


def test_tester_cannot_use_session_key():
    assert has_permission(UserRole.TESTER, "use_session_key") is False


def test_operator_can_run_test_and_real_requests():
    assert has_permission(UserRole.OPERATOR, "run_test_request") is True
    assert has_permission(UserRole.OPERATOR, "run_real_request") is True


def test_operator_can_check_key_liveness():
    assert has_permission(UserRole.OPERATOR, "check_key_liveness") is True


def test_admin_has_both_save_permissions():
    # Admin должен видеть чекбокс "Save response" в API Tester в обоих
    # режимах (Test и Real), не только в Real.
    assert has_permission(UserRole.ADMIN, "save_test_response") is True
    assert has_permission(UserRole.ADMIN, "save_response") is True
