# lokale Dateien, Usernamen, Chatverlauf

import os
import platform
from pathlib import Path
import random
import tempfile

class _Unknown: ...

_GET_APP_DATA_DIR__PATH : str|None|_Unknown = _Unknown()

def _get_app_data_dir__init() -> str|None:
    if os.name == "nt": # Windows
        return os.getenv("APPDATA")
    if platform.system() == "Darwin": # MacOS
        return str(Path.home()) + "/Library/Application Support"
    if platform.system() == "Linux":
        if ("ANDROID_STORAGE" in os.environ): # Android
            return os.getenv("EXTERNAL_STORAGE")
        else: # Linux
            return str(Path.home()) + "/.local/share"
    return None

def get_app_data_dir() -> str|None:
    global _GET_APP_DATA_DIR__PATH
    if isinstance(_GET_APP_DATA_DIR__PATH, _Unknown):
        _GET_APP_DATA_DIR__PATH = _get_app_data_dir__init()
    return _GET_APP_DATA_DIR__PATH

_GET_STORAGE_DIR__PATH : str|None|_Unknown = _Unknown()

def get_storage_dir() -> str|None:
    global _GET_STORAGE_DIR__PATH
    if isinstance(_GET_STORAGE_DIR__PATH,_Unknown):
        r = get_app_data_dir()
        if r != None:
            r += "/jllc"
            os.makedirs(r,exist_ok=True)
        _GET_STORAGE_DIR__PATH = r
    assert(not isinstance(_GET_STORAGE_DIR__PATH,_Unknown))
    return _GET_STORAGE_DIR__PATH


_USER_NAME : str|None = None

def _get_user_name_filename() -> str|None:
    storage_dir = get_storage_dir()
    return storage_dir + "/username.txt" if storage_dir != None else None

def set_user_name(username : str):
    global _USER_NAME
    if username == _USER_NAME: return
    _USER_NAME = username
    filename_real = _get_user_name_filename()
    if filename_real == None: return
    file_temp = tempfile.NamedTemporaryFile(delete=False)
    filename_tmp = file_temp.name
    try:
        file_temp.write(username.encode("utf-8"))
        file_temp.close()
        os.replace(filename_tmp,filename_real)
    except:
        if os.access(filename_tmp, os.F_OK):
            os.remove(filename_tmp)

def get_user_name() -> str:
    username = _USER_NAME
    assert(username != None)
    return username

def _load_user_name() -> str|None:
    filename = _get_user_name_filename()
    if filename == None: return None
    if not os.access(filename, os.F_OK | os.R_OK): return None
    return str(Path(filename).read_bytes(),"utf-8")

_USER_NAME = _load_user_name()
if _USER_NAME is None:
    user_input = input("Choose your username: ").strip()
    if not user_input:
        set_user_name(f"New User {random.randint(0,0xFFFF)}")
    set_user_name(user_input)


if __name__ == "__main__":
    print("starting tests: localchat/core/storage")
    print(f"system: {platform.system()}")
    print(f"app data dir: {get_app_data_dir()}")
    print(f"storage dir: {get_storage_dir()}")
    print(f"user name: {get_user_name()}")
    new_user_name = f"New User {random.randint(0,0xFFFF)}"
    print(f"attempting to set user name to: {new_user_name}")
    set_user_name(new_user_name)
    print(f"updated user name: {get_user_name()}")
    print("finished tests: localchat/core/storage")
