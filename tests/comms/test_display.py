from p2pchat.comms import display
from p2pchat.comms.display import format_message
from p2pchat.comms.message import make_announcement, make_chat, JOIN, USER, FILE


def test_chat_line():
    assert format_message(make_chat("alice", "1.1.1.1", "hello")) == "alice: hello"


def test_color_adds_escape_codes():
    out = format_message(make_chat("alice", "1.1.1.1", "hello"), use_color=True)
    assert "\033[" in out and "hello" in out


def test_user_announcement_is_marked_even_without_color():
    out = format_message(make_announcement(USER, "alice", "1.1.1.1", "Lab at 5"))
    assert out == " [ANNOUNCEMENT] alice: Lab at 5 "


def test_announcement_is_highlighted_with_color():
    out = format_message(make_announcement(USER, "alice", "1.1.1.1", "Lab at 5"), use_color=True)
    assert out.startswith("\033[1;30;43m")


def test_join_line():
    out = format_message(make_announcement(JOIN, "bob", "10.0.0.7"))
    assert out == "* bob joined (10.0.0.7)"


def test_file_line():
    msg = make_announcement(FILE, "bob", "1.1.1.1", extra={"name": "a.pdf"})
    assert format_message(msg) == "* bob uploaded a.pdf"


def test_file_name_from_network_is_cleaned():
    msg = make_announcement(FILE, "bob", "1.1.1.1", extra={"name": "a\x1b[31m.pdf"})
    assert "\x1b" not in format_message(msg)


def test_unknown_announcement_type_still_shows():
    out = format_message(make_announcement("weird", "bob", "1.1.1.1", "hi"))
    assert "bob" in out and "hi" in out


def test_show_prints_one_line(capsys):
    display.show(make_chat("alice", "1.1.1.1", "hello"))
    assert capsys.readouterr().out == "alice: hello\n"


def test_info_prints_with_star(capsys):
    display.info("3 peers")
    assert capsys.readouterr().out == "* 3 peers\n"