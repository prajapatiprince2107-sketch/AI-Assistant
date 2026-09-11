import subprocess

from utils.platform import press_media_key, get_os, is_windows

VK_VOLUME_UP = 0xAF
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_MUTE = 0xAD
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1


def _linux_volume(direction):
    try:
        if direction == "up":
            subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"])
        elif direction == "down":
            subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%"])
        elif direction == "mute":
            subprocess.Popen(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])
        return True
    except Exception:
        return False


def _mac_volume(direction):
    try:
        if direction == "up":
            subprocess.Popen(["osascript", "-e", "set volume output volume (output volume of (get volume settings) + 10)"])
        elif direction == "down":
            subprocess.Popen(["osascript", "-e", "set volume output volume (output volume of (get volume settings) - 10)"])
        elif direction == "mute":
            subprocess.Popen(["osascript", "-e", "set volume output muted not (output muted of (get volume settings))"])
        return True
    except Exception:
        return False


def handle(user_input):
    lower = user_input.lower().strip()
    system = get_os()

    if lower in ("volume up", "increase volume", "louder", "volume louder"):
        if system == "windows":
            press_media_key(VK_VOLUME_UP, "Volume Up")
        elif system == "linux":
            if not _linux_volume("up"):
                return "Volume control not available on this system."
        elif system == "mac":
            if not _mac_volume("up"):
                return "Volume control not available on this system."
        return "Volume increased, Prince."

    if lower in ("volume down", "decrease volume", "quieter", "volume quieter"):
        if system == "windows":
            press_media_key(VK_VOLUME_DOWN, "Volume Down")
        elif system == "linux":
            if not _linux_volume("down"):
                return "Volume control not available on this system."
        elif system == "mac":
            if not _mac_volume("down"):
                return "Volume control not available on this system."
        return "Volume decreased, Prince."

    if lower in ("mute", "unmute", "mute volume", "unmute volume", "toggle mute"):
        if system == "windows":
            press_media_key(VK_VOLUME_MUTE, "Mute")
        elif system == "linux":
            if not _linux_volume("mute"):
                return "Volume control not available on this system."
        elif system == "mac":
            if not _mac_volume("mute"):
                return "Volume control not available on this system."
        return "Volume toggled, Prince."

    if lower in ("play music", "play", "resume music", "resume", "resume playing"):
        if system == "windows":
            press_media_key(VK_MEDIA_PLAY_PAUSE, "Play/Pause")
            return "Playing music, Prince."
        return "Media playback control is only available on Windows."

    if lower in ("pause music", "pause", "stop music", "stop"):
        if system == "windows":
            press_media_key(VK_MEDIA_PLAY_PAUSE, "Play/Pause")
            return "Paused, Prince."
        return "Media playback control is only available on Windows."

    if lower in ("next song", "next track", "skip song", "next"):
        if system == "windows":
            press_media_key(VK_MEDIA_NEXT_TRACK, "Next Track")
            return "Next song, Prince."
        return "Media playback control is only available on Windows."

    if lower in ("previous song", "previous track", "previous", "back song", "last song"):
        if system == "windows":
            press_media_key(VK_MEDIA_PREV_TRACK, "Previous Track")
            return "Previous song, Prince."
        return "Media playback control is only available on Windows."

    if lower in ("brightness up", "increase brightness", "brighter"):
        if is_windows():
            try:
                import wmi
                w = wmi.WMI(namespace="wmi")
                monitors = w.WmiMonitorBrightnessMethods()
                for m in monitors:
                    current = m.CurrentBrightness
                    new_brightness = min(current + 10, 100)
                    m.WmiSetBrightness(new_brightness, 0)
                return "Brightness increased, Prince."
            except ImportError:
                return "Brightness control requires the wmi module. Run: pip install wmi"
            except Exception:
                return "Could not adjust brightness."
        return "Brightness control is only available on Windows."

    if lower in ("brightness down", "decrease brightness", "dimmer"):
        if is_windows():
            try:
                import wmi
                w = wmi.WMI(namespace="wmi")
                monitors = w.WmiMonitorBrightnessMethods()
                for m in monitors:
                    current = m.CurrentBrightness
                    new_brightness = max(current - 10, 0)
                    m.WmiSetBrightness(new_brightness, 0)
                return "Brightness decreased, Prince."
            except ImportError:
                return "Brightness control requires the wmi module. Run: pip install wmi"
            except Exception:
                return "Could not adjust brightness."
        return "Brightness control is only available on Windows."

    if lower in ("minimize window", "minimize", "minimize all"):
        if is_windows():
            try:
                import ctypes
                user32 = ctypes.windll.user32
                user32.keybd_event(0x5B, 0, 0, 0)
                user32.keybd_event(0x4D, 0, 0, 0)
                user32.keybd_event(0x4D, 0, 2, 0)
                user32.keybd_event(0x5B, 0, 2, 0)
                return "Window minimized, Prince."
            except Exception:
                return "Could not minimize window."
        return "This feature is only available on Windows."

    if lower in ("show desktop", "minimize all windows"):
        if is_windows():
            try:
                import ctypes
                user32 = ctypes.windll.user32
                user32.keybd_event(0x5B, 0, 0, 0)
                user32.keybd_event(0x44, 0, 0, 0)
                user32.keybd_event(0x44, 0, 2, 0)
                user32.keybd_event(0x5B, 0, 2, 0)
                return "Showing desktop, Prince."
            except Exception:
                return "Could not show desktop."
        return "This feature is only available on Windows."

    return None
