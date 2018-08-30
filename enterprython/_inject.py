"""
enterprython - Type-based dependency-injection
"""

import configparser
import inspect
import sys
from typing import Any, Callable, Dict, Optional, Type, TypeVar, List, Generic, Union, Tuple

VER_3_7_AND_UP = sys.version_info[:3] >= (3, 7, 0)  # PEP 560

# pylint: disable=no-name-in-module
if VER_3_7_AND_UP:
    from typing import _GenericAlias  # type: ignore
else:
    pass
# pylint: enable=no-name-in-module

TypeT = TypeVar('TypeT')


class _Component(Generic[TypeT]):  # pylint: disable=unsubscriptable-object
    """Internal class to store components for DI."""

    def __init__(self, the_type: Callable[..., TypeT],
                 target_types: Tuple[Type[Any], ...],
                 singleton: bool) -> None:
        """Figure out and store base classes."""
        self._type = the_type
        self._is_singleton = singleton
        self._target_types = target_types
        self._instance: Optional[TypeT] = None

    def matches(self, the_type: Callable[..., TypeT]) -> bool:
        """Check if component can be used for injection of the_type."""
        return the_type in self._target_types

    def set_instance_if_singleton(self, instance: TypeT) -> None:
        """If this component is a singleton, set its instance."""
        if self._is_singleton:
            assert self._instance is None
            self._instance = instance

    def get_instance(self) -> Optional[TypeT]:
        """Access singleton instance if present."""
        assert self._is_singleton or self._instance is None
        return self._instance

    def get_type(self) -> Callable[..., TypeT]:
        """Underlying target type of component."""
        return self._type


class _Factory(Generic[TypeT]):  # pylint: disable=unsubscriptable-object
    """Internal class to store factories for DI."""

    def __init__(self, func: Callable[..., TypeT],
                 singleton: bool) -> None:
        """Figure out and store base classes."""
        return_type = inspect.signature(func).return_annotation
        if return_type is inspect.Signature.empty:
            raise TypeError(f'Unknown return type of {func.__name__}')
        self._func = func
        self._is_singleton = singleton
        self._return_type: Type[Any] = return_type
        self._target_types: Tuple[Type[Any], ...] = inspect.getmro(return_type)
        self._instance: Optional[TypeT] = None

    def matches(self, the_type: Callable[..., TypeT]) -> bool:
        """Check if factory can be used for injection of the_type."""
        return the_type in self._target_types

    def get_instance(self) -> Optional[TypeT]:
        """Access singleton instance if present."""
        if not self._is_singleton or self._instance is None:
            self._instance = self._func()
        return self._instance

    def get_return_type(self) -> Type[Any]:
        """Type of constructed object."""
        return self._return_type


ValueType = Union[str, float, int, bool]

ENTERPRYTHON_VALUES: Dict[str, Dict[str, ValueType]] = {}
ENTERPRYTHON_COMPONENTS: List[_Component] = []
ENTERPRYTHON_FACTORIES: List[_Factory] = []


def add_values(new_values: Dict[str, Dict[str, ValueType]]) -> None:
    """Extent current value store (section, name, value)."""
    global ENTERPRYTHON_VALUES  # pylint: disable=global-statement
    for section, names_with_values in new_values.items():
        if section in ENTERPRYTHON_VALUES:
            for name, new_value in names_with_values.items():
                if name in ENTERPRYTHON_VALUES[section]:
                    raise ValueError(f'Duplicate value: {section}.{name}')
    for section, names_with_values in new_values.items():
        for name, new_value in names_with_values.items():
            if section not in ENTERPRYTHON_VALUES:
                ENTERPRYTHON_VALUES[section] = {}
            ENTERPRYTHON_VALUES[section][name] = new_value


def add_value(section: str, name: str, new_value: ValueType) -> None:
    """Add a single new value to the store."""
    add_values({section: {name: new_value}})


def set_values(values: Dict[str, Dict[str, ValueType]]) -> None:
    """Set global enterprython value store (section, name, value)."""
    global ENTERPRYTHON_VALUES  # pylint: disable=global-statement
    ENTERPRYTHON_VALUES = {}
    add_values(values)


def set_values_from_config(config: configparser.ConfigParser) -> None:
    """Set global enterprython value store from a ConfigParser."""
    set_values({s: dict(config.items(s)) for s in config.sections()})


def _create(the_type: Callable[..., TypeT]) -> Optional[TypeT]:
    stored_factory = _get_factory(the_type)
    if stored_factory:
        return stored_factory.get_instance()

    stored_component = _get_component(the_type)
    if stored_component:
        instance = stored_component.get_instance()
        if instance is not None:
            return instance  # type: ignore
    return None


