"""
enterprython - Type-based dependency injection
"""
from ._inject import assemble
from ._inject import component
from ._inject import factory
from ._inject import load_command_args
from ._inject import load_config
from ._inject import load_env_vars
from ._inject import setting

# pylint: disable=invalid-name
name = "enterprython"

__author__ = "Tobias Hermann"
__copyright__ = "Copyright 2018, Tobias Hermann"
__email__ = "editgym@gmail.com"
__license__ = "MIT"
__version__ = "0.7.0"
