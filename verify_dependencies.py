#!/usr/bin/env python3
"""Verify external dependencies for generate-3plus1-diagrams.

This script checks only user/environment prerequisites: Python packages,
browser runtime, draw.io runtime, and optional network access. Repository files,
fixtures, generated artifacts, and renderer self-tests are internal health
checks and are intentionally outside this dependency check.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys
from urllib.request import Request, urlopen


def pass_check(name: str, detail: str = "") -> None:
    print(f"PASS {name}{': ' + detail if detail else ''}")


def warn_check(name: str, detail: str) -> None:
    print(f"WARN {name}: {detail}")


def fail_check(name: str, detail: str) -> None:
    print(f"FAIL {name}: {detail}")


def import_module(module_name: str, package_name: str) -> bool:
    try:
        module = __import__(module_name)
    except Exception as exc:
        fail_check(package_name, str(exc))
        return False

    version = getattr(module, "__version__", "")
    pass_check(package_name, version or "import ok")
    return True


async def check_playwright_chromium() -> bool:
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:
        fail_check("playwright chromium", f"playwright import failed: {exc}")
        return False

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            await browser.close()
    except Exception as exc:
        fail_check(
            "playwright chromium",
            f"{exc}. Run `python -m playwright install chromium`.",
        )
        return False

    pass_check("playwright chromium", "launch ok")
    return True


def check_drawio_runtime(check_network: bool) -> None:
    extension_root = Path.home() / ".vscode" / "extensions" / "hediet.vscode-drawio-1.9.0"
    webapp_index = extension_root / "drawio" / "src" / "main" / "webapp" / "index.html"
    if webapp_index.exists():
        pass_check("draw.io webapp", str(webapp_index))
        return

    if not check_network:
        warn_check(
            "draw.io webapp",
            "local VS Code draw.io webapp not found; exporter will fall back to https://embed.diagrams.net/.",
        )
        return

    try:
        request = Request("https://embed.diagrams.net/", method="HEAD")
        with urlopen(request, timeout=10) as response:
            pass_check("draw.io web runtime", f"HTTP {response.status}")
    except Exception as exc:
        fail_check("draw.io web runtime", str(exc))
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify dependencies for generate-3plus1-diagrams.")
    parser.add_argument(
        "--check-network",
        action="store_true",
        help="Also verify access to the remote diagrams.net embed runtime when no local webapp is installed.",
    )
    args = parser.parse_args()

    ok = True
    ok = import_module("PIL", "pillow") and ok
    ok = import_module("playwright", "playwright") and ok
    ok = asyncio.run(check_playwright_chromium()) and ok

    try:
        check_drawio_runtime(args.check_network)
    except Exception:
        ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
