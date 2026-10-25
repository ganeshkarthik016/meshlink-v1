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

KEEPALIVE_IDLE = 15          # seconds of silence before the first check
KEEPALIVE_INTERVAL = 10      # seconds between checks
KEEPALIVE_COUNT = 3          # missed checks before the peer is declared dead (15 + 3x10 = 45 s)

# Where discovery requests are sent. The second address lets nodes on the same machine find each other.
BROADCAST_ADDRESSES = ("255.255.255.255", "127.255.255.255")

MAX_NAME = 100               # longest file name we accept (characters)
MAX_REGISTER = 500           # most files we remember
MAX_SERVING = 8              # downloads we serve at the same time
FILE_TIMEOUT = 30            # seconds of silence before a file transfer is dropped