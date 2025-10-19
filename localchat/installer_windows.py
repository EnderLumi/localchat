import os
import sys
from pathlib import Path

def install_windows_launcher():
    if sys.platform != "win32":
        return

    target_dir = Path(os.getenv("LOCALAPPDATA")) / "Microsoft" / "WindowsApps"
    target_dir.mkdir(parents=True, exist_ok=True)

    launcher_path = target_dir / "localchat.cmd"

    python_exe = sys.executable
    module_call = " -m localchat %*"

    content = f"@echo off\r\n\"{python_exe}\"{module_call}\r\n"

    try:
        launcher_path.write_text(content, encoding="utf-8")
    except PermissionError:
        pass  # still safe to continue

def post_install():
    install_windows_launcher()

if __name__ == "__main__":
    post_install()
