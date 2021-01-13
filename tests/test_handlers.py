import pytest

from faker_events.handlers import Stream


@pytest.fixture
def standard_stream():
    return Stream()


def test_stream_prints(capsys, standard_stream):
    standard_stream.send('Hello World')
    assert capsys.readouterr().out == 'Hello World\n'
