"""Base model and shared shapes.

JSON is camelCase (``sizeBytes``, ``nextCursor``) to match ``frontend/src/api/types.ts``.
Two kinds of optionality follow the TypeScript exactly:

- ``T | null`` in TS  → a plain ``T | None`` field, always present, serialised as ``null``;
- ``field?: T`` in TS → ``= omitted()``, left out of the JSON entirely when it is ``None``.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    def dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)


def _is_none(value: object) -> bool:
    return value is None


def omitted() -> Any:
    """Default for an optional (``field?``) property: absent from the JSON when unset."""
    return Field(default=None, exclude_if=_is_none)


ErrorCode = Literal["llm_unavailable", "rate_limited", "timeout", "parse_failure", "unknown"]
DocType = Literal["contract", "opinion", "pleading", "other"]
DocStatus = Literal["queued", "parsing", "indexing", "ready", "failed"]
Mode = Literal["auto", "ask", "summary", "draft"]
Intent = Literal["ask", "summary", "draft"]


class ApiErrorBody(CamelModel):
    code: ErrorCode
    message: str
    retry_after_sec: int | None = omitted()


class Page[T](CamelModel):
    items: list[T]
    next_cursor: str | None = None
