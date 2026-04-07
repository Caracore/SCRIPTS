# data/plugins/example_plugin.py
"""
Plugin exemple - Démontre comment créer un plugin pour le gestionnaire.
"""
import sys
import os

# Ajouter le chemin parent pour importer les modules du plugin
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from plugins.base import Plugin, PluginMeta, HookType


class ExamplePlugin(Plugin):
    """Plugin exemple avec toutes les fonctionnalités."""
    
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="example-plugin",
            version="1.0.0",
            author="Communauté",
            description="Plugin exemple montrant les fonctionnalités disponibles",
            homepage="https://github.com/example/plugin",
            license="MIT"
        )
    
    def on_load(self, program) -> bool:
        """Appelé au chargement du plugin."""
        self.program = program
        print(f"[{self.meta.name}] Chargé avec succès!")
        return True
    
    def on_unload(self, program) -> None:
        """Appelé au déchargement."""
        print(f"[{self.meta.name}] Déchargé")
    
    def get_hooks(self):
        """Enregistre les hooks."""
        return {
            HookType.ON_STARTUP: self.on_startup,
            HookType.PRE_EXECUTE: self.before_execute,
            HookType.POST_EXECUTE: self.after_execute,
        }
    
    def on_startup(self):
        """Hook appelé au démarrage."""
        print("[Example] Bienvenue! Ce message vient du plugin exemple.")
    
    def before_execute(self, script_name, script_path):
        """Hook appelé avant l'exécution d'un script."""
        print(f"[Example] Préparation de: {script_name}")
        return True  # Retourner False pour annuler l'exécution
    
    def after_execute(self, script_name, script_path, return_code):
        """Hook appelé après l'exécution d'un script."""
        status = "✓" if return_code == 0 else "✗"
        print(f"[Example] {script_name} terminé {status}")
    
    def get_languages(self):
        """Ajoute le support de Rust."""
        return {
            "rust": {
                "ext": ".rs",
                "cmd": ["rustc", "-o", "temp_rust_binary"],
                "run_cmd": ["./temp_rust_binary"],
                "template": '''// {name}
fn main() {{
    println!("Bonjour depuis Rust!");
}}
'''
            }
        }
    
    def get_templates(self):
        """Ajoute des templates de scripts."""
        return {
            "web-scraper": '''#!/usr/bin/env python3
"""Web scraper template"""
import requests
from bs4 import BeautifulSoup

def scrape(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    # Ajouter votre logique de scraping ici
    return soup.title.string if soup.title else "Pas de titre"

if __name__ == "__main__":
    url = input("URL à scraper: ")
    print(scrape(url))
''',
            "api-client": '''#!/usr/bin/env python3
"""API REST client template"""
import requests
import json

BASE_URL = "https://api.example.com"

def get_data(endpoint):
    response = requests.get(f"{BASE_URL}/{endpoint}")
    return response.json()

def post_data(endpoint, data):
    response = requests.post(f"{BASE_URL}/{endpoint}", json=data)
    return response.json()

if __name__ == "__main__":
    result = get_data("users")
    print(json.dumps(result, indent=2))
'''
        }
    
    def get_menu_items(self):
        """Ajoute des éléments au menu."""
        return [
            {
                "key": "x",
                "label": "Exemple Plugin Action",
                "handler": self.custom_action
            }
        ]
    
    def custom_action(self):
        """Action personnalisée du menu."""
        print("\n=== Action du Plugin Exemple ===")
        print("Ceci est une action personnalisée!")
        print("Vous pouvez ajouter n'importe quelle fonctionnalité ici.")
        input("\nAppuyez sur Entrée pour continuer...")
    
    def get_settings_schema(self):
        """Schéma des paramètres configurables."""
        return {
            "show_notifications": {
                "type": "boolean",
                "default": True,
                "description": "Afficher les notifications"
            },
            "log_executions": {
                "type": "boolean",
                "default": False,
                "description": "Logger les exécutions dans un fichier"
            }
        }
