import json, urllib.request, urllib.error, threading, webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**k): super().__init__(*a,directory=str(ROOT),**k)
    def do_POST(self):
        if self.path!="/api/speak": self.send_error(404); return
        n=int(self.headers.get("Content-Length","0"))
        data=json.loads(self.rfile.read(n) or "{}")
        text=str(data.get("text","")).strip()
        key=(ROOT/"ELEVENLABS_API_KEY.txt").read_text(encoding="utf-8").strip() if (ROOT/"ELEVENLABS_API_KEY.txt").exists() else ""
        voice=(ROOT/"VOICE_ID.txt").read_text(encoding="utf-8").strip() if (ROOT/"VOICE_ID.txt").exists() else "21m00Tcm4TlvDq8ikWAM"
        if not key or key.startswith("PASTE_"):
            self.send_error(503,"Add your ElevenLabs API key to ELEVENLABS_API_KEY.txt"); return
        body=json.dumps({"text":text,"model_id":"eleven_multilingual_v2",
                         "voice_settings":{"stability":0.45,"similarity_boost":0.82,"style":0.35,"use_speaker_boost":True}}).encode()
        req=urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128",
            data=body,headers={"xi-api-key":key,"Content-Type":"application/json"},method="POST")
        try:
            with urllib.request.urlopen(req,timeout=60) as r: audio=r.read()
            self.send_response(200); self.send_header("Content-Type","audio/mpeg"); self.send_header("Content-Length",str(len(audio))); self.end_headers(); self.wfile.write(audio)
        except urllib.error.HTTPError as e:
            msg=e.read().decode("utf-8","replace"); self.send_response(502); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(msg.encode())
        except Exception as e: self.send_error(502,str(e))
print("SHALU AI 11.7 SERVER READY")
threading.Timer(.8,lambda:webbrowser.open("http://127.0.0.1:8765/index.html")).start()
ThreadingHTTPServer(("127.0.0.1",8765),Handler).serve_forever()
