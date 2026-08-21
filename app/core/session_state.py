import json
from pathlib import Path

from app.core.settings import AppMode, UserRole, can_use_real_mode

DEFAULT_ROLE = UserRole.VIEWER
DEFAULT_MODE = AppMode.TEST


def load_session_state(path: Path) -> tuple[UserRole, AppMode]:
    """
    Роль и режим, выбранные в прошлый раз в Settings — чтобы не выбирать
    их заново при каждом запуске. Файла ещё нет при первом запуске (и
    сразу после git clone) — тогда просто дефолты, ничего не падает.

    Отдельно валидируем сохранённую пару role/mode через
    can_use_real_mode(): не доверяем файлу на диске вслепую — он мог
    остаться от старой версии матрицы прав или быть отредактирован
    руками. Битую роль/режим просто откатываем на дефолт, а не роняем
    запуск приложения.
    """
    path = Path(path)

    if not path.exists():
        return DEFAULT_ROLE, DEFAULT_MODE

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    try:
        role = UserRole(data["role"])
    except (KeyError, ValueError):
        role = DEFAULT_ROLE

    try:
        mode = AppMode(data["mode"])
    except (KeyError, ValueError):
        mode = DEFAULT_MODE

    if mode == AppMode.REAL and not can_use_real_mode(role):
        mode = DEFAULT_MODE

    return role, mode


def save_session_state(path: Path, role: UserRole, mode: AppMode) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {"role": role.value, "mode": mode.value}

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
