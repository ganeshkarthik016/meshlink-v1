import pytest

from p2pchat.discovery import protocol


def test_round_trip():
    data = protocol.build(protocol.REQUEST, b"A" * 8, b"B" * 8, 50002)
    packet = protocol.parse(data)
    assert packet == protocol.Packet(protocol.REQUEST, b"A" * 8, b"B" * 8, 50002)


def test_packet_is_20_bytes():
    assert len(protocol.build(protocol.REPLY, b"A" * 8, b"B" * 8, 1)) == 20


@pytest.mark.parametrize("bad", [b"", b"junk", b"x" * 19, b"x" * 21])
def test_wrong_size_is_rejected(bad):
    assert protocol.parse(bad) is None


def test_wrong_version_or_kind_is_rejected():
    good = protocol.build(protocol.REQUEST, b"A" * 8, b"B" * 8, 1)
    assert protocol.parse(bytes([9]) + good[1:]) is None            # unknown version
    assert protocol.parse(good[:1] + bytes([7]) + good[2:]) is None  # unknown kind

def test_ids_must_be_8_bytes():
    with pytest.raises(ValueError):
        protocol.build(protocol.REQUEST, b"short", b"B" * 8, 1)
    with pytest.raises(ValueError):
        protocol.build(protocol.REQUEST, b"A" * 8, b"B" * 9, 1)