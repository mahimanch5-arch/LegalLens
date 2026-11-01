"""Encryption at rest for uploaded files (NFR-9)."""

from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import Settings, get_settings


def _load_key(settings: Settings) -> bytes:
    if settings.encryption_key:
        return settings.encryption_key.encode()
    if not settings.is_dev:
        raise RuntimeError("LL_ENCRYPTION_KEY must be set outside dev/test.")
    # Dev convenience: generate once and keep it next to the data it protects.
    key_file = settings.data_dir / ".blobkey"
    if key_file.exists():
        return key_file.read_bytes().strip()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    key_file.write_bytes(key)
    return key


@lru_cache
def get_fernet() -> Fernet:
    return Fernet(_load_key(get_settings()))


def encrypt(data: bytes) -> bytes:
    return get_fernet().encrypt(data)


def decrypt(token: bytes) -> bytes:
    return get_fernet().decrypt(token)
