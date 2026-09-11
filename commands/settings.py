import subprocess

from utils.platform import is_windows

SETTINGS = {
    "open wifi settings": "ms-settings:network-wifi",
    "open wi-fi settings": "ms-settings:network-wifi",
    "open wifi": "ms-settings:network-wifi",
    "open bluetooth settings": "ms-settings:bluetooth",
    "open bluetooth": "ms-settings:bluetooth",
    "open display settings": "ms-settings:display",
    "open display": "ms-settings:display",
    "open sound settings": "ms-settings:sound",
    "open sound": "ms-settings:sound",
    "open windows settings": "ms-settings:",
    "open settings": "ms-settings:",
    "open personalization": "ms-settings:personalization",
    "open personalization settings": "ms-settings:personalization",
    "open windows update": "ms-settings:windowsupdate",
    "open update": "ms-settings:windowsupdate",
    "open default apps": "ms-settings:defaultapps",
    "open notifications": "ms-settings:notifications",
    "open battery settings": "ms-settings:batterysaver",
}


def handle(user_input):
    lower = user_input.lower().strip()

    for cmd, uri in SETTINGS.items():
        if lower == cmd:
            if is_windows():
                try:
                    subprocess.Popen(["cmd", "/c", "start", uri])
                    return f"Opening settings, Prince."
                except Exception:
                    return "Could not open settings page."
            return "This feature is only available on Windows."

    return None
