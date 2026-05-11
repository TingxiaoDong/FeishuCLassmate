#!/usr/bin/env python3
"""Minimal POST receiver for Temi sidecar ASR webhook testing.

Run:
  python3 scripts/asr-webhook-echo.py [port]

Default port 9877 (override if busy: python3 scripts/asr-webhook-echo.py 10088).

Then start sidecar with:
  export TEMI_ASR_WEBHOOK_URL=http://127.0.0.1:9877/
  cd temi-sidecar && TEMI_IP=<robot_ip> uv run uvicorn server:app --host 127.0.0.1 --port 8091

Speak to Temi (WOZ must emit onASRCompleted). This process prints each POST body.
Simulate without robot:
  curl -sS -X POST http://127.0.0.1:9877/ -H 'Content-Type: application/json' \\
    -d '{"event":"onASRCompleted","text":"测试语音识别","raw":{"event":"onASRCompleted","text":"测试语音识别"}}'
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        print("\n--- ASR webhook POST ---")
        print(body)
        try:
            data = json.loads(body)
            print("parsed.text:", data.get("text"))
        except json.JSONDecodeError as e:
            print("JSON error:", e, file=sys.stderr)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"ok":true}\n')

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    host = "127.0.0.1"
    port = 9877
    if len(sys.argv) >= 2:
        port = int(sys.argv[1])
    httpd = HTTPServer((host, port), Handler)
    print(f"Listening on http://{host}:{port}/ (POST only)")
    print(f"Set TEMI_ASR_WEBHOOK_URL=http://{host}:{port}/ before starting temi-sidecar.")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
