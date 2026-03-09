from setuptools import setup
import sys

# ruft beim Build oder pip install den Windows-Launcher-Installer auf
if sys.platform == "win32":
    try:
        from installer_windows import post_install
        post_install()
    except Exception as e:
        print(f"[localchat installer warning] {e}")

    """ich binn mir nicht sicher, ob man das für windows evlt braucht, aber es ist auch schon so in der pyproject.toml datei drin. muss ich noch testen"""
    #extras_require = {
    #    "plus": ["prompt_toolkit"],
    #}

"""
Do not add "argon2" to the requirements.
"argon2" is installed as "argon2-cffi".
Attempting to install it as "argon2" will install some other library.
"""

setup(install_requires=['cryptography', 'argon2-cffi'])
