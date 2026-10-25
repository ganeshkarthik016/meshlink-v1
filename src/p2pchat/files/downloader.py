"""Download one file from the person who uploaded it (a temporary TCP connection)."""
import hashlib
import os
import socket

from p2pchat import config
from p2pchat.files.register import Entry
from p2pchat.files.shared import safe_name


def download(entry: Entry, folder: str = config.DOWNLOAD_DIR) -> str:
    """Download the file into `folder` and return the path it was saved to.
    Raises ValueError with a readable message if anything goes wrong."""
    name = safe_name(entry.name)         # never trust a name, even one the register checked
    if not name:
        raise ValueError("bad file name")
    os.makedirs(folder, exist_ok=True)
    final = os.path.join(folder, name)   # an older download with the same name is replaced
    part = final + ".part"               # we only use the real name once the file is verified
    try:
        _fetch(entry, name, part)
        os.replace(part, final)
    except OSError as e:                 # connection refused, timeout, disk error...
        raise ValueError(f"download failed: {e}") from e
    finally:
        if os.path.exists(part):         # something went wrong: leave no half file behind
            os.remove(part)
    return final


def _fetch(entry: Entry, name: str, part: str):
    with socket.create_connection((entry.ip, entry.port), timeout=config.CONNECT_TIMEOUT) as sock:
        sock.settimeout(config.FILE_TIMEOUT)
        sock.sendall(name.encode() + b"\n")
        size = int.from_bytes(_read_exact(sock, 8), "big")
        if size == 0:
            raise ValueError("the uploader no longer has this file")
        if size != entry.size:
            raise ValueError("the file changed after it was announced")
        digest = hashlib.sha256()
        remaining = size
        with open(part, "wb") as out:
            while remaining > 0:
                chunk = sock.recv(min(config.CHUNK_SIZE, remaining))
                if not chunk:
                    raise ValueError("connection lost before the file was complete")
                out.write(chunk)
                digest.update(chunk)
                remaining -= len(chunk)
    if digest.hexdigest() != entry.sha256:
        raise ValueError("the file arrived damaged (checksum does not match)")


def _read_exact(sock, n: int) -> bytes:
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ValueError("connection lost")
        data += chunk
    return data