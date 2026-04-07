# plugins/base.py
"""
Classes de base pour créer des plugins.
"""
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, Dict, Optional, List, Callable


class HookType(Enum):
    """Types de hooks disponibles pour les plugins."""
    # Hooks de cycle de vie
    ON_STARTUP = auto()          # Au démarrage du programme
    ON_SHUTDOWN = auto()         # À la fermeture du programme
    
    # Hooks de menu
    ON_MENU_DISPLAY = auto()     # Avant affichage du menu
    ON_MENU_CHOICE = auto()      # Après choix dans le menu
    
    # Hooks de scripts
    PRE_EXECUTE = auto()         # Avant exécution d'un script
    POST_EXECUTE = auto()        # Après exécution d'un script
    PRE_CREATE = auto()          # Avant création d'un script
    POST_CREATE = auto()         # Après création d'un script
    PRE_EDIT = auto()            # Avant édition d'un script
    POST_EDIT = auto()           # Après édition d'un script
    
    # Hooks d'extension
    REGISTER_LANGUAGE = auto()   # Enregistrer un nouveau langage
    REGISTER_COMMAND = auto()    # Enregistrer une nouvelle commande menu
    REGISTER_TEMPLATE = auto()   # Enregistrer un template de script


class PluginMeta:
    """Métadonnées d'un plugin."""
    def __init__(
        self,
        name: str,
        version: str,
        author: str,
        description: str = "",
        dependencies: List[str] = None,
        homepage: str = "",
        license: str = "MIT"
    ):
        self.name = name
        self.version = version
        self.author = author
        self.description = description
        self.dependencies = dependencies or []
        self.homepage = homepage
        self.license = license

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "dependencies": self.dependencies,
            "homepage": self.homepage,
            "license": self.license
        }


class Plugin(ABC):
    """
    Classe de base pour créer un plugin.
    
    Exemple d'utilisation:
    
    class MonPlugin(Plugin):
        @property
        def meta(self):
            return PluginMeta(
                name="mon-plugin",
                version="1.0.0",
                author="MonNom",
                description="Description du plugin"
            )
        
        def on_load(self, program):
            print("Plugin chargé!")
            return True
            
        def get_hooks(self):
            return {
                HookType.ON_STARTUP: self.on_startup,
                HookType.PRE_EXECUTE: self.before_run
            }
    """
    
    @property
    @abstractmethod
    def meta(self) -> PluginMeta:
        """Retourne les métadonnées du plugin."""
        pass
    
    @abstractmethod
    def on_load(self, program: Any) -> bool:
        """
        Appelé au chargement du plugin.
        Retourne True si le chargement a réussi, False sinon.
        """
        pass
    
    def on_unload(self, program: Any) -> None:
        """Appelé au déchargement du plugin."""
        pass
    
    def get_hooks(self) -> Dict[HookType, Callable]:
        """
        Retourne les hooks enregistrés par ce plugin.
        Chaque hook est une fonction qui sera appelée au moment approprié.
        """
        return {}
    
    def get_menu_items(self) -> List[Dict[str, Any]]:
        """
        Retourne les éléments de menu à ajouter.
        Format: [{"key": "x", "label": "Ma commande", "handler": self.ma_fonction}]
        """
        return []
    
    def get_languages(self) -> Dict[str, Dict[str, Any]]:
        """
        Retourne les langages à ajouter.
        Format: {"rust": {"ext": ".rs", "cmd": ["cargo", "run"], "template": "..."}}
        """
        return {}
    
    def get_templates(self) -> Dict[str, str]:
        """
        Retourne les templates de scripts.
        Format: {"web-scraper": "import requests\\n..."}
        """
        return {}
    
    def get_settings_schema(self) -> Dict[str, Any]:
        """
        Retourne le schéma des paramètres du plugin.
        Format: {"setting_name": {"type": "string", "default": "value", "description": "..."}}
        """
        return {}
