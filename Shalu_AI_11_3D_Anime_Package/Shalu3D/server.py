from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import os, webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print('[Shalu3D]', fmt % args)

server = ThreadingHTTPServer(('127.0.0.1', 8765), Handler)
url='http://127.0.0.1:8765/index.html'
print('SHALU 3D SERVER READY')
print('Open:', url)
webbrowser.open(url)
try:
    server.serve_forever()
except KeyboardInterrupt:
    print('\nShalu 3D stopped.')
finally:
    server.server_close()
