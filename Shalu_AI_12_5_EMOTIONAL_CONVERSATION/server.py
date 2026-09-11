from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import webbrowser

ROOT = Path(__file__).parent.resolve()
PORT = 8765

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

url = f"http://127.0.0.1:{PORT}/index.html"
print(f"SHALU AI 12.5 running at {url}")
webbrowser.open(url)

server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
