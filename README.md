# Meshlink

Meshlink is a terminal-based, password-protected peer-to-peer messaging and file-sharing project written in Python. It is designed to let devices on a local network discover one another, exchange encrypted chat messages, forward messages through connected peers, and share files without relying on a central chat server.

> Meshlink is an experimental project. Read the limitations and security notes before using it for anything sensitive.

## Features

- UDP-based peer discovery on the local network.
- Password-protected rooms.
- Encrypted chat messages.
- Multi-hop message forwarding through connected peers.
- Duplicate-message suppression.
- Peer listing and basic room commands.
- File announcements and peer-to-peer downloads.
- SHA-256 verification of downloaded files.
- Configurable network addresses, ports, and file directories.
- Terminal-only interface.

## How it works

Meshlink discovers peers on the local network and establishes TCP connections for communication. Messages can be forwarded through connected peers, allowing a message to travel beyond a node's direct connections.

```text
Node A  <---->  Node B  <---->  Node C
   \____________________________/
       Connections depend on the
       network and peer discovery
```

This diagram is illustrative. Meshlink does not guarantee that every pair of nodes will connect directly or that every node will discover every other node.

## Requirements

- Python 3.10 or newer.
- A local network that permits the required UDP discovery traffic and TCP connections.
- The project's Python dependencies.
- A terminal with ANSI escape-sequence support for the intended display behavior.

Only Linux has been tested. See [SETUP.md](SETUP.md) for installation, firewall configuration, and troubleshooting.

## Installation

Clone the repository:

```bash
git clone https://github.com/ganeshkarthik016/meshlink-v1.git
cd meshlink-v1
```

Create and activate a virtual environment.

**Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows PowerShell:**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Install Meshlink and its development dependencies:

```bash
python -m pip install -e ".[dev]"
```

For more detailed setup instructions, see [SETUP.md](SETUP.md).

## Start Meshlink

Start a node using your own nickname, room ID, and password:

```bash
meshlink --nick YOUR_NICKNAME --room YOUR_ROOM_ID
```

Enter the room password when prompted. The password must be at least eight characters long.

Every participant must use exactly the same room ID and password. The room ID is not a substitute for the password.

For example, two devices could use the same room ID and password while choosing different nicknames:

```bash
meshlink --nick GK --room LAB_CC
```

Use your actual nickname and room ID in place of the placeholders. Do not copy example IP addresses from documentation into your configuration.

## Command-line options

| Option        | Purpose                                                 |
| ------------- | ------------------------------------------------------- |
| `--nick`      | Nickname advertised by this node.                       |
| `--room`      | Room ID used for discovery and room membership.         |
| `--ip`        | Explicitly sets the IP address advertised by this node. |
| `--port`      | TCP port used for peer/chat connections.                |
| `--file-port` | TCP port used for file transfers.                       |
| `--shared`    | Directory containing files made available for sharing.  |
| `--downloads` | Directory where downloaded files are saved.             |

See [SETUP.md](SETUP.md) for examples, defaults, firewall rules, and instructions for choosing the correct LAN address.

## Default network ports

| Protocol |    Port | Purpose                      |
| -------- | ------: | ---------------------------- |
| UDP      | `50001` | Local-network peer discovery |
| TCP      | `50002` | Peer/chat connections        |
| TCP      | `50003` | File transfers               |

If you change the TCP ports, update your firewall rules accordingly. The discovery port is shared by nodes using the default configuration.

## Chat commands

The following commands are available from the Meshlink terminal interface:

| Command              | Purpose                                      |
| -------------------- | -------------------------------------------- |
| `/help`              | Display available commands.                  |
| `/peers`             | List known peers.                            |
| `/announce <text>`   | Send a text announcement.                    |
| `/upload <path>`     | Share a local file.                          |
| `/files`             | List known file announcements.               |
| `/download <number>` | Download a file using its local list number. |
| `/quit`              | Leave Meshlink.                              |

File-list numbers are local to each node. A number displayed on one device may refer to a different file on another device.

## File sharing

