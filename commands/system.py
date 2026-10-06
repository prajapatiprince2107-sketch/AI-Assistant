import datetime
import platform
import shutil
import socket
import subprocess
import sys

from utils.platform import get_os, is_windows

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def _get_battery_psutil():
    if not HAS_PSUTIL:
        return None
    bat = psutil.sensors_battery()
    if bat is None:
        return None
    return f"Battery: {bat.percent}% {'Charging' if bat.power_plugged else 'On Battery'}"


def _get_battery_windows():
    try:
        import ctypes
        ctypes.windll.kernel32
        system_status = ctypes.windll.kernel32.GetSystemPowerStatus()
        percent = system_status[2]
        plugged = system_status[1] == 1
        if percent == 255:
            return "Battery status unavailable."
        return f"Battery: {percent}% {'Charging' if plugged else 'On Battery'}"
    except Exception:
        return None


def _get_ram_info():
    if HAS_PSUTIL:
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024 ** 3)
        used_gb = mem.used / (1024 ** 3)
        return f"RAM: {used_gb:.1f} GB used / {total_gb:.1f} GB total ({mem.percent}%)"
    if is_windows():
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            c_ulonglong = ctypes.c_ulonglong
            mem_status = ctypes.c_ulonglong()
            kernel32.GetPhysicallyInstalledMemory(ctypes.byref(mem_status))
            total_gb = mem_status.value / (1024 ** 3)
            return f"RAM: ~{total_gb:.1f} GB total (install psutil for detailed info)"
        except Exception:
            pass
    return "Could not retrieve RAM info. Install psutil: pip install psutil"


def handle(user_input):
    lower = user_input.lower().strip()

    if lower in ("pc information", "system information", "system info", "my pc info"):
        os_name = platform.system()
        os_version = platform.version()
        arch = platform.machine()
        return (f"OS: {os_name}\nVersion: {os_version}\nArchitecture: {arch}\n"
                f"Processor: {platform.processor()}")

    if lower in ("computer name", "pc name", "my computer name"):
        return f"Your computer name is {platform.node()}."

    if lower in ("cpu information", "processor information", "cpu info", "processor info"):
        info = f"Processor: {platform.processor()}"
        if HAS_PSUTIL:
            info += f"\nCPU Cores: {psutil.cpu_count(logical=False)} physical, {psutil.cpu_count()} logical"
            info += f"\nCPU Usage: {psutil.cpu_percent(interval=1)}%"
        return info

    if lower in ("ram usage", "memory usage", "ram info", "memory info"):
        return _get_ram_info()

    if lower in ("disk space", "storage information", "disk info", "storage info"):
        drive = "C:\\\\" if is_windows() else "/"
        try:
            usage = shutil.disk_usage(drive)
            total_gb = usage.total / (1024 ** 3)
            used_gb = usage.used / (1024 ** 3)
            free_gb = usage.free / (1024 ** 3)
            return (f"Disk Space:\nTotal: {total_gb:.1f} GB\n"
                    f"Used: {used_gb:.1f} GB\nFree: {free_gb:.1f} GB")
        except Exception as e:
            return f"Could not get disk info: {e}"

    if lower in ("battery status", "battery info", "battery"):
        result = None
        if is_windows():
            result = _get_battery_windows()
        if result is None:
            result = _get_battery_psutil()
        if result is None:
            return "Battery info unavailable. Install psutil for battery status."
        return result

    if lower.startswith("what time") or lower == "current time":
        now = datetime.datetime.now().strftime("%I:%M %p")
        return f"The current time is {now}, Prince."

    if lower.startswith("what date") or lower == "today date" or lower == "what is the date":
        today = datetime.datetime.now().strftime("%A, %B %d, %Y")
        return f"Today's date is {today}, Prince."

    if lower in ("check internet", "internet status", "internet connection"):
        try:
            sock = socket.create_connection(("1.1.1.1", 53), timeout=3)
            sock.close()
            return "You are connected to the internet, Prince."
        except (socket.timeout, OSError):
            return "No internet connection detected, Prince."

    if lower in ("my ip address", "ip address", "what is my ip"):
        try:
            ip = socket.gethostbyname(socket.gethostname())
            return f"Your IP address is {ip}"
        except Exception:
            return "Could not retrieve IP address."

    if lower in ("wifi status", "network status", "wifi info"):
        try:
            if is_windows():
                result = subprocess.run(
                    ["netsh", "wlan", "show", "interfaces"],
                    capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.split("\n"):
                    line = line.strip()
                    if line.startswith("SSID") or line.startswith("State") or line.startswith("Signal"):
                        return result.stdout.strip()[:500]
                return result.stdout.strip()[:500] if result.stdout.strip() else "WiFi info not available."
            else:
                result = subprocess.run(
                    ["ifconfig"], capture_output=True, text=True, timeout=5
                )
                return result.stdout.strip()[:500] if result.stdout.strip() else "Network info not available."
        except Exception:
            return "Could not retrieve network info."

    if lower in ("what is my name", "who am i", "what's my name", "do you know me"):
        return "Your name is Prince."

    if lower in ("what can you do", "help", "your features", "what are your features"):
        return (
            "Here's what I can do, Prince:\n"
            "- Open apps: Notepad, Calculator, VS Code, Spotify, etc.\n"
            "- Open folders: Downloads, Documents, Desktop, C/D drive\n"
            "- System info: CPU, RAM, battery, disk, IP, time, date\n"
            "- Media: Volume up/down, mute, play/pause, next/prev\n"
            "- File manager: Create, find, delete, rename, list files\n"
            "- Web: Open websites, Google/YouTube search\n"
            "- Settings: WiFi, Bluetooth, Display, Sound settings\n"
            "- Clipboard: Read, clear, copy text\n"
            "- Utilities: Timer, calculator, notes, jokes\n"
            "- Ask me anything! I'll search the web if needed."
        )

    return None
