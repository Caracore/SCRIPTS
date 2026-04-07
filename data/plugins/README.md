# Guide de Création de Plugins

Ce guide explique comment créer des plugins pour le Gestionnaire de Scripts.

## Structure d'un Plugin

Un plugin peut être :
- **Un fichier unique** : `mon_plugin.py`
- **Un module** : `mon_plugin/plugin.py` ou `mon_plugin/__init__.py`

Placez vos plugins dans : `data/plugins/` ou `data/plugins/community/`

## Exemple Minimal

```python
from plugins.base import Plugin, PluginMeta, HookType

class MonPlugin(Plugin):
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="mon-plugin",
            version="1.0.0",
            author="VotreNom",
            description="Description de mon plugin"
        )
    
    def on_load(self, program) -> bool:
        print("Plugin chargé!")
        return True  # True = succès
```

## Hooks Disponibles

| Hook | Description | Arguments |
|------|-------------|-----------|
| `ON_STARTUP` | Au démarrage | - |
| `ON_SHUTDOWN` | À la fermeture | - |
| `ON_MENU_DISPLAY` | Avant affichage menu | - |
| `ON_MENU_CHOICE` | Après choix menu | `choice` |
| `PRE_EXECUTE` | Avant exécution script | `script_name`, `script_path` |
| `POST_EXECUTE` | Après exécution | `script_name`, `script_path`, `return_code` |
| `PRE_CREATE` | Avant création script | `script_name` |
| `POST_CREATE` | Après création | `script_path` |
| `PRE_EDIT` | Avant édition | `script_path` |
| `POST_EDIT` | Après édition | `script_path` |

### Utilisation des Hooks

```python
def get_hooks(self):
    return {
        HookType.ON_STARTUP: self.au_demarrage,
        HookType.PRE_EXECUTE: self.avant_execution,
    }

def au_demarrage(self):
    print("Démarrage!")

def avant_execution(self, script_name, script_path):
    print(f"Exécution de {script_name}")
    return True  # False pour annuler
```

## Ajouter des Langages

```python
def get_languages(self):
    return {
        "rust": {
            "ext": ".rs",
            "cmd": ["rustc", "-o", "output"],
            "template": "fn main() { println!(\"Hello!\"); }"
        },
        "go": {
            "ext": ".go",
            "cmd": ["go", "run"],
            "template": "package main\nimport \"fmt\"\nfunc main() { fmt.Println(\"Hello!\") }"
        }
    }
```

## Ajouter des Éléments au Menu

```python
def get_menu_items(self):
    return [
        {
            "key": "m",  # Touche pour activer
            "label": "Mon Action",
            "handler": self.mon_action
        }
    ]

def mon_action(self):
    print("Action exécutée!")
    input("Entrée pour continuer...")
```

## Ajouter des Templates

```python
def get_templates(self):
    return {
        "web-api": '''#!/usr/bin/env python3
from flask import Flask
app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World!"

if __name__ == "__main__":
    app.run()
'''
    }
```

## Paramètres du Plugin

```python
def get_settings_schema(self):
    return {
        "api_key": {
            "type": "string",
            "default": "",
            "description": "Clé API"
        },
        "debug_mode": {
            "type": "boolean",
            "default": False,
            "description": "Mode debug"
        }
    }
```

## Bonnes Pratiques

1. **Toujours retourner `True`** dans `on_load()` si le chargement réussit
2. **Gérer les erreurs** gracieusement pour ne pas bloquer le gestionnaire
3. **Documenter** les dépendances dans `PluginMeta.dependencies`
4. **Tester** votre plugin avant de le partager

## Publication

Pour partager votre plugin avec la communauté :
1. Créez un dépôt GitHub
2. Ajoutez un `README.md` avec les instructions
3. Spécifiez la licence dans `PluginMeta.license`
