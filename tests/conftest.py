"""pytest configuration and shared fixtures."""
import os
import socket
import threading
import time
import http.server
import functools
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: tests that take more than 1 second")
    config.addinivalue_line("markers", "integration: tests that require file I/O")
    config.addinivalue_line(
        "markers", "e2e: end-to-end tests that require a browser (playwright)"
    )


# ---------------------------------------------------------------------------
# E2E fixtures — only active when pytest-playwright is installed
# ---------------------------------------------------------------------------

E2E_PORT = 8765
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _wait_port_ready(host: str, port: int, timeout: float = 5.0) -> None:
    """Poll a TCP port until it accepts connections (or timeout)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"HTTP server em {host}:{port} não respondeu em {timeout}s")


@pytest.fixture(scope="session")
def e2e_http_server():
    """Start a local HTTP server serving the project root on port 8765.

    Espera a porta aceitar conexões antes de retornar — sem isso, o primeiro
    `page.goto()` pode chegar antes do thread serve_forever ter feito bind,
    causando ECONNREFUSED intermitente (especialmente em runners de CI).
    """
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=_PROJECT_ROOT,
    )
    server = http.server.HTTPServer(("localhost", E2E_PORT), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _wait_port_ready("localhost", E2E_PORT)
    yield f"http://localhost:{E2E_PORT}"
    server.shutdown()


@pytest.fixture()
def e2e_page(e2e_http_server):
    """Return a Playwright page pointed at the local server.

    Requires pytest-playwright to be installed. Tests using this fixture
    should be marked with @pytest.mark.e2e.
    """
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError:
        pytest.skip("playwright not installed — skipping E2E test")

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page()
        yield page
        browser.close()
