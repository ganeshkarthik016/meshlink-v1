"""The peers we are connected to, and the threads that serve them."""
import socket
import threading

from p2pchat import config
from p2pchat.comms.link import Link


class PeerTable:
    def __init__(self, on_data):
        """on_data(data, link) is called for every message that arrives from a peer."""
        self.on_data = on_data
        self._peers = {}                 # Link -> True if they connected to us
        self._lock = threading.Lock()    # protects _peers; never held while using the network
        self._server = None
        self.port = None                 # the port we listen on (set by listen)

    # ---------- counting ----------

    def count(self) -> int:
        with self._lock:
            return len(self._peers)

    def has_ip(self, ip: str) -> bool:
        with self._lock:
            return any(link.ip == ip for link in self._peers)

    def can_accept(self) -> bool:
        """True if we still have room for someone connecting to us.
        (Discovery uses this: a full node does not answer broadcasts.)"""
        with self._lock:
            return self._has_room(incoming=True)

    def _has_room(self, incoming: bool) -> bool:
        """Call only while holding the lock."""
        total = len(self._peers)
        in_count = sum(self._peers.values())      # True counts as 1
        out_count = total - in_count
        if total >= config.MAX_PEERS:
            return False
        if incoming:
            return in_count < config.MAX_IN
        return out_count < config.MAX_OUT

    # ---------- adding and removing ----------

    def add(self, link: Link, incoming: bool) -> bool:
        """Start serving this link. Returns False if we are full (caller closes it)."""
        with self._lock:                  # check and insert in one step, so two threads
            if not self._has_room(incoming):   # can never both take the last slot
                return False
            self._peers[link] = incoming
        threading.Thread(target=self._listen, args=(link,), daemon=True).start()
        return True

    def remove(self, link: Link):
        with self._lock:
            self._peers.pop(link, None)
        link.close()

    def connect_to(self, ip: str, port: int) -> bool:
        """Connect to a peer we found. Returns True if it worked."""
        with self._lock:
            if not self._has_room(incoming=False):
                return False
        link = Link.connect(ip, port)
        if link is None:
            return False
        if not self.add(link, incoming=False):
            link.close()
            return False
        return True

    # ---------- sending ----------

    def send_all(self, data: bytes, skip: Link | None = None):
        """Send to every peer except `skip` (the one we got it from)."""
        with self._lock:
            links = [link for link in self._peers if link is not skip]
        for link in links:                # send outside the lock: a slow peer must not block others
            link.send(data)               # a failed send closes the link; its thread removes it

    # ---------- receiving ----------

    def _listen(self, link: Link):
        """One thread per peer: wait for messages until the connection ends."""
        try:
            while (data := link.receive()) is not None:
                self.on_data(data, link)
        finally:
            self.remove(link)

    def listen(self, port: int):
        """Start accepting connections. Use port 0 to let the system pick (for tests)."""
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("", port))
        self._server.listen()
        self.port = self._server.getsockname()[1]
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while True:
            try:
                conn, addr = self._server.accept()
            except OSError:               # the server socket was closed
                break
            link = Link(conn, addr[0])
            if not self.add(link, incoming=True):
                link.close()

    def close(self):
        """Stop listening and drop every peer."""
        if self._server is not None:
            try:
                self._server.shutdown(socket.SHUT_RDWR)   # wakes up accept()
            except OSError:
                pass
            self._server.close()
        with self._lock:
            links = list(self._peers)
        for link in links:
            self.remove(link)