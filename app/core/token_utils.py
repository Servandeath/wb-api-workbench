def mask_token(token: str) -> str:
    if len(token) <= 12:
        return "*" * len(token)

    return f"{token[:8]}...{'*' * 12}...{token[-6:]}"
