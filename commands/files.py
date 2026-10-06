import os
import shutil
from pathlib import Path

from utils.platform import open_path, get_os

DOCUMENTS = Path.home() / "Documents"
SEARCH_ROOTS = [
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "Downloads",
]

PENDING_DELETE = {"active": False, "path": None}


def _find_file(name):
    name_lower = name.lower().strip()
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            for fname in filenames:
                if name_lower in fname.lower():
                    return Path(dirpath) / fname
    if is_windows():
        for drive in ["C:\\", "D:\\"]:
            drive_path = Path(drive)
            if drive_path.exists():
                for dirpath, dirnames, filenames in os.walk(drive_path):
                    for fname in filenames:
                        if name_lower in fname.lower():
                            return Path(dirpath) / fname
                    if len(dirnames) > 200:
                        dirnames.clear()
    return None


def handle(user_input):
    global PENDING_DELETE
    lower = user_input.lower().strip()

    if PENDING_DELETE["active"]:
        if lower in ("yes", "y", "confirm", "do it", "go ahead"):
            path = PENDING_DELETE["path"]
            PENDING_DELETE = {"active": False, "path": None}
            if path and path.exists():
                try:
                    if path.is_file():
                        path.unlink()
                    else:
                        shutil.rmtree(path)
                    return f"Deleted: {path.name}, Prince."
                except Exception as e:
                    return f"Could not delete: {e}"
            return "File not found. It may have already been deleted."
        elif lower in ("no", "n", "cancel", "nope", "nevermind"):
            PENDING_DELETE = {"active": False, "path": None}
            return "Delete cancelled, Prince."

    if lower.startswith("create folder ") or lower.startswith("make folder "):
        name = user_input.split(None, 2)[-1]
        folder_path = DOCUMENTS / name
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            return f"Created folder '{name}' in Documents, Prince."
        except Exception as e:
            return f"Could not create folder: {e}"

    if lower.startswith("create file ") or lower.startswith("make file "):
        name = user_input.split(None, 2)[-1]
        if not name.endswith(".txt"):
            name += ".txt"
        file_path = DOCUMENTS / name
        try:
            file_path.touch()
            return f"Created file '{name}' in Documents, Prince."
        except Exception as e:
            return f"Could not create file: {e}"

    if lower.startswith("find file ") or lower.startswith("search file ") or lower.startswith("find ") or lower.startswith("search "):
        parts = user_input.split(None, 2)
        if len(parts) < 3:
            return "Tell me the file name to search, Prince."
        name = parts[2]
        result = _find_file(name)
        if result:
            return f"Found: {result}\nDo you want me to open it?"
        return f"No file found matching '{name}', Prince."

    if lower.startswith("delete file ") or lower.startswith("remove file "):
        parts = user_input.split(None, 2)
        if len(parts) < 3:
            return "Tell me the file name to delete, Prince."
        name = parts[2]
        result = _find_file(name)
        if result:
            PENDING_DELETE = {"active": True, "path": result}
            return f"Found: {result.name}\nAre you sure you want to delete it? (yes/no)"
        return f"No file found matching '{name}', Prince."

    if lower.startswith("open file "):
        parts = user_input.split(None, 2)
        if len(parts) < 3:
            return "Tell me the file name to open, Prince."
        name = parts[2]
        result = _find_file(name)
        if result:
            open_path(result)
            return f"Opening {result.name}, Prince."
        return f"No file found matching '{name}', Prince."

    if lower.startswith("rename file "):
        parts = user_input.split(None, 2)
        if len(parts) < 3:
            return "Use: rename file X to Y"
        rest = parts[2]
        if " to " in rest:
            old_name, new_name = rest.split(" to ", 1)
        elif " as " in rest:
            old_name, new_name = rest.split(" as ", 1)
        else:
            return "Use: rename file X to Y"
        result = _find_file(old_name.strip())
        if result:
            new_path = result.parent / new_name.strip()
            try:
                result.rename(new_path)
                return f"Renamed to '{new_name.strip()}', Prince."
            except Exception as e:
                return f"Could not rename: {e}"
        return f"No file found matching '{old_name.strip()}', Prince."

    if lower in ("list downloads", "show downloads", "downloads list"):
        dl = Path.home() / "Downloads"
        if not dl.exists():
            return "Downloads folder not found."
        items = sorted(dl.iterdir(), key=lambda p: p.name.lower())
        if not items:
            return "Downloads folder is empty, Prince."
        lines = []
        for item in items[:15]:
            prefix = "[DIR] " if item.is_dir() else "      "
            lines.append(f"{prefix}{item.name}")
        msg = f"Downloads ({len(items)} items total):\n" + "\n".join(lines)
        if len(items) > 15:
            msg += f"\n...and {len(items) - 15} more items."
        return msg

    return None
