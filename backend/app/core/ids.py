import secrets
from datetime import UTC, datetime

_ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"  # Crockford-style base32, lowercase


def new_id(prefix: str, length: int = 14) -> str:
    """Readable prefixed id, e.g. ``doc_4k2m9x0q7c1vbn``."""
    return f"{prefix}_{''.join(secrets.choice(_ALPHABET) for _ in range(length))}"


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso(dt: datetime) -> str:
    """ISO-8601 UTC with a trailing Z, e.g. ``2026-10-05T14:03:00.123Z``."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
