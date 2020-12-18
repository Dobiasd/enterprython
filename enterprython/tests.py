"""
enterprython - tests
"""

import configparser
import unittest
from abc import ABC, abstractmethod
from typing import NamedTuple, List

from ._inject import assemble, component, factory, value
from ._inject import set_values_from_config, add_values, set_values

__author__ = "Tobias Hermann"
__copyright__ = "Copyright 2018, Tobias Hermann"
__email__ = "editgym@gmail.com"
__license__ = "MIT"


# pylint: disable=too-few-public-methods

class ServiceInterface(ABC):
    """Defines interface of a service that can greet."""

    @abstractmethod
    def greet(self, name: str) -> str:
        """Shall return greeting message."""


@component()
class Service(ServiceInterface):
    """Example service"""

    def greet(self, name: str) -> str:
        """Returns greeting message."""
        return f'Hello, {name}!'


@component(singleton=False)
class ServiceNonSingleton:
    """Example service"""


class WithValue:
    """Example class using a configuration value"""

    def __init__(self) -> None:
        """Reads a value from the configuration."""
        self._value: int = value(int, 'WithValue', 'value')

    def show_value(self) -> str:
        """Returns string representation of value."""
        return str(self._value)


class Client:
    """Depends on Service"""

    def __init__(self, service: Service) -> None:
        """Use constructor injection."""
        self._service = service

    def greet_world(self) -> str:
        """Uses Service to greet the world."""
        return self._service.greet("World")


class ServiceFromFactory(NamedTuple):
    """Depends on nothing."""
    value: int = 42


@factory()
def service_factory() -> ServiceFromFactory:
    """Create a service."""
    return ServiceFromFactory(40)


class ClientServiceFromFactory(NamedTuple):
    """Depends on ServiceFromFactory."""
    service: ServiceFromFactory


class ServiceFromFactoryNonSingleton(NamedTuple):
    """Depends on nothing."""
    value: int = 42


@factory(singleton=False)
def service_factory_non_singleton() -> ServiceFromFactoryNonSingleton:
    """Create a service."""
    return ServiceFromFactoryNonSingleton()


class ClientServiceFromFactoryNonSingleton(NamedTuple):
    """Depends on ServiceFromFactoryNonSingleton."""
    service: ServiceFromFactoryNonSingleton


def client_func(service: Service) -> str:
    """Use function argument injection."""
    return service.greet("World")


class ClientNonSingleton:
    """Depends on ServiceNonSingleton."""

    def __init__(self, service: ServiceNonSingleton) -> None:
        self._service = service


class ClientWithoutTypeAnnotation:
    """Depends on some unknown thing."""

    def __init__(self, service) -> None:  # type: ignore
        self._service = service


@component()
class Layer3(NamedTuple):
    """Depends on nothing."""
    value: int = 42


@component()
class Layer2(NamedTuple):
    """Depends on Layer3"""
    service: Layer3


class Layer1(NamedTuple):
    """Depends on Layer2"""
    service: Layer2


@component()
class ServiceA(NamedTuple):
    """Depends on nothing."""
    value: str = "A"


@component()
class ServiceB(NamedTuple):
    """Depends on nothing."""
    value: str = "B"


class ServiceCNoComponent(NamedTuple):
    """Depends on nothing."""
    value: str = "C"


@component()
class ClientAB(NamedTuple):
    """Depends on ServiceA and ServiceB."""
    service_a: ServiceA
    service_b: ServiceB


@component()
class ClientABDefaultB(NamedTuple):
    """Depends on ServiceA and ServiceB."""
    service_a: ServiceA
    service_b: ServiceB = ServiceB('BDefault')


@component()
class ClientACDefaultC(NamedTuple):
    """Depends on ServiceA and ServiceB."""
    service_a: ServiceA
    service_c: ServiceCNoComponent = ServiceCNoComponent('CDefault')


class ClientKWArg:
    """Depends on Service"""

    def __init__(self, service: Service, name: str) -> None:
        """Use constructor injection."""
        self._service = service
        self._name = name

    def greet_world(self) -> str:
        """Uses Service to greet the world."""
        return self._service.greet(self._name)


