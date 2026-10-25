"""The prompt loop: reads what the user types and runs commands."""
from p2pchat.comms import display

HELP = """Type a message and press Enter to chat. Commands:
  /announce <text>   send a highlighted announcement
  /peers             show who you are connected to
  /help              show this help
  /quit              leave"""


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
    else:
        display.info("Unknown command. Type /help")
    return True