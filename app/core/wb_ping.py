"""
Проверка живости ключа: пинг разделов WB API, доступных токену по битам.

Логика перенесена из боевого валидатора ключей
(reference/api_key_stats.gs, функции pingOne_/reducePing_): дёргаем /ping
каждого раздела, который есть в bitmask токена, и сводим коды ответов
в один статус. Между запросами — пауза, чтобы не словить рейт-лимит WB.

Пинг намеренно не использует raise_for_status() — 401/403/429 здесь
не ошибки клиента, а значимые статусы, которые нужно увидеть и свести.
"""

import asyncio

import httpx

from app.core.wb_token import get_scopes_with_ping_urls

PING_TIMEOUT_SECONDS = 10
# Пауза между пингами разных разделов одного токена (см. reference-скрипт).
PING_SLEEP_SECONDS = 0.35


async def ping_url(client: httpx.AsyncClient, token: str, url: str) -> int | str:
    """
    Дёрнуть один /ping URL, вернуть HTTP-код ответа.

    Сетевые ошибки (таймаут, обрыв соединения и т.д.) возвращаются как
    строка "ERR", а не пробрасываются исключением — reduce_ping_results
    работает со списком кодов, а не с try/except на каждый раздел.
    """
    try:
        response = await client.get(
            url,
            headers={"Authorization": token},
            timeout=PING_TIMEOUT_SECONDS,
        )
        return response.status_code
    except httpx.HTTPError:
        return "ERR"


def reduce_ping_results(codes: list[int | str]) -> str:
    """
    Свести коды ответов нескольких разделов в один статус.

    Порядок приоритета — как в боевом скрипте: любой 200 значит, что
    ключ живой ("OK"), даже если другие разделы вернули ошибку. Иначе
    смотрим на самый значимый код ошибки: 401 -> 429 -> 403 -> остальное.
    Пустой список (нечего было пинговать) тоже считается ошибкой.
    """
    if 200 in codes:
        return "OK"
    if 401 in codes:
        return "401"
    if 429 in codes:
        return "429"
    if 403 in codes:
        return "403"
    return "ERROR"


async def ping_token(token: str, bitmask: int) -> str:
    """
    Пропинговать все разделы, доступные токену по bitmask, вернуть сводный статус.

    Разделы без ping URL (например Read only) пропускаются. Если у токена
    нет ни одного раздела с URL, пинговать нечего — возвращается "NO_SCOPES".
    """
    scopes = [
        (name, url)
        for _bit, name, url in get_scopes_with_ping_urls(bitmask)
        if url is not None
    ]

    if not scopes:
        return "NO_SCOPES"

    codes: list[int | str] = []

    async with httpx.AsyncClient() as client:
        for index, (_name, url) in enumerate(scopes):
            if index:
                await asyncio.sleep(PING_SLEEP_SECONDS)
            codes.append(await ping_url(client, token, url))

    return reduce_ping_results(codes)
