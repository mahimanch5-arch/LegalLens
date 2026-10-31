from app.core.errors import bad_request

DEFAULT_LIMIT = 30
MAX_LIMIT = 100


def parse_cursor(cursor: str | None) -> int:
    """Cursors are opaque to the client; today they encode an offset."""
    if not cursor:
        return 0
    if not cursor.isdigit():
        raise bad_request("The cursor is not valid. Reload the list and try again.")
    return int(cursor)


def clamp_limit(limit: int | None) -> int:
    return max(1, min(limit or DEFAULT_LIMIT, MAX_LIMIT))


def next_cursor(offset: int, limit: int, total: int) -> str | None:
    return str(offset + limit) if offset + limit < total else None
