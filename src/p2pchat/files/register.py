"""The register: every file announced in the room, numbered by us."""
import ipaddress
import threading
from dataclasses import dataclass

from p2pchat import config
from p2pchat.files.shared import safe_name


@dataclass
class Entry:
    ssno: int         # serial number given by OUR code: the first file we hear about is #1
    name: str
    nick: str         # who uploaded it
    ip: str           # where to download it from
    port: int
    size: int
    sha256: str


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _is_ip(x) -> bool:
    if not isinstance(x, str):
        return False
    try:
        ipaddress.ip_address(x)
        return True
    except ValueError:
        return False


def _is_hash(x) -> bool:
    return isinstance(x, str) and len(x) == 64 and all(c in "0123456789abcdefABCDEF" for c in x)


class Register:
    def __init__(self):
        self._entries = {}              # (ip, port, name) -> Entry
        self._next_ssno = 1
        self._lock = threading.Lock()

    def add(self, name, nick, ip, port, size, sha256) -> Entry | None:
        """Add a file, or replace the same file from the same uploader (it keeps its number).
        Returns None if anything is invalid or the register is full.
        Everything here came from the network, so everything is checked."""
        name = safe_name(name) if isinstance(name, str) else ""
        if not name or not isinstance(nick, str) or not _is_ip(ip):
            return None
        if not _is_int(port) or not 0 < port < 65536:
            return None
        if not _is_int(size) or not 0 < size <= config.MAX_FILE_SIZE:
            return None
        if not _is_hash(sha256):
            return None
        key = (ip, port, name)
        with self._lock:
            old = self._entries.get(key)
            if old is None and len(self._entries) >= config.MAX_REGISTER:
                return None
            if old is None:
                ssno = self._next_ssno
                self._next_ssno += 1
            else:
                ssno = old.ssno
            entry = Entry(ssno, name, nick, ip, port, size, sha256.lower())
            self._entries[key] = entry
            return entry

    def get(self, ssno: int) -> Entry | None:
        with self._lock:
            return next((e for e in self._entries.values() if e.ssno == ssno), None)

    def all(self) -> list[Entry]:
        with self._lock:
            return sorted(self._entries.values(), key=lambda e: e.ssno)