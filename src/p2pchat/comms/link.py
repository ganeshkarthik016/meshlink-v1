"""One TCP connection to one peer. Sends and receives whole messages ("frames").

TCP is a stream of bytes with no message boundaries, so every message is sent as
4 bytes of length, then that many bytes of data. The receiver reads the length
first, then reads exactly that many bytes."""
import socket
import threading

from p2pchat import config


class Link:
    def __init__(self, sock: socket.socket, ip: str):
        self.sock = sock
        self.ip = ip
        self._send_lock = threading.Lock()   # several threads may send to the same peer
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)     # notice dead peers
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, config.KEEPALIVE_IDLE)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, config.KEEPALIVE_INTERVAL)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, config.KEEPALIVE_COUNT)
        except (OSError, AttributeError):    # these options are Linux-only; others skip them
            pass

    @classmethod
    def connect(cls, ip: str, port: int) -> "Link | None":
        """Open a connection to a peer. Returns None if it fails."""
        try:
            sock = socket.create_connection((ip, port), timeout=config.CONNECT_TIMEOUT)
            sock.settimeout(None)    # after connecting, wait as long as needed for data
        except OSError:
            return None
        return cls(sock, ip)

    def send(self, data: bytes) -> bool:
        """Send one message. Returns False if it could not be sent."""
        if len(data) > config.MAX_FRAME:
            return False
        try:
            with self._send_lock:    # so two messages never get mixed together
                self.sock.sendall(len(data).to_bytes(4, "big") + data)
            return True
        except OSError:
            self.close()
            return False

    def receive(self) -> bytes | None:
        """Wait for one whole message. Returns None if the connection is closed
        or broken. (An empty message is b"", so always check `is None`.)"""
        header = self._read_exact(4)
        if header is None:
            return None
        length = int.from_bytes(header, "big")
        if length > config.MAX_FRAME:    # check BEFORE reading, so nobody can make us
            self.close()                 # wait for or store a huge amount of data
            return None
        return self._read_exact(length)

    def _read_exact(self, n: int) -> bytes | None:
        """recv() may return less than asked, so keep reading until we have n bytes."""
        data = b""
        while len(data) < n:
            try:
                chunk = self.sock.recv(n - len(data))
            except OSError:
                return None
            if not chunk:                # empty means the other side closed
                return None
            data += chunk
        return data

    def close(self):
        """Safe to call more than once. shutdown() also wakes up a thread
        that is waiting inside receive()."""
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()