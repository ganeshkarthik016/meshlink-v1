"""One message = one small JSON object.
The same shape is used for chat, announcements and file announcements."""
import json
import uuid
from dataclasses import dataclass, field, asdict

from p2pchat import config

# kind
CHAT = "message"
ANNOUNCEMENT = "announcement"

# announce_type (only used when kind is ANNOUNCEMENT)
JOIN = "join"    # "I am here"
USER = "user"    # a highlighted note written by a user
FILE = "file"    # someone uploaded a file


def clean(text: str, limit: int) -> str:
    """Remove control characters (they can mess up the terminal) and cut to limit."""
    return "".join(c for c in text if c.isprintable())[:limit]


@dataclass
class Message:
    kind: str
    nick: str
    ip: str
    text: str = ""
    announce_type: str = ""
    extra: dict = field(default_factory=dict)   # file name, size, port, sha256...
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def __post_init__(self):
        self.nick = clean(self.nick, config.MAX_NICK)
        self.text = clean(self.text, config.MAX_TEXT)

    def to_bytes(self) -> bytes:
        return json.dumps(asdict(self)).encode()

    @classmethod
    def from_bytes(cls, data: bytes) -> "Message":
        """Rebuild a message. Raises ValueError if the data is not a valid message."""
        try:
            d = json.loads(data.decode())
            for name in ("id", "kind", "nick", "ip", "text", "announce_type"):
                if not isinstance(d[name], str):
                    raise ValueError(name)
            if not isinstance(d["extra"], dict):
                raise ValueError("extra")
            if d["kind"] not in (CHAT, ANNOUNCEMENT) or not 0 < len(d["id"]) <= 64:
                raise ValueError("kind or id")
            return cls(kind=d["kind"], nick=d["nick"], ip=d["ip"], text=d["text"],
                       announce_type=d["announce_type"], extra=d["extra"], id=d["id"])
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            raise ValueError("bad message") from e


def make_chat(nick: str, ip: str, text: str) -> Message:
    return Message(kind=CHAT, nick=nick, ip=ip, text=text)


def make_announcement(announce_type: str, nick: str, ip: str,
                      text: str = "", extra: dict | None = None) -> Message:
    return Message(kind=ANNOUNCEMENT, nick=nick, ip=ip, text=text,
                   announce_type=announce_type, extra=extra or {})