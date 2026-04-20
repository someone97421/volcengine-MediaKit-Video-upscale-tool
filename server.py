from __future__ import annotations

import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


HOST = "127.0.0.1"
PORT = 38473
PROXY_PREFIX = "/proxy/amk"
REMOTE_BASE = "https://amk.cn-beijing.volces.com"


class AppHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        if self.path.startswith(PROXY_PREFIX):
            self._proxy_request("GET")
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path.startswith(PROXY_PREFIX):
            self._proxy_request("POST")
            return
        self.send_error(405, "POST not allowed")

    def _proxy_request(self, method: str) -> None:
        remote_path = self.path[len(PROXY_PREFIX):] or "/"
        target_url = f"{REMOTE_BASE}{remote_path}"

        body = None
        if method in {"POST", "PUT", "PATCH"}:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length > 0 else None

        headers = {}
        for key in ("Authorization", "Content-Type"):
            value = self.headers.get(key)
            if value:
                headers[key] = value

        request = Request(target_url, data=body, headers=headers, method=method)

        try:
            with urlopen(request, timeout=120) as response:
                payload = response.read()
                self.send_response(response.status)
                self.send_header("Content-Type", response.headers.get("Content-Type", "application/json; charset=utf-8"))
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
        except HTTPError as error:
            payload = error.read()
            self.send_response(error.code)
            self.send_header("Content-Type", error.headers.get("Content-Type", "application/json; charset=utf-8"))
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except URLError as error:
            payload = json.dumps({
                "success": False,
                "error": str(error.reason),
                "target_url": target_url
            }).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)


def main() -> None:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Serving on http://{HOST}:{PORT}")
    print(f"MediaKit proxy on http://{HOST}:{PORT}{PROXY_PREFIX}")
    server.serve_forever()


if __name__ == "__main__":
    main()
