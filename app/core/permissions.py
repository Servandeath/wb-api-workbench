from app.core.settings import UserRole


# Tester НЕ получает use_session_key/run_test_request/save_test_response —
# свободный API Tester (даже Test mode с одноразовым ключом) требует
# понимания, что такое метод/путь/JSON body, это не для роли "нажать
# кнопку и посмотреть, живой ли ключ". Взамен — check_key_liveness:
# кнопка Check в Keys, канонический "проверочный скрипт" (wb_ping/
# ozon_ping), ничего руками писать не нужно.
PERMISSIONS = {
    UserRole.VIEWER: {
        "view_api_methods",
        "view_json_responses",
        "view_masked_keys",
    },
    UserRole.TESTER: {
        "view_api_methods",
        "view_json_responses",
        "view_masked_keys",
        "check_key_liveness",
    },
    UserRole.OPERATOR: {
        "view_api_methods",
        "view_json_responses",
        "view_masked_keys",
        "check_key_liveness",
        "use_session_key",
        "run_test_request",
        "run_real_request",
        "save_test_response",
        "save_response",
        "import_files",
        "update_data",
    },
    UserRole.ADMIN: {
        "view_api_methods",
        "view_json_responses",
        "view_masked_keys",
        "view_full_key",
        "add_key",
        "delete_key",
        "check_key_liveness",
        "use_session_key",
        "run_test_request",
        "run_real_request",
        "save_test_response",
        "save_response",
        "import_files",
        "update_data",
        "update_settings",
        "manage_users",
        "clear_database",
    },
}


def has_permission(role: UserRole, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())
