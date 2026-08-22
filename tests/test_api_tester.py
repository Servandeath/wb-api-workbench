import asyncio

import httpx
import pytest

from app.core.api_tester import normalize_path, parse_json_body, send_wb_request


def run(coro):
    return asyncio.run(coro)


# ---- parse_json_body ----


def test_parse_json_body_empty_string_returns_none():
    assert parse_json_body("") is None


def test_parse_json_body_whitespace_only_returns_none():
    assert parse_json_body("   \n  ") is None


def test_parse_json_body_valid_object():
    assert parse_json_body('{"a": 1, "b": "x"}') == {"a": 1, "b": "x"}


def test_parse_json_body_invalid_json_raises():
    with pytest.raises(ValueError):
        parse_json_body("{not json")


def test_parse_json_body_non_object_raises():
    with pytest.raises(ValueError):
        parse_json_body("[1, 2, 3]")


# ---- normalize_path ----


def test_normalize_path_strips_leading_slash():
    assert normalize_path("/api/v1/foo") == "api/v1/foo"


def test_normalize_path_strips_whitespace():
    assert normalize_path("  api/v1/foo  ") == "api/v1/foo"


def test_normalize_path_empty_raises():
    with pytest.raises(ValueError):
        normalize_path("   ")


# ---- send_wb_request ----


def test_send_wb_request_get_success():
    def handler(request):
        return httpx.Response(200, json={"result": "ok"})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await send_wb_request(client, "token123", "GET", "/api/v1/foo")

    result = run(scenario())

    assert result["status_code"] == 200
    assert result["body"] == {"result": "ok"}


def test_send_wb_request_get_sends_auth_header_and_builds_url():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json={})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await send_wb_request(
                client, "my-token", "GET", "/api/v1/foo", base_url="https://example.test"
            )

    run(scenario())

    assert seen["url"] == "https://example.test/api/v1/foo"
    assert seen["auth"] == "my-token"


def test_send_wb_request_post_sends_json_body():
    seen = {}

    def handler(request):
        seen["method"] = request.method
        seen["body"] = request.content
        return httpx.Response(201, json={"created": True})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await send_wb_request(
                client, "token", "POST", "/api/v1/foo", json_body={"name": "x"}
            )

    result = run(scenario())

    assert seen["method"] == "POST"
    assert b'"name"' in seen["body"]
    assert result["status_code"] == 201
    assert result["body"] == {"created": True}


def test_send_wb_request_does_not_raise_on_error_status():
    def handler(request):
        return httpx.Response(400, json={"error": "bad request"})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await send_wb_request(client, "token", "GET", "/api/v1/foo")

    result = run(scenario())

    assert result["status_code"] == 400
    assert result["body"] == {"error": "bad request"}


def test_send_wb_request_non_json_response_returns_raw_text():
    def handler(request):
        return httpx.Response(500, text="internal error")

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await send_wb_request(client, "token", "GET", "/api/v1/foo")

    result = run(scenario())

    assert result["status_code"] == 500
    assert result["body"] == "internal error"
