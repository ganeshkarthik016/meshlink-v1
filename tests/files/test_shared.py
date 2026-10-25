import hashlib

import pytest

from p2pchat import config
from p2pchat.files.shared import SharedFolder, safe_name


@pytest.mark.parametrize("raw, expected", [
    ("a.pdf", "a.pdf"),
    ("../../etc/passwd", "passwd"),
    ("/etc/passwd", "passwd"),
    ("C:\\docs\\file.txt", "file.txt"),
    ("..", ""),
    (".", ""),
    ("", ""),
    ("a\x1bb.txt", "ab.txt"),
])
def test_safe_name(raw, expected):
    assert safe_name(raw) == expected


def test_safe_name_is_cut_to_limit():
    assert len(safe_name("x" * 500)) == config.MAX_NAME


def test_add_copies_and_describes_the_file(tmp_path):
    src = tmp_path / "notes.txt"
    src.write_bytes(b"hello" * 1000)
    shared = SharedFolder(str(tmp_path / "shared"))
    info = shared.add(str(src))
    assert info.name == "notes.txt" and info.size == 5000
    assert info.sha256 == hashlib.sha256(b"hello" * 1000).hexdigest()
    assert (tmp_path / "shared" / "notes.txt").read_bytes() == b"hello" * 1000


def test_same_name_is_replaced(tmp_path):
    src = tmp_path / "notes.txt"
    shared = SharedFolder(str(tmp_path / "shared"))
    src.write_bytes(b"old")
    shared.add(str(src))
    src.write_bytes(b"newer")
    info = shared.add(str(src))
    assert info.size == 5
    assert (tmp_path / "shared" / "notes.txt").read_bytes() == b"newer"


def test_file_already_in_shared_folder(tmp_path):
    shared = SharedFolder(str(tmp_path / "shared"))
    (tmp_path / "shared").mkdir()
    (tmp_path / "shared" / "a.txt").write_bytes(b"data")
    assert shared.add(str(tmp_path / "shared" / "a.txt")).size == 4


def test_bad_files_are_rejected(tmp_path, monkeypatch):
    shared = SharedFolder(str(tmp_path / "shared"))
    with pytest.raises(ValueError):
        shared.add(str(tmp_path / "missing.txt"))
    with pytest.raises(ValueError):
        shared.add(str(tmp_path))                          # a folder, not a file
    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")
    with pytest.raises(ValueError):
        shared.add(str(empty))
    big = tmp_path / "big.txt"
    big.write_bytes(b"x" * 20)
    monkeypatch.setattr(config, "MAX_FILE_SIZE", 10)
    with pytest.raises(ValueError):
        shared.add(str(big))


def test_path_of_only_gives_plain_names(tmp_path):
    shared = SharedFolder(str(tmp_path / "shared"))
    (tmp_path / "shared").mkdir()
    (tmp_path / "shared" / "a.txt").write_bytes(b"data")
    (tmp_path / "secret.txt").write_bytes(b"secret")
    assert shared.path_of("a.txt") == str(tmp_path / "shared" / "a.txt")
    assert shared.path_of("missing.txt") is None
    assert shared.path_of("../secret.txt") is None
    assert shared.path_of("/etc/passwd") is None
    assert shared.path_of("") is None