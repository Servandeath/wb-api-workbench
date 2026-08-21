import pytest

from app.core.settings import UserRole
from app.core.users import (
    UserAccount,
    add_user,
    find_user,
    change_user_role,
    create_user,
    deactivate_user,
    username_exists,
)


def test_create_user_with_role():
    user = create_user("manager1", UserRole.TESTER)

    assert isinstance(user, UserAccount)
    assert user.username == "manager1"
    assert user.role == UserRole.TESTER
    assert user.is_active is True


def test_create_user_strips_username():
    user = create_user("  manager1  ", UserRole.OPERATOR)

    assert user.username == "manager1"
    assert user.role == UserRole.OPERATOR


def test_create_user_with_empty_username_raises_error():
    with pytest.raises(ValueError):
        create_user("   ", UserRole.VIEWER)


def test_username_exists_returns_true_for_existing_user():
    users = [
        create_user("manager1", UserRole.TESTER),
    ]

    assert username_exists(users, "manager1") is True


def test_username_exists_ignores_case():
    users = [
        create_user("Manager1", UserRole.TESTER),
    ]

    assert username_exists(users, "manager1") is True


def test_username_exists_returns_false_for_missing_user():
    users = [
        create_user("manager1", UserRole.TESTER),
    ]

    assert username_exists(users, "manager2") is False


def test_add_user_adds_user_to_list():
    users = []

    user = add_user(users, "manager1", UserRole.TESTER)

    assert user.username == "manager1"
    assert user.role == UserRole.TESTER
    assert users == [user]


def test_add_user_rejects_duplicate_username():
    users = [
        create_user("manager1", UserRole.TESTER),
    ]

    with pytest.raises(ValueError):
        add_user(users, "manager1", UserRole.OPERATOR)


def test_add_user_rejects_duplicate_username_with_different_case():
    users = [
        create_user("Manager1", UserRole.TESTER),
    ]

    with pytest.raises(ValueError):
        add_user(users, "manager1", UserRole.OPERATOR)


def test_change_user_role():
    user = create_user("manager1", UserRole.TESTER)

    updated_user = change_user_role(user, UserRole.OPERATOR)

    assert updated_user.role == UserRole.OPERATOR


def test_deactivate_user():
    user = create_user("manager1", UserRole.OPERATOR)

    updated_user = deactivate_user(user)

    assert updated_user.is_active is False


def test_find_user_returns_user():
    users = [
        create_user("manager1", UserRole.TESTER),
        create_user("manager2", UserRole.OPERATOR),
    ]

    found = find_user(users, "manager2")

    assert found is not None
    assert found.username == "manager2"


def test_find_user_ignores_case():
    users = [create_user("Manager1", UserRole.TESTER)]

    found = find_user(users, "manager1")

    assert found is not None
    assert found.username == "Manager1"


def test_find_user_returns_none_when_missing():
    users = [create_user("manager1", UserRole.TESTER)]

    assert find_user(users, "ghost") is None
