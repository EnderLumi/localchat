# lokale Dateien, Usernamen, Chatverlauf

import os
import platform
from pathlib import Path
import random
import tempfile
from typing import Any
from collections.abc import Callable

from package import Package, PackageFactory, UserNamePackageFieldType, ColorPackageFieldType
from utils import ConcurrentLazy

def _app_data_dir() -> str|None:
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

"""
Variable that can be used to acces the OS specific app data directory.
"""
app_data_dir = ConcurrentLazy(_app_data_dir)

def get_app_data_dir() -> str|None:
    """
    Returns the directory path to this operating
    systems equiavalent to %APPDATA% on Windows.
    Returns None in case this OS is not supported.
    (Supported operating systems: Windows, macOS, Android, Ubuntu, Linux in general (not all distros tested))
    """
    return app_data_dir.get()

def _storage_dir() -> str|None:
    p = app_data_dir.get()
    if p != None:
        p += "/jllc"
        os.makedirs(p,exist_ok=True)
    return p

"""
Variable that can be used to acces the OS specific storage directory.
This is where any save files of this app are stored.
"""
storage_dir = ConcurrentLazy(_storage_dir)

def get_storage_dir() -> str|None:
    """
    Returns the directory path to where
    any save data of this app should be
    saved.
    Returns None in case this OS is not supported.
    """
    return storage_dir.get()

OPTIONS_PACKAGE_FACTORY = PackageFactory(set([
    UserNamePackageFieldType("user.name"),
    ColorPackageFieldType("user.name.color",True),
    ]))

class StoredPackage: ...

class StoredPackage(Package):
    def __init__(self, factory, onChange : Callable[[StoredPackage],None]):
        super().__init__(factory)
        self._onChange = onChange

    def set_on_change(self, onChange : Callable[[StoredPackage],None]):
        self._onChange = onChange
    def get_on_change(self, onChange : Callable[[StoredPackage],None]):
        return self._onChange

    def __setitem__(self, key : str, value : Any):
        super().__setitem__(key,value)
        self._onChange(self)
    def __delitem__(self, key : str) -> None:
        super().__delitem__(key)
        self._onChange(self)

def _load_options() -> Package:
    """
    Loads the users options as a package.
    """
    options = StoredPackage(OPTIONS_PACKAGE_FACTORY, lambda x: None)
    if storage_dir.get() == None:
        print("""waring: storage operations are not supported for this operating system.
Any changes made will not be saved.""")
        return options
    options_file_name = storage_dir.get() + "/options.bin"
    if os.access(options_file_name,os.R_OK):
        try:

            with open(options_file_name,"rb") as options_file:
                options.deserialize(options_file)
        except (IOError, EOFError) as error:
            ignored = input(f"""An error occured while reading your options from '{options_file_name}'.
Press enter to reset your options.
Exit the application if you don't want your options to be resetted.
""")
            os.remove(options_file_name)
    elif (old_username := _load_user_name()) != None:
        options.set_on_change(_save_options)
        try:
            options["user.name"] = old_username
        except ValueError:
            ...
    options.set_on_change(_save_options)
    return options

def _save_options(options : Package):
    """
    Saves the users options as a package.
    """
    if storage_dir.get() == None: return
    options_file_name = storage_dir.get() + "/options.bin"
    file_temp = tempfile.NamedTemporaryFile(delete=False)
    filename_tmp = file_temp.name
    try:
        options.serialize(file_temp)
        file_temp.close()
        os.replace(filename_tmp,options_file_name)
    except:
        if not file_temp.closed:
            try: file_temp.close()
            except: ...
        if os.access(filename_tmp, os.F_OK):
            os.remove(filename_tmp)

def _get_user_name_filename() -> str|None:
    return storage_dir.get() + "/username.txt" if storage_dir.get() != None else None

def set_user_name(username : str):
    options["user.name"] = username

def get_user_name() -> str:
    return options["user.name"]

def _load_user_name() -> str|None:
    filename = _get_user_name_filename()
    if filename == None: return None
    if not os.access(filename, os.F_OK | os.R_OK): return None
    return str(Path(filename).read_bytes(),"utf-8")

options = _load_options()

if __name__ == "__main__":
    print("starting tests: localchat/core/storage")
    print(f"system: {platform.system()}")
    print(f"app data dir: {get_app_data_dir()}")
    print(f"storage dir: {storage_dir.get()}")
    print(f"user name: {options['user.name'] if 'user.name' in options else 'N/A'}")
    new_user_name = input("username:") #f"New User {random.randint(0,0xFFFF)}"
    print(f"attempting to set user name to: {new_user_name}")
    options["user.name"] = new_user_name
    print(f"updated user name: {options['user.name']}")
    print("finished tests: localchat/core/storage")
