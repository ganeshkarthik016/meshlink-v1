# Meshlink Setup Guide

This guide covers installation, configuration, firewall rules, testing, and troubleshooting for Meshlink.

## 1. Requirements

- Python 3.10 or newer.
- Two devices on the same local network for the simplest peer-to-peer test.
- A terminal that supports ANSI escape sequences.
- A network that allows the required UDP broadcast and TCP traffic.

Linux is the only platform tested so far. Windows and macOS instructions are provided where applicable, but behavior may differ.

## 2. Clone and install

Clone the repository:

```bash
git clone https://github.com/ganeshkarthik016/meshlink-v1.git
cd meshlink-v1
```

Create a virtual environment.

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

If the `meshlink` command is not found, confirm that the virtual environment is activated and rerun the installation command.

## 3. Start a node

Run:

```bash
meshlink --nick YOUR_NICKNAME --room YOUR_ROOM_ID
```

Replace `YOUR_NICKNAME` and `YOUR_ROOM_ID` with your chosen nickname and room ID. Enter the room password when prompted.

Every participant must use the **exact same room ID and password**. Nicknames should be different so participants can distinguish one another.

The password must be at least eight characters long.

## 4. Command-line options

| Option        | Purpose                                                 |
| ------------- | ------------------------------------------------------- |
| `--nick`      | Nickname advertised by this node.                       |
| `--room`      | Room ID used for discovery and room membership.         |
| `--ip`        | Explicitly sets the IP address advertised by this node. |
| `--port`      | TCP port used for peer/chat connections.                |
| `--file-port` | TCP port used for file transfers.                       |
| `--shared`    | Directory containing files made available for sharing.  |
| `--downloads` | Directory where downloaded files are saved.             |

For example, to configure custom ports and directories:

```bash
meshlink --nick YOUR_NICKNAME --room YOUR_ROOM_ID \
  --port 51002 --file-port 51003 \
  --shared ./shared --downloads ./downloads
```

### Choosing the advertised IP address

Meshlink advertises one IP address. If automatic address selection chooses the wrong interface, specify your device's LAN address with `--ip`.

On Linux, `hostname -I` can show your machine's assigned addresses. Choose the address belonging to the network your peers use. Do not use `127.0.0.1` for communication between different devices.

Example syntax, using a placeholder rather than a real device address:

```bash
meshlink --nick YOUR_NICKNAME --room YOUR_ROOM_ID --ip YOUR_LAN_IP
```

Replace `YOUR_LAN_IP` with your own LAN address. The address may change when you reconnect to a network or use a different interface.

## 5. Running multiple nodes on one computer

To run more than one Meshlink node on the same computer, give each instance:

- A unique nickname.
- A different TCP `--port`.
- A different `--file-port`.
- Separate shared and download directories to avoid mixing files.

Example:

```bash
meshlink --nick NODE_ONE --room YOUR_ROOM_ID \
  --port 51002 --file-port 51003 \
  --shared ./shared-one --downloads ./downloads-one
```

In a second terminal:

```bash
meshlink --nick NODE_TWO --room YOUR_ROOM_ID \
  --port 52002 --file-port 52003 \
  --shared ./shared-two --downloads ./downloads-two
```

Use the same room password in both instances. The default UDP discovery port is shared by local nodes, so you do not need to choose a different discovery port for each instance.

## 6. Firewall configuration

Meshlink uses these default ports:

| Protocol |    Port | Purpose                      |
| -------- | ------: | ---------------------------- |
| UDP      | `50001` | Local-network peer discovery |
| TCP      | `50002` | Peer/chat connections        |
| TCP      | `50003` | File transfers               |

Allow the required traffic on each device. If you use custom TCP ports, allow those ports instead of `50002` and `50003`.

### Linux with UFW

For the default ports:

```bash
sudo ufw allow 50001/udp
sudo ufw allow 50002/tcp
sudo ufw allow 50003/tcp
```

These rules permit the traffic at the firewall level. Your network may still block broadcast traffic or isolate devices.

### Windows

