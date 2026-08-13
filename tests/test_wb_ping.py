import asyncio

import httpx

from app.core import wb_ping
from app.core.wb_ping import ping_token, ping_url, reduce_ping_results


def run(coro):
    """Маленький хелпер, чтобы не тянуть pytest-asyncio ради нескольких тестов."""
    return asyncio.run(coro)


def test_reduce_ping_results_ok_wins_over_errors():
    assert reduce_ping_results([401, 200, 403]) == "OK"


def test_reduce_ping_results_401():
    assert reduce_ping_results([401, 429]) == "401"


def test_reduce_ping_results_429():
    assert reduce_ping_results([429, 403]) == "429"


def test_reduce_ping_results_403():
    assert reduce_ping_results([403, 500]) == "403"


def test_reduce_ping_results_other_error():
    assert reduce_ping_results([500, "ERR"]) == "ERROR"


def test_reduce_ping_results_empty_is_error():
    assert reduce_ping_results([]) == "ERROR"


def test_ping_url_returns_status_code():
    def handler(request):
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)

    async def scenario():
        async with httpx.AsyncClient(transport=transport) as client:
            return await ping_url(client, "token", "https://example.com/ping")

    assert run(scenario()) == 200


def test_ping_url_sends_raw_token_in_authorization_header():
    seen_headers = {}

    def handler(request):
        seen_headers["Authorization"] = request.headers.get("Authorization")
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)

    async def scenario():
        async with httpx.AsyncClient(transport=transport) as client:
            await ping_url(client, "my-token", "https://example.com/ping")

    run(scenario())

    assert seen_headers["Authorization"] == "my-token"


def test_ping_url_returns_err_on_network_failure():
    def handler(request):
        raise httpx.ConnectError("boom", request=request)

    transport = httpx.MockTransport(handler)

    async def scenario():
        async with httpx.AsyncClient(transport=transport) as client:
            return await ping_url(client, "token", "https://example.com/ping")

    assert run(scenario()) == "ERR"


def test_ping_token_returns_no_scopes_when_bitmask_has_no_ping_urls(monkeypatch):
    monkeypatch.setattr(wb_ping, "PING_SLEEP_SECONDS", 0)

    # bit 30 (Read only) is the only scope and it has no ping URL.
    read_only_bitmask = 2 ** 30

    assert run(ping_token("token", read_only_bitmask)) == "NO_SCOPES"


def test_ping_token_pings_every_scope_and_reduces(monkeypatch):
    monkeypatch.setattr(wb_ping, "PING_SLEEP_SECONDS", 0)

    calls = []

    def handler(request):
        calls.append(str(request.url))
        if "seller-analytics-api" in str(request.url):
            return httpx.Response(401)
        return httpx.Response(200)

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *a, **k: real_async_client(transport=httpx.MockTransport(handler)),
    )

    bitmask = 2 ** 1 | 2 ** 2  # Content + Analytics

    result = run(ping_token("token", bitmask))

    assert len(calls) == 2
    assert result == "OK"  # Content returns 200, so OK wins even though Analytics is 401
