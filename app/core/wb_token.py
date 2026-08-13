"""
Декодер JWT-токенов Wildberries API.

Читает payload токена (без проверки подписи) и достаёт из него:
кабинет (oid), тип, права (по битам), срок действия.

Права зашиты в поле "s" (bitmask): каждый бит = доступ к разделу API.
Источник модели — рабочий валидатор ключей + реальные токены WB.
"""

import base64
import json
import time


# Разделы API по битам поля "s". Бит -> человекочитаемое имя.
WB_SCOPES = {
    1: "Content",
    2: "Analytics",
    3: "Prices and discounts",
    4: "Marketplace",
    5: "Statistics",
    6: "Promotion",
    7: "Feedbacks and Questions",
    9: "Buyers chat",
    10: "Supplies",
    11: "Buyers returns",
    12: "Documents",
    13: "Finance",
    16: "Users",
    30: "Read only",
}

# Тип токена по полю "acc".
WB_TYPES = {
    1: "Base",
    2: "Test",
    3: "Personal",
    4: "Service",
}

# Бит "только чтение" внутри bitmask.
READ_ONLY_BIT = 30


def _decode_base64url(part: str) -> bytes:
    """Декодировать одну часть JWT из base64url в байты."""
    normalized = part.replace("-", "+").replace("_", "/")
    padding = "=" * (-len(normalized) % 4)
    return base64.b64decode(normalized + padding)


def decode_jwt(token: str) -> dict:
    """
    Вернуть payload токена как словарь.

    JWT состоит из трёх частей через точку: header.payload.signature.
    Нам нужна средняя часть (payload). Подпись не проверяем — только читаем.
    """
    parts = token.strip().split(".")
    if len(parts) < 2:
        raise ValueError("Некорректный JWT: ожидалось минимум 2 части")

    payload_bytes = _decode_base64url(parts[1])
    return json.loads(payload_bytes.decode("utf-8"))


def has_scope(bitmask: int, bit: int) -> bool:
    """Проверить, установлен ли бит в маске прав."""
    return (bitmask & (2 ** bit)) != 0


def get_scopes(bitmask: int) -> list[str]:
    """Список доступных разделов API по маске прав."""
    return [
        name
        for bit, name in WB_SCOPES.items()
        if has_scope(bitmask, bit)
    ]


def token_info(token: str, now: int | None = None) -> dict:
    """
    Собрать полную информацию о токене для дашборда.

    now — текущее время (unix seconds); по умолчанию системное.
    Параметр нужен, чтобы тесты могли зафиксировать время.
    """
    if now is None:
        now = int(time.time())

    payload = decode_jwt(token)

    bitmask = int(payload.get("s", 0))
    exp = int(payload.get("exp", 0))
    days_left = (exp - now) // 86400 if exp else None

    return {
        # внешний ID кабинета; часть типов токенов кладёт его в sid, а не oid
        "cabinet_id": payload.get("oid") or payload.get("sid"),
        "user_id": payload.get("uid"),         # внешний ID пользователя
        "token_id": payload.get("id"),         # внутренний UUID токена
        "acc_type": WB_TYPES.get(payload.get("acc"), str(payload.get("acc", ""))),
        "scopes": get_scopes(bitmask),
        "is_read_only": has_scope(bitmask, READ_ONLY_BIT),
        "is_test": bool(payload.get("t", False)),
        "for": payload.get("for"),             # назначение токена, если указано
        "bitmask": bitmask,
        "expires_at": exp,
        "days_left": days_left,
        "is_active": exp > now if exp else False,
    }