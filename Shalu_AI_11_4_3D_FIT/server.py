from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import webbrowser, threading

ROOT = Path(__file__).resolve().parent
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(ROOT),**kwargs)

def open_browser():
    webbrowser.open("http://127.0.0.1:8765/index.html")

print("SHALU 3D SERVER READY")
print("Open: http://127.0.0.1:8765/index.html")
threading.Timer(0.8, open_browser).start()
ThreadingHTTPServer(("127.0.0.1",8765),Handler).serve_forever()
