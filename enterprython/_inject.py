"""
enterprython - Type-based dependency injection
"""

import inspect
import os
import sys
from typing import Any, Callable, Dict, Optional, Type, TypeVar, List, Generic, Union, Tuple

import toml

VER_3_7_AND_UP = sys.version_info[:3] >= (3, 7, 0)  # PEP 560

# pylint: disable=no-name-in-module
if VER_3_7_AND_UP:
    from typing import _GenericAlias  # type: ignore
else:
    pass
# pylint: enable=no-name-in-module

TypeT = TypeVar('TypeT')


class _Setting:  # pylint: disable=too-few-public-methods
    def __init__(self, key: str):
        self.key = key


class _SettingMetadata:  # pylint: disable=too-few-public-methods
    def __init__(self, name: str, typ: Optional[Type[Any]], key: str):
        self.name = name
        self.typ = typ
        self.key = key


class _ParameterMetadata:  # pylint: disable=too-few-public-methods
    def __init__(self, name: str, typ: Type[Any], has_default: bool):
        self.name = name
        self.typ = typ
        self.has_default = has_default


class _Component(Generic[TypeT]):  # pylint: disable=unsubscriptable-object
    """Internal class to store components for DI."""

    def __init__(self, the_type: Callable[..., TypeT],
                 singleton: bool,
                 profiles: List[str]) -> None:
        """Figure out and store base classes."""
        self._type = the_type
        self._is_singleton = singleton
        self._profiles = profiles
        self._instance: Optional[TypeT] = None
        self._target_types: Tuple[Type[Any], ...] = inspect.getmro(the_type)  # type: ignore
        self._settings = _get_settings(the_type)

    def matches(self, the_type: Callable[..., TypeT],
                profile: Optional[str]) -> bool:
        """Check if component can be used for injection of the_type."""
        if self._profiles and not profile:
            return False
        if profile and self._profiles and profile not in self._profiles:
            return False
        return the_type in self._target_types  # type: ignore

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

    def get_setting(self, name: str) -> Optional[_SettingMetadata]:
        """Search setting by name"""
        for entry in self._settings:
            if entry.name == name:
                return entry
        return None


class _Factory(Generic[TypeT]):  # pylint: disable=unsubscriptable-object
    """Internal class to store factories for DI."""

    def __init__(self, func: Callable[..., TypeT],
                 singleton: bool,
                 profiles: List[str]) -> None:
        """Figure out and store base classes."""
        return_type = inspect.signature(func).return_annotation
        if return_type is inspect.Signature.empty:
            raise TypeError(f'Unknown return type of {func.__name__}')
        self._func = func
        self._is_singleton = singleton
        self._profiles = profiles
        self._return_type: Type[Any] = return_type
        self._target_types: Tuple[Type[Any], ...] = inspect.getmro(return_type)
        self._instance: Optional[TypeT] = None

    def matches(self, the_type: Callable[..., TypeT],
                profile: Optional[str]) -> bool:
        """Check if factory can be used for injection of the_type."""
        if self._profiles and not profile:
            return False
        if profile and self._profiles and profile not in self._profiles:
            return False
        return the_type in self._target_types  # type: ignore

    def get_instance(self) -> Optional[TypeT]:
        """Access singleton instance if present."""
        if not self._is_singleton or self._instance is None:
            self._instance = self._func()
        return self._instance

    def get_return_type(self) -> Type[Any]:
        """Type of constructed object."""
        return self._return_type


ValueType = Union[str, float, int, bool]

ENTERPRYTHON_VALUE_STORE: Dict[str, ValueType] = {}
ENTERPRYTHON_COMPONENTS: List[_Component[Any]] = []
ENTERPRYTHON_FACTORIES: List[_Factory[Any]] = []


