from unittest.mock import patch

from faker_events import __main__ as main


@patch('faker_events.EventGenerator.live_stream')
def test_main(mocked_live_stream):
    """
    Ensure the live stream is started
    """
    main.main()
    mocked_live_stream.assert_called_once()
