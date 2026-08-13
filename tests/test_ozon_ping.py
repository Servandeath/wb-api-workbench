import asyncio
import json

import httpx

from app.core.ozon_ping import (
    check_performance_key,
    check_seller_key,
    classify_performance_status,
    classify_seller_status,
)


def run(coro):
    """Маленький хелпер, чтобы не тянуть pytest-asyncio ради нескольких тестов."""
    return asyncio.run(coro)


# ---- classify_seller_status ----


def test_classify_seller_status_200_is_ok():
    assert classify_seller_status(200) == "OK"


def test_classify_seller_status_400_is_bad_request():
    assert classify_seller_status(400) == "BAD_REQUEST"


def test_classify_seller_status_401_is_unauthorized():
    assert classify_seller_status(401) == "UNAUTHORIZED"


def test_classify_seller_status_403_is_forbidden():
    assert classify_seller_status(403) == "FORBIDDEN"


def test_classify_seller_status_404_is_not_found():
    assert classify_seller_status(404) == "NOT_FOUND"


def test_classify_seller_status_429_is_rate_limited():
    assert classify_seller_status(429) == "RATE_LIMITED"


def test_classify_seller_status_unknown_code_is_error():
    assert classify_seller_status(500) == "ERROR"


def test_classify_seller_status_err_string_is_error():
    assert classify_seller_status("ERR") == "ERROR"


# ---- classify_performance_status ----


def test_classify_performance_status_200_with_token_is_ok():
    assert classify_performance_status(200, has_access_token=True) == "OK"


def test_classify_performance_status_200_without_token_is_error():
    assert classify_performance_status(200, has_access_token=False) == "ERROR"


def test_classify_performance_status_401_is_unauthorized():
    assert classify_performance_status(401, has_access_token=False) == "UNAUTHORIZED"


def test_classify_performance_status_403_is_forbidden():
    assert classify_performance_status(403, has_access_token=False) == "FORBIDDEN"


def test_classify_performance_status_429_is_rate_limited():
    assert classify_performance_status(429, has_access_token=False) == "RATE_LIMITED"


def test_classify_performance_status_redirect_codes():
    for code in (301, 302, 307, 308):
        assert classify_performance_status(code, has_access_token=False) == "REDIRECT"


def test_classify_performance_status_unknown_code_is_error():
    assert classify_performance_status(500, has_access_token=False) == "ERROR"


# ---- check_seller_key ----


def test_check_seller_key_success():
    def handler(request):
        return httpx.Response(200, json={"result": {"items": []}})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await check_seller_key(client, "12345", "seller-api-key")

    result = run(scenario())

    assert result["status"] == "OK"
    assert result["code"] == 200


def test_check_seller_key_sends_client_id_and_api_key_headers():
    seen = {}

    def handler(request):
        seen["Client-Id"] = request.headers.get("Client-Id")
        seen["Api-Key"] = request.headers.get("Api-Key")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await check_seller_key(client, "12345", "secret-key")

    run(scenario())

    assert seen["Client-Id"] == "12345"
    assert seen["Api-Key"] == "secret-key"
    assert seen["body"]["limit"] == 1


def test_check_seller_key_unauthorized():
    def handler(request):
        return httpx.Response(401, text="invalid api key")

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await check_seller_key(client, "12345", "bad-key")

    result = run(scenario())

    assert result["status"] == "UNAUTHORIZED"
    assert result["code"] == 401


def test_check_seller_key_network_failure_returns_err():
    def handler(request):
        raise httpx.ConnectError("boom", request=request)

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await check_seller_key(client, "12345", "key")

    result = run(scenario())

    assert result["status"] == "ERROR"
    assert result["code"] == "ERR"


# ---- check_performance_key ----


def test_check_performance_key_success_parses_token_fields():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "access_token": "abc123",
                "token_type": "Bearer",
                "expires_in": 1800,
            },
        )

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await check_performance_key(client, "client-id", "client-secret")

    result = run(scenario())

    assert result["status"] == "OK"
    assert result["access_token_present"] is True
    assert result["expires_in"] == 1800
    assert result["token_type"] == "Bearer"


def test_check_performance_key_sends_client_credentials_body():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"access_token": "x"})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await check_performance_key(client, "cid", "csecret")

    run(scenario())

    assert seen["body"] == {
        "client_id": "cid",
        "client_secret": "csecret",
        "grant_type": "client_credentials",
    }


def test_check_performance_key_200_without_token_is_error():
    def handler(request):
        return httpx.Response(200, json={"unexpected": "shape"})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await check_performance_key(client, "cid", "csecret")

    result = run(scenario())

    assert result["status"] == "ERROR"
    assert result["access_token_present"] is False


def test_check_performance_key_unauthorized():
    def handler(request):
        return httpx.Response(401, text="invalid client")

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await check_performance_key(client, "cid", "bad-secret")

    result = run(scenario())

    assert result["status"] == "UNAUTHORIZED"
    assert result["access_token_present"] is False


def test_check_performance_key_network_failure_returns_err():
    def handler(request):
        raise httpx.ConnectError("boom", request=request)

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await check_performance_key(client, "cid", "csecret")

    result = run(scenario())

    assert result["status"] == "ERROR"
    assert result["code"] == "ERR"
