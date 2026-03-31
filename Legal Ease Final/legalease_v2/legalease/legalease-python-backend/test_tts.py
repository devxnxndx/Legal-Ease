import sys
import os

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))

from main import app


client = TestClient(app)

print("Registered routes:")
for route in app.routes:
    methods = getattr(route, "methods", None)
    path = getattr(route, "path", None)
    if methods and path:
        print(f"{sorted(methods)} {path}")

print("\nTest 1: Testing /api/voice/voices...")
res_voices = client.get("/api/voice/voices")
print(
    "Response voices:",
    res_voices.status_code,
    res_voices.json() if res_voices.status_code == 200 else res_voices.text,
)

print("\nTest 2: Testing /api/voice/speak...")
payload = {
    "text": "Hello world",
    "language": "english",
}
res_speak = client.post("/api/voice/speak", json=payload)

print("Status:", res_speak.status_code)
print("Content-Type:", res_speak.headers.get("content-type"))

if res_speak.status_code == 200:
    print("X-Spoken-Summary:", res_speak.headers.get("X-Spoken-Summary", "")[:200])
    print("Audio bytes length:", len(res_speak.content))
else:
    print("Error:", res_speak.text[:500])

print("\nDone.")