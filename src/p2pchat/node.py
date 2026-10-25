"""Wires the pieces together. The only file that knows about all of them."""
import socket

from p2pchat import config
from p2pchat.comms import display
from p2pchat.comms.forwarder import Forwarder
from p2pchat.comms.message import (
    JOIN, USER, Message, clean, make_announcement, make_chat,
)
from p2pchat.comms.peers import PeerTable
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
        self.broadcast_id, key = derive_keys(room_id, password)   # broadcast_id: used by discovery later
        # The two objects need each other, so the lambda looks up self.forwarder
        # only when a message arrives, by which time it exists.
        self.peers = PeerTable(lambda data, link: self.forwarder.handle(data, link))
        self.forwarder = Forwarder(key, self.peers, deliver or display.show)

    def start(self, port: int):
        self.peers.listen(port)

    def connect(self, ip: str, port: int) -> bool:
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
        self.peers.close()