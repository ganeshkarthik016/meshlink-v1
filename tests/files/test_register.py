import pytest

from p2pchat import config
from p2pchat.files.register import Register

HASH = "a" * 64


def add(reg, **changes):
    args = dict(name="a.pdf", nick="bob", ip="10.0.0.5", port=50003, size=100, sha256=HASH)
    args.update(changes)
    return reg.add(**args)


def test_numbers_start_at_one_and_count_up():
    reg = Register()
    assert add(reg, name="a.pdf").ssno == 1
    assert add(reg, name="b.pdf").ssno == 2


def test_same_uploader_same_name_replaces_and_keeps_number():
    reg = Register()
    add(reg, size=100)
    entry = add(reg, size=250)
    assert entry.ssno == 1
    assert len(reg.all()) == 1
    assert reg.get(1).size == 250


def test_different_uploader_same_name_is_a_separate_entry():
    reg = Register()
    add(reg, port=50003)
    add(reg, port=50005)
    assert len(reg.all()) == 2


@pytest.mark.parametrize("bad", [
    {"name": 5}, {"name": ".."}, {"name": ""},
    {"ip": "not an ip"}, {"ip": 5},
    {"port": 0}, {"port": 70000}, {"port": "x"}, {"port": True},
    {"size": 0}, {"size": -1}, {"size": 10**12}, {"size": "9"},
    {"sha256": "abc"}, {"sha256": "z" * 64}, {"sha256": 5},
])
def test_invalid_announcements_are_rejected(bad):
    reg = Register()
    assert add(reg, **bad) is None
    assert reg.all() == []


def test_name_is_made_safe():
    assert add(Register(), name="../../x.txt").name == "x.txt"


def test_full_register_refuses_new_files_but_allows_replacing(monkeypatch):
    monkeypatch.setattr(config, "MAX_REGISTER", 2)
    reg = Register()
    add(reg, name="a")
    add(reg, name="b")
    assert add(reg, name="c") is None
    assert add(reg, name="a", size=7).size == 7


def test_get_unknown_number():
    assert Register().get(5) is None