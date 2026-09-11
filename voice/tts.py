import asyncio
import os
import subprocess
import tempfile

import edge_tts

from config import VOICES
from utils.platform import get_os


async def generate_voice(text, voice, filename):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)


def speak(text, language="en"):
    voice = VOICES.get(language, VOICES["en"])
    output_file = os.path.join(tempfile.gettempdir(), "shalu_tts.mp3")
    try:
        asyncio.run(generate_voice(text, voice, output_file))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(generate_voice(text, voice, output_file))
        finally:
            loop.close()
    _play(output_file)
    return True


def _play(filename):
    system = get_os()
    if system == "windows":
        os.startfile(filename)
    elif system == "mac":
        subprocess.Popen(["afplay", filename])
    else:
        subprocess.Popen(["aplay", filename])