import ctypes
import os
import subprocess
import sys
import webbrowser


def get_os():
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def is_windows():
    return get_os() == "windows"


def open_path(path):
    system = get_os()
    try:
        if system == "windows":
            os.startfile(str(path))
        elif system == "mac":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as e:
        print(f"Could not open {path}: {e}")


def open_url(url):
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Could not open URL {url}: {e}")


def open_app(command, name):
    try:
        if isinstance(command, str):
            subprocess.Popen(command, shell=True)
        else:
            subprocess.Popen(command)
    except Exception as e:
        print(f"Could not launch {name}: {e}")


def press_media_key(vk_code, key_name="media key"):
    if not is_windows():
        print(f"Media keys are Windows-only. Skipping {key_name}.")
        return
    try:
        user32 = ctypes.windll.user32
        KEYEVENTF_KEYUP = 0x0002
        user32.keybd_event(vk_code, 0, 0, 0)
        user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
    except Exception as e:
        print(f"Could not press {key_name} (vk_code {vk_code}): {e}")


def lock_screen():
    system = get_os()
    try:
        if system == "windows":
            subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
        elif system == "mac":
            subprocess.Popen(["pmset", "displaysleepnow"])
        else:
            subprocess.Popen(["loginctl", "lock-session"])
    except Exception as e:
        print(f"Could not lock the screen: {e}")