def _create(the_type: Callable[..., TypeT],
            profile: Optional[str] = None) -> Tuple[Optional[TypeT], Optional[_Component[Any]]]:
    stored_component = _get_component(the_type, profile)
    stored_factory = _get_factory(the_type, profile)

    instance: Optional[TypeT] = None
    if stored_factory:
        instance = stored_factory.get_instance()
    elif stored_component:
        instance = stored_component.get_instance()

    return (instance, stored_component)


def _get_parameters_from_signature(the_type: Callable[..., TypeT]) -> List[_ParameterMetadata]:
    signature = inspect.signature(the_type)
    parameters: List[_ParameterMetadata] = []
    for param in signature.parameters.values():
        if param.name == 'self':
            continue
        if param.kind != inspect.Parameter.POSITIONAL_OR_KEYWORD:
            raise TypeError('Only parameters of kind POSITIONAL_OR_KEYWORD '
                            'supported in target functions.')
        if param.annotation is inspect.Signature.empty:
            raise TypeError('Parameter needs needs a type annotation.')
        parameters.append(_ParameterMetadata(param.name, param.annotation,
                                             param.default != inspect.Signature.empty))
    return parameters


def _append_path(preffix: str, path: str) -> str:
    """Appends the path, handles if preffix is empty"""
    path = path.lstrip("_")
    return path.upper() if len(preffix) == 0 else preffix + "_" + path.upper()


def _get_value_store_key(parameter_path: str,
                         parameter_name: str,
                         comp: Optional[_Component[Any]]) -> str:
    """Gets the default key based on the attribute path or the statically defined setting key"""
    key = parameter_path
    if comp:
        item = comp.get_setting(parameter_name)
        if item:
            key = item.key
    return key


def _missing_value(the_type: Callable[..., TypeT],
                   param: _ParameterMetadata, param_path: str) -> None:
    msg = f"{param.name} attribute in class"
    msg += f"{the_type.__module__}.{the_type.__name__} "
    msg += "is not defined in value store. "
    msg += f"Provide it using key: {param_path} or an static setting key"
    raise AttributeError(msg)


def _enforce_type(expected_type: Type[ValueType], key: str) -> ValueType:
    try:
        stored_value = ENTERPRYTHON_VALUE_STORE[key]
        return expected_type(stored_value)
    except ValueError as err:
        msg = f"Error injecting value with key:{key}. "
        msg += f"Expected type: {expected_type} but {type(stored_value)} was given"
        raise ValueError(msg) from err


def assemble(the_type: Callable[..., TypeT],
             profile: Optional[str] = None,
             **kwargs: Any) -> TypeT:
    """Create an instance of a certain type,
    using constructor injection if needed."""
    return _assemble_impl(the_type, profile, **kwargs)


def _assemble_impl(the_type: Callable[..., TypeT],
                   profile: Optional[str] = None,
                   inject_path: str = "",
                   **kwargs: Any) -> TypeT:
    """Internal implementation of the assemble,
    tracks the traversal path"""
    uses_manual_args = False
    ready_result, stored_component = _create(the_type, profile)

    if ready_result is not None:
        return ready_result

    arguments: Dict[str, Any] = kwargs

    uses_manual_args = False
    for param in _get_parameters_from_signature(the_type):
        parameter_path = _append_path(inject_path, param.name)
        if param.name in arguments:
            uses_manual_args = True
            continue
        if _is_list_type(param.typ):
            parameter_components = _get_components(
                _get_list_type_elem_type(param.typ), profile)
            arguments[param.name] = list(map(_assemble_impl,
                                             map(lambda comp: comp.get_type(),
                                                 parameter_components)))
        elif _is_value_type(param.typ):
            key = _get_value_store_key(parameter_path, param.name, stored_component)
            if key in ENTERPRYTHON_VALUE_STORE:
                arguments[param.name] = _enforce_type(param.typ, key)
            elif not param.has_default:
                _missing_value(the_type, param, parameter_path)

        else:
            parameter_component = _get_component(param.typ, profile)
            param_factory = _get_factory(param.typ, profile)
            if parameter_component is not None:
                arguments[param.name] = _assemble_impl(
                    parameter_component.get_type(), profile, parameter_path)  # parameter_type?
            elif param_factory:
                arguments[param.name] = param_factory.get_instance()

    result = the_type(**arguments)
    if stored_component and not uses_manual_args:
        stored_component.set_instance_if_singleton(result)
    return result


