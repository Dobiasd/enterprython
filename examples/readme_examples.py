#!/usr/bin/env python3

"""
enterprython - examples from README.md
"""
import configparser

from enterprython import assemble, component, configure, value

__author__ = "Tobias Hermann"
__copyright__ = "Copyright 2018, Tobias Hermann"
__email__ = "editgym@gmail.com"
__license__ = "MIT"


@component()
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
    assemble(Client).run()


if __name__ == "__main__":
    main()
