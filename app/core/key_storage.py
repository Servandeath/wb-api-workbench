from dataclasses import dataclass

import keyring

from app.core.token_utils import mask_token


SERVICE_NAME = "wb-api-workbench"


@dataclass
class StoredKeyInfo:
    name: str
    masked_token: str
    storage_type: str = "windows_keyring"


class KeyStorage:
    def save_token(self, key_name: str, token: str) -> StoredKeyInfo:
        if not key_name:
            raise ValueError("Key name is required")

        if not token:
            raise ValueError("Token is required")

        keyring.set_password(SERVICE_NAME, key_name, token)

        return StoredKeyInfo(
            name=key_name,
            masked_token=mask_token(token),
        )

    def get_token(self, key_name: str) -> str | None:
        return keyring.get_password(SERVICE_NAME, key_name)

    def delete_token(self, key_name: str) -> None:
        keyring.delete_password(SERVICE_NAME, key_name)
