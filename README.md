# Gestionnaire de Scripts

Un gestionnaire de scripts CLI extensible avec système de plugins.

## Installation

### Windows
```batch
# Double-cliquez sur install.bat
# OU
python install.py
```

### Linux / macOS
```bash
chmod +x install.sh
./install.sh
# OU
python3 install.py
```

Après installation, lancez avec : `script-manager`

## Fonctionnalités

- **Exécution de scripts** : Python, Bash, PowerShell, JavaScript, Lua, Batch
- **Modes d'exécution** : Normal, détaché (arrière-plan), nouveau terminal
- **Auto-start** : Scripts lancés automatiquement au démarrage
- **Plugins** : Système extensible par la communauté
- **Thèmes** : ASCII art et dashboard personnalisables

## Structure

```
SCRIPTS/
├── main.py           # Point d'entrée
├── program.py        # Classe principale
├── script.py         # Gestion des scripts
├── launcher.py       # Lancement détaché
├── themes.py         # Personnalisation ASCII
├── install.py        # Installateur Python
├── install.bat       # Installateur Windows
├── install.sh        # Installateur Linux
├── plugins/          # Framework de plugins
└── data/
    ├── scripts/      # Vos scripts
    ├── plugins/      # Plugins installés
    └── ascii_arts/   # ASCII personnalisés
```

## Plugins

Voir [Guide de création de plugins](data/plugins/README.md)

## Personnalisation

Menu **8. Personnalisation [T]** pour :
- Changer l'ASCII art du dashboard (10 thèmes inclus)
- Ajouter vos propres ASCII arts
- Personnaliser le message de bienvenue

