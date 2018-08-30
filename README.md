![logo](https://github.com/Dobiasd/enterprython/raw/master/logo/enterprython.png)

[![Build Status](https://travis-ci.org/Dobiasd/enterprython.svg?branch=master)][travis]
[![(License MIT 1.0)](https://img.shields.io/badge/license-MIT%201.0-blue.svg)][license]

[travis]: https://travis-ci.org/Dobiasd/enterprython
[license]: LICENSE


enterprython
============
**Python library providing type-based dependency-injection**


Table of contents
-----------------
  * [Introduction](#introduction)
  * [Features](#features)
    * [Abstract base classes](#abstract-base-classes)
    * [Factories](#factories)
    * [Non-singleton services](#non-singleton-services)
    * [Service lists](#service-lists)
    * [Mixing managed and manual injection](#mixing-managed-and-manual-injection)
    * [Free functions as clients](#free-functions-as-clients)
    
  * [Requirements and Installation](#requirements-and-installation)


Introduction
------------

If you plan to develop [SOLID](https://en.wikipedia.org/wiki/SOLID)/[domain-driven](https://en.wikipedia.org/wiki/Domain-driven_design) (i.e., enterprisey) software, you probably want to apply [dependency injection](https://en.wikipedia.org/wiki/Dependency_injection) on your class constructors,
and use a library doing the lookup for you based on static type annotations, instead of configuring the object graph manually.

`enterprython` provides exactly that.

```python
from enterprython import assemble, component


@component()
class Service:
    def __init__(self) -> None:
        self._greeting: str = "Hello"

    def greet(self, name: str) -> str:
        return f"{self._greeting}, {name}!"


class Client:
    def __init__(self, service: Service) -> None:
        self._service = service

    def run(self) -> None:
        print(self._service.greet("World"))


assemble(Client).run()
```

Output:

```
Hello, World!
```


Features
--------

### Abstract base classes

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


Requirements and Installation
-----------------------------

You need Python 3.6.5 or higher.

```bash
python3 -m pip install enterprython
```

Or, if you like to use latest version from this repository:
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
