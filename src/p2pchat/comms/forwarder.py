"""What happens to every message that arrives:
decrypt -> seen before? -> forward to everyone except where it came from -> show."""
import threading
from collections import OrderedDict

from p2pchat import config
from p2pchat.comms.crypto import decrypt, encrypt
from p2pchat.comms.message import Message


class SeenSet:
    """Remembers the last `limit` message IDs. The oldest are forgotten first."""

    def __init__(self, limit: int):
        self._ids = OrderedDict()
        self._limit = limit
        self._lock = threading.Lock()

    def add(self, message_id: str) -> bool:
        """True if the ID is new, False if we have seen it. Checking and adding
        happen in one step, so two threads can never both think it is new."""
        with self._lock:
            if message_id in self._ids:
                return False
            self._ids[message_id] = None
            if len(self._ids) > self._limit:
                self._ids.popitem(last=False)      # forget the oldest
            return True


class Forwarder:
    def __init__(self, key: bytes, peers, deliver):
        """peers: anything with send_all(data, skip=None) (the PeerTable).
        deliver(message): called once for each new message, to show it."""
        self.key = key
        self.peers = peers
        self.deliver = deliver
        self.seen = SeenSet(config.SEEN_LIMIT)

    def handle(self, data: bytes, link):
        """Called for every frame that arrives from a peer."""
        try:
            message = Message.from_bytes(decrypt(self.key, data))
        except ValueError:
            return                      # wrong room, damaged or garbage: drop, never forward
        if not self.seen.add(message.id):
            return                      # we have seen this one: drop (this stops loops)
        self.peers.send_all(data, skip=link)    # forward the same encrypted bytes
        self.deliver(message)           # forward first, so a display problem cannot stop the mesh

    def send(self, message: Message):
        """Send a message we wrote ourselves."""
        self.seen.add(message.id)       # so when it comes back around, we ignore it
        self.peers.send_all(encrypt(self.key, message.to_bytes()))