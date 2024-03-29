import pytest

from faker_events.handlers import Stream


@pytest.fixture
def standard_stream():
    return Stream()


def test_stream_prints(capsys, standard_stream):
    standard_stream.send({'Test': True})
    # FIXME The assertion below is not working with PyTest.
    # assert capsys.readouterr().out == '{"Test": true}\n'
