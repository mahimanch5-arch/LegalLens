#!/usr/bin/env python
"""
LegalLens Backend Entry Point

Run the FastAPI application with Uvicorn.

Usage:
    python run.py                 # Run on default port 8000
    python run.py --port 5000     # Run on port 5000
    python run.py --reload        # Run with auto-reload on code changes
"""

import argparse
import os
import sys

import uvicorn

# Force UTF-8 encoding on Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"


def main():
    parser = argparse.ArgumentParser(description="Run LegalLens FastAPI backend")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to run on (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run on (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on file changes"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)"
    )

    args = parser.parse_args()

    print("[*] Starting Legal Lens Backend")
    print(f"    Host: {args.host}")
    print(f"    Port: {args.port}")
    print(f"    Reload: {args.reload}")
    print(f"    Workers: {args.workers}")
    print(f"\n[+] API will be available at http://{args.host}:{args.port}/api")
    print(f"[+] Interactive docs at http://{args.host}:{args.port}/api/docs\n")

    try:
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers if not args.reload else 1,
            log_level="info"
        )
    except Exception as e:
        print(f"[!] Error starting server: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