def setting(key: str) -> _Setting:
    """Attribute decorator"""
    return _Setting(key)


def _get_settings_from_dataclass(the_class: Callable[..., TypeT],
                                 annotations: Dict[str, type]) -> List[_SettingMetadata]:
    """get settings from dataclass"""
    settings: List[_SettingMetadata] = []
    for annotation_name, annotation_type in annotations.items():
        default = getattr(the_class, annotation_name, None)
        if isinstance(default, _Setting):
            settings.append(_SettingMetadata(annotation_name, annotation_type, default.key))
    return settings


def _get_settings_from_attrs(the_class: Callable[..., TypeT],
                             annotations: Dict[str, type]) -> List[_SettingMetadata]:
    """get settings from attrs class"""
    settings: List[_SettingMetadata] = []
    # default values are stored outside annotations:
    attributes = getattr(the_class, "__attrs_attrs__", [])
    for attribute in attributes:
        default = getattr(attribute, "default", None)
        attribute_name = str(getattr(attribute, "name", None))
        if default and isinstance(default, _Setting):
            # type is stored in annotation
            annotation_type = annotations.get(attribute_name, None)
            settings.append(_SettingMetadata(attribute_name, annotation_type, default.key))
    return settings


def _get_settings(the_class: Callable[..., TypeT]) -> List[_SettingMetadata]:
    """Gets the class attributes decorated as settings"""
    settings: List[_SettingMetadata] = []
    cls_annotations = the_class.__dict__.get('__annotations__', {})
    if cls_annotations:
        if hasattr(the_class, '__dataclass_fields__'):
            settings = _get_settings_from_dataclass(the_class, cls_annotations)
        elif hasattr(the_class, "__attrs_attrs__"):
            settings = _get_settings_from_attrs(the_class, cls_annotations)
    return settings


def component(singleton: bool = True,  # pylint: disable=dangerous-default-value
              profiles: List[str] = []) -> Callable[[Callable[..., TypeT]],  # pylint: disable=dangerous-default-value
                                                    Callable[..., TypeT]]:
    """Annotation to register a class to be available for DI."""

    def register(the_class: Callable[..., TypeT]) -> Callable[..., TypeT]:
        """Register component and forward type."""
        if not inspect.isclass(the_class):
            raise TypeError('Only classes can be registered as components.')
        if inspect.isabstract(the_class):
            raise TypeError('Can not register abstract class as component.')
        _add_component(the_class, singleton, profiles)
        return the_class

    return register


def factory(singleton: bool = True,  # pylint: disable=dangerous-default-value
            profiles: List[str] = []) -> Callable[[Callable[..., TypeT]],
                                                  Callable[..., TypeT]]:
    """Annotation to register a factory to be available for DI."""

    def register(func: Callable[..., TypeT]) -> Callable[..., TypeT]:
        """Register component and forward type."""
        if not inspect.isfunction(func):
            raise TypeError('Only functions can be registered as factories.')
        _add_factory(func, singleton, profiles)
        return func

    return register


def _get_components(the_type: Callable[..., TypeT],
                    profile: Optional[str]) -> List[_Component[TypeT]]:
    """Return stored component for type if available."""
    return [stored_component
            for stored_component in ENTERPRYTHON_COMPONENTS
            if stored_component.matches(the_type, profile)]


def _get_component(the_type: Callable[..., TypeT],
                   profile: Optional[str]) -> Optional[_Component[TypeT]]:
    """Return stored component for type if available."""
    components = _get_components(the_type, profile)
    if len(components) > 1:
        raise TypeError(f'Ambiguous dependency {the_type.__name__}.')
    if not components:
        return None
    return components[0]


