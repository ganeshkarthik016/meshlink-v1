"""The prompt loop: reads what the user types and runs commands."""
import threading

from p2pchat.comms import display

HELP = """Type a message and press Enter to chat. Commands:
  /announce <text>     send a highlighted announcement
  /upload <path>       share a file with everyone
  /files               list shared files
  /download <number>   download a file from the /files list
  /peers               show who you are connected to
  /help                show this help
  /quit                leave"""


def run(node):
    display.say(HELP)
    while True:
        try:
            line = display.read_line().strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        if line.startswith("/"):
            if not run_command(node, line):
                break
        else:
            show_own(node.chat(line))


def show_own(msg):
    """Messages we send never come back to us, so we show them ourselves."""
    if msg is not None:
        display.show(msg)


def run_command(node, line: str) -> bool:
    """Returns False when the user wants to quit."""
    command, _, rest = line.partition(" ")
    command, rest = command.lower(), rest.strip()
    if command == "/quit":
        return False
    if command == "/help":
        display.say(HELP)
    elif command == "/peers":
        ips = node.peers.ips()
        display.info(f"{len(ips)} peer(s): {', '.join(ips) or 'none'}")
    elif command == "/announce":
        if rest:
            show_own(node.announce(rest))
        else:
            display.info("Usage: /announce <text>")
    elif command == "/upload":
        upload(node, rest)
    elif command == "/files":
        list_files(node)
    elif command == "/download":
        start_download(node, rest)
    else:
        display.info("Unknown command. Type /help")
    return True


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("bytes", "KB", "MB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "bytes" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def upload(node, path: str):
    if not path:
        display.info("Usage: /upload <path to file>")
        return
    try:
        msg = node.upload(path)
    except (ValueError, OSError) as e:
        display.info(f"Upload failed: {e}")
        return
    display.show(msg)


def list_files(node):
    entries = node.register.all()
    if not entries:
        display.info("No files have been shared yet.")
        return
    for e in entries:
        display.say(f"  #{e.ssno}  {e.name}  ({human_size(e.size)})  from {e.nick} @ {e.ip}")


def start_download(node, text: str):
    try:
        ssno = int(text.lstrip("#"))
    except ValueError:
        display.info("Usage: /download <number from /files>")
        return
    # In the background, so you can keep chatting while it downloads.
    threading.Thread(target=run_download, args=(node, ssno), daemon=True).start()


def run_download(node, ssno: int):
    display.info(f"Downloading #{ssno}...")
    try:
        path = node.download(ssno)
    except ValueError as e:
        display.info(f"Download failed: {e}")
        return
    display.info(f"Saved to {path}")