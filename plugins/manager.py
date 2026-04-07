# plugins/manager.py
"""
Gestionnaire de plugins - charge, active et coordonne les plugins.
"""
import os
import sys
import json
import importlib.util
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path

from .base import Plugin, PluginMeta, HookType


class PluginManager:
    """Gestionnaire central des plugins."""
    
    PLUGINS_DIR = "plugins"
    COMMUNITY_DIR = "community"
    CONFIG_FILE = "plugins.json"
    
    def __init__(self, program: Any):
        self.program = program
        self.plugins: Dict[str, Plugin] = {}
        self.hooks: Dict[HookType, List[Callable]] = {hook: [] for hook in HookType}
        self.menu_items: List[Dict[str, Any]] = []
        self.additional_languages: Dict[str, Dict] = {}
        self.templates: Dict[str, str] = {}
        
        # Chemins des plugins
        self.base_path = Path(program.current_path)
        self.plugins_path = self.base_path / "data" / self.PLUGINS_DIR
        self.community_path = self.plugins_path / self.COMMUNITY_DIR
        self.config_path = self.base_path / "data" / self.CONFIG_FILE
        
        # Créer les dossiers si nécessaire
        self.plugins_path.mkdir(parents=True, exist_ok=True)
        self.community_path.mkdir(parents=True, exist_ok=True)
        
        # Configuration des plugins
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Charge la configuration des plugins."""
        default = {
            "enabled_plugins": [],
            "disabled_plugins": [],
            "plugin_settings": {}
        }
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return {**default, **json.load(f)}
        except (json.JSONDecodeError, IOError):
            pass
        return default
    
    def _save_config(self) -> None:
        """Sauvegarde la configuration des plugins."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def discover_plugins(self) -> List[str]:
        """Découvre tous les plugins disponibles."""
        discovered = []
        
        for plugins_dir in [self.plugins_path, self.community_path]:
            if not plugins_dir.exists():
                continue
            
            for item in plugins_dir.iterdir():
                # Plugin en tant que module (dossier avec __init__.py)
                if item.is_dir():
                    init_file = item / "__init__.py"
                    plugin_file = item / "plugin.py"
                    if init_file.exists() or plugin_file.exists():
                        discovered.append(str(item))
                
                # Plugin en tant que fichier unique
                elif item.suffix == ".py" and item.stem not in ["__init__", "base", "manager"]:
                    discovered.append(str(item))
        
        return discovered
    
    def load_plugin(self, plugin_path: str) -> Optional[Plugin]:
        """Charge un plugin depuis son chemin."""
        path = Path(plugin_path)
        
        try:
            # Déterminer le fichier à charger
            if path.is_dir():
                plugin_file = path / "plugin.py"
                if not plugin_file.exists():
                    plugin_file = path / "__init__.py"
                module_name = path.stem
            else:
                plugin_file = path
                module_name = path.stem
            
            if not plugin_file.exists():
                print(f"[Plugin] Fichier introuvable: {plugin_file}")
                return None
            
            # Charger le module dynamiquement
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if spec is None or spec.loader is None:
                print(f"[Plugin] Impossible de charger: {plugin_path}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Trouver la classe Plugin dans le module
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, Plugin) and 
                    attr is not Plugin):
                    plugin_class = attr
                    break
            
            if plugin_class is None:
                print(f"[Plugin] Aucune classe Plugin trouvée dans: {plugin_path}")
                return None
            
            # Instancier et charger le plugin
            plugin = plugin_class()
            if plugin.on_load(self.program):
                return plugin
            else:
                print(f"[Plugin] Échec du chargement: {plugin.meta.name}")
                return None
                
        except Exception as e:
            print(f"[Plugin] Erreur lors du chargement de {plugin_path}: {e}")
            return None
    
    def register_plugin(self, plugin: Plugin) -> bool:
        """Enregistre un plugin et ses hooks."""
        name = plugin.meta.name
        
        if name in self.plugins:
            print(f"[Plugin] '{name}' déjà enregistré")
            return False
        
        # Enregistrer le plugin
        self.plugins[name] = plugin
        
        # Enregistrer les hooks
        for hook_type, handler in plugin.get_hooks().items():
            self.hooks[hook_type].append(handler)
        
        # Enregistrer les éléments de menu
        self.menu_items.extend(plugin.get_menu_items())
        
        # Enregistrer les langages
        self.additional_languages.update(plugin.get_languages())
        
        # Enregistrer les templates
        self.templates.update(plugin.get_templates())
        
        print(f"[Plugin] '{name}' v{plugin.meta.version} chargé")
        return True
    
    def unload_plugin(self, name: str) -> bool:
        """Décharge un plugin."""
        if name not in self.plugins:
            return False
        
        plugin = self.plugins[name]
        plugin.on_unload(self.program)
        
        # Retirer les hooks
        for hook_type, handler in plugin.get_hooks().items():
            if handler in self.hooks[hook_type]:
                self.hooks[hook_type].remove(handler)
        
        # Retirer les éléments de menu
        for item in plugin.get_menu_items():
            if item in self.menu_items:
                self.menu_items.remove(item)
        
        # Retirer les langages
        for lang in plugin.get_languages():
            self.additional_languages.pop(lang, None)
        
        # Retirer les templates
        for template in plugin.get_templates():
            self.templates.pop(template, None)
        
        del self.plugins[name]
        print(f"[Plugin] '{name}' déchargé")
        return True
    
    def load_all(self) -> None:
        """Charge tous les plugins activés."""
        discovered = self.discover_plugins()
        disabled = self.config.get("disabled_plugins", [])
        
        for plugin_path in discovered:
            path = Path(plugin_path)
            name = path.stem
            
            if name in disabled:
                continue
            
            plugin = self.load_plugin(plugin_path)
            if plugin:
                self.register_plugin(plugin)
    
    def trigger_hook(self, hook_type: HookType, *args, **kwargs) -> List[Any]:
        """Déclenche un hook et retourne les résultats."""
        results = []
        for handler in self.hooks[hook_type]:
            try:
                result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"[Plugin] Erreur dans hook {hook_type.name}: {e}")
        return results
    
    def get_all_languages(self) -> Dict[str, Dict]:
        """Retourne tous les langages (natifs + plugins)."""
        from script import Script
        return {**Script.LANGUAGES, **self.additional_languages}
    
    def enable_plugin(self, name: str) -> bool:
        """Active un plugin."""
        disabled = self.config.get("disabled_plugins", [])
        if name in disabled:
            disabled.remove(name)
            self.config["disabled_plugins"] = disabled
            self._save_config()
            return True
        return False
    
    def disable_plugin(self, name: str) -> bool:
        """Désactive un plugin."""
        disabled = self.config.get("disabled_plugins", [])
        if name not in disabled:
            disabled.append(name)
            self.config["disabled_plugins"] = disabled
            self._save_config()
            self.unload_plugin(name)
            return True
        return False
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """Liste tous les plugins avec leur statut."""
        plugins_info = []
        discovered = self.discover_plugins()
        
        for plugin_path in discovered:
            path = Path(plugin_path)
            name = path.stem
            
            info = {
                "name": name,
                "path": plugin_path,
                "loaded": name in self.plugins,
                "enabled": name not in self.config.get("disabled_plugins", [])
            }
            
            if name in self.plugins:
                meta = self.plugins[name].meta
                info.update(meta.to_dict())
            
            plugins_info.append(info)
        
        return plugins_info
    
    def get_plugin_settings(self, name: str) -> Dict[str, Any]:
        """Récupère les paramètres d'un plugin."""
        return self.config.get("plugin_settings", {}).get(name, {})
    
    def set_plugin_setting(self, name: str, key: str, value: Any) -> None:
        """Définit un paramètre pour un plugin."""
        if "plugin_settings" not in self.config:
            self.config["plugin_settings"] = {}
        if name not in self.config["plugin_settings"]:
            self.config["plugin_settings"][name] = {}
        self.config["plugin_settings"][name][key] = value
        self._save_config()