def _get_factories(the_type: Callable[..., TypeT],
                   profile: Optional[str]) -> List[_Factory[TypeT]]:
    """Return stored factories for type if available."""
    return [stored_factory
            for stored_factory in ENTERPRYTHON_FACTORIES
            if stored_factory.matches(the_type, profile)]


def _get_factory(the_type: Callable[..., TypeT],
                 profile: Optional[str]) -> Optional[_Factory[TypeT]]:
    """Return stored factory for type if available."""
    factories = _get_factories(the_type, profile)
    if len(factories) > 1:
        raise TypeError(f'Multiple factories available for {the_type.__name__}.')
    if not factories:
        return None
    return factories[0]


def _add_component(the_type: Callable[..., TypeT],
                   singleton: bool,
                   profiles: List[str]) -> None:
    """Store new component for DI."""
    new_component = _Component(the_type, singleton, profiles)
    if _get_component(new_component.get_type(), None) is not None:
        raise TypeError(f'{the_type.__name__} '
                        'already registered as component.')

    for profile in profiles:
        if _get_component(new_component.get_type(), profile) is not None:
            raise TypeError(f'{the_type.__name__} '
                            'already registered as component for profile "{profile}".')
    ENTERPRYTHON_COMPONENTS.append(new_component)


def _add_factory(func: Callable[..., TypeT],
                 singleton: bool,
                 profiles: List[str]) -> None:
    """Store new factory for DI."""
    new_factory = _Factory(func, singleton, profiles)
    if _get_factory(new_factory.get_return_type(), None) is not None:
        raise TypeError(f'{func.__name__} '
                        'already registered as component.')

    for profile in profiles:
        if _get_factory(new_factory.get_return_type(), profile) is not None:
            raise TypeError(f'{func.__name__} '
                            'already registered as component for profile "{profile}".')
    ENTERPRYTHON_FACTORIES.append(new_factory)


def _is_list_type(the_type: Callable[..., TypeT]) -> bool:
    try:
        if VER_3_7_AND_UP:
            return _is_instance(the_type,
                                _GenericAlias) and _type_origin_is(the_type, list)
        return issubclass(the_type, List)  # type: ignore
    except TypeError:
        return False


def _is_value_type(the_type: Callable[..., TypeT]) -> bool:
    return the_type in [bool, float, int, str]  # type: ignore


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


def load_config(app_name: str, paths: List[str]) -> None:
    """loads the configuration from a list of files,
    then from environment variables and finally from command arguments"""
    for path in paths:
        try:
            _merge_dicts(ENTERPRYTHON_VALUE_STORE, toml.load(path))  # type: ignore
        except Exception as exception:
            raise Exception(f"Error loading file: {path}") from exception
    _merge_dicts(ENTERPRYTHON_VALUE_STORE, load_env_vars(app_name))
    _merge_dicts(ENTERPRYTHON_VALUE_STORE, load_command_args())


def _merge_dicts(dict1: Dict[str, ValueType], dict2: Dict[str, ValueType]) -> None:
    """
    Merges dict2 into dict1. dict1 is modified in-place
    """
    for key, val in dict2.items():
        dict1[key.upper()] = val


def load_env_vars(app_name: str) -> Dict[str, ValueType]:
    """Load environment variables"""
    values: Dict[str, Any] = {}
    preffix = f"{app_name.upper()}_"
    preffix_len = len(preffix)
    clean_var_name: str

    env = os.environ

    for var_name, var_value in env.items():
        if var_name.startswith(preffix):
            clean_var_name = var_name[preffix_len:]
            values[clean_var_name] = var_value
    return values


def load_command_args() -> Dict[str, ValueType]:
    """Load command line arguments"""
    values: Dict[str, Any] = {}
    arg_name: str
    arg_value: str
    for arg in sys.argv:
        if arg.startswith("--") and arg.find("=") > 0:
            arg_name, arg_value = arg.lstrip("-").split("=")
            arg_value = arg_value.strip()
            values[arg_name] = arg_value
    return values
