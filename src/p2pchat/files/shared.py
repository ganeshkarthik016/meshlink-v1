"""The shared folder: copies of the files we uploaded, ready for others to download."""
import hashlib
import os
import shutil
from dataclasses import dataclass

from p2pchat import config


def safe_name(name: str) -> str:
    """Keep only the file-name part (no folders, no control characters).
    Returns "" if nothing usable is left. File names arrive from the network,
    so this runs on every one of them."""
    name = os.path.basename(name.replace("\\", "/"))
    name = "".join(c for c in name if c.isprintable()).strip()
    name = name[:config.MAX_NAME]
    return "" if name in ("", ".", "..") else name


def sha256_of(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(config.CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class SharedFile:
    name: str
    size: int
    sha256: str


class SharedFolder:
    def __init__(self, folder: str = config.SHARED_DIR):
        self.folder = folder

    def add(self, path: str) -> SharedFile:
        """Copy a file into the shared folder. A file with the same name is replaced.
        Raises ValueError with a readable message if the file cannot be shared."""
        path = os.path.expanduser(path.strip().strip("'\""))
        if not os.path.isfile(path):
            raise ValueError(f"not a file: {path}")
        name = safe_name(os.path.basename(path))
        if not name:
            raise ValueError("this file name cannot be shared")
        size = os.path.getsize(path)
        if size == 0:
            raise ValueError("the file is empty")
        if size > config.MAX_FILE_SIZE:
            raise ValueError(f"the file is bigger than {config.MAX_FILE_SIZE // (1024 * 1024)} MB")
        os.makedirs(self.folder, exist_ok=True)
        dest = os.path.join(self.folder, name)
        if os.path.abspath(path) != os.path.abspath(dest):     # already in the folder: nothing to copy
            shutil.copyfile(path, dest)
        return SharedFile(name, os.path.getsize(dest), sha256_of(dest))

    def path_of(self, name: str) -> str | None:
        """Where a shared file is on disk, or None. Only plain names are accepted,
        so a request like ../../etc/passwd can never leave the folder."""
        if not name or name != safe_name(name):
            return None
        path = os.path.join(self.folder, name)
        return path if os.path.isfile(path) else None