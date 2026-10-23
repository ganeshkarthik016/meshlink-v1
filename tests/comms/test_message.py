import pytest

from p2pchat.comms.message import (
    Message, make_chat, make_announcement, CHAT, ANNOUNCEMENT, FILE,
)


def test_round_trip():
    m = make_chat("alice", "192.168.1.5", "hello")
    back = Message.from_bytes(m.to_bytes())
    assert back == m


def test_ids_are_unique():
    ids = {make_chat("a", "1.1.1.1", "x").id for _ in range(1000)}
    assert len(ids) == 1000


def test_control_characters_removed():
    m = make_chat("al\x1bice", "1.1.1.1", "hi\n\x1b[31mred")
    assert m.nick == "alice"
    assert "\x1b" not in m.text and "\n" not in m.text


def test_text_is_cut_to_limit():
    m = make_chat("a", "1.1.1.1", "x" * 5000)
    assert len(m.text) == 1024


def test_file_announcement_keeps_extra():
    m = make_announcement(FILE, "bob", "1.1.1.1", extra={"name": "a.pdf", "port": 50003})
    back = Message.from_bytes(m.to_bytes())
    assert back.kind == ANNOUNCEMENT
    assert back.extra["name"] == "a.pdf"


@pytest.mark.parametrize("bad", [b"", b"not json", b"[1,2]", b'{"id": "x"}', b"\xff\xfe"])
def test_garbage_raises_value_error(bad):
    with pytest.raises(ValueError):
        Message.from_bytes(bad)


def test_wrong_kind_rejected():
    m = make_chat("a", "1.1.1.1", "x")
    data = m.to_bytes().replace(CHAT.encode(), b"hack")
    with pytest.raises(ValueError):
        Message.from_bytes(data)