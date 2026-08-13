from app.core.settings import UserRole


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
        "use_session_key",
        "run_test_request",
        "save_test_response",
    },
    UserRole.OPERATOR: {
        "view_api_methods",
        "view_json_responses",
        "view_masked_keys",
        "use_session_key",
        "run_test_request",
        "run_real_request",
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
        "use_session_key",
        "run_test_request",
        "run_real_request",
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
