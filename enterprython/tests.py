"""
enterprython - tests
"""

import configparser
import unittest
from abc import ABC, abstractmethod

from enterprython import assemble, component, configure, value

__author__ = "Tobias Hermann"
__copyright__ = "Copyright 2018, Tobias Hermann"
__email__ = "editgym@gmail.com"
__license__ = "MIT"


class ServiceInterface(ABC):  # pylint: disable=too-few-public-methods
    """Define interface of a service that can greet."""

    @abstractmethod
    def greet(self, name: str) -> str:
        """Shall return greeting message."""
        pass


@component()  # pylint: disable=too-few-public-methods
class Service(ServiceInterface):
    """Example service"""

    def greet(self, name: str) -> str:
        """Returns greeting message."""
        return f"Hello, {name}!"


class WithValue:  # pylint: disable=too-few-public-methods
    """Example class using a configuration value"""

    def __init__(self) -> None:
        """Reads a value from the configuration."""
        self._value: int = value(int, 'WithValue', 'value')

    def show_value(self) -> str:
        """Returns string representation of value."""
        return str(self._value)


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


class ClientDependingOnInterface:  # pylint: disable=too-few-public-methods
    """Depends on Service"""

    def __init__(self, service: ServiceInterface) -> None:
        """Use constructor injection."""
        self._service = service

    def greet_world(self) -> str:
        """Uses Service to greet the world."""
        return self._service.greet("World")


class FullTest(unittest.TestCase):
    """Check basic functionality."""

    def test_assemble(self) -> None:
        """Basic component lookup."""
        self.assertEqual("Hello, World!", assemble(Client).greet_world())

    def test_value(self) -> None:
        """Using value from configuration."""
        config = configparser.ConfigParser()
        config.read_string("""
            [WithValue]
            value = 42
        """)
        configure(config)
        self.assertEqual('42', assemble(WithValue).show_value())

    def test_uniqueness(self) -> None:
        """Multiple calls to assemble shall return the same object."""
        self.assertTrue(assemble(Client)._service is assemble(Client)._service)  # pylint: disable=protected-access

    def test_double_registration(self) -> None:
        """Multiple calls to assemble shall return the same object."""
        with self.assertRaises(TypeError):
            @component()
            @component()
            class Duplicate:  # pylint: disable=too-few-public-methods,unused-variable
                """Class to be registered multiple times."""
                pass

    def test_interface(self) -> None:
        """Concrete object shall be injected."""
        self.assertEqual("Hello, World!",
                         assemble(ClientDependingOnInterface).greet_world())
