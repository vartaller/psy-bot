import base64
import hashlib
import os

from cryptography.fernet import Fernet

BOT_TOKEN = os.environ["BOT_TOKEN"]
DATABASE_URL = os.environ["DATABASE_URL"]
ENCRYPTION_SECRET = os.environ["ENCRYPTION_SECRET"]


def _fernet(user_id: int) -> Fernet:
    key = hashlib.sha256(f"{ENCRYPTION_SECRET}:{user_id}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(user_id: int, text: str) -> str:
    return _fernet(user_id).encrypt(text.encode()).decode()


def decrypt(user_id: int, token: str) -> str:
    return _fernet(user_id).decrypt(token.encode()).decode()


def safe_decrypt(user_id: int, token: str) -> str:
    try:
        return decrypt(user_id, token)
    except Exception:
        return "—"
