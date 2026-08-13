import json
from pathlib import Path

from cryptography.fernet import Fernet

from app.config import SECURE_DIR
from app.core.token_utils import mask_token


MASTER_KEY_PATH = SECURE_DIR / "master.key"
TOKENS_PATH = SECURE_DIR / "encrypted_keys.json"


def ensure_secure_dir() -> None:
    SECURE_DIR.mkdir(parents=True, exist_ok=True)


def load_or_create_master_key() -> bytes:
    ensure_secure_dir()

    if MASTER_KEY_PATH.exists():
        return MASTER_KEY_PATH.read_bytes()

    key = Fernet.generate_key()
    MASTER_KEY_PATH.write_bytes(key)
    return key


class EncryptedFileKeyStorage:
    def __init__(self) -> None:
        key = load_or_create_master_key()
        self.fernet = Fernet(key)

    def _load_data(self) -> dict:
        ensure_secure_dir()

        if not TOKENS_PATH.exists():
            return {}

        with TOKENS_PATH.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _save_data(self, data: dict) -> None:
        ensure_secure_dir()

        with TOKENS_PATH.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def save_token(self, key_name: str, token: str) -> dict:
        if not key_name:
            raise ValueError("Key name is required")

        if not token:
            raise ValueError("Token is required")

        data = self._load_data()

        encrypted_token = self.fernet.encrypt(token.encode("utf-8")).decode("utf-8")

        data[key_name] = {
            "encrypted_token": encrypted_token,
            "masked_token": mask_token(token),
            "storage_type": "encrypted_file",
        }

        self._save_data(data)

        return {
            "name": key_name,
            "masked_token": mask_token(token),
            "storage_type": "encrypted_file",
        }

    def get_token(self, key_name: str) -> str | None:
        data = self._load_data()

        item = data.get(key_name)
        if not item:
            return None

        encrypted_token = item["encrypted_token"]

        return self.fernet.decrypt(
            encrypted_token.encode("utf-8")
        ).decode("utf-8")

    def delete_token(self, key_name: str) -> None:
        data = self._load_data()

        if key_name in data:
            del data[key_name]
            self._save_data(data)
