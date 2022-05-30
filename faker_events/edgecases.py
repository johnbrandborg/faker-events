from copy import deepcopy
from random import choice, choices, randint


def remove_data(message: dict) -> None:
    """
    Passes the values and will randomly remove the value.
    """

    message[choice(tuple(message.keys()))] = None


def clear_data(message: dict) -> None:
    """
    Passes the values and will randomly clear the value.
    """

    selected_key = choice(tuple(message.keys()))
    value_type = type(message.get(selected_key))

    if value_type is float:
        message[selected_key] = 0.0

    if value_type is int:
        message[selected_key] = 0

    if value_type is str:
        message[selected_key] = ""


def change_type(message: dict) -> None:
    """
    Passes the values and will randomly change the data type.
    """

    selected_key = choice(tuple(message.keys()))
    value_type = type(message.get(selected_key))

    if value_type is float:
        new_type = choices([int, str])[0]
        message[selected_key] = new_type(message[selected_key])

    if value_type is int:
        new_type = choices([float, str])[0]
        message[selected_key] = new_type(message[selected_key])

    if value_type is bool:
        new_type = choices([float, int, str])[0]
        message[selected_key] = new_type(message[selected_key])

    if value_type is str:
        try:
            new_type = choices([float, int, str])[0]
            message[selected_key] = new_type(message[selected_key])
        except ValueError:
            pass


_duplication_cache = {}


def duplicate_data(message: dict) -> None:
    """
    Passes the values and will duplicate the key data from previous events.
    """
    global _duplication_cache

    if not _duplication_cache:
        _duplication_cache = deepcopy(message)

    selected_key = choice(tuple(message.keys()))
    message[selected_key] = _duplication_cache[selected_key]

    _duplication_cache = deepcopy(message)


class EdgeCase:
    """
    Creates edge cases where the data is modified in ways it shouldn't have
    been.
    """

    def __init__(self, cases: list, weights: list, probability=1):
        self.cases = cases
        self.weights = weights
        self.probability = probability

    def corrupt(self, message):
        if randint(0, 100) > (100 - self.probability):
            choices(self.cases, self.weights, k=1)[0](message)
