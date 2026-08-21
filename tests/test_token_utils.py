import json

from app.core.token_utils import mask_ozon_credentials, mask_token


def test_mask_token_short_fully_masked():
    assert mask_token("abc") == "***"
    assert mask_token("123456789012") == "*" * 12


def test_mask_token_long_keeps_head_and_tail():
    token = "abcdefgh" + "x" * 20 + "tail12"
    masked = mask_token(token)

    assert masked.startswith("abcdefgh")
    assert masked.endswith("tail12")
    assert "x" not in masked


def test_mask_ozon_credentials_seller():
    secret = json.dumps({"client_id": "1234567890", "api_key": "abcdefghijklmno"})

    masked = mask_ozon_credentials(secret)

    assert masked.startswith("client_id=")
    assert "api_key=" in masked
    assert "1234567890" not in masked
    assert "abcdefghijklmno" not in masked
    assert "client_secret" not in masked


def test_mask_ozon_credentials_performance():
    secret = json.dumps({"client_id": "1234567890", "client_secret": "abcdefghijklmno"})

    masked = mask_ozon_credentials(secret)

    assert "client_secret=" in masked
    assert "api_key" not in masked
    assert "abcdefghijklmno" not in masked


def test_mask_ozon_credentials_falls_back_on_bad_json():
    assert mask_ozon_credentials("not-json") == mask_token("not-json")
