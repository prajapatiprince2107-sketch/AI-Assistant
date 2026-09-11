from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
import webbrowser,threading
ROOT=Path(__file__).resolve().parent
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**k): super().__init__(*a,directory=str(ROOT),**k)
print("SHALU AI 11.5 SERVER READY")
print("Open: http://127.0.0.1:8765/index.html")
threading.Timer(.8,lambda:webbrowser.open("http://127.0.0.1:8765/index.html")).start()
ThreadingHTTPServer(("127.0.0.1",8765),Handler).serve_forever()
