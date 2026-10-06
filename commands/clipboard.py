import sys

_root = None


def _get_root():
    global _root
    if _root is None:
        try:
            import tkinter
            _root = tkinter.Tk()
            _root.withdraw()
        except Exception:
            return None
    return _root


def handle(user_input):
    lower = user_input.lower().strip()

    if lower in ("read my clipboard", "clipboard content", "what is in my clipboard",
                  "what's in my clipboard", "what do i have copied", "paste clipboard"):
        root = _get_root()
        if root is None:
            return "Could not access clipboard."
        try:
            import tkinter
            content = root.clipboard_get()
            if content:
                return f"Clipboard content:\n{content}"
            return "Clipboard is empty, Prince."
        except tkinter.TclError:
            return "Clipboard is empty, Prince."

    if lower in ("clear clipboard", "empty clipboard", "clear my clipboard"):
        root = _get_root()
        if root is None:
            return "Could not access clipboard."
        try:
            import tkinter
            root.clipboard_clear()
            return "Clipboard cleared, Prince."
        except Exception:
            return "Could not clear clipboard."

    if lower.startswith("copy to clipboard ") or lower.startswith("copy this "):
        if lower.startswith("copy to clipboard "):
            text = user_input[len("copy to clipboard "):]
        else:
            text = user_input[len("copy this "):]
        root = _get_root()
        if root is None:
            return "Could not access clipboard."
        try:
            import tkinter
            root.clipboard_clear()
            root.clipboard_append(text)
            return f"Copied to clipboard: {text[:50]}{'...' if len(text) > 50 else ''}"
        except Exception:
            return "Could not copy to clipboard."

    return None
