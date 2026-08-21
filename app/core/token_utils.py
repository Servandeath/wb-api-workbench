import json


def mask_token(token: str) -> str:
    if len(token) <= 12:
        return "*" * len(token)

    return f"{token[:8]}...{'*' * 12}...{token[-6:]}"


def mask_ozon_credentials(secret_json: str) -> str:
    """
    Ozon-ключи хранятся как JSON-строка ({"client_id": ..., "api_key": ...}
    или {"client_id": ..., "client_secret": ...}) — mask_token() на такой
    строке маскирует байты JSON целиком (фигурные скобки, кавычки, ключи
    полей), а не сами значения, и выглядит нечитаемо. Здесь маскируем
    значения полей по отдельности и собираем читаемую подпись.

    При некорректном JSON откатываемся на обычный mask_token — не должно
    случаться в реальной работе (secret всегда приходит из
    _collect_ozon_secret), но не должны падать на неожиданном вводе.
    """
    try:
        data = json.loads(secret_json)
    except (TypeError, ValueError):
        return mask_token(secret_json)

    client_id = str(data.get("client_id", ""))
    secret_field = "api_key" if "api_key" in data else "client_secret"
    secret_value = str(data.get(secret_field, ""))

    return f"client_id={mask_token(client_id)} {secret_field}={mask_token(secret_value)}"
