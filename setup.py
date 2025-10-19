from setuptools import setup
import sys

# ruft beim Build oder pip install den Windows-Launcher-Installer auf
if sys.platform == "win32":
    try:
        from installer_windows import post_install
        post_install()
    except Exception as e:
        print(f"[localchat installer warning] {e}")

setup()
