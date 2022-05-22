from io import StringIO
from unittest.mock import patch

from faker_events.text_color import eprint, Palatte


def test_eprint_creates_messages_to_stderr(capsys):
    eprint("NOTICE: Testing")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "NOTICE: Testing\n"


def test_eprint_creates_colored_messages_to_stderr(capsys):
    eprint("NOTICE: Testing", Palatte.BLUE)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "\x1b[0;34mNOTICE: Testing\x1b[0m\n"