1. Use `/upload <path>` to share a file.
2. Meshlink copies the file into the configured shared directory and announces it to connected peers.
3. Other nodes can use `/files` to view known announcements.
4. Use `/download <number>` to download a file.
5. Meshlink verifies the completed download using SHA-256.

The file sender must remain online and reachable during the download. Downloads use a single source and do not support resuming an interrupted transfer.

## Security notes

Meshlink is an experimental project, not a security-audited messaging system.

- Chat messages are encrypted, but file transfers are not encrypted.
- The discovery identifier, which is derived from the room ID and password, is visible on the local network.
- A room password can be attacked offline if an attacker captures the relevant public discovery information. Use a strong, unique password.
- The design does not provide forward secrecy.
- Messages are not digitally signed, so nicknames and advertised IP addresses are not authenticated identities.
- Replay protection is limited; previously seen message IDs are retained in a bounded cache.
- File-transfer connections do not authenticate the sender or encrypt file contents.
- There is no comprehensive rate limiting against flooding or resource exhaustion.

Do not use Meshlink to transmit sensitive information or assume that a matching nickname proves someone's identity.

## Limitations

### Network discovery and connectivity

- Discovery requires UDP broadcast. Some Wi-Fi networks block broadcast traffic or isolate connected devices, preventing peer discovery.
- There is no manual-connect fallback when discovery fails.
- Discovery runs at startup. Disconnected groups do not automatically merge later, and lost peers are not necessarily replaced.
- Meshlink supports IPv4 only.
- Nodes using the default configuration share UDP discovery port `50001`.
- Each node advertises one IP address. If Meshlink chooses the wrong network interface, use `--ip` to specify the correct LAN address.
- The peer limit is eight. A node at its limit does not respond to new discovery requests.

### Platform and terminal support

- Only Linux has been tested. Windows and macOS have not been fully tested.
- Discovery uses a Linux-specific facility and skips that facility on other operating systems. On Windows, discovery may use only the default interface.
- Operating-system keepalive defaults may mean a dead connection takes a long time to be detected, potentially around two hours.
- Terminal rendering may behave differently across terminal emulators. Incoming messages can disrupt the line currently being typed, although the typed text remains.
- ANSI escape-sequence support is expected.
- Some filenames that are valid on Linux may contain characters that are invalid on Windows.
- Tests may fail on platforms that have not been tested.
- Windows Firewall may display a prompt when Meshlink starts networking.

### Connections and messaging

- There is no separate connection-authentication handshake. An untrusted device may consume one of the five incoming connection slots.
- An untrusted peer cannot read correctly encrypted chat messages without the appropriate room key. Invalid messages are dropped.
- The discovery identifier, which is derived from the room ID and password, is visible on the local network.
- Password-based key derivation with scrypt slows offline password guessing but cannot make a weak password strong.
- There is no forward secrecy.
- Messages are not digitally signed. Nicknames and advertised IP addresses can be spoofed.
- Replay protection is limited. The node remembers only the most recent 1,000 message IDs; an ID may be accepted again after it is evicted. Messages do not include a timestamp for replay-age validation.
- There is no comprehensive rate limiting. A peer can flood chat traffic or fill the 500-entry file register.

### File sharing

- File contents are transferred without encryption, and the file server does not authenticate download requests. Anyone who can reach the file-transfer service and knows the required address, port, and file name may be able to download a shared file.
- A file announcement can contain an incorrect IP address or port. SHA-256 verification detects content that does not match the expected hash, but it does not authenticate the person who announced the file.
- File announcements are not sent as history to newcomers. Re-uploading a file announces it again to currently connected peers.
- The file register is not persistent across restarts.
- File-list numbers are local to each node and can differ between devices.
- The uploader must remain online and reachable for the download to complete.
- Downloads use a single source and cannot resume after interruption.
- The full-file hash is checked after the transfer completes.
- Re-uploading a file replaces its previous register entry.
- Downloads may overwrite an existing destination file with the same name.
- Uploading copies the entire file into the shared directory. The maximum supported file size is 100 MB.

## Project status

Meshlink is a learning and experimentation project. Its networking, security, platform compatibility, and file-sharing behavior have practical limitations that should be understood before use.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
