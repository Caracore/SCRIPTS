# data/plugins/aliases/plugin.py
"""
Plugin Aliases Manager - Gestionnaire d'alias multi-shell.
Permet de créer et gérer des alias pour PowerShell, CMD, Git Bash, Bash, Zsh.
Compatible Windows et Linux.
"""
import os
import sys
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from plugins.base import Plugin, PluginMeta, HookType


class ShellType(Enum):
    """Types de shells supportés."""
    POWERSHELL = "powershell"
    CMD = "cmd"
    GIT_BASH = "git_bash"
    BASH = "bash"
    ZSH = "zsh"


class AliasManager:
    """Gestionnaire d'alias pour différents shells."""
    
    # Configuration des shells
    SHELL_CONFIG = {
        ShellType.POWERSHELL: {
            "name": "PowerShell",
            "icon": "🔷",
            "config_file": None,  # Déterminé dynamiquement
            "alias_format": 'function {name} {{ {command} $args }}',
            "simple_alias_format": 'Set-Alias -Name {name} -Value {command}',
            "comment": "# ",
            "available_on": ["nt", "posix"]
        },
        ShellType.CMD: {
            "name": "CMD (doskey)",
            "icon": "⬛",
            "config_file": None,  # Fichier batch personnalisé
            "alias_format": 'doskey {name}={command} $*',
            "comment": "REM ",
            "available_on": ["nt"]
        },
        ShellType.GIT_BASH: {
            "name": "Git Bash",
            "icon": "🟠",
            "config_file": None,  # ~/.bashrc ou ~/.bash_profile
            "alias_format": "alias {name}='{command}'",
            "comment": "# ",
            "available_on": ["nt", "posix"]
        },
        ShellType.BASH: {
            "name": "Bash",
            "icon": "🟢",
            "config_file": None,  # ~/.bashrc
            "alias_format": "alias {name}='{command}'",
            "comment": "# ",
            "available_on": ["posix"]
        },
        ShellType.ZSH: {
            "name": "Zsh",
            "icon": "🟣",
            "config_file": None,  # ~/.zshrc
            "alias_format": "alias {name}='{command}'",
            "comment": "# ",
            "available_on": ["posix"]
        }
    }
    
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self._init_shell_paths()
    
    def _init_shell_paths(self) -> None:
        """Initialise les chemins des fichiers de config pour chaque shell."""
        home = Path.home()
        
        # PowerShell profile
        if os.name == 'nt':
            # Windows PowerShell
            ps_profile = Path(os.environ.get('USERPROFILE', '')) / 'Documents' / 'WindowsPowerShell' / 'Microsoft.PowerShell_profile.ps1'
            # PowerShell Core (cross-platform)
            ps_core_profile = Path(os.environ.get('USERPROFILE', '')) / 'Documents' / 'PowerShell' / 'Microsoft.PowerShell_profile.ps1'
            self.SHELL_CONFIG[ShellType.POWERSHELL]["config_file"] = ps_core_profile if ps_core_profile.parent.exists() else ps_profile
        else:
            # Linux/Mac PowerShell Core
            self.SHELL_CONFIG[ShellType.POWERSHELL]["config_file"] = home / '.config' / 'powershell' / 'Microsoft.PowerShell_profile.ps1'
        
        # CMD - fichier batch dans notre dossier data
        self.SHELL_CONFIG[ShellType.CMD]["config_file"] = self.data_path / "cmd_aliases.bat"
        
        # Git Bash (Windows) - utilise .bashrc dans le home
        if os.name == 'nt':
            self.SHELL_CONFIG[ShellType.GIT_BASH]["config_file"] = home / '.bashrc'
        else:
            self.SHELL_CONFIG[ShellType.GIT_BASH]["config_file"] = home / '.bashrc'
        
        # Bash
        self.SHELL_CONFIG[ShellType.BASH]["config_file"] = home / '.bashrc'
        
        # Zsh
        self.SHELL_CONFIG[ShellType.ZSH]["config_file"] = home / '.zshrc'
    
    def get_available_shells(self) -> List[ShellType]:
        """Retourne les shells disponibles sur ce système."""
        available = []
        current_os = os.name
        
        for shell_type, config in self.SHELL_CONFIG.items():
            if current_os in config["available_on"]:
                available.append(shell_type)
        
        return available
    
    def get_config_path(self, shell: ShellType) -> Optional[Path]:
        """Retourne le chemin du fichier de config d'un shell."""
        return self.SHELL_CONFIG.get(shell, {}).get("config_file")
    
    def format_alias(self, shell: ShellType, name: str, command: str, is_simple: bool = False) -> str:
        """Formate un alias pour un shell donné."""
        config = self.SHELL_CONFIG.get(shell, {})
        
        # Pour PowerShell, utiliser le format simple si c'est juste un exe
        if shell == ShellType.POWERSHELL:
            if is_simple:
                return f"Set-Alias -Name {name} -Value {command}"
            else:
                # Fonction pour commande complexe
                return f"function {name} {{ {command} $args }}"
        
        elif shell == ShellType.CMD:
            return f"doskey {name}={command} $*"
        
        elif shell in [ShellType.BASH, ShellType.ZSH, ShellType.GIT_BASH]:
            # Échapper les quotes dans la commande
            escaped_cmd = command.replace("'", "'\\''")
            return f"alias {name}='{escaped_cmd}'"
        
        return ""
    
    def get_shell_header(self, shell: ShellType) -> str:
        """Retourne l'en-tête pour la section d'alias."""
        comment = self.SHELL_CONFIG.get(shell, {}).get("comment", "# ")
        return f"\n{comment}{'='*50}\n{comment}Aliases gérés par Script Manager\n{comment}{'='*50}\n"
    
    def get_shell_footer(self, shell: ShellType) -> str:
        """Retourne le pied pour la section d'alias."""
        comment = self.SHELL_CONFIG.get(shell, {}).get("comment", "# ")
        return f"{comment}{'='*50}\n{comment}Fin des aliases Script Manager\n{comment}{'='*50}\n"


