from app.core.permissions import has_permission
from app.core.settings import UserRole


def test_admin_can_add_key():
    assert has_permission(UserRole.ADMIN, "add_key") is True


def test_viewer_cannot_add_key():
    assert has_permission(UserRole.VIEWER, "add_key") is False
