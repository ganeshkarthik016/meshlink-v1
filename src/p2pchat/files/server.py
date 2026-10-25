"""Serves our shared files to anyone who asks. One short TCP connection per download.

The downloader sends the file name and a newline. We answer with 8 bytes
(the file size, or 0 if we do not have it), then the file, then close."""
import os
import socket
import threading

from p2pchat import config
from p2pchat.files.shared import SharedFolder


def _read_name(conn) -> str:
    """Read one line. Returns "" if it is missing, too long or not text."""
    data = b""
    while len(data) < 400:
        byte = conn.recv(1)
        if not byte:
            return ""
        if byte == b"\n":
            try:
                return data.decode()
            except UnicodeDecodeError:
                return ""
        data += byte
    return ""


class FileServer:
    def __init__(self, shared: SharedFolder):
        self.shared = shared
        self.port = None
        self._server = None
        self._slots = threading.BoundedSemaphore(config.MAX_SERVING)

    def start(self, port: int):
        """Use port 0 to let the system pick one (for tests)."""
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("", port))
        self._server.listen()
        self.port = self._server.getsockname()[1]
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while True:
            try:
                conn, _ = self._server.accept()
            except OSError:                      # server socket was closed
                break
            if self._slots.acquire(blocking=False):
                threading.Thread(target=self._serve, args=(conn,), daemon=True).start()
            else:
                conn.close()                     # too many downloads at the same time

    def _serve(self, conn):
        try:
            conn.settimeout(config.FILE_TIMEOUT)
            path = self.shared.path_of(_read_name(conn))
            if path is None:
                conn.sendall((0).to_bytes(8, "big"))
                return
            with open(path, "rb") as f:
                size = os.fstat(f.fileno()).st_size
                conn.sendall(size.to_bytes(8, "big"))
                while chunk := f.read(config.CHUNK_SIZE):
                    conn.sendall(chunk)
        except OSError:
            pass
        finally:
            conn.close()
            self._slots.release()

    def stop(self):
        if self._server is not None:
            try:
                self._server.shutdown(socket.SHUT_RDWR)      # wakes up accept()
            except OSError:
                pass
            self._server.close()