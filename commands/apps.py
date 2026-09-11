import os
import shutil
import subprocess
from pathlib import Path

from utils.platform import open_path, open_url, get_os, is_windows

APPS = {
    "open notepad": ("notepad", "Notepad"),
    "open calculator": ("calc", "Calculator"),
    "open paint": ("mspaint", "Paint"),
    "open task manager": ("taskmgr", "Task Manager"),
    "open command prompt": ("cmd", "Command Prompt"),
    "open powershell": ("powershell", "PowerShell"),
    "open word": ("winword", "Microsoft Word"),
    "open excel": ("excel", "Microsoft Excel"),
    "open powerpoint": ("powerpnt", "Microsoft PowerPoint"),
}

FOLDERS = {
    "open downloads": Path.home() / "Downloads",
    "open documents": Path.home() / "Documents",
    "open pictures": Path.home() / "Pictures",
    "open desktop": Path.home() / "Desktop",
    "open c drive": Path("C:\\"),
    "open d drive": Path("D:\\"),
    "open project folder": Path(__file__).parent.parent,
}


def _open_app(command, name):
    system = get_os()
    if system == "windows":
        try:
            subprocess.Popen(command, shell=True)
            return True
        except Exception:
            try:
                os.startfile(command)
                return True
            except Exception:
                return False
    else:
        if shutil.which(command):
            try:
                subprocess.Popen([command])
                return True
            except Exception:
                return False
    return False


def _open_vscode():
    system = get_os()
    if system == "windows":
        if shutil.which("code"):
            try:
                subprocess.Popen(["cmd", "/c", "code"])
                return True
            except Exception:
                pass
        for p in [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Microsoft VS Code" / "Code.exe",
            Path(r"C:\Program Files\Microsoft VS Code\Code.exe"),
            Path(r"C:\Users") / os.getlogin() / "AppData" / "Local" / "Programs" / "Microsoft VS Code" / "Code.exe",
        ]:
            if p.exists():
                try:
                    subprocess.Popen([str(p)])
                    return True
                except Exception:
                    pass
        return False
    else:
        if shutil.which("code"):
            try:
                subprocess.Popen(["code"])
                return True
            except Exception:
                return False
        return False


def _open_spotify():
    system = get_os()
    if system == "windows":
        try:
            subprocess.Popen(["cmd", "/c", "start", "spotify:"])
            return True
        except Exception:
            pass
        for p in [
            Path(os.environ.get("APPDATA", "")) / "Spotify" / "Spotify.exe",
            Path(r"C:\Users") / os.getlogin() / "AppData" / "Roaming" / "Spotify" / "Spotify.exe",
        ]:
            if p.exists():
                try:
                    subprocess.Popen([str(p)])
                    return True
                except Exception:
                    pass
        return False
    else:
        if shutil.which("spotify"):
            try:
                subprocess.Popen(["spotify"])
                return True
            except Exception:
                pass
        return False


def handle(user_input):
    lower = user_input.lower().strip()

    for cmd, (command, name) in APPS.items():
        if lower == cmd or lower == cmd.replace("open ", ""):
            if _open_app(command, name):
                return f"Opening {name}, Prince."
            return f"Sorry Prince, I couldn't find {name}."

    if lower in ("open vscode", "open visual studio code", "vscode"):
        if _open_vscode():
            return "Opening VS Code, Prince."
        return "Sorry Prince, VS Code is not installed."

    if lower in ("open spotify", "spotify"):
        if _open_spotify():
            return "Opening Spotify, Prince."
        return "Sorry Prince, Spotify is not installed."

    if lower in ("open file explorer", "file explorer", "open files", "open my computer", "my computer"):
        if is_windows():
            try:
                subprocess.Popen(["explorer"])
                return "Opening File Explorer, Prince."
            except Exception:
                return "Sorry Prince, couldn't open File Explorer."
        else:
            open_path(Path.home())
            return "Opening Home folder, Prince."

    for cmd, folder in FOLDERS.items():
        if lower == cmd:
            if folder.exists():
                open_path(folder)
                return f"Opening {folder.name}, Prince."
            return f"Sorry Prince, {folder} doesn't exist."

    return None
