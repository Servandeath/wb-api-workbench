import importlib
import sys
from dataclasses import dataclass
from pathlib import Path

from app.config import BASE_DIR, DATA_DIR, RAW_DATA_DIR, IMPORTS_DIR, CACHE_DIR, SECURE_DIR
from app.core.encrypted_file_storage import EncryptedFileKeyStorage
from app.core.permissions import has_permission
from app.core.session_key_storage import SessionKeyStorage
from app.core.settings import UserRole
from sqlalchemy import inspect
from app.db.database import engine, init_db

REQUIRED_LIBRARIES = ["httpx", "customtkinter", "cryptography", "sqlalchemy", "keyring"]


@dataclass
class DiagnosticResult:
    name: str
    status: str
    message: str


def check_python_version() -> DiagnosticResult:
    version = sys.version_info

    if version.major == 3 and version.minor >= 11:
        return DiagnosticResult(
            name="Python version",
            status="OK",
            message=f"Python {version.major}.{version.minor}.{version.micro}",
        )

    return DiagnosticResult(
        name="Python version",
        status="FAIL",
        message=f"Python {version.major}.{version.minor}.{version.micro}; expected 3.11+",
    )


def check_project_folders() -> DiagnosticResult:
    required_paths: list[Path] = [
        BASE_DIR,
        DATA_DIR,
        RAW_DATA_DIR,
        IMPORTS_DIR,
        CACHE_DIR,
        SECURE_DIR,
    ]

    missing = [str(path) for path in required_paths if not path.exists()]

    if not missing:
        return DiagnosticResult(
            name="Project folders",
            status="OK",
            message="All required folders exist",
        )

    return DiagnosticResult(
        name="Project folders",
        status="FAIL",
        message="Missing folders: " + ", ".join(missing),
    )


def check_permissions() -> DiagnosticResult:
    checks = [
        has_permission(UserRole.ADMIN, "add_key") is True,
        has_permission(UserRole.VIEWER, "add_key") is False,
        has_permission(UserRole.OPERATOR, "run_real_request") is True,
        # Tester больше не гоняет свободные запросы (см. permissions.py) —
        # ему доступна только canned-проверка живости ключа.
        has_permission(UserRole.TESTER, "check_key_liveness") is True,
        has_permission(UserRole.TESTER, "run_test_request") is False,
    ]

    if all(checks):
        return DiagnosticResult(
            name="Permissions",
            status="OK",
            message="Role permissions work correctly",
        )

    return DiagnosticResult(
        name="Permissions",
        status="FAIL",
        message="Permission matrix has unexpected results",
    )


def check_session_key_storage() -> DiagnosticResult:
    storage = SessionKeyStorage()
    storage.save_token("test", "secret-token")

    token = storage.get_token("test")
    storage.delete_token("test")

    if token == "secret-token" and storage.get_token("test") is None:
        return DiagnosticResult(
            name="Session key storage",
            status="OK",
            message="Temporary key storage works correctly",
        )

    return DiagnosticResult(
        name="Session key storage",
        status="FAIL",
        message="Temporary key storage failed",
    )


def check_database(bind_engine=engine) -> DiagnosticResult:
    expected_tables = {"api_keys", "api_request_logs"}
    try:
        init_db(bind_engine=bind_engine)
        existing = set(inspect(bind_engine).get_table_names())
    except Exception as error:
        return DiagnosticResult(
            name="Database",
            status="FAIL",
            message=f"Cannot inspect database: {error}",
        )

    missing = expected_tables - existing
    if not missing:
        return DiagnosticResult(
            name="Database",
            status="OK",
            message="Database ready, all tables exist",
        )
    return DiagnosticResult(
        name="Database",
        status="FAIL",
        message="Missing tables: " + ", ".join(sorted(missing)),
    )

def check_libraries() -> DiagnosticResult:
    missing = []
    for name in REQUIRED_LIBRARIES:
        try:
            importlib.import_module(name)
        except ImportError:
            missing.append(name)

    if not missing:
        return DiagnosticResult(
            name="Libraries",
            status="OK",
            message="All required libraries are installed",
        )

    return DiagnosticResult(
        name="Libraries",
        status="FAIL",
        message="Missing libraries: " + ", ".join(missing),
    )


def check_encrypted_storage() -> DiagnosticResult:
    """
    Круговая проверка EncryptedFileKeyStorage: пишем разовый пробный
    секрет, читаем его обратно, потом сразу удаляем — реальные сохранённые
    ключи пользователя эта проверка не трогает.
    """
    storage = EncryptedFileKeyStorage()
    probe_name = "__diagnostics_probe__"

    try:
        storage.save_token(probe_name, "diagnostics-secret")
        token = storage.get_token(probe_name)
    except Exception as error:
        return DiagnosticResult(
            name="Encrypted storage",
            status="FAIL",
            message=f"Cannot write/read encrypted storage: {error}",
        )
    finally:
        storage.delete_token(probe_name)

    if token == "diagnostics-secret":
        return DiagnosticResult(
            name="Encrypted storage",
            status="OK",
            message="Encrypted file storage round-trips correctly",
        )

    return DiagnosticResult(
        name="Encrypted storage",
        status="FAIL",
        message="Encrypted file storage round-trip failed",
    )


def run_diagnostics() -> list[DiagnosticResult]:
    return [
        check_python_version(),
        check_project_folders(),
        check_libraries(),
        check_permissions(),
        check_session_key_storage(),
        check_encrypted_storage(),
        check_database(),
    ]


def format_diagnostics(results: list[DiagnosticResult]) -> str:
    lines = []

    for result in results:
        icon = "OK" if result.status == "OK" else "FAIL"
        lines.append(f"[{icon}] {result.name}: {result.message}")

    return "\n".join(lines)
