"""Everything the user sees. This is the only file (with cli.py) that prints."""
import sys
import threading

from p2pchat import config
from p2pchat.comms.message import Message, CHAT, JOIN, USER, FILE, clean

PROMPT = "> "

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
CYAN = "\033[36m"
HIGHLIGHT = "\033[1;30;43m"      # bold black text on a yellow background

_lock = threading.Lock()         # so two threads never print at the same time
_waiting = False                 # True while the prompt is waiting for the user to type


def _paint(code: str, text: str, use_color: bool) -> str:
    return f"{code}{text}{RESET}" if use_color else text


def format_message(msg: Message, use_color: bool = False) -> str:
    """Turn a message into one line of text. Announcements are marked in words too,
    so they stand out even where colours don't work."""
    if msg.kind == CHAT:
        return f"{_paint(BOLD, msg.nick, use_color)}: {msg.text}"
    if msg.announce_type == USER:
        return _paint(HIGHLIGHT, f" [ANNOUNCEMENT] {msg.nick}: {msg.text} ", use_color)
    if msg.announce_type == JOIN:
        return _paint(GREEN, f"* {msg.nick} joined ({clean(msg.ip, 45)})", use_color)
    if msg.announce_type == FILE:
        name = clean(str(msg.extra.get("name", "?")), 100)   # comes from the network: clean it
        return _paint(CYAN, f"* {msg.nick} uploaded {name}", use_color)
    return f"* {msg.nick}: {msg.text}"       # unknown announcement types are still shown


def say(text: str):
    """Print one line. If the user is in the middle of typing, redraw the prompt after it."""
    with _lock:
        if sys.stdout.isatty():
            sys.stdout.write("\r\033[K" + text + "\n")     # wipe the half-typed line first
            if _waiting:
                sys.stdout.write(PROMPT)
        else:
            sys.stdout.write(text + "\n")
        sys.stdout.flush()


def show(msg: Message):
    say(format_message(msg, use_color=sys.stdout.isatty()))


def info(text: str):
    say(f"* {text}")


def read_line() -> str:
    """Show the prompt and wait for a line. Raises EOFError / KeyboardInterrupt."""
    global _waiting
    with _lock:
        _waiting = True
        sys.stdout.write(PROMPT)
        sys.stdout.flush()
    try:
        line = input()
    finally:
        with _lock:
            _waiting = False
    if sys.stdout.isatty():
        sys.stdout.write("\033[A\033[2K\r")     # remove the line the user typed; show() prints
        sys.stdout.flush()                      # the formatted version instead
    return line