If Windows Firewall prompts you when Meshlink starts, review the prompt and allow network access on the appropriate network profile if you trust the network. If discovery or connections fail, check Windows Firewall rules for the UDP discovery port and both TCP ports.

## 7. Testing on two devices

1. Connect both devices to the same network. A phone hotspot is the simplest first test.
2. Allow the firewall ports on both devices (see section 6).
3. Start Meshlink on the first device. Check that the `Listening on` line shows its LAN address, not `127.0.0.1`.
4. Start Meshlink on the second device using the same room ID and password. It should print `Connected to 1 peer(s)`, and the first device should show that the second one joined.
5. Run `/peers` on both devices. Each should list the other device's IP address.
6. Send a message each way. Then upload a file on one device and download it on the other.
7. Compare the two file copies using SHA-256. On Linux, run:

   ```bash
   sha256sum path/to/original-file
   sha256sum path/to/downloaded-file
   ```

   The hash values should match.

If a step fails, use the troubleshooting section below. A successful local test does not guarantee that Meshlink will work on networks that block UDP broadcast or isolate clients.

## 8. Troubleshooting

### Peers do not discover each other

- Confirm that both devices are connected to the same local network.
- Confirm that both are using the same room ID **and password**.
- Check that UDP port `50001` is allowed by the firewall.
- Check whether the router or Wi-Fi network blocks UDP broadcast or isolates connected devices.
- Check that Meshlink is advertising the correct LAN address.
- Discovery runs at startup. Restarting a node may be necessary after changing the network or correcting its address.

### Messages are not appearing

- Check `/peers` on both devices.
- Confirm that both participants entered the same room ID and exact same password.
- Check the TCP peer port on each device and confirm that firewall rules allow the connection.
- Remember that a peer can connect while still being unable to decrypt messages if its password differs.

### File downloads fail

- Confirm that the uploader remains online and reachable.
- Check that the advertised file is still available.
- Confirm that the file-transfer TCP port is allowed by the firewall.
- Check that the download destination is writable and that sufficient disk space is available.
- A download does not resume after interruption. Start it again from the beginning.

### Password and room rules

- The password must be at least 8 characters.
- Everyone in a room must type exactly the same room ID and password. If the passwords differ, the nodes may connect but nobody sees any message (they cannot decrypt each other's messages, and no error is shown).

### `Address already in use` when starting

Another program, or another copy of Meshlink, is already using the TCP port. Start this copy with a different `--port` and `--file-port` (see "Running multiple nodes on one computer").

### The start-up line shows `Listening on 127.0.0.1`

Meshlink could not find your network address. Start it with `--ip` set to your LAN address (`hostname -I` on Linux).

## 9. Running tests

Activate your virtual environment and install the development dependencies if you have not already:

```bash
python -m pip install -e ".[dev]"
```

Run the test suite:

```bash
python -m pytest
```

Tests may behave differently on platforms that have not been tested. A passing test suite does not establish that every network configuration or security property has been verified.

## 10. Known limitations

- Only Linux has been tested. Windows and macOS remain unverified.
- Discovery relies on UDP broadcast and may fail on networks that block broadcasts or isolate devices.
- Discovery runs at startup; disconnected groups do not automatically merge later.
- Meshlink supports IPv4 and advertises one IP address per node.
- The peer limit is eight, and a node at capacity does not respond to new discovery requests.
- Connection authentication is limited. Untrusted peers may consume incoming connection slots.
- Password-based encryption does not provide forward secrecy or authenticated identities.
- Nicknames and advertised IP addresses can be spoofed, and replay protection is bounded.
- Chat traffic and the file register have no comprehensive rate limiting.
- File transfers are not encrypted and do not authenticate download requests.
- File announcements are not persisted or sent as history to newcomers.
- Downloads use one source, cannot resume, and are checked against a whole-file SHA-256 hash at completion.
- The maximum supported upload size is 100 MB.
- Terminal behavior and filename compatibility may differ across operating systems.

For the full limitations and security notes, see [README.md](README.md).

## 11. License

Meshlink is distributed under the MIT License. See [LICENSE](LICENSE).
