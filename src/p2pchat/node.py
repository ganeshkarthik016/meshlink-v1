"""Wires the pieces together. The only file that knows about all of them."""
import os
import socket

from p2pchat import config
from p2pchat.comms import display
from p2pchat.comms.forwarder import Forwarder
from p2pchat.comms.message import (
    JOIN, USER, Message, clean, make_announcement, make_chat,
)
from p2pchat.comms.peers import PeerTable
from p2pchat.discovery.broadcaster import find_peers
from p2pchat.discovery.listener import Listener
from p2pchat.keys import derive_keys


def find_my_ip() -> str:
    """Our address on the local network. Connecting a UDP socket sends nothing;
    it only makes the system choose which network card would be used."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


class Node:
    def __init__(self, nick: str, room_id: str, password: str, ip=None, deliver=None):
        self.nick = clean(nick, config.MAX_NICK) or "anon"
        self.ip = ip or find_my_ip()
        self.node_id = os.urandom(8)                 # new every run; lets us ignore our own broadcast
        self.broadcast_id, key = derive_keys(room_id, password)
        self.udp_port = config.UDP_PORT
        self.listener = None
        # The two objects need each other, so the lambda looks up self.forwarder
        # only when a message arrives, by which time it exists.
        self.peers = PeerTable(lambda data, link: self.forwarder.handle(data, link))
        self.forwarder = Forwarder(key, self.peers, deliver or display.show)

    def start(self, tcp_port: int, udp_port: int = config.UDP_PORT):
        """Start accepting connections and answering discovery requests."""
        self.udp_port = udp_port
        self.peers.listen(tcp_port)
        self.listener = Listener(self.broadcast_id, self.node_id, self.peers.port,
                                 self.peers.can_accept, udp_port)
        self.listener.start()

    def join(self, wait: float = config.DISCOVERY_WAIT) -> int:
        """Look for our room on the network and connect to the first few that answer.
        Returns how many peers we connected to."""
        found = find_peers(self.broadcast_id, self.node_id, self.udp_port, wait,
                           limit=config.MAX_OUT)
        connected = sum(1 for ip, port in found if self.peers.connect_to(ip, port))
        if connected:
            self.say_hello()
        return connected

    def connect(self, ip: str, port: int) -> bool:
        """Connect straight to one peer (used by tests)."""
        return self.peers.connect_to(ip, port)

    def chat(self, text: str) -> Message | None:
        """Send a chat message. Returns it so the caller can show it, or None if it was empty."""
        msg = make_chat(self.nick, self.ip, text)
        if not msg.text:
            return None
        self.forwarder.send(msg)
        return msg

    def announce(self, text: str) -> Message | None:
        msg = make_announcement(USER, self.nick, self.ip, text)
        if not msg.text:
            return None
        self.forwarder.send(msg)
        return msg

    def say_hello(self):
        """Tell everyone "I am here"."""
        self.forwarder.send(make_announcement(JOIN, self.nick, self.ip))

    def stop(self):
        if self.listener is not None:
            self.listener.stop()
        self.peers.close()