def assemble(the_type: Callable[..., TypeT], **kwargs: Any) -> TypeT:
    """Create an instance of a certain type,
    using constructor injection if needed."""

    global ENTERPRYTHON_COMPONENTS  # pylint: disable=global-statement

    ready_result = _create(the_type)
    if ready_result is not None:
        return ready_result

    signature = inspect.signature(the_type)

    parameters: Dict[str, Type[Any]] = {}
    for param in signature.parameters.values():
        if param.name == 'self':
            continue
        if param.kind != inspect.Parameter.POSITIONAL_OR_KEYWORD:
            raise TypeError('Only parameters of kind POSITIONAL_OR_KEYWORD '
                            'supported in target functions.')
        if param.annotation is inspect.Signature.empty:
            raise TypeError('Parameter needs needs a type annotation.')
        parameters[param.name] = param.annotation

    arguments: Dict[str, Any] = kwargs
    uses_manual_args = False
    for parameter_name, parameter_type in parameters.items():
        if parameter_name in arguments:
            uses_manual_args = True
            continue
        if _is_list_type(parameter_type):
            parameter_components = _get_components(_get_list_type_elem_type(parameter_type))
            arguments[parameter_name] = list(map(assemble,
                                                 map(lambda comp: comp.get_type(),
                                                     parameter_components)))
        else:
            parameter_component = _get_component(parameter_type)
            param_factory = _get_factory(parameter_type)
            if parameter_component is not None:
                arguments[parameter_name] = assemble(
                    parameter_component.get_type())  # parameter_type?
            elif param_factory:
                arguments[parameter_name] = param_factory.get_instance()
    result = the_type(**arguments)
    stored_component = _get_component(the_type)
    if stored_component and not uses_manual_args:
        stored_component.set_instance_if_singleton(result)
    return result


def value(the_type: Callable[..., TypeT], config_section: str, value_name: str) -> TypeT:
    """Get a config value from the global enterprython config store."""
    assert the_type in [bool, float, int, str]
    return the_type(ENTERPRYTHON_VALUES[config_section][value_name])


def component(singleton: bool = True) -> Callable[[Callable[..., TypeT]],
                                                  Callable[..., TypeT]]:
    """Annotation to register a class to be available for DI."""

    def register(the_class: Callable[..., TypeT]) -> Callable[..., TypeT]:
        """Register component and forward type."""
        if not inspect.isclass(the_class):
            raise TypeError('Only classes can be registered as components.')
        if inspect.isabstract(the_class):
            raise TypeError(f'Can not register abstract class as component.')
        global ENTERPRYTHON_COMPONENTS  # pylint: disable=global-statement
        target_types = inspect.getmro(the_class)  # type: ignore
        _add_component(the_class, target_types, singleton)
        return the_class

    return register


def factory(singleton: bool = True) -> Callable[[Callable[..., TypeT]],
                                                Callable[..., TypeT]]:
    """Annotation to register a factory to be available for DI."""

    def register(func: Callable[..., TypeT]) -> Callable[..., TypeT]:
        """Register component and forward type."""
        if not inspect.isfunction(func):
            raise TypeError('Only functions can be registered as factories.')
        global ENTERPRYTHON_COMPONENTS  # pylint: disable=global-statement
        _add_factory(func, singleton)
        return func

    return register


def _get_components(the_type: Callable[..., TypeT]) -> List[_Component]:
    """Return stored component for type if available."""
    return [stored_component
            for stored_component in ENTERPRYTHON_COMPONENTS
            if stored_component.matches(the_type)]


def _get_component(the_type: Callable[..., TypeT]) -> Optional[_Component]:
    """Return stored component for type if available."""
    components = _get_components(the_type)
    if len(components) > 1:
        raise TypeError(f'Ambiguous dependency {the_type.__name__}.')
    if not components:
        return None
    return components[0]


def _get_factories(the_type: Callable[..., TypeT]) -> List[_Factory]:
    """Return stored factories for type if available."""
    return [stored_factory
            for stored_factory in ENTERPRYTHON_FACTORIES
            if stored_factory.matches(the_type)]


def _get_factory(the_type: Callable[..., TypeT]) -> Optional[_Factory]:
    """Return stored factory for type if available."""
    factories = _get_factories(the_type)
    if len(factories) > 1:
        raise TypeError(f'Multiple factories available for {the_type.__name__}.')
    if not factories:
        return None
    return factories[0]


def _add_component(the_type: Callable[..., TypeT],
                   target_types: Tuple[Type[Any], ...],
                   singleton: bool) -> None:
    """Store new component for DI."""
    global ENTERPRYTHON_COMPONENTS  # pylint: disable=global-statement
    new_component = _Component(the_type, target_types, singleton)
    if _get_component(new_component.get_type()) is not None:
        raise TypeError(f'{the_type.__name__} '
                        'already registered as component.')
    ENTERPRYTHON_COMPONENTS.append(new_component)


def _add_factory(func: Callable[..., TypeT],
                 singleton: bool) -> None:
    """Store new factory for DI."""
    global ENTERPRYTHON_FACTORIES  # pylint: disable=global-statement
    new_factory = _Factory(func, singleton)
    if _get_factory(new_factory.get_return_type()) is not None:
        raise TypeError(f'{func.__name__} '
                        'already registered as component.')
    ENTERPRYTHON_FACTORIES.append(new_factory)


def _is_list_type(the_type: Callable[..., TypeT]) -> bool:
    try:
        if VER_3_7_AND_UP:
            return _is_instance(the_type,
                                _GenericAlias) and _type_origin_is(the_type, list)
        return issubclass(the_type, List)  # type: ignore
    except TypeError:
        return False


def _is_instance(the_value: TypeT, the_type: Callable[..., TypeT]) -> bool:
    return isinstance(the_value, the_type)  # type: ignore


def _type_origin_is(the_type: Callable[..., TypeT], origin: Any) -> bool:
    assert hasattr(the_type, '__origin__')
    return the_type.__origin__ is origin  # type: ignore


def _get_list_type_elem_type(list_type: Callable[..., TypeT]) -> Callable[..., Any]:
    """Return the type of a single element of the list type."""
    assert _is_list_type(list_type)
    list_args = list_type.__args__  # type: ignore
    assert len(list_args) == 1
    return list_args[0]  # type: ignore
