"""Answers "is anyone here?" broadcasts from people in our room."""
import socket
import threading

from p2pchat.discovery import protocol


class Listener:
    def __init__(self, broadcast_id: bytes, node_id: bytes, tcp_port: int, can_reply, udp_port: int):
        """can_reply(): returns False when we are full, so we stay quiet."""
        self.broadcast_id = broadcast_id
        self.node_id = node_id
        self.tcp_port = tcp_port
        self.can_reply = can_reply
        self.udp_port = udp_port
        self._sock = None
        self._thread = None
        self._running = False

    def start(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   # nodes on one machine share the port
        self._sock.bind(("", self.udp_port))
        self._sock.settimeout(0.5)           # so the loop can notice stop()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while self._running:
            try:
                data, addr = self._sock.recvfrom(64)
            except socket.timeout:
                continue
            except OSError:
                break
            if self._should_reply(protocol.parse(data)):
                reply = protocol.build(protocol.REPLY, self.broadcast_id,
                                       self.node_id, self.tcp_port)
                try:
                    self._sock.sendto(reply, addr)       # straight back to whoever asked
                except OSError:
                    pass

    def _should_reply(self, packet) -> bool:
        """The business rules of discovery, all in one place."""
        return (packet is not None
                and packet.kind == protocol.REQUEST
                and packet.broadcast_id == self.broadcast_id     # same room
                and packet.node_id != self.node_id               # not our own broadcast
                and self.can_reply())                            # we have room for one more

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1)
        if self._sock is not None:
            self._sock.close()