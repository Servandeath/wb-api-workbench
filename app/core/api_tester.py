"""
Core-логика раздела API Tester: разбор JSON-тела запроса из формы и сам
HTTP-вызов к WB API.

Сознательно не через app.core.http_client.WBHttpClient — у него
response.raise_for_status() кидает исключение на любой не-2xx статус,
что для пинг-проверок (wb_ping.py) и тестера одинаково неудобно: тестеру
как раз важно увидеть тело ответа 400/401/429, а не потерять его в
исключении. wb_ping.py/ozon_ping.py уже обходят http_client тем же
способом — прямой httpx.
"""

import json

import httpx


def parse_json_body(text: str) -> dict | None:
    """
    Текст из поля "JSON body" в форме -> dict для запроса, или None если
    поле пустое (GET, или POST без тела). Пустая/пробельная строка -
    валидное "тела нет", а не ошибка.
    """
    stripped = text.strip()
    if not stripped:
        return None

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON body: {error}") from error

    if not isinstance(parsed, dict):
        raise ValueError('JSON body must be an object, e.g. {"key": "value"}')

    return parsed


def normalize_path(path: str) -> str:
    stripped = path.strip()
    if not stripped:
        raise ValueError("Path is required")

    return stripped.lstrip("/")


async def send_wb_request(
    client: httpx.AsyncClient,
    token: str,
    method: str,
    path: str,
    json_body: dict | None = None,
    base_url: str = "https://seller-api.wildberries.ru",
) -> dict:
    """
    Выполняет запрос к WB API и всегда возвращает
    {"status_code": int, "body": dict|str} — включая ошибочные статусы,
    без исключения. Сетевой сбой (нет соединения и т.п.) — отдельный
    случай, httpx.RequestError по-прежнему летит наверх, вызывающий код
    должен ловить его сам.
    """
    url = f"{base_url.rstrip('/')}/{normalize_path(path)}"
    headers = {"Authorization": token, "Content-Type": "application/json"}

    if method == "GET":
        response = await client.get(url, headers=headers, timeout=30)
    else:
        response = await client.post(
            url, headers=headers, json=json_body or {}, timeout=30
        )

    try:
        body = response.json()
    except ValueError:
        body = response.text

    return {"status_code": response.status_code, "body": body}