class ClientDependingOnInterface:
    """Depends on Service"""

    def __init__(self, service: ServiceInterface) -> None:
        """Use constructor injection."""
        self._service = service

    def greet_world(self) -> str:
        """Uses Service to greet the world."""
        return self._service.greet("World")


class MultiServiceInterface(ABC):
    """Define interface for multiple services."""
    _value: str = "Interface"


@component()
class ServiceMultiA(MultiServiceInterface):
    """Example service A"""

    def __init__(self) -> None:
        """Depends on nothing."""
        self._value = "A"


@component()
class ServiceMultiB(MultiServiceInterface):
    """Example service B"""

    def __init__(self) -> None:
        """Depends on nothing."""
        self._value = "B"


class ClientDependingOnOneOfTwoServices:
    """Depends on ServiceMultiA or ServiceMultiB"""

    def __init__(self, service: MultiServiceInterface) -> None:
        """Use constructor injection."""
        self._service = service


class ClientDependingOnAllMultiServiceInterfaceImpls:
    """Depends on ServiceMultiA and ServiceMultiB"""

    def __init__(self, services: List[MultiServiceInterface]) -> None:
        """Use constructor injection."""
        self._services = services


class BasicTest(unittest.TestCase):
    """Check basic functionality."""

    def test_assemble(self) -> None:
        """Basic component lookup."""
        self.assertEqual("Hello, World!", assemble(Client).greet_world())

    def test_assemble_func(self) -> None:
        """Free function instead of constructor."""
        self.assertEqual("Hello, World!", assemble(client_func))

    def test_singleton(self) -> None:
        """Multiple calls to assemble shall return the same object."""
        self.assertTrue(assemble(Client)._service is assemble(Client)._service)  # pylint: disable=protected-access

    def test_non_singleton(self) -> None:
        """Multiple calls to assemble shall return the same object."""
        self.assertTrue(
            assemble(ClientNonSingleton)._service is not  # pylint: disable=protected-access
            assemble(ClientNonSingleton)._service)  # pylint: disable=protected-access

    def test_namedtuple(self) -> None:
        """Nested injection."""
        self.assertEqual(42, assemble(Layer2).service.value)

    def test_multiple_layers(self) -> None:
        """Nested injection."""
        self.assertEqual(42, assemble(Layer1).service.service.value)


class FactoryTest(unittest.TestCase):
    """Check factory functionality."""

    def test_construct_service(self) -> None:
        """Factory function creates service."""
        self.assertEqual(40, assemble(ServiceFromFactory).value)

    def test_factory(self) -> None:
        """Factory function produces dependency."""
        self.assertEqual(40, assemble(ClientServiceFromFactory).service.value)

    def test_factory_singleton(self) -> None:
        """Factory function as component."""
        self.assertTrue(assemble(ClientServiceFromFactory).service is
                        assemble(ClientServiceFromFactory).service)  # pylint: disable=protected-access

    def test_factory_non_singleton(self) -> None:
        """Factory function as component."""
        self.assertTrue(
            assemble(ClientServiceFromFactoryNonSingleton).service is not  # pylint: disable=protected-access
            assemble(ClientServiceFromFactoryNonSingleton).service)  # pylint: disable=protected-access


class ValueTest(unittest.TestCase):
    """Check value store."""

    def test_value(self) -> None:
        """Using value from configuration."""
        config = configparser.ConfigParser()
        config.read_string("""
            [WithValue]
            value = 42
        """)
        set_values_from_config(config)
        self.assertEqual('42', WithValue().show_value())

    def test_add_config_value(self) -> None:
        """Manually adding a value."""
        set_values({})
        add_values({'WithValue': {'value': 43}})
        self.assertEqual('43', WithValue().show_value())

    def test_try_replace_value(self) -> None:
        """Values must be unique."""
        set_values({})
        add_values({'WithValue': {'value': 43}})
        with self.assertRaises(ValueError):
            add_values({'WithValue': {'value': 43}})


