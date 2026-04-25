import urllib.request
import json
import sys

base = "http://127.0.0.1:8091"

tests = [
    ("/turn", {"degrees": 90, "speed": 0.5}),
    ("/tilt", {"degrees": 15, "speed": 0.5}),
    ("/move", {"x": 1.0, "y": 0.0}),
    ("/ask", {"text": "hello"}),
    ("/wakeup", None),
    ("/follow-start", None),
    ("/follow-stop", None),
    ("/detection-start", None),
    ("/detection-stop", None),
    ("/save-location", {"name": "test"}),
    ("/delete-location", {"name": "test"}),
    ("/status", None),
]

for path, body in tests:
    try:
        url = base + path
        if body is None:
            req = urllib.request.Request(url, method="POST")
        else:
            req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as r:
            resp = r.read().decode()
        print(f"OK  POST {path}: {resp[:200]}")
    except Exception as e:
        print(f"ERR POST {path}: {e}", file=sys.stderr)
