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
    parser.add_argument("--port", type=int, default=config.TCP_PORT, help="TCP port for chat links")
    parser.add_argument("--file-port", type=int, default=config.FILE_PORT, help="TCP port for file downloads")
    parser.add_argument("--shared", default=config.SHARED_DIR, help="folder for files you upload")
    parser.add_argument("--downloads", default=config.DOWNLOAD_DIR, help="folder for downloaded files")
    parser.add_argument("--ip", help="your IP on the network (only if the automatic one is wrong)")
    args = parser.parse_args()

    password = getpass.getpass("Room password: ")
    if len(password) < config.MIN_PASSWORD:
        sys.exit(f"Password must be at least {config.MIN_PASSWORD} characters.")

    node = Node(args.nick, args.room.strip(), password, ip=args.ip,
                shared_dir=args.shared, download_dir=args.downloads)
    node.start(args.port, file_port=args.file_port)
    display.info(f"Listening on {node.ip}:{node.peers.port} (files on port {node.file_server.port}). "
                 "Looking for peers...")

    connected = node.join()
    if connected:
        display.info(f"Connected to {connected} peer(s).")
    else:
        display.info("No peers found yet. Anyone who joins later will find you.")

    cli.run(node)
    node.stop()


if __name__ == "__main__":
    main()