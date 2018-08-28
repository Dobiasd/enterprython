![logo](https://github.com/Dobiasd/enterprython/raw/master/logo/enterprython.png)

[![Build Status](https://travis-ci.org/Dobiasd/enterprython.svg?branch=master)][travis]
[![(License MIT 1.0)](https://img.shields.io/badge/license-MIT%201.0-blue.svg)][license]

[travis]: https://travis-ci.org/Dobiasd/enterprython
[license]: LICENSE


enterprython
============
**Type-based dependency-injection framework**


Table of contents
-----------------
  * [Introduction](#introduction)
  * [Requirements and Installation](#requirements-and-installation)


Introduction
------------

todo: explain IoC, SLP, DI with config, DI with annotations and static types

```python
import configparser

from enterprython import component, configure, create, value


@component
class Service:
    def __init__(self) -> None:
        self._greeting: str = value(str, 'service', 'greeting')

    def greet(self, name: str) -> str:
        return f"{self._greeting}, {name}!"


class Client:
    def __init__(self, service: Service) -> None:
        self._service = service

    def run(self) -> None:
        print(self._service.greet("World"))


def main():
    config = configparser.ConfigParser()
    config.read_string("""
        [service]
        greeting = Hello
    """)
    configure(config)
    create(Client).run()
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
