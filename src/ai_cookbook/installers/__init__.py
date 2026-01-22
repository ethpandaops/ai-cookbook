"""Installers package for PandaOps Cookbook."""

from .base import BaseInstaller, InteractiveInstaller, InstallationResult
from .commands import CommandsInstaller
from .skills import SkillsInstaller
from .code_standards import CodeStandardsInstaller
from .hooks import HooksInstaller
from .scripts import ScriptsInstaller

__all__ = [
    'BaseInstaller',
    'InteractiveInstaller',
    'InstallationResult',
    'CommandsInstaller',
    'SkillsInstaller',
    'CodeStandardsInstaller',
    'HooksInstaller',
    'ScriptsInstaller',
]