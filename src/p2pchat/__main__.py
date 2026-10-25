"""Start with:  python -m p2pchat --nick alice --room lab"""
import argparse
import getpass
import sys

from p2pchat import cli, config
from p2pchat.comms import display
from p2pchat.node import Node


def main():
    parser = argparse.ArgumentParser(prog="p2pchat")
    parser.add_argument("--nick", required=True)
    parser.add_argument("--room", required=True)
    parser.add_argument("--port", type=int, default=config.TCP_PORT, help="TCP port to listen on")
    parser.add_argument("--ip", help="your IP on the network (only if the automatic one is wrong)")
    parser.add_argument("--peer", help="TEMPORARY: ip:port of a peer; removed when discovery is done")
    args = parser.parse_args()

    password = getpass.getpass("Room password: ")
    if len(password) < config.MIN_PASSWORD:
        sys.exit(f"Password must be at least {config.MIN_PASSWORD} characters.")

    node = Node(args.nick, args.room.strip(), password, ip=args.ip)
    node.start(args.port)
    display.info(f"Listening on {node.ip}:{node.peers.port}")

    if args.peer:                                   # TEMPORARY, replaced by discovery
        ip, _, port = args.peer.partition(":")
        if node.connect(ip, int(port)):
            node.say_hello()
        else:
            display.info(f"Could not connect to {args.peer}")

    cli.run(node)
    node.stop()


if __name__ == "__main__":
    main()