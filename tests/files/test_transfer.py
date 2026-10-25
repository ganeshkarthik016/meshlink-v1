import hashlib
import socket

import pytest

from p2pchat.files.downloader import download
from p2pchat.files.register import Entry
from p2pchat.files.server import FileServer
from p2pchat.files.shared import SharedFolder

DATA = bytes(range(256)) * 1000          # 256,000 bytes: several chunks


@pytest.fixture
def setup(tmp_path):
    shared = SharedFolder(str(tmp_path / "shared"))
    server = FileServer(shared)
    server.start(0)

    def share(name="a.bin", data=DATA, **changes):
        src = tmp_path / "src" / name
        src.parent.mkdir(exist_ok=True)
        src.write_bytes(data)
        info = shared.add(str(src))
        fields = dict(ssno=1, name=info.name, nick="bob", ip="127.0.0.1",
                      port=server.port, size=info.size, sha256=info.sha256)
        fields.update(changes)
        return Entry(**fields)

    yield share, server, tmp_path
    server.stop()


def test_download_works(setup):
    share, _, tmp_path = setup
    entry = share()
    path = download(entry, str(tmp_path / "dl"))
    assert open(path, "rb").read() == DATA
    assert not list((tmp_path / "dl").glob("*.part"))


def test_file_that_is_gone(setup):
    share, _, tmp_path = setup
    entry = share(name="nope.bin", data=b"x")
    (tmp_path / "shared" / "nope.bin").unlink()
    with pytest.raises(ValueError, match="no longer has"):
        download(entry, str(tmp_path / "dl"))


def test_changed_size_is_refused(setup):
    share, _, tmp_path = setup
    entry = share(size=DATA.__len__() + 1)
    with pytest.raises(ValueError, match="changed"):
        download(entry, str(tmp_path / "dl"))


def test_wrong_checksum_deletes_the_file(setup):
    share, _, tmp_path = setup
    entry = share(sha256="0" * 64)
    with pytest.raises(ValueError, match="damaged"):
        download(entry, str(tmp_path / "dl"))
    assert list((tmp_path / "dl").iterdir()) == []       # no .part, no final file


def test_nobody_listening(setup):
    share, server, tmp_path = setup
    entry = share()
    server.stop()
    with pytest.raises(ValueError, match="failed"):
        download(entry, str(tmp_path / "dl"))


def test_server_never_leaves_its_folder(setup):
    _, server, tmp_path = setup
    (tmp_path / "secret.txt").write_bytes(b"secret")
    with socket.create_connection(("127.0.0.1", server.port), timeout=2) as s:
        s.sendall(b"../secret.txt\n")
        assert s.recv(8) == bytes(8)                     # "I do not have it"


def test_server_survives_garbage(setup):
    share, server, tmp_path = setup
    for junk in (b"no newline", b"\xff\xfe\n", b"x" * 1000):
        with socket.create_connection(("127.0.0.1", server.port), timeout=2) as s:
            s.sendall(junk)
    entry = share()
    assert open(download(entry, str(tmp_path / "dl")), "rb").read() == DATA


def test_name_in_entry_cannot_escape_the_downloads_folder(setup):
    share, _, tmp_path = setup
    entry = share(name="evil.txt", data=b"data")
    entry.name = "../evil.txt"
    path = download(entry, str(tmp_path / "dl"))
    assert path == str(tmp_path / "dl" / "evil.txt")
    assert not (tmp_path / "evil.txt").exists()