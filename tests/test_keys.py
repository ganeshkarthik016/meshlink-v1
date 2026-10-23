from p2pchat.keys import derive_keys


def test_same_input_same_output():
    assert derive_keys("lab", "password1") == derive_keys("lab", "password1")


def test_sizes():
    broadcast_id, key = derive_keys("lab", "password1")
    assert len(broadcast_id) == 8
    assert len(key) == 32


def test_one_character_changes_everything():
    a = derive_keys("lab", "password1")
    b = derive_keys("lab", "password2")
    assert a[0] != b[0]
    assert a[1] != b[1]


def test_room_id_matters():
    assert derive_keys("lab1", "password1") != derive_keys("lab2", "password1")