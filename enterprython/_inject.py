"""
enterprython - Type-based dependency-injection
"""

import configparser
import inspect
from typing import Any, Callable, Dict, Optional, Type, TypeVar, List, Generic

TypeT = TypeVar('TypeT')


class _Component(Generic[TypeT]):
    """Internal class to store components for DI."""

    def __init__(self, the_type: Callable[..., TypeT], singleton: bool) -> None:
        """Figure out and store base classes."""
        self._type = the_type
        self._is_singleton = singleton
        self._base_classes = inspect.getmro(the_type)  # type: ignore
        self._instance: Optional[TypeT] = None

    def matches(self, the_type: Callable[..., TypeT]) -> bool:
        """Check if component can be used for injection of the_type."""
        return the_type in self._base_classes

    def set_instance_if_singleton(self, instance: TypeT) -> None:
        """If this component is a singleton, set it's instance."""
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


ENTERPRYTHON_CONFIG: Optional[configparser.ConfigParser] = None
ENTERPRYTHON_COMPONENTS: List[_Component] = []


def _get_component(constructor: Callable[..., TypeT]) -> Optional[_Component]:
    """Return stored component for type if available."""
    for stored_component in ENTERPRYTHON_COMPONENTS:
        if stored_component.matches(constructor):
            return stored_component
    return None


def _add_component(constructor: Callable[..., TypeT], singleton: bool) -> None:
    """Store new component for DI."""
    global ENTERPRYTHON_COMPONENTS  # pylint: disable=global-statement
    assert _get_component(constructor) is None
    ENTERPRYTHON_COMPONENTS.append(_Component(constructor, singleton))


def configure(config: configparser.ConfigParser) -> None:
    """Set global enterprython value configuration."""
    global ENTERPRYTHON_CONFIG  # pylint: disable=global-statement
    ENTERPRYTHON_CONFIG = config


def assemble(constructor: Callable[..., TypeT], **kwargs: Any) -> TypeT:
    """Create an instance of a certain type,
    using constructor injection if needed."""

    global ENTERPRYTHON_COMPONENTS  # pylint: disable=global-statement

    stored_component = _get_component(constructor)
    if stored_component:
        instance = stored_component.get_instance()
        if instance is not None:
            return instance  # type: ignore

    signature = inspect.signature(constructor)

    parameters: Dict[str, Type[Any]] = {}
    for param in signature.parameters.values():
        if param.name == 'self':
            continue
        if param.kind != inspect.Parameter.POSITIONAL_OR_KEYWORD:
            raise TypeError('Only parameters of kind POSITIONAL_OR_KEYWORD '
                            'supported in target functions.')
        parameters[param.name] = param.annotation

    arguments: Dict[str, Any] = kwargs
    for parameter_name, parameter_type in parameters.items():
        parameter_component = _get_component(parameter_type)
        if parameter_component is not None:
            arguments[parameter_name] = assemble(parameter_component.get_type())
            break
    result = constructor(**arguments)
    if stored_component:
        stored_component.set_instance_if_singleton(result)
    return result


def value(the_type: Callable[..., TypeT], config_section: str, value_name: str) -> TypeT:
    """Get a config value from the global enterprython config store."""
    assert the_type in [bool, float, int, str]
    if the_type == bool:
        return ENTERPRYTHON_CONFIG.getboolean(config_section, value_name)  # type: ignore
    if the_type == float:
        return ENTERPRYTHON_CONFIG.getfloat(config_section, value_name)  # type: ignore
    if the_type == int:
        return ENTERPRYTHON_CONFIG.getint(config_section, value_name)  # type: ignore
    return ENTERPRYTHON_CONFIG.get(config_section, value_name)  # type: ignore


def component(singleton: bool = True) -> Callable[[Callable[..., TypeT]],
                                                  Callable[..., TypeT]]:
    """Annotation to register a class to be available for DI to constructors."""

    def register(the_type: Callable[..., TypeT]) -> Callable[..., TypeT]:
        """Register component and forward type."""
        if not inspect.isclass(the_type):
            raise TypeError(f'Only classes can be registered.')
        if inspect.isabstract(the_type):
            raise TypeError(f'Can not register abstract class as component.')
        global ENTERPRYTHON_COMPONENTS  # pylint: disable=global-statement
        if _get_component(the_type) is not None:
            raise TypeError(f'{the_type.__name__} '
                            'already registered as component.')
        _add_component(the_type, singleton)
        return the_type

    return register
