import queue
import time

import sounddevice as sd
import speech_recognition as sr

LANGUAGES = ("en-IN", "hi-IN", "gu-IN")
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 500
IGNORABLE_ERRORS = (sr.UnknownValueError, sr.RequestError)


def find_microphone():
    try:
        devices = sd.query_devices()
        for index, device in enumerate(devices):
            if device["max_input_channels"] > 0:
                return index, device["name"]
    except Exception:
        pass
    return None, "No usable microphone"


def listen(device_index=None, timeout=6.0, silence_limit=2.0):
    if device_index is None:
        device_index, _ = find_microphone()
        if device_index is None:
            return ""

    audio_queue = queue.Queue()
    sample_width = 2

    def callback(indata, frames, time_info, status):
        audio_queue.put(indata.copy())

    chunks = []
    silence_started = None
    started = time.time()
    with sd.InputStream(
        device=device_index,
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        callback=callback,
    ):
        while time.time() - started < timeout:
            try:
                data = audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            peak = max(abs(sample) for sample in data.flat)
            if peak > SILENCE_THRESHOLD:
                chunks.append(data)
                silence_started = None
            elif chunks:
                if silence_started is None:
                    silence_started = time.time()
                elif time.time() - silence_started >= silence_limit:
                    break

    if not chunks:
        return ""

    raw_audio = b"".join(bytes(chunk) for chunk in chunks)
    recognizer = sr.Recognizer()
    audio_data = sr.AudioData(raw_audio, SAMPLE_RATE, sample_width)
    return _recognize(recognizer, audio_data)


def _recognize(recognizer, audio_data):
    for language in LANGUAGES:
        try:
            return recognizer.recognize_google(audio_data, language=language)
        except IGNORABLE_ERRORS:
            continue
    return ""


def microphone_test():
    index, name = find_microphone()
    if index is None:
        return name
    text = listen(index, timeout=4.0, silence_limit=1.5)
    if text:
        return f"Microphone works. Heard: {text}"
    return "Microphone found, but no speech detected."