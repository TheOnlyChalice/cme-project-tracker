"""
Local development server for the CME API.

Runs the same handler() that Lambda runs, on http://localhost:3001, so the
backend can be developed and tested without Docker, LocalStack, or Terraform.

Usage (from the repo root, in Git Bash):
    python backend/v1/dev_server.py
    python backend/v1/dev_server.py --port 3002

Settings (such as the PostgreSQL connection) are read from backend/v1/.env
if that file exists. Copy .env.sample to .env to create it.
"""

import argparse
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))

# Make "function" and "app" importable no matter which folder this is run from.
sys.path.insert(0, HERE)


# [ACME: DEV ENV FILE HERE]
# How: Before the app loads, each KEY=VALUE line in backend/v1/.env becomes an
#      environment variable, unless that variable is already set.
# Why: The database settings (host, password, database name) must be set
#      before the app chooses its storage backend. A local .env file saves
#      typing them into every new terminal, and .gitignore keeps it (and your
#      password) out of GitHub. On Lambda, the workshop injects these settings
#      instead.
def load_env_file(path: str) -> None:
    """
    Load KEY=VALUE lines from a file into the environment.

    Args:
        path: The file to read; missing files are ignored.
    """
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file(os.path.join(HERE, ".env"))

from function import handler  # noqa: E402  pylint: disable=wrong-import-position

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
    # [ACME: CORS AUTH HEADER HERE]
    # How: Authorization is listed by name rather than relying on "*".
    # Why: Browsers don't let the "*" wildcard cover the Authorization header,
    #      so without this the React app on port 3000 couldn't send its token.
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
}


# [ACME: LOCAL DEV SERVER HERE]
# How: A standard-library HTTP server turns each request into the same event
#      shape a Lambda Function URL sends, calls handler(), and writes the
#      response back, adding CORS headers for the React app on port 3000.
# Why: The workshop's start-dev.sh needs PostgreSQL, MongoDB, Docker,
#      LocalStack, and Terraform. None of that is needed for an in-memory
#      backend, and because this calls the exact code Lambda runs, behavior
#      locally matches behavior once deployed from the WorkSpace.
class LambdaRequestHandler(BaseHTTPRequestHandler):
    """Translate HTTP requests into Lambda events and back."""

    def _handle(self) -> None:
        """Build a Lambda event from this request, run it, and send the reply."""
        url = urlsplit(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8") if length else ""

        # Lambda joins repeated query keys with commas, so do the same here.
        query = {key: ",".join(values) for key, values in parse_qs(url.query).items()}

        event: dict[str, Any] = {
            "rawPath": url.path,
            "rawQueryString": url.query,
            "queryStringParameters": query or None,
            "headers": {key.lower(): value for key, value in self.headers.items()},
            "requestContext": {"http": {"method": self.command, "path": url.path}},
            "body": body or None,
            "isBase64Encoded": False,
        }

        result = handler(event)
        status = int(result.get("statusCode", 200))
        payload = result.get("body") or ""

        self.send_response(status)
        for key, value in {**result.get("headers", {}), **CORS_HEADERS}.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(payload.encode("utf-8"))))
        self.end_headers()
        if payload:
            self.wfile.write(payload.encode("utf-8"))

    def do_OPTIONS(self) -> None:  # noqa: N802 (name required by BaseHTTPRequestHandler)
        """Answer browser CORS preflight requests."""
        self.send_response(204)
        for key, value in CORS_HEADERS.items():
            self.send_header(key, value)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests."""
        self._handle()

    def do_POST(self) -> None:  # noqa: N802
        """Handle POST requests."""
        self._handle()

    def do_PUT(self) -> None:  # noqa: N802
        """Handle PUT requests."""
        self._handle()

    def do_PATCH(self) -> None:  # noqa: N802
        """Handle PATCH requests."""
        self._handle()

    def do_DELETE(self) -> None:  # noqa: N802
        """Handle DELETE requests."""
        self._handle()


def main() -> None:
    """Start the dev server."""
    parser = argparse.ArgumentParser(description="Run the CME API locally.")
    parser.add_argument("--port", type=int, default=3001, help="Port to listen on (default 3001).")
    args = parser.parse_args()

    # [ACME: LOCALHOST ONLY HERE]
    # How: The server binds to 127.0.0.1 rather than 0.0.0.0.
    # Why: Only your own machine can reach it, and the Bandit security scan in
    #      the repo's GitHub workflow flags servers that listen on all interfaces.
    server = ThreadingHTTPServer(("127.0.0.1", args.port), LambdaRequestHandler)
    from app.store import store  # pylint: disable=import-outside-toplevel
    print(f"Storage: {store.backend_name}")
    print(f"CME API running at http://localhost:{args.port}/api/v1  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
