"""
PandaOps Cookbook - Installation and management tools for Ethereum node operations
"""

from .config.settings import VERSION, ORG_NAME

__version__ = VERSION
__author__ = ORG_NAME
__description__ = "Installation and management tools for Ethereum node operations"

# Package imports
from . import config
from . import installers
from . import utils

__all__ = ["config", "installers", "utils"]