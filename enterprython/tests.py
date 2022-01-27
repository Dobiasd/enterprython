"""
enterprython - tests
"""

import dataclasses as dc
import os
import sys
import unittest
from abc import ABC, abstractmethod
from typing import Any, NamedTuple, List
from unittest.mock import patch

import attrs

from ._inject import assemble, component, factory, load_config, setting, ValueType

print(f"Version info: {sys.version_info}")

__author__ = "Tobias Hermann"
__copyright__ = "Copyright 2018, Tobias Hermann"
__email__ = "editgym@gmail.com"
__license__ = "MIT"

_APP_NAME = "TEST"


def _load_config() -> None:
    load_config(_APP_NAME, ["test/config.toml"])


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


@component()
@attrs.define
class ServiceWithValues:
    """Service with values"""
    attrib1: int
    attrib2: str
    attrib3: bool

    def greet(self, name: str) -> str:
        """Returns greeting message with values"""
        return f'Hello, {name}!{self.attrib1},{self.attrib2},{self.attrib3}'


@component()
@attrs.define
class ServiceWithValuesPrecedence:
    """Service with values"""
    precedence_attrib1: int
    precedence_attrib2: int

    def get_value_attrib1(self) -> int:
        """Returns attribute1 value"""
        return self.precedence_attrib1

    def get_value_attrib2(self) -> int:
        """Returns attribute2 value"""
        return self.precedence_attrib2


@component()
@attrs.define
class ServiceWithValuesAndSettingDecorator:
    """Class with values demoing setting decorator"""
    attrib3: bool
    # inject below attributes from given config keys:
    attrib1: int = setting("COMMON_ATTRIB1")  # type: ignore
    attrib2: str = setting("COMMON_ATTRIB2")  # type: ignore

    def greet(self, name: str) -> str:
        """Returns greeting message with values"""
        return f'Hello, {name}!{self.attrib1},{self.attrib2},{self.attrib3}'


class BaseServicePreventValueInjection(ABC):
    """Base service to test preventing value injection"""

    @abstractmethod
    def get_value(self) -> ValueType:
        """return non injectable value"""


@component(profiles=["attrs"])
@attrs.define
class ServiceWithValuesPreventAttributeInjection(BaseServicePreventValueInjection):
    """Class with values showing how to prevent injection"""
    # to prevent the attribute value injection using attrs or dataclass field decorator:
    # 1. use init=False to exclude it from the generated __init__ method
    # 2. set the default value
    attrib3: bool = attrs.field(init=False, default=True)

    def get_value(self) -> ValueType:
        return self.attrib3


@component(profiles=["dataclass"])
@dc.dataclass
class ServiceWithValuesPreventAttributeInjectionDc(BaseServicePreventValueInjection):
    """Class with values, showing how to prevent injection"""
    attrib3: bool = dc.field(init=False, default=True)

    def get_value(self) -> ValueType:
        return self.attrib3


@component()
@dc.dataclass
class ServiceWithValuesAndSettingDecoratorDc:
    """Class with values demoing setting decorator"""
    attrib3: bool
    # inject below attributes from given config keys:
    attrib1: int = setting("COMMON_ATTRIB1")  # type: ignore
    attrib2: str = setting("COMMON_ATTRIB2")  # type: ignore

    def greet(self, name: str) -> str:
        """Returns greeting message with values"""
        return f'Hello, {name}!{self.attrib1},{self.attrib2},{self.attrib3}'


class Client:
    """Depends on Service"""

    def __init__(self, service: Service) -> None:
        """Use constructor injection."""
        self._service = service

    def greet_world(self) -> str:
        """Uses Service to greet the world."""
        return self._service.greet("World")


@attrs.define
class ClientWithValueInjection:
    """Value injection"""
    service: ServiceWithValues

    def greet_world(self) -> str:
        """Returns greeting message with values"""
        return self.service.greet("World")


@attrs.define
class ClientWithValuePrecedence:
    """Value injection and precedence"""
    service: ServiceWithValuesPrecedence

    def get_value_attrib1(self) -> ValueType:
        """Returns attribute1 value"""
        return self.service.get_value_attrib1()

    def get_value_attrib2(self) -> ValueType:
        """Returns attribute2 value"""
        return self.service.get_value_attrib2()


@attrs.define
class ClientWithValueInjectionSettingDecorator:
    """Value injection with setting decorator"""
    service: ServiceWithValuesAndSettingDecorator

    def greet_world(self) -> str:
        """Returns greeting message with values."""
        return self.service.greet("World")


@attrs.define
class ClientWithValuesPreventInjection:
    """Client preventing value injection"""
    service: BaseServicePreventValueInjection

    def get_value(self) -> ValueType:
        """Returns value."""
        return self.service.get_value()


@dc.dataclass
class ClientWithValueInjectionSettingDecoratorDc:
    """Client with value injection and setting decorator"""
    service: ServiceWithValuesAndSettingDecoratorDc

    def greet_world(self) -> str:
        """Returns greeting message with values."""
        return self.service.greet("World")


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


class ValueInjectionTests(unittest.TestCase):
    """Tests value injection"""

    @classmethod
    def setUpClass(cls) -> None:
        _load_config()

    def test_inject_basic(self) -> None:
        """Tests value injection"""
        msg = assemble(ClientWithValueInjection).greet_world()
        self.assertEqual("Hello, World!10,test WOW,False", msg)

    def test_inject_setting_decorator(self) -> None:
        """Tests value injection using setting decorator"""
        msg = assemble(ClientWithValueInjectionSettingDecorator).greet_world()
        self.assertEqual("Hello, World!55,test common,False", msg)

    def test_inject_setting_decorator_dataclass(self) -> None:
        """Tests value injection using setting decorator and dataclass"""
        msg = assemble(ClientWithValueInjectionSettingDecoratorDc).greet_world()
        self.assertEqual("Hello, World!55,test common,False", msg)

    def test_inject_prevent_attribute_injection_attrs(self) -> None:
        """Tests value injection prevention using attrs"""
        val = assemble(ClientWithValuesPreventInjection, profile="attrs").get_value()
        self.assertEqual(val, True)

    def test_inject_prevent_attribute_injection_dataclass(self) -> None:
        """Tests value injection prevention using dataclass"""
        val = assemble(ClientWithValuesPreventInjection, profile="dataclass").get_value()
        self.assertEqual(val, True)


class ValueInjectionPrecedenceTest(unittest.TestCase):
    """Test value injection precedence"""
    env_patcher: Any
    arg_patcher: Any

    @classmethod
    def setUpClass(cls) -> None:
        """patches environment variables and command line args before testing precedence"""
        cls.env_patcher = patch.dict(os.environ, {
            f"{_APP_NAME}_SERVICE_PRECEDENCE_ATTRIB1": "11",
            f"{_APP_NAME}_SERVICE_PRECEDENCE_ATTRIB2": "12"})
        cls.arg_patcher = patch.object(sys, "argv", ["--service_precedence_attrib2=13"])
        cls.env_patcher.start()
        cls.arg_patcher.start()

        _load_config()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        cls.env_patcher.stop()
        cls.arg_patcher.stop()

    def test_inject_env_arg_precedence(self) -> None:
        """Tests value injection with precedence from environment vars and command args"""
        client = assemble(ClientWithValuePrecedence)
        val_attrib1 = client.get_value_attrib1()
        val_attrib2 = client.get_value_attrib2()
        # attrib1 is overwritten from env vars:
        self.assertEqual(val_attrib1, 11)
        # attrib2 is overwritten from args:
        self.assertEqual(val_attrib2, 13)
