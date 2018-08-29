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
  * [Requirements and Installation](#requirements-and-installation)


Introduction
------------

If you plan to write enterprisey software, you probably want to apply [dependency injection](https://en.wikipedia.org/wiki/Dependency_injection) on your class constructors,
and use a library doing the lookup for you based on static type annotations, instead of configuring the object graph manually.

`enterprython` provides exactly that.

```python
from enterprython import assemble, component, configure, value


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
