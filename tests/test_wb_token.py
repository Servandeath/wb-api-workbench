import base64
import json

from app.core.wb_token import (
    decode_jwt,
    get_scope_hosts,
    get_scopes,
    get_scopes_with_ping_urls,
    has_scope,
    token_info,
)


def _make_token(payload: dict) -> str:
    """
    Собрать синтетический JWT без подписи для тестов edge-кейсов payload.
    decode_jwt/token_info подпись не проверяют, так что произвольные
    header/signature part'ы допустимы.
    """
    payload_b64 = (
        base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8"))
        .rstrip(b"=")
        .decode("ascii")
    )
    return f"header.{payload_b64}.signature"


# Реальный WB-токен (read-only, кабинет 4102012) как золотой образец.
# Протухает в 2026, но для структуры и разбора битов срок не важен.
SAMPLE_TOKEN = (
    "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjYwMzAydjEiLCJ0eXAiOiJKV1QifQ."
    "eyJhY2MiOjEsImVudCI6MSwiZXhwIjoxNzk3MjgwMDkyLCJpZCI6IjAxOWVjYTY1"
    "LTNiMzktNzkwOS1hNTAzLWI1OTVmZGZiYTc0NSIsImlpZCI6NDM4ODM3NDMsIm9p"
    "ZCI6NDEwMjAxMiwicyI6MTA3Mzc0MTgyOCwic2lkIjoiMTMwZjQ0NTAtYTVkMS00"
    "Mzg0LTlhYTItMjJhNmJjOGZmMDI1IiwidCI6ZmFsc2UsInVpZCI6NDM4ODM3NDN9."
    "8L_RWR4TmSHmrTwHuZNdhqnu4wYTm7H-bPg4H_zQvu7V8Y1Zqy3Tr843mTh8iHiJ"
    "C5wjXyEZ04jixFKqrn__Lw"
)

# exp токена = 1797280092. Фиксируем "сейчас" на 161 день раньше,
# чтобы is_active/days_left в тестах были стабильны и не зависели от даты запуска.
BEFORE_EXP = 1797280092 - 161 * 86400


def test_decode_jwt_returns_payload():
    payload = decode_jwt(SAMPLE_TOKEN)

    assert payload["oid"] == 4102012
    assert payload["acc"] == 1
    assert payload["s"] == 1073741828


def test_decode_jwt_rejects_bad_token():
    import pytest

    with pytest.raises(ValueError):
        decode_jwt("not-a-jwt")


def test_has_scope():
    bitmask = 1073741828  # Analytics (бит 2) + Read only (бит 30)

    assert has_scope(bitmask, 2) is True
    assert has_scope(bitmask, 30) is True
    assert has_scope(bitmask, 1) is False


def test_get_scopes():
    scopes = get_scopes(1073741828)

    assert scopes == ["Analytics", "Read only"]


def test_token_info_external_ids():
    info = token_info(SAMPLE_TOKEN, now=BEFORE_EXP)

    assert info["cabinet_id"] == 4102012
    assert info["user_id"] == 43883743


def test_token_info_type_and_scopes():
    info = token_info(SAMPLE_TOKEN, now=BEFORE_EXP)

    assert info["acc_type"] == "Base"
    assert info["scopes"] == ["Analytics", "Read only"]
    assert info["is_read_only"] is True
    assert info["is_test"] is False


def test_token_info_active_before_exp():
    info = token_info(SAMPLE_TOKEN, now=BEFORE_EXP)

    assert info["is_active"] is True
    assert info["days_left"] == 161


def test_token_info_expired_after_exp():
    after_exp = 1797280092 + 86400

    info = token_info(SAMPLE_TOKEN, now=after_exp)

    assert info["is_active"] is False
    assert info["days_left"] < 0


def test_token_info_prefers_oid_over_sid():
    token = _make_token({"oid": 111, "sid": "some-uuid", "exp": 0, "s": 0})

    info = token_info(token, now=0)

    assert info["cabinet_id"] == 111


def test_token_info_falls_back_to_sid_when_oid_missing():
    token = _make_token({"sid": "some-uuid", "exp": 0, "s": 0})

    info = token_info(token, now=0)

    assert info["cabinet_id"] == "some-uuid"


def test_token_info_reads_for_field():
    token = _make_token({"for": "marketplace-api", "exp": 0, "s": 0})

    info = token_info(token, now=0)

    assert info["for"] == "marketplace-api"


def test_token_info_for_defaults_to_none():
    token = _make_token({"exp": 0, "s": 0})

    info = token_info(token, now=0)

    assert info["for"] is None


def test_get_scopes_with_ping_urls_includes_url():
    bitmask = 1073741828  # Analytics (бит 2) + Read only (бит 30)

    scopes = get_scopes_with_ping_urls(bitmask)

    assert scopes == [
        (2, "Analytics", "https://seller-analytics-api.wildberries.ru/ping"),
        (30, "Read only", None),
    ]


def test_get_scope_hosts_strips_ping_suffix():
    hosts = dict(get_scope_hosts())

    assert hosts["Analytics"] == "https://seller-analytics-api.wildberries.ru"
    assert hosts["Statistics"] == "https://statistics-api.wildberries.ru"


def test_get_scope_hosts_excludes_read_only():
    names = [name for name, _url in get_scope_hosts()]

    assert "Read only" not in names


def test_get_scope_hosts_returns_all_scopes_not_just_a_bitmask():
    # В отличие от get_scopes_with_ping_urls, тут не про конкретный токен -
    # это полный список разделов, независимо от прав.
    names = [name for name, _url in get_scope_hosts()]

    assert "Content" in names
    assert "Finance" in names
    assert "Users" in names
    assert len(names) == 13