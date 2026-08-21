from dataclasses import dataclass

from app.core.settings import UserRole


@dataclass
class UserAccount:
    username: str
    role: UserRole
    is_active: bool = True


def normalize_username(username: str) -> str:
    return username.strip()


def username_exists(users: list[UserAccount], username: str) -> bool:
    normalized_username = normalize_username(username)

    return any(
        user.username.lower() == normalized_username.lower()
        for user in users
    )


def create_user(username: str, role: UserRole) -> UserAccount:
    normalized_username = normalize_username(username)

    if not normalized_username:
        raise ValueError("Username cannot be empty")

    return UserAccount(username=normalized_username, role=role)


def add_user(
    users: list[UserAccount],
    username: str,
    role: UserRole,
) -> UserAccount:
    if username_exists(users, username):
        raise ValueError(f"Username already exists: {normalize_username(username)}")

    user = create_user(username, role)
    users.append(user)

    return user


def find_user(users: list[UserAccount], username: str) -> UserAccount | None:
    normalized_username = normalize_username(username)

    for user in users:
        if user.username.lower() == normalized_username.lower():
            return user

    return None


def change_user_role(user: UserAccount, new_role: UserRole) -> UserAccount:
    user.role = new_role
    return user


def deactivate_user(user: UserAccount) -> UserAccount:
    user.is_active = False
    return user