class Alias:
    """Représente un alias."""
    
    def __init__(
        self,
        name: str,
        command: str,
        description: str = "",
        shells: List[str] = None,
        is_simple: bool = False,
        created_at: str = None,
        alias_id: str = None
    ):
        self.id = alias_id or name
        self.name = name
        self.command = command
        self.description = description
        self.shells = shells or []
        self.is_simple = is_simple  # True si c'est juste un exe (pour Set-Alias)
        self.created_at = created_at or datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "description": self.description,
            "shells": self.shells,
            "is_simple": self.is_simple,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alias':
        return cls(
            alias_id=data.get("id"),
            name=data.get("name", ""),
            command=data.get("command", ""),
            description=data.get("description", ""),
            shells=data.get("shells", []),
            is_simple=data.get("is_simple", False),
            created_at=data.get("created_at")
        )


class AliasesPlugin(Plugin):
    """
    Plugin de gestion des alias multi-shell.
    
    Fonctionnalités:
    - Création d'alias pour PowerShell, CMD, Git Bash, Bash, Zsh
    - Export automatique vers les fichiers de configuration
    - Alias prédéfinis courants
    - Backup des configs avant modification
    """
    
    # Alias prédéfinis suggérés
    PRESET_ALIASES = [
        {"name": "n", "command": "nvim", "description": "Ouvrir Neovim", "is_simple": True},
        {"name": "v", "command": "vim", "description": "Ouvrir Vim", "is_simple": True},
        {"name": "c", "command": "code", "description": "Ouvrir VS Code", "is_simple": True},
        {"name": "g", "command": "git", "description": "Raccourci Git", "is_simple": True},
        {"name": "py", "command": "python", "description": "Python", "is_simple": True},
        {"name": "ll", "command": "ls -la", "description": "Liste détaillée", "is_simple": False},
        {"name": "cls", "command": "clear", "description": "Effacer l'écran (Linux)", "is_simple": False},
        {"name": "...", "command": "cd ../..", "description": "Remonter 2 niveaux", "is_simple": False},
        {"name": "gs", "command": "git status", "description": "Git status", "is_simple": False},
        {"name": "ga", "command": "git add .", "description": "Git add all", "is_simple": False},
        {"name": "gc", "command": "git commit -m", "description": "Git commit", "is_simple": False},
        {"name": "gp", "command": "git push", "description": "Git push", "is_simple": False},
        {"name": "gl", "command": "git log --oneline -10", "description": "Git log court", "is_simple": False},
    ]
    
    def __init__(self):
        self._program = None
        self._data_path = None
        self._data_file = None
        self._aliases: List[Alias] = []
        self._manager: Optional[AliasManager] = None
    
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="aliases",
            version="1.0.0",
            author="Gestionnaire de Scripts",
            description="Gestionnaire d'alias multi-shell (PowerShell, CMD, Bash, Zsh)",
            homepage="",
            license="MIT"
        )
    
    def on_load(self, program: Any) -> bool:
        """Initialise le plugin."""
        self._program = program
        self._data_path = Path(program.current_path) / "data" / "plugins" / "aliases"
        self._data_path.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_path / "aliases.json"
        self._manager = AliasManager(self._data_path)
        self._load_aliases()
        return True
    
    def on_unload(self, program: Any) -> None:
        """Sauvegarde les alias."""
        self._save_aliases()
    
    def get_menu_items(self) -> List[Dict[str, Any]]:
        return [
            {"key": "X", "label": "Alias Manager         [X]", "handler": self.show_menu}
        ]
    
    def _load_aliases(self) -> None:
        """Charge les alias depuis le fichier."""
        try:
            if self._data_file and self._data_file.exists():
                with open(self._data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._aliases = [Alias.from_dict(a) for a in data.get("aliases", [])]
        except (json.JSONDecodeError, IOError):
            self._aliases = []
    
    def _save_aliases(self) -> None:
        """Sauvegarde les alias."""
        try:
            if self._data_file:
                data = {"aliases": [a.to_dict() for a in self._aliases]}
                with open(self._data_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[Aliases] Erreur sauvegarde: {e}")
    
    def _clear_screen(self) -> None:
        """Nettoie l'écran."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_menu(self) -> None:
        """Menu principal."""
        while True:
            self._clear_screen()
            available_shells = self._manager.get_available_shells()
            
            print("\n" + "=" * 55)
            print("           ⌨️  ALIAS MANAGER")
            print("=" * 55)
            
            # Shells disponibles
            print(f"\n📋 Shells disponibles sur ce système:")
            for shell in available_shells:
                config = self._manager.SHELL_CONFIG[shell]
                print(f"   {config['icon']} {config['name']}")
            
            # Alias configurés
            print(f"\n🔗 Alias configurés: {len(self._aliases)}")
            if self._aliases:
                for i, alias in enumerate(self._aliases[:8], 1):
                    shells_icons = " ".join([
                        self._manager.SHELL_CONFIG[ShellType(s)]["icon"] 
                        for s in alias.shells 
                        if s in [st.value for st in ShellType]
                    ])
                    print(f"   {i}. {alias.name} → {alias.command[:30]}{'...' if len(alias.command) > 30 else ''} [{shells_icons}]")
                if len(self._aliases) > 8:
                    print(f"   ... et {len(self._aliases) - 8} autres")
            
            print("\n" + "-" * 55)
            print("  1. ➕ Ajouter un alias")
            print("  2. 📋 Voir tous les alias")
            print("  3. ✏️  Modifier un alias")
            print("  4. 🗑️  Supprimer un alias")
            print("  5. 📦 Alias prédéfinis")
            print("  6. 🚀 Appliquer aux shells")
            print("  7. 📂 Voir les fichiers de config")
            print("  8. 💾 Backup des configs")
            print("  R. Retour")
            
            choice = input("\nChoix: ").strip().lower()
            
            if choice == "1":
                self._add_alias()
            elif choice == "2":
                self._show_all_aliases()
            elif choice == "3":
                self._edit_alias()
            elif choice == "4":
                self._delete_alias()
            elif choice == "5":
                self._preset_aliases()
            elif choice == "6":
                self._apply_to_shells()
            elif choice == "7":
                self._show_config_files()
            elif choice == "8":
                self._backup_configs()
            elif choice == "r":
                break
    
    def _add_alias(self) -> None:
        """Ajoute un nouvel alias."""
        self._clear_screen()
        print("\n" + "=" * 55)
        print("           ➕ NOUVEL ALIAS")
        print("=" * 55)
        
        # Nom de l'alias
        name = input("\nNom de l'alias (ex: n, gs, ll): ").strip()
        if not name:
            print("❌ Nom requis.")
            input("\nAppuyez sur Entrée...")
            return
        
        # Vérifier doublon
        if any(a.name == name for a in self._aliases):
            print(f"❌ L'alias '{name}' existe déjà.")
            input("\nAppuyez sur Entrée...")
            return
        
        # Commande
        command = input("Commande à exécuter (ex: nvim, git status): ").strip()
        if not command:
            print("❌ Commande requise.")
            input("\nAppuyez sur Entrée...")
            return
        
        # Description
        description = input("Description (optionnel): ").strip()
        
        # Type d'alias
        print("\nType d'alias:")
        print("  1. Simple (juste un programme: nvim, code, git)")
        print("  2. Complexe (commande avec arguments)")
        type_choice = input("Choix [1/2]: ").strip()
        is_simple = type_choice == "1"
        
        # Sélection des shells
        shells = self._select_shells()
        if not shells:
            print("❌ Aucun shell sélectionné.")
            input("\nAppuyez sur Entrée...")
            return
        
        # Créer l'alias
        alias = Alias(
            name=name,
            command=command,
            description=description,
            shells=shells,
            is_simple=is_simple
        )
        
        self._aliases.append(alias)
        self._save_aliases()
        
        print(f"\n✅ Alias '{name}' → '{command}' créé!")
        print(f"   Shells: {', '.join(shells)}")
        
        # Proposer d'appliquer maintenant
        apply = input("\n🚀 Appliquer aux shells maintenant? (o/N): ").strip().lower()
        if apply == "o":
            self._apply_alias_to_shells(alias)
        
        input("\nAppuyez sur Entrée...")
    
    def _select_shells(self) -> List[str]:
        """Permet de sélectionner les shells cibles."""
        available = self._manager.get_available_shells()
        
        print("\nShells disponibles:")
        for i, shell in enumerate(available, 1):
            config = self._manager.SHELL_CONFIG[shell]
            print(f"  {i}. {config['icon']} {config['name']}")
        print(f"  A. Tous les shells disponibles")
        
        selection = input("\nNuméros (séparés par virgule) ou A: ").strip().lower()
        
        if selection == "a":
            return [s.value for s in available]
        
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(",")]
            return [available[i].value for i in indices if 0 <= i < len(available)]
        except (ValueError, IndexError):
            return []
    
    def _show_all_aliases(self) -> None:
        """Affiche tous les alias."""
        self._clear_screen()
        print("\n" + "=" * 65)
        print("           📋 TOUS LES ALIAS")
        print("=" * 65)
        
        if not self._aliases:
            print("\n📭 Aucun alias configuré.")
            input("\nAppuyez sur Entrée...")
            return
        
        print(f"\n{'#':<4} {'Nom':<10} {'Commande':<25} {'Shells':<15} {'Type':<8}")
        print("-" * 65)
        
        for i, alias in enumerate(self._aliases, 1):
            shells_str = ", ".join([s[:3] for s in alias.shells])
            if len(shells_str) > 13:
                shells_str = shells_str[:11] + ".."
            cmd = alias.command[:23] + ".." if len(alias.command) > 23 else alias.command
            type_str = "Simple" if alias.is_simple else "Complexe"
            
            print(f"{i:<4} {alias.name:<10} {cmd:<25} {shells_str:<15} {type_str:<8}")
            
            if alias.description:
                print(f"     └─ {alias.description}")
        
        print("-" * 65)
        print(f"Total: {len(self._aliases)} alias")
        
        input("\nAppuyez sur Entrée...")
    
    def _edit_alias(self) -> None:
        """Modifie un alias existant."""
        self._clear_screen()
        print("\n" + "=" * 55)
        print("           ✏️  MODIFIER UN ALIAS")
        print("=" * 55)
        
        alias = self._select_alias()
        if not alias:
            return
        
        print(f"\nAlias actuel: {alias.name} → {alias.command}")
        print(f"Description: {alias.description or '-'}")
        print(f"Shells: {', '.join(alias.shells)}")
        print(f"Type: {'Simple' if alias.is_simple else 'Complexe'}")
        print("\n(Appuyez sur Entrée pour garder la valeur actuelle)")
        
        # Nom
        new_name = input(f"\nNouveau nom [{alias.name}]: ").strip()
        if new_name and new_name != alias.name:
            if any(a.name == new_name for a in self._aliases if a.id != alias.id):
                print(f"❌ L'alias '{new_name}' existe déjà.")
                input("\nAppuyez sur Entrée...")
                return
            alias.name = new_name
        
        # Commande
        new_command = input(f"Nouvelle commande [{alias.command}]: ").strip()
        if new_command:
            alias.command = new_command
        
        # Description
        new_desc = input(f"Nouvelle description [{alias.description or '-'}]: ").strip()
        if new_desc:
            alias.description = new_desc
        
        # Shells
        print("\nModifier les shells? (o/N): ", end="")
        if input().strip().lower() == "o":
            new_shells = self._select_shells()
            if new_shells:
                alias.shells = new_shells
        
        self._save_aliases()
        print("\n✅ Alias mis à jour!")
        input("\nAppuyez sur Entrée...")
    
    def _delete_alias(self) -> None:
        """Supprime un alias."""
        self._clear_screen()
        print("\n" + "=" * 55)
        print("           🗑️  SUPPRIMER UN ALIAS")
        print("=" * 55)
        
        alias = self._select_alias()
        if not alias:
            return
        
        confirm = input(f"\n⚠️  Supprimer '{alias.name}' → '{alias.command}'? (o/N): ").strip().lower()
        if confirm == "o":
            self._aliases.remove(alias)
            self._save_aliases()
            print("\n✅ Alias supprimé!")
            print("\n⚠️  Note: L'alias reste actif dans les shells jusqu'au rechargement.")
        else:
            print("\n❌ Suppression annulée.")
        
        input("\nAppuyez sur Entrée...")
    
    def _select_alias(self) -> Optional[Alias]:
        """Sélectionne un alias dans la liste."""
        if not self._aliases:
            print("\n📭 Aucun alias configuré.")
            input("\nAppuyez sur Entrée...")
            return None
        
        print("\nAlias disponibles:")
        for i, alias in enumerate(self._aliases, 1):
            print(f"  {i}. {alias.name} → {alias.command}")
        
        choice = input("\nNuméro (ou R pour retour): ").strip().lower()
        if choice == "r":
            return None
        
        try:
            return self._aliases[int(choice) - 1]
        except (ValueError, IndexError):
            print("❌ Choix invalide.")
            input("\nAppuyez sur Entrée...")
            return None
    
    def _preset_aliases(self) -> None:
        """Menu des alias prédéfinis."""
        self._clear_screen()
        print("\n" + "=" * 55)
        print("           📦 ALIAS PRÉDÉFINIS")
        print("=" * 55)
        
        print("\nAlias suggérés:")
        existing_names = [a.name for a in self._aliases]
        
        for i, preset in enumerate(self.PRESET_ALIASES, 1):
            exists = "✓" if preset["name"] in existing_names else " "
            type_str = "S" if preset["is_simple"] else "C"
            print(f"  {i}. [{exists}] {preset['name']:<6} → {preset['command']:<20} ({type_str}) {preset['description']}")
        
        print("\n  A. Ajouter tous les alias manquants")
        print("  R. Retour")
        
        choice = input("\nNuméro à ajouter (ou A/R): ").strip().lower()
        
        if choice == "r":
            return
        
        if choice == "a":
            # Ajouter tous les alias manquants
            added = 0
            shells = self._select_shells()
            if not shells:
                print("❌ Aucun shell sélectionné.")
                input("\nAppuyez sur Entrée...")
                return
            
            for preset in self.PRESET_ALIASES:
                if preset["name"] not in existing_names:
                    alias = Alias(
                        name=preset["name"],
                        command=preset["command"],
                        description=preset["description"],
                        shells=shells,
                        is_simple=preset["is_simple"]
                    )
                    self._aliases.append(alias)
                    added += 1
            
            self._save_aliases()
            print(f"\n✅ {added} alias ajouté(s)!")
        else:
            try:
                idx = int(choice) - 1
                preset = self.PRESET_ALIASES[idx]
                
                if preset["name"] in existing_names:
                    print(f"\n⚠️  '{preset['name']}' existe déjà.")
                else:
                    shells = self._select_shells()
                    if shells:
                        alias = Alias(
                            name=preset["name"],
                            command=preset["command"],
                            description=preset["description"],
                            shells=shells,
                            is_simple=preset["is_simple"]
                        )
                        self._aliases.append(alias)
                        self._save_aliases()
                        print(f"\n✅ Alias '{preset['name']}' ajouté!")
            except (ValueError, IndexError):
                print("❌ Choix invalide.")
        
        input("\nAppuyez sur Entrée...")
    
    def _apply_to_shells(self) -> None:
        """Applique tous les alias aux shells."""
        self._clear_screen()
        print("\n" + "=" * 55)
        print("           🚀 APPLIQUER AUX SHELLS")
        print("=" * 55)
        
        if not self._aliases:
            print("\n📭 Aucun alias à appliquer.")
            input("\nAppuyez sur Entrée...")
            return
        
        print(f"\n{len(self._aliases)} alias à appliquer.")
        print("\nCette action va modifier les fichiers de configuration")
        print("de vos shells pour y ajouter les alias.")
        
        confirm = input("\n⚠️  Continuer? (o/N): ").strip().lower()
        if confirm != "o":
            print("\n❌ Opération annulée.")
            input("\nAppuyez sur Entrée...")
            return
        
        # Backup d'abord
        print("\n💾 Création des backups...")
        self._create_backups()
        
        # Appliquer pour chaque shell
        results = {}
        available_shells = self._manager.get_available_shells()
        
        for shell in available_shells:
            shell_aliases = [a for a in self._aliases if shell.value in a.shells]
            if shell_aliases:
                success = self._write_aliases_to_shell(shell, shell_aliases)
                results[shell] = (len(shell_aliases), success)
        
        # Afficher les résultats
        print("\n" + "-" * 55)
        print("Résultats:")
        for shell, (count, success) in results.items():
            config = self._manager.SHELL_CONFIG[shell]
            status = "✅" if success else "❌"
            print(f"  {config['icon']} {config['name']}: {status} {count} alias")
        
        print("\n📝 Pour activer les alias:")
        print("  • PowerShell: Redémarrer ou taper '. $PROFILE'")
        print("  • Bash/Zsh: Taper 'source ~/.bashrc' ou 'source ~/.zshrc'")
        print("  • CMD: Les alias seront actifs au prochain démarrage")
        
        input("\nAppuyez sur Entrée...")
    
    def _apply_alias_to_shells(self, alias: Alias) -> None:
        """Applique un seul alias aux shells."""
        for shell_value in alias.shells:
            try:
                shell = ShellType(shell_value)
                self._write_aliases_to_shell(shell, [alias], append=True)
            except ValueError:
                continue
    
    def _write_aliases_to_shell(self, shell: ShellType, aliases: List[Alias], append: bool = False) -> bool:
        """Écrit les alias dans le fichier de config d'un shell."""
        config_path = self._manager.get_config_path(shell)
        if not config_path:
            return False
        
        try:
            # Créer le dossier parent si nécessaire
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Lire le contenu existant
            existing_content = ""
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    existing_content = f.read()
            
            # Générer le bloc d'alias
            header = self._manager.get_shell_header(shell)
            footer = self._manager.get_shell_footer(shell)
            
            alias_lines = []
            comment = self._manager.SHELL_CONFIG[shell].get("comment", "# ")
            
            for alias in aliases:
                if alias.description:
                    alias_lines.append(f"{comment}{alias.description}")
                formatted = self._manager.format_alias(shell, alias.name, alias.command, alias.is_simple)
                alias_lines.append(formatted)
                alias_lines.append("")
            
            alias_block = header + "\n".join(alias_lines) + footer
            
            # Supprimer l'ancien bloc s'il existe
            start_marker = "Aliases gérés par Script Manager"
            end_marker = "Fin des aliases Script Manager"
            
            if start_marker in existing_content:
                # Trouver et remplacer le bloc existant
                lines = existing_content.split("\n")
                new_lines = []
                in_block = False
                
                for line in lines:
                    if start_marker in line:
                        in_block = True
                        continue
                    if end_marker in line:
                        in_block = False
                        continue
                    if not in_block:
                        new_lines.append(line)
                
                existing_content = "\n".join(new_lines)
            
            # Écrire le nouveau contenu
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(existing_content.rstrip() + "\n" + alias_block)
            
            return True
            
        except Exception as e:
            print(f"[Aliases] Erreur pour {shell.value}: {e}")
            return False
    
    def _show_config_files(self) -> None:
        """Affiche les chemins des fichiers de config."""
        self._clear_screen()
        print("\n" + "=" * 60)
        print("           📂 FICHIERS DE CONFIGURATION")
        print("=" * 60)
        
        available = self._manager.get_available_shells()
        
        for shell in available:
            config = self._manager.SHELL_CONFIG[shell]
            path = self._manager.get_config_path(shell)
            exists = "✓" if path and path.exists() else "✗"
            
            print(f"\n{config['icon']} {config['name']}:")
            print(f"   Fichier: {path}")
            print(f"   Existe: {exists}")
        
        print("\n" + "-" * 60)
        print("  O. Ouvrir un fichier dans l'éditeur")
        print("  R. Retour")
        
        choice = input("\nChoix: ").strip().lower()
        
        if choice == "o":
            print("\nQuel fichier?")
            for i, shell in enumerate(available, 1):
                config = self._manager.SHELL_CONFIG[shell]
                print(f"  {i}. {config['name']}")
            
            idx = input("\nNuméro: ").strip()
            try:
                shell = available[int(idx) - 1]
                path = self._manager.get_config_path(shell)
                if path:
                    from launcher import DetachedLauncher
                    DetachedLauncher.open_file_detached(str(path))
                    print(f"\n✅ Ouverture de {path}")
            except (ValueError, IndexError):
                print("❌ Choix invalide.")
            
            input("\nAppuyez sur Entrée...")
    
    def _backup_configs(self) -> None:
        """Crée des backups des fichiers de config."""
        self._clear_screen()
        print("\n" + "=" * 55)
        print("           💾 BACKUP DES CONFIGURATIONS")
        print("=" * 55)
        
        print("\nCette action va sauvegarder les fichiers de config actuels.")
        confirm = input("\nContinuer? (o/N): ").strip().lower()
        
        if confirm != "o":
            return
        
        self._create_backups()
        
        input("\nAppuyez sur Entrée...")
    
    def _create_backups(self) -> None:
        """Crée les backups."""
        backup_dir = self._data_path / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        available = self._manager.get_available_shells()
        backed_up = 0
        
        for shell in available:
            path = self._manager.get_config_path(shell)
            if path and path.exists():
                try:
                    backup_path = backup_dir / f"{shell.value}_{path.name}"
                    shutil.copy2(path, backup_path)
                    backed_up += 1
                    print(f"  ✅ {self._manager.SHELL_CONFIG[shell]['name']}: {path.name}")
                except Exception as e:
                    print(f"  ❌ {shell.value}: {e}")
        
        print(f"\n💾 {backed_up} fichier(s) sauvegardé(s) dans:")
        print(f"   {backup_dir}")
