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


# Разделы API по битам поля "s". Бит -> (человекочитаемое имя, ping URL).
# URL берётся из боевого валидатора ключей (reference/api_key_stats.gs).
# "Read only" — не раздел API, а флаг; ping URL для него нет.
WB_SCOPES = {
    1: ("Content", "https://content-api.wildberries.ru/ping"),
    2: ("Analytics", "https://seller-analytics-api.wildberries.ru/ping"),
    3: ("Prices and discounts", "https://discounts-prices-api.wildberries.ru/ping"),
    4: ("Marketplace", "https://marketplace-api.wildberries.ru/ping"),
    5: ("Statistics", "https://statistics-api.wildberries.ru/ping"),
    6: ("Promotion", "https://advert-api.wildberries.ru/ping"),
    7: ("Feedbacks and Questions", "https://feedbacks-api.wildberries.ru/ping"),
    9: ("Buyers chat", "https://buyer-chat-api.wildberries.ru/ping"),
    10: ("Supplies", "https://supplies-api.wildberries.ru/ping"),
    11: ("Buyers returns", "https://returns-api.wildberries.ru/ping"),
    12: ("Documents", "https://documents-api.wildberries.ru/ping"),
    13: ("Finance", "https://finance-api.wildberries.ru/ping"),
    16: ("Users", "https://user-management-api.wildberries.ru/ping"),
    30: ("Read only", None),
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
        for bit, (name, _url) in WB_SCOPES.items()
        if has_scope(bitmask, bit)
    ]


def get_scopes_with_ping_urls(bitmask: int) -> list[tuple[int, str, str | None]]:
    """
    Доступные разделы API по маске прав вместе с их ping URL.

    Возвращает (bit, name, ping_url); ping_url — None для разделов без
    отдельного эндпоинта (например Read only). Используется модулем
    проверки живости ключей (wb_ping).
    """
    return [
        (bit, name, url)
        for bit, (name, url) in WB_SCOPES.items()
        if has_scope(bitmask, bit)
    ]


def get_scope_hosts() -> list[tuple[str, str]]:
    """
    Все разделы API вместе с их базовым хостом (без маски прав — это не
    "что доступно этому токену", а полный список разделов WB API).

    Нужно API Tester: у WB нет единого домена для всех методов, у каждого
    раздела свой хост (content-api, statistics-api, ...) — значит выбор
    раздела должен определять base_url запроса, а не только показывать
    имя. Хост получаем из ping URL, отбросив суффикс "/ping". "Read only"
    пропускаем — это флаг токена, а не раздел с собственным API (у него и
    ping URL нет).
    """
    return [
        (name, url.removesuffix("/ping"))
        for _bit, (name, url) in sorted(WB_SCOPES.items())
        if url is not None
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