![logo](https://github.com/Dobiasd/enterprython/raw/master/logo/enterprython.png)

[![CI](https://github.com/Dobiasd/enterprython/workflows/ci/badge.svg)](https://github.com/Dobiasd/enterprython/actions)
[![(License MIT 1.0)](https://img.shields.io/badge/license-MIT%201.0-blue.svg)][license]

[license]: LICENSE

enterprython
============

**Python library providing type-based dependency injection**

Table of contents
-----------------

* [Introduction](#introduction)
* [Features](#features)
  * [Abstract base classes and profiles](#abstract-base-classes-and-profiles)
  * [Factories](#factories)
  * [Non-singleton services](#non-singleton-services)
  * [Service lists](#service-lists)
  * [Mixing managed and manual injection](#mixing-managed-and-manual-injection)
  * [Free functions as clients](#free-functions-as-clients)
  * [Value store](#value-store)
  * [Value injection](#value-injection)
* [Requirements and Installation](#requirements-and-installation)

Introduction
------------

If you plan to develop [SOLID](https://en.wikipedia.org/wiki/SOLID) / [domain-driven](https://en.wikipedia.org/wiki/Domain-driven_design) (i.e., enterprisey) software, you probably [want](why_you_want_formal_dependency_injection_in_python_too.md) to apply [inversion of control](https://en.wikipedia.org/wiki/Inversion_of_control) in the form of [dependency injection](https://en.wikipedia.org/wiki/Dependency_injection) when writing the constructors of your classes.
Also, you likely want to use a library doing the needed lookups for you based on static type annotations, instead of manually configuring the object graph.

`enterprython` provides exactly that.

```python
from enterprython import assemble, component

@component()
class Service:
    def __init__(self) -> None:
        self._greeting: str = 'Hello'

    def greet(self, name: str) -> str:
        return f'{self._greeting}, {name}!'

class Client:
    def __init__(self, service: Service) -> None:
        self._service = service

    def run(self) -> None:
        print(self._service.greet('World'))


assemble(Client).run()
```

Output:

```text
Hello, World!
```

Features
--------

### Abstract base classes and profiles

A client may depend on an abstract base class. Enterprython will inject the matching implementation.

```python
from abc import ABC
from enterprython import assemble, component

class ServiceInterface(ABC):
    ...

@component()
class ServiceImpl(ServiceInterface):
    ...

class Client:
    def __init__(self, services: ServiceInterface) -> None:
        ...

assemble(Client)
```

One singleton instance of `ServiceImpl` is created and injected into `Client`.

This feature enables the use of different profiles.
For example, you might want to use different classes implementing an interface
for your production environment compared to when running integration tests.
By providing a `profiles` list, you can limit when the component is available.

```python
@component(profiles=['prod'])
class ServiceImpl(ServiceInterface):
    ...
    
@component(profiles=['test'])
class ServiceMock(ServiceInterface):
    ...

assemble(Client, profile='test')
```

### Factories

Annotating a function with `@factory()` registers a factory for its return type.

```python

from enterprython import assemble, component

class Service:
    ...

@factory()
def service_factory() -> Service:
    return Service()

class Client:
    def __init__(self, service: Service) -> None:
        ...

assemble(Client)
```

`service_factory` is used to create the `Service` instance for calling the constructor of `Client`.

### Non-singleton services

If a service is annotated with `@component(singleton=False)` a new instance of it is created with every injection.

```python
@component(singleton=False)
class Service:
    ...

class Client:
    def __init__(self, service: Service) -> None:
        ...
```

### Service lists

A client may depend on a list of implementations of a service interface.

```python
from abc import ABC
from typing import List
from enterprython import assemble, component

class ServiceInterface(ABC):
    pass

@component()
class ServiceA(ServiceInterface):
    ...

@component()
class ServiceB(ServiceInterface):
    ...

class Client:
    def __init__(self, services: List[ServiceInterface]) -> None:
        ...

assemble(Client)
```

`[ServiceA(), ServiceB()]` is injected into `Client`.

### Mixing managed and manual injection

One part of a client's dependencies might be injected manually, the rest automatically.

```python

from enterprython import assemble, component

@component()
class ServiceA:
    ...

class ServiceB:
    ...

class Client:
    def __init__(self, service_a: ServiceA, service_b: ServiceB) -> None:
        ...

assemble(Client, service_b=ServiceB())
```

`service_a` comes from the DI container, `service_b` from user code.

If `ServiceB` also has a `@component()` annotation, the manually provided object is preferred.

### Free functions as clients

Since class constructors are fundamentally just normal functions, we can inject dependencies into free functions too.

```python

from enterprython import assemble, component

@component()
class Service:
    ...

def client(service: Service) -> None:
    ...

assemble(client)
```

A singleton instance of `Service` is created and used to call `client`.

### Value Store
The value store supports merging multiple sources using the following precedence order:
1. Configuration files using the list provided order. **toml** format is the only supported for now.
2. Environment variables. Variables must be prefixed with the application name 
3. Command line arguments. Arguments must follow the format: --key=value.

Command-line arguments overwrite environment variables and environment variables overwrite configuration files.

To load the value store use the helper function `load_config` as below.

```python
load_config(app_name="myapp", paths=["config.toml"])
```

`app_name` is the application name and is required to identify environment variables.

`paths` is a list of relative file paths, files will be loaded and merged in the same order.

### Value Injection

Service's value-type attributes are automatically injected from the value store using either the traversal path or a given value store key.

Python [dataclass](https://docs.python.org/3/library/dataclasses.html) and [attrs](https://www.attrs.org/en/stable/) are supported.

`@attrs.define` or `@dc.dataclass` decorators are provided after the `@component` decorator 

Notice that `attrs` and `dc` module alias is being used to highlight what library is used.

Feel free to use the more compact `@define` and `@dataclass` versions in your production code.


```python
import attrs

@component()
@attrs.define
class Service:
    attrib1: int
    attrib2: str
    attrib3: bool

    ...

class Client:
    service: Service

    ...

load_config("myapp", ["config.toml"])
assemble(Client)
```

config.toml:
```toml
service_attrib1 = 10
service_attrib2 = "mystring"
service_attrib3 = false
```

attrib1, attrib2, and attrib3 will be injected using the configuration entries listed above. 

By default, enterprython will use the attribute path convention (notice the **service_** prefix in each of the configuration entries )

If multiple services need to read the same configuration entry, the `setting` decorator let you provide your custom key:

```python
@component()
@attrs.define
class Service:
    attrib1: int = setting("MYATTRIB1")
    attrib2: str = setting("MYATTRIB2")
    attrib3: bool = setting("MYATTRIB3")

    ...

class Client:
    service: Service

    ...

load_config("myapp", ["config.toml"])
assemble(Client)
```

config.toml:
```toml
MYATTRIB1 = 10
MYATTRIB2 = "mystring"
MYATTRIB3 = false
```

The value injection provides type-checking and enforces injection of any attribute without defaults.

To skip injecting an attribute, you can:
1. Use the attribute default value.
2. Use the attrs/dataclass `field` decorator providing `init=False` and `default=...`  to opt-out from injection. 
Using this, the attribute will not get injected (even if a matching entry exists in the value store)

```python
@component()
@attrs.define
class Service:
    # below attribute WILL be injected from the value store
    # an entry MUST exist in the value store
    attrib1: int
    # below attribute CAN be injected from the value store,
    # if not provided in value store, then the default is used
    attrib2: str = "test"
    # below attribute will not be injected
    # any entry in the value store will be ignored
    attrib3: bool = attrs.field(init=False, default=True)
```



Requirements and Installation
-----------------------------

You need Python 3.7 or higher.

```bash
python3 -m pip install enterprython
```

Or, if you like to use the latest version from this repository:

```bash
git clone https://github.com/Dobiasd/enterprython
cd enterprython
python3 -m pip install .
```

License
-------
Distributed under the MIT License.
(See accompanying file [`LICENSE`](https://github.com/Dobiasd/enterprython/blob/master/LICENSE) or at
[https://opensource.org/licenses/MIT](https://opensource.org/licenses/MIT))
