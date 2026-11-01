"""Writes the OpenAPI schema to docs/api/openapi.json (the M0 "API contract first" artifact).

uv run python -m scripts.export_openapi
"""

import json
from pathlib import Path

from app.core.config import Settings
from app.main import create_app

OUT = Path(__file__).resolve().parents[2] / "docs" / "api" / "openapi.json"


def main() -> None:
    # Production settings, so the dev-only /api/dev routes are not part of the published contract.
    schema = create_app(Settings(env="prod")).openapi()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(schema['paths'])} paths)")


if __name__ == "__main__":
    main()
