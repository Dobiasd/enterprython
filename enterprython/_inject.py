"""
enterprython - Type-based dependency-injection framework
"""

import configparser
import inspect
from typing import Any, Dict, Optional, Type, TypeVar

TypeT = TypeVar('TypeT')

ENTERPRYTHON_CONFIG: Optional[configparser.ConfigParser] = None
ENTERPRYTHON_COMPONENTS: Dict[TypeT, Any] = {}


def configure(config: configparser.ConfigParser) -> None:
    """Set global enterprython value configuration."""
    global ENTERPRYTHON_CONFIG  # pylint: disable=global-statement
    ENTERPRYTHON_CONFIG = config


def assemble(constructor: TypeT, **kwargs: Any) -> TypeT:
    """Create an instance of a certain type,
    using constructor injection if needed."""

    global ENTERPRYTHON_COMPONENTS  # pylint: disable=global-statement

    if constructor in ENTERPRYTHON_COMPONENTS:
        if ENTERPRYTHON_COMPONENTS[constructor]:
            return ENTERPRYTHON_COMPONENTS[constructor]  # type: ignore

    signature = inspect.signature(constructor)

    parameters: Dict[str, TypeT] = {}
    for param in signature.parameters.values():
        if param.name == 'self':
            continue
        if param.kind != inspect.Parameter.POSITIONAL_OR_KEYWORD:
            raise TypeError('Only parameters of kind POSITIONAL_OR_KEYWORD '
                            'supported in target functions.')
        parameters[param.name] = param.annotation

    arguments: Dict[str, Any] = kwargs
    for parameter_name, parameter_type in parameters.items():
        for comp in ENTERPRYTHON_COMPONENTS:
            base_classes = inspect.getmro(comp)
            if parameter_type == comp or parameter_type in base_classes:
                arguments[parameter_name] = assemble(comp)
                break
    result = constructor(**arguments)
    if constructor in ENTERPRYTHON_COMPONENTS:
        ENTERPRYTHON_COMPONENTS[constructor] = result
    return result


def value(the_type: Type[TypeT], config_section: str, value_name: str) -> TypeT:
    """Get a config value from the global enterprython config store."""
    assert the_type in [bool, float, int, str]
    if the_type == bool:
        return ENTERPRYTHON_CONFIG.getboolean(config_section, value_name)  # type: ignore
    if the_type == float:
        return ENTERPRYTHON_CONFIG.getfloat(config_section, value_name)  # type: ignore
    if the_type == int:
        return ENTERPRYTHON_CONFIG.getint(config_section, value_name)  # type: ignore
    return ENTERPRYTHON_CONFIG.get(config_section, value_name)  # type: ignore


def component(constructor: TypeT) -> TypeT:
    """Annotation to register a class to be available for DI to constructors."""
    if inspect.isabstract(constructor):
        raise TypeError(f'Can not register abstract class as component.')
    global ENTERPRYTHON_COMPONENTS  # pylint: disable=global-statement
    if constructor in ENTERPRYTHON_COMPONENTS:
        raise TypeError(f'{constructor.__name__} '
                        'already registered as component.')
    ENTERPRYTHON_COMPONENTS[constructor] = None
    return constructor
