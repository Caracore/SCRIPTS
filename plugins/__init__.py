# plugins/__init__.py
"""
Système de plugins pour le Gestionnaire de Scripts.
Permet à la communauté d'ajouter des fonctionnalités.
"""
from .manager import PluginManager
from .base import Plugin, HookType

__all__ = ['PluginManager', 'Plugin', 'HookType']
