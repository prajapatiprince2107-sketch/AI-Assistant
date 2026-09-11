
import http.server
import socketserver
import os
import sys
import json
import subprocess
import tempfile
import uuid
from urllib.parse import urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
VOICE = "en_US-amy-medium"
PORT = 8765

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE, **kwargs)

    def log_message(self, fmt, *args):
        print(fmt % args)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/speak":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
            text = str(data.get("text", "")).strip()
            emotion = str(data.get("emotion", "neutral")).lower()

            if not text:
                self.send_error(400, "No text")
                return

            # Keep the voice natural. Emotion is expressed mainly by
            # sentence punctuation, pacing, and VRM facial animation.
            length_scale = {
                "happy": 0.94,
                "surprised": 0.90,
                "sad": 1.10,
                "angry": 0.92,
                "relaxed": 1.06,
                "neutral": 1.00,
            }.get(emotion, 1.0)

            temp_name = os.path.join(
                tempfile.gettempdir(), f"shalu_{uuid.uuid4().hex}.wav"
            )

            cmd = [
                sys.executable, "-m", "piper",
                "-m", VOICE,
                "-f", temp_name,
                "--length_scale", str(length_scale),
                "--",
                text
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60
            )

            if result.returncode != 0 or not os.path.exists(temp_name):
                msg = (result.stderr or result.stdout or "Piper synthesis failed")
                self.send_error(500, msg[-1000:])
                return

            with open(temp_name, "rb") as f:
                audio = f.read()

            try:
                os.remove(temp_name)
            except OSError:
                pass

            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(audio)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(audio)

        except subprocess.TimeoutExpired:
            self.send_error(504, "Voice generation timed out")
        except Exception as exc:
            self.send_error(500, str(exc))

if __name__ == "__main__":
    print("=" * 58)
    print(" SHALU AI 13.0 - LOCAL NEURAL VOICE")
    print(" http://127.0.0.1:8765")
    print("=" * 58)
    print("Voice:", VOICE)
    print("Keep this window open while using Shalu.")
    with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler) as httpd:
        httpd.allow_reuse_address = True
        httpd.serve_forever()
