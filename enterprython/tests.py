"""
enterprython - tests
"""

import configparser
import unittest

from enterprython import assemble, component, configure, value

__author__ = "Tobias Hermann"
__copyright__ = "Copyright 2018, Tobias Hermann"
__email__ = "editgym@gmail.com"
__license__ = "MIT"


@component
class Service:  # pylint: disable=too-few-public-methods
    """Example service"""

    def __init__(self) -> None:
        """Reads a value from the configuration."""
        self._greeting: str = value(str, 'service', 'greeting')

    def greet(self, name: str) -> str:
        """Returns greeting message according to configuration."""
        return f"{self._greeting}, {name}!"


class Client:  # pylint: disable=too-few-public-methods
    """Depends on Service"""

    def __init__(self, service: Service) -> None:
        """Use constructor injection."""
        self._service = service

    def greet_world(self) -> str:
        """Uses Service to greet the world."""
        return self._service.greet("World")


class ClientKWArg:  # pylint: disable=too-few-public-methods
    """Depends on Service"""

    def __init__(self, service: Service, name: str) -> None:
        """Use constructor injection."""
        self._service = service
        self._name = name

    def greet_world(self) -> str:
        """Uses Service to greet the world."""
        return self._service.greet(self._name)


class FullTest(unittest.TestCase):
    """Check basic functionality."""

    def test_all(self) -> None:
        """Full functionality."""
        config = configparser.ConfigParser()
        config.read_string("""
            [service]
            greeting = Hello
        """)
        configure(config)
        self.assertEqual("Hello, World!",
                         assemble(ClientKWArg, name="World").greet_world())

    def test_uniqueness(self) -> None:
        """Multiple calls to assemble shall return the same object."""
        self.assertTrue(assemble(Client)._service is assemble(Client)._service)  # pylint: disable=protected-access

    def test_double_registration(self) -> None:
        """Multiple calls to assemble shall return the same object."""
        with self.assertRaises(TypeError):
            @component
            @component
            class Duplicate:  # pylint: disable=too-few-public-methods,unused-variable
                """Class to be registered multiple times."""
                pass
