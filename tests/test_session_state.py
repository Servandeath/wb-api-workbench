from app.core.session_state import (
    DEFAULT_MODE,
    DEFAULT_ROLE,
    load_session_state,
    save_session_state,
)
from app.core.settings import AppMode, UserRole


def test_load_session_state_returns_defaults_when_file_missing(tmp_path):
    path = tmp_path / "session.json"

    role, mode = load_session_state(path)

    assert role == DEFAULT_ROLE
    assert mode == DEFAULT_MODE


def test_save_then_load_roundtrips(tmp_path):
    path = tmp_path / "session.json"

    save_session_state(path, UserRole.OPERATOR, AppMode.REAL)
    role, mode = load_session_state(path)

    assert role == UserRole.OPERATOR
    assert mode == AppMode.REAL


def test_save_creates_parent_directories(tmp_path):
    path = tmp_path / "nested" / "session.json"

    save_session_state(path, UserRole.ADMIN, AppMode.TEST)

    assert path.exists()


def test_load_falls_back_on_invalid_role(tmp_path):
    path = tmp_path / "session.json"
    path.write_text('{"role": "NotARole", "mode": "Test"}', encoding="utf-8")

    role, mode = load_session_state(path)

    assert role == DEFAULT_ROLE
    assert mode == AppMode.TEST


def test_load_falls_back_on_invalid_mode(tmp_path):
    path = tmp_path / "session.json"
    path.write_text('{"role": "Admin", "mode": "NotAMode"}', encoding="utf-8")

    role, mode = load_session_state(path)

    assert role == UserRole.ADMIN
    assert mode == DEFAULT_MODE


def test_load_downgrades_real_mode_for_role_that_cannot_use_it(tmp_path):
    # Матрица прав могла поменяться после того, как файл был записан —
    # не доверяем сохранённой комбинации role/mode вслепую.
    path = tmp_path / "session.json"
    path.write_text('{"role": "Viewer", "mode": "Real"}', encoding="utf-8")

    role, mode = load_session_state(path)

    assert role == UserRole.VIEWER
    assert mode == AppMode.TEST


def test_load_keeps_real_mode_for_role_allowed_to_use_it(tmp_path):
    path = tmp_path / "session.json"
    path.write_text('{"role": "Operator", "mode": "Real"}', encoding="utf-8")

    role, mode = load_session_state(path)

    assert role == UserRole.OPERATOR
    assert mode == AppMode.REAL
