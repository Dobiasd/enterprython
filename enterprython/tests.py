"""
enterprython - tests
"""

import configparser
import unittest
from abc import ABC, abstractmethod
from typing import NamedTuple

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


@component(singleton=False)  # pylint: disable=too-few-public-methods
class ServiceNonSingleton:
    """Example service"""
    pass


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


class ClientNonSingleton:  # pylint: disable=too-few-public-methods
    """Depends on ServiceNonSingleton"""

    def __init__(self, service: ServiceNonSingleton) -> None:
        self._service = service


@component()  # pylint: disable=too-few-public-methods
class Layer3(NamedTuple):
    """Depends on nothing."""
    value: int = 42


@component()  # pylint: disable=too-few-public-methods
class Layer2(NamedTuple):
    """Depends on Layer3"""
    service: Layer3


class Layer1(NamedTuple):  # pylint: disable=too-few-public-methods
    """Depends on Layer2"""
    service: Layer2


@component()  # pylint: disable=too-few-public-methods
class ServiceA(NamedTuple):
    """Depends on nothing."""
    value: str = "A"


@component()  # pylint: disable=too-few-public-methods
class ServiceB(NamedTuple):
    """Depends on nothing."""
    value: str = "B"


@component()  # pylint: disable=too-few-public-methods
class ClientAB(NamedTuple):
    """Depends on ServiceA and ServiceB."""
    service_a: ServiceA
    service_b: ServiceB


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

    def test_singleton(self) -> None:
        """Multiple calls to assemble shall return the same object."""
        self.assertTrue(assemble(Client)._service is assemble(Client)._service)  # pylint: disable=protected-access

    def test_non_singleton(self) -> None:
        """Multiple calls to assemble shall return the same object."""
        self.assertTrue(
            assemble(ClientNonSingleton)._service is not  # pylint: disable=protected-access
            assemble(ClientNonSingleton)._service)  # pylint: disable=protected-access

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

    def test_namedtuple(self) -> None:
        """Nested injection."""
        self.assertEqual(42, assemble(Layer2).service.value)

    def test_multiple_layers(self) -> None:
        """Nested injection."""
        self.assertEqual(42, assemble(Layer1).service.service.value)

    def test_multiple_services(self) -> None:
        """Multi-injection."""
        client = assemble(ClientAB)
        self.assertEqual("A", client.service_a.value)
        self.assertEqual("B", client.service_b.value)
