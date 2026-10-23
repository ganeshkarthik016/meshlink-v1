"""Every number and setting lives here. Change it here, not in the code."""

# Ports
UDP_PORT = 50001    # discovery broadcast
TCP_PORT = 50002    # chat links
FILE_PORT = 50003   # file downloads

# Peer limits
MAX_OUT = 3                  # connections we start
MAX_IN = 5                   # connections we accept
MAX_PEERS = MAX_OUT + MAX_IN # 8 in total

# Discovery
DISCOVERY_WAIT = 2           # seconds to collect replies

# Chat
SEEN_LIMIT = 1000            # remember the last N message IDs
MAX_TEXT = 1024              # bytes
MAX_NICK = 32                # bytes

# Files
SHARED_DIR = "shared"        # uploads are copied here
DOWNLOAD_DIR = "downloads"
CHUNK_SIZE = 64 * 1024
MAX_FILE_SIZE = 100 * 1024 * 1024

# Room
MIN_PASSWORD = 8             # characters

MAX_FRAME = 16 * 1024        # biggest message we accept on a chat link (bytes)
CONNECT_TIMEOUT = 3          # seconds to wait when connecting to a peer