class ErrorTest(unittest.TestCase):
    """Check exceptions."""

    def test_unknown_service_type(self) -> None:
        """A service parameter needs a type annotation."""
        with self.assertRaises(TypeError):
            assemble(ClientWithoutTypeAnnotation)

    def test_double_registration(self) -> None:
        """A class may only be registered once."""
        with self.assertRaises(TypeError):
            @component()  # pylint: disable=unused-variable
            @component()
            class Duplicate:  # pylint: disable=unused-variable
                """Class to be registered multiple times."""

    def test_ambiguous(self) -> None:
        """Ambiguous dependency."""
        with self.assertRaises(TypeError):
            assemble(ClientDependingOnOneOfTwoServices)

    def test_additional_factory(self) -> None:
        """Ambiguous dependency due to a factory."""
        with self.assertRaises(TypeError):
            @component()
            def service_factory_forbidden() -> Service:  # pylint: disable=unused-variable
                """Conflict with component."""
                return Service()


class AbstractTest(unittest.TestCase):
    """Check interfaces."""

    def test_interface(self) -> None:
        """Concrete object shall be injected."""
        self.assertEqual("Hello, World!",
                         assemble(ClientDependingOnInterface).greet_world())

    def test_multiple_services(self) -> None:
        """Multi-injection."""
        client = assemble(ClientAB)
        self.assertEqual('A', client.service_a.value)
        self.assertEqual('B', client.service_b.value)

    def test_manual_overwrite(self) -> None:
        """Prefer manually provided services."""
        client = assemble(ClientAB, service_b=ServiceB('BManual'))
        self.assertEqual('A', client.service_a.value)
        self.assertEqual('BManual', client.service_b.value)

    def test_default_arguments(self) -> None:
        """Use default arguments in clients if nothing else is given."""
        client = assemble(ClientACDefaultC)
        self.assertEqual('A', client.service_a.value)
        self.assertEqual('CDefault', client.service_c.value)

    def test_overwrite_default(self) -> None:
        """Prefer components over default arguments."""
        client = assemble(ClientABDefaultB)
        self.assertEqual('A', client.service_a.value)
        self.assertEqual('B', client.service_b.value)

    def test_service_list(self) -> None:
        """Inject multiple services as List."""
        client = assemble(ClientDependingOnAllMultiServiceInterfaceImpls)
        self.assertEqual(2, len(client._services))  # pylint: disable=protected-access
        self.assertEqual("A", client._services[0]._value)  # pylint: disable=protected-access
        self.assertEqual("B", client._services[1]._value)  # pylint: disable=protected-access


class ServiceInterfaceProfiles(ABC):
    """Defines interface of a service that can greet."""

    @abstractmethod
    def greet(self, name: str) -> str:
        """Shall return greeting message."""


@component(profiles=['prod'])
class ServiceProd(ServiceInterfaceProfiles):
    """Example service"""

    def greet(self, name: str) -> str:
        """Returns greeting message."""
        return f'prod: Hello, {name}!'


@component(profiles=['test', 'dev'])
class ServiceTest(ServiceInterfaceProfiles):  # pylint: disable=too-few-public-methods
    """Example service"""

    def greet(self, name: str) -> str:
        """Returns greeting message."""
        return f'testdev: Hello, {name}!'


class ClientDependingOnInterfaceProfile:
    """Depends on Service"""

    def __init__(self, service: ServiceInterfaceProfiles) -> None:
        """Use constructor injection."""
        self._service = service

    def greet_world(self) -> str:
        """Uses Service to greet the world."""
        return self._service.greet("World")


class ProfileTest(unittest.TestCase):
    """Check profiles."""

    def test_selected_profile_1(self) -> None:
        """Object is available."""
        self.assertEqual("prod: Hello, World!",
                         assemble(ClientDependingOnInterfaceProfile, 'prod').greet_world())

    def test_selected_profile_2(self) -> None:
        """Object is available."""
        self.assertEqual("testdev: Hello, World!",
                         assemble(ClientDependingOnInterfaceProfile, 'test').greet_world())

    def test_selected_profile_3(self) -> None:
        """Object is available."""
        self.assertEqual("testdev: Hello, World!",
                         assemble(ClientDependingOnInterfaceProfile, 'dev').greet_world())

    def test_no_profile_fail(self) -> None:
        """Object is not available."""
        with self.assertRaises(TypeError):
            assemble(ClientDependingOnInterfaceProfile, "unknown_profile")
