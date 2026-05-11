"""pytest configuration and shared fixtures."""
import os
import threading
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


@pytest.fixture(scope="session")
def e2e_http_server():
    """Start a local HTTP server serving the project root on port 8765."""
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=_PROJECT_ROOT,
    )
    server = http.server.HTTPServer(("localhost", E2E_PORT), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
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
