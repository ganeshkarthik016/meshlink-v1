from p2pchat.cli import human_size


def test_human_size():
    assert human_size(500) == "500 bytes"
    assert human_size(2048) == "2.0 KB"
    assert human_size(100 * 1024 * 1024) == "100.0 MB"