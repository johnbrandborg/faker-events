from argparse import Namespace
from unittest.mock import Mock, patch
import pytest

import faker_events
from faker_events import __main__ as main


@pytest.fixture
def arguments():
    namespace = Namespace()
    namespace.num_profiles = 1
    namespace.profiles_file = None
    namespace.script = None
    namespace.update_profiles = False
    return namespace


def setup_function():
    faker_events.EventGenerator.start = Mock()
    faker_events.ProfileGenerator.save = Mock()


def test_cli_start(arguments):
    """
    Ensure the live stream is started
    """
    main.cli(arguments)
    faker_events.EventGenerator.start.assert_called_once()


def test_cli_load_script(arguments):
    """
    Load a python script if supplied
    """
    arguments.script = "application/myscript.py"

    with patch("importlib.import_module") as import_module:
        main.cli(arguments)

        import_module.assert_called_with("application.myscript")


def test_cli_fail_load_script(arguments):
    """
    If the supplied python script is not found, return 1 to exit.
    """
    arguments.script = "application/myscript.py"
    patch("importlib.import_module", Mock(side_effect=ModuleNotFoundError()))

    assert main.cli(arguments) == 1


def test_cli_update_profiles(capsys, arguments):
    """
    Check that the CLI will attempt to run save profiles on completion
    """
    arguments.profiles_file = 'profiles.json'
    arguments.update_profiles = True

    main.cli(arguments)

    faker_events.ProfileGenerator.save.assert_called_with('profiles.json')
