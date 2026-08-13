"""
Проверка живости ключей Ozon.

В отличие от WB, ключ Ozon непрозрачный (не JWT) — узнать, что он даёт,
можно только реальным вызовом API, локального декодирования нет.
У Ozon два независимых типа credentials на одного продавца:

- Seller API: Client-Id + Api-Key, проверяется лёгким POST на
  /v3/product/list (limit=1).
- Performance API: Client ID + Client Secret, проверяется через OAuth2
  client_credentials на /api/client/token.

Логика и трактовка кодов перенесены из боевого валидатора
(reference/ozon_key_stats.gs, checkOzonSellerEndpoint_ / checkOzonPerformanceFull_).
"""

import httpx

SELLER_PRODUCT_LIST_URL = "https://api-seller.ozon.ru/v3/product/list"
PERFORMANCE_TOKEN_URL = "https://api-performance.ozon.ru/api/client/token"

REQUEST_TIMEOUT_SECONDS = 15


def classify_seller_status(code: int | str) -> str:
    """
    Свести HTTP-код ответа Seller API в статус.

    Те же коды, что и в боевом скрипте: 200 — ключ рабочий, 400 —
    запрос сформирован неверно (но ключ, вероятно, валиден), 401 —
    ключ не авторизован, 403 — запрещено, 404 — метод недоступен,
    429 — упёрлись в рейт-лимит. Всё остальное — общая ошибка.
    """
    mapping = {
        200: "OK",
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        429: "RATE_LIMITED",
    }
    return mapping.get(code, "ERROR")


def classify_performance_status(code: int | str, has_access_token: bool) -> str:
    """
    Свести ответ Performance API (OAuth2 token endpoint) в статус.

    Успех — только 200 с access_token в теле; 200 без токена (сервер
    ответил, но без ожидаемого поля) трактуется как ошибка, а не как OK.
    """
    if code == 200 and has_access_token:
        return "OK"
    if code == 401:
        return "UNAUTHORIZED"
    if code == 403:
        return "FORBIDDEN"
    if code == 429:
        return "RATE_LIMITED"
    if code in (301, 302, 307, 308):
        return "REDIRECT"
    return "ERROR"


async def check_seller_key(
    client: httpx.AsyncClient,
    client_id: str,
    api_key: str,
) -> dict:
    """
    Проверить ключ Seller API лёгким запросом (список товаров, limit=1).

    Сетевые ошибки не пробрасываются исключением: код "ERR", статус "ERROR".
    """
    try:
        response = await client.post(
            SELLER_PRODUCT_LIST_URL,
            headers={
                "Client-Id": str(client_id),
                "Api-Key": str(api_key),
            },
            json={"filter": {"visibility": "ALL"}, "last_id": "", "limit": 1},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        code = response.status_code

        return {
            "status": classify_seller_status(code),
            "code": code,
            "body": response.text,
        }
    except httpx.HTTPError as error:
        return {
            "status": "ERROR",
            "code": "ERR",
            "body": str(error),
        }


async def check_performance_key(
    client: httpx.AsyncClient,
    client_id: str,
    client_secret: str,
) -> dict:
    """
    Проверить credentials Performance API через OAuth2 client_credentials.

    Сетевые ошибки не пробрасываются исключением: код "ERR", статус "ERROR".
    """
    try:
        response = await client.post(
            PERFORMANCE_TOKEN_URL,
            headers={"Accept": "application/json"},
            json={
                "client_id": str(client_id),
                "client_secret": str(client_secret),
                "grant_type": "client_credentials",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        code = response.status_code

        payload: dict = {}
        has_token = False
        if code == 200:
            try:
                payload = response.json()
                has_token = "access_token" in payload
            except ValueError:
                payload = {}

        return {
            "status": classify_performance_status(code, has_token),
            "code": code,
            "access_token_present": has_token,
            "expires_in": payload.get("expires_in"),
            "token_type": payload.get("token_type"),
            "body": response.text,
        }
    except httpx.HTTPError as error:
        return {
            "status": "ERROR",
            "code": "ERR",
            "access_token_present": False,
            "expires_in": None,
            "token_type": None,
            "body": str(error),
        }
