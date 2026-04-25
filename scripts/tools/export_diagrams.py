from __future__ import annotations

import argparse
import asyncio
import base64
import json
import posixpath
import tempfile
import threading
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from PIL import Image
from playwright.async_api import ConsoleMessage, async_playwright


DRAWIO_EXTENSION_ROOT = Path.home() / ".vscode" / "extensions" / "hediet.vscode-drawio-1.9.0"
DRAWIO_WEBAPP_ROOT = DRAWIO_EXTENSION_ROOT / "drawio" / "src" / "main" / "webapp"
DRAWIO_WEBAPP_INDEX = DRAWIO_WEBAPP_ROOT / "index.html"
DRAWIO_REMOTE_EMBED_URL = "https://embed.diagrams.net/"
HARNESS_TEMPLATE = Path(__file__).with_name("drawio_export_harness.html")
BACKGROUND = (255, 255, 255, 255)


def iter_targets(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if target.is_dir():
        return sorted(target.glob("*.drawio"))
    raise FileNotFoundError(f"Target not found: {target}")


def ensure_drawio_runtime() -> None:
    if not DRAWIO_WEBAPP_ROOT.exists() and not DRAWIO_REMOTE_EMBED_URL:
        raise FileNotFoundError(
            "Bundled draw.io webapp not found at "
            f"{DRAWIO_WEBAPP_ROOT}. Install the VS Code draw.io extension first."
        )
    if not HARNESS_TEMPLATE.exists():
        raise FileNotFoundError(f"Harness template not found: {HARNESS_TEMPLATE}")


def build_harness_html(base_href: str) -> str:
    template = HARNESS_TEMPLATE.read_text(encoding="utf-8")
    return template.replace("__BASE_HREF__", base_href)


def drawio_base_href(host: str, port: int) -> str:
    if DRAWIO_WEBAPP_INDEX.exists():
        return f"http://{host}:{port}/index.html"
    return DRAWIO_REMOTE_EMBED_URL


def default_drawio_config() -> dict[str, Any]:
    return {
        "compressXml": True,
        "simpleLabels": False,
    }


class DrawioHarness:
    def __init__(self, page) -> None:
        self.page = page
        self.events: list[dict[str, Any]] = []
        self.pending_waiters: list[tuple[str, asyncio.Future[dict[str, Any]]]] = []

    async def on_console(self, message: ConsoleMessage) -> None:
        if message.type == "error":
            print(f"[drawio console error] {message.text}")

    async def on_drawio_message(self, payload: Any) -> None:
        if isinstance(payload, str):
            text = payload
        else:
            text = json.dumps(payload)
        try:
            message = json.loads(text)
        except json.JSONDecodeError:
            return
        if not isinstance(message, dict):
            return
        self.events.append(message)
        for expected_event, future in list(self.pending_waiters):
            if future.done():
                self.pending_waiters.remove((expected_event, future))
                continue
            if message.get("event") == expected_event:
                future.set_result(message)
                self.pending_waiters.remove((expected_event, future))
                break

    async def wait_for_event(self, event_name: str, timeout_ms: int = 30000) -> dict[str, Any]:
        for index, existing in enumerate(self.events):
            if existing.get("event") == event_name:
                return self.events.pop(index)
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        waiter = (event_name, future)
        self.pending_waiters.append(waiter)
        try:
            result = await asyncio.wait_for(future, timeout=timeout_ms / 1000)
            if result in self.events:
                self.events.remove(result)
            return result
        finally:
            if waiter in self.pending_waiters:
                self.pending_waiters.remove(waiter)

    async def send_action(self, action: dict[str, Any]) -> None:
        serialized = json.dumps(action, ensure_ascii=False)
        await self.page.evaluate("(payload) => window.__dispatchHostMessage(payload)", serialized)


class DrawioRequestHandler(SimpleHTTPRequestHandler):
    webapp_root: Path
    harness_path: Path

    def translate_path(self, path: str) -> str:
        parsed = urlsplit(path)
        clean_path = posixpath.normpath(unquote(parsed.path))
        if clean_path in {"/", "/harness.html"}:
            return str(self.harness_path)
        return str(self.webapp_root / clean_path.lstrip("/"))

    def log_message(self, format: str, *args: Any) -> None:
        return


@contextmanager
def start_drawio_server():
    with tempfile.TemporaryDirectory(prefix="drawio-export-") as temp_dir:
        temp_root = Path(temp_dir)
        server = ThreadingHTTPServer(("127.0.0.1", 0), DrawioRequestHandler)
        host, port = server.server_address

        harness_path = temp_root / "harness.html"
        harness_path.write_text(
            build_harness_html(drawio_base_href(host, port)),
            encoding="utf-8",
        )

        handler = type(
            "BoundDrawioRequestHandler",
            (DrawioRequestHandler,),
            {
                "webapp_root": DRAWIO_WEBAPP_ROOT,
                "harness_path": harness_path,
            },
        )
        server.RequestHandlerClass = handler

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://{host}:{port}/harness.html"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def flatten_png_background(path: Path) -> None:
    with Image.open(path) as img:
        rgba = img.convert("RGBA")
        flattened = Image.alpha_composite(Image.new("RGBA", rgba.size, BACKGROUND), rgba).convert("RGB")
        flattened.save(path)


async def export_with_real_drawio(
    drawio_path: Path,
    output_path: Path,
    *,
    flatten_png: bool = True,
) -> None:
    ensure_drawio_runtime()

    with start_drawio_server() as harness_url:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                page = await browser.new_page(viewport={"width": 1600, "height": 1200})
                harness = DrawioHarness(page)

                await page.expose_function("drawioHostPostMessage", harness.on_drawio_message)
                page.on("console", harness.on_console)
                await page.goto(harness_url, wait_until="load")

                await harness.wait_for_event("configure")
                await harness.send_action({
                    "action": "configure",
                    "config": default_drawio_config(),
                })

                await harness.wait_for_event("init")

                xml = drawio_path.read_text(encoding="utf-8")
                await harness.send_action({
                    "action": "load",
                    "xml": xml,
                    "autosave": 1,
                })

                await harness.send_action({
                    "action": "export",
                    "format": "xml",
                    "actionId": "export-xml",
                })
                await harness.wait_for_event("export")

                format_name = "xmlpng" if output_path.suffix.lower() == ".png" else "xmlsvg"
                await harness.send_action({
                    "action": "export",
                    "format": format_name,
                    "actionId": f"export-{format_name}",
                })
                export_event = await harness.wait_for_event("export", timeout_ms=60000)

                data = str(export_event.get("data") or "")
                prefix = (
                    "data:image/png;base64,"
                    if output_path.suffix.lower() == ".png"
                    else "data:image/svg+xml;base64,"
                )
                if not data.startswith(prefix):
                    raise ValueError(
                        f"Unexpected export payload for {drawio_path}: missing prefix {prefix!r}"
                    )

                decoded = base64.b64decode(data[len(prefix):])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(decoded)
                await page.close()
            finally:
                await browser.close()

    if flatten_png and output_path.suffix.lower() == ".png":
        flatten_png_background(output_path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export generated draw.io diagrams using the real draw.io renderer."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="docs/architecture",
        help="Directory containing .drawio files",
    )
    parser.add_argument(
        "--format",
        default="png",
        choices=["png", "svg"],
        help="Export format",
    )
    parser.add_argument(
        "--output-dir",
        help="Directory for exported previews (defaults to <target>/exports)",
    )
    parser.add_argument(
        "--preserve-alpha",
        action="store_true",
        help="Keep PNG alpha instead of flattening onto white.",
    )
    args = parser.parse_args()

    target = Path(args.target)
    try:
        ensure_drawio_runtime()
        files = iter_targets(target)
    except Exception as exc:
        print(f"export_diagrams.py failed: {exc}")
        return 1

    if not files:
        print(f"export_diagrams.py failed: no .drawio files found in {target}")
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else (
        target.parent / "exports" if target.is_file() else target / "exports"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        for drawio_path in files:
            output_path = output_dir / f"{drawio_path.stem}.{args.format}"
            asyncio.run(
                export_with_real_drawio(
                    drawio_path,
                    output_path,
                    flatten_png=not args.preserve_alpha,
                )
            )
            print(f"Exported {drawio_path} -> {output_path}")
    except Exception as exc:
        print(f"export_diagrams.py failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
