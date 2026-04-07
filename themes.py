# themes.py
"""
Gestion des thèmes et ASCII art personnalisables.
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional


# ASCII Arts par défaut disponibles
DEFAULT_ASCII_ARTS = {
    "default": r'''
      _____ _____ ______ ___________ _____ 
     /  ___/  __ \| ___ \_   _| ___ \_   _|
     \ `--.| /  \/| |_/ / | | | |_/ / | |  
      `--. \ |    |    /  | | |  __/  | |  
     /\__/ / \__/\| |\ \ _| |_| |     | |  
     \____/ \____/\_| \_|\___/\_|     \_/  
''',
    
    "minimal": r'''
    ╔═╗╔═╗╦═╗╦╔═╗╔╦╗  ╔╦╗╔═╗╔╗╔╔═╗╔═╗╔═╗╦═╗
    ╚═╗║  ╠╦╝║╠═╝ ║   ║║║╠═╣║║║╠═╣║ ╦║╣ ╠╦╝
    ╚═╝╚═╝╩╚═╩╩   ╩   ╩ ╩╩ ╩╝╚╝╩ ╩╚═╝╚═╝╩╚═
''',
    
    "box": r'''
    ┌─────────────────────────────────────┐
    │   ★ GESTIONNAIRE DE SCRIPTS ★      │
    │        ═══════════════════          │
    │    Automatisation & Productivité    │
    └─────────────────────────────────────┘
''',
    
    "retro": r'''
    ░██████╗░█████╗░██████╗░██╗██████╗░████████╗
    ██╔════╝██╔══██╗██╔══██╗██║██╔══██╗╚══██╔══╝
    ╚█████╗░██║░░╚═╝██████╔╝██║██████╔╝░░░██║░░░
    ░╚═══██╗██║░░██╗██╔══██╗██║██╔═══╝░░░░██║░░░
    ██████╔╝╚█████╔╝██║░░██║██║██║░░░░░░░░██║░░░
    ╚═════╝░░╚════╝░╚═╝░░╚═╝╚═╝╚═╝░░░░░░░░╚═╝░░░
''',
    
    "wave": r'''
           ~^~^~^~^~^~^~^~^~^~^~^~^~^~^~
        ≈≈≈  SCRIPT MANAGER v1.0  ≈≈≈
           ~^~^~^~^~^~^~^~^~^~^~^~^~^~^~
''',
    
    "code": r'''
    ╭──────────────────────────────────────╮
    │  < SCRIPT MANAGER />                 │
    │  ════════════════════                │
    │  function manage() { ... }           │
    ╰──────────────────────────────────────╯
''',
    
    "cyber": r'''
    ╔══════════════════════════════════════╗
    ║ ▄▄▄▄▄ ▄▄▄▄▄ ▄▄▄▄  ▄▄▄ ▄▄▄▄  ▄▄▄▄▄ ║
    ║ █▀▀▀▀ █     █   █  █  █   █   █   ║
    ║ ▀▀▀▀█ █     ████   █  ████    █   ║
    ║ ▄▄▄▄█ ▀▄▄▄▄ █  ▀▄ ▄█▄ █      ▄█▄  ║
    ╚══════════════════════════════════════╝
''',
    
    "simple": r'''
    ─────────────────────────────
       GESTIONNAIRE DE SCRIPTS
    ─────────────────────────────
''',
    
    "stars": r'''
    ★ ═══════════════════════════════ ★
    ║   ✦ Script Manager ✦           ║
    ║   ════════════════             ║
    ║   Gérez vos scripts facilement ║
    ★ ═══════════════════════════════ ★
''',
    
    "none": ""
}


class ThemeManager:
    """Gère les thèmes et l'ASCII art du dashboard."""
    
    CONFIG_FILE = "themes.json"
    CUSTOM_ASCII_DIR = "ascii_arts"
    
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.config_path = self.data_path / self.CONFIG_FILE
        self.custom_ascii_path = self.data_path / self.CUSTOM_ASCII_DIR
        
        # Créer le dossier pour les ASCII personnalisés
        self.custom_ascii_path.mkdir(parents=True, exist_ok=True)
        
        # Charger la configuration
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Charge la configuration des thèmes."""
        default = {
            "current_ascii": "default",
            "show_info": True,
            "custom_welcome": "",
            "colors_enabled": False
        }
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return {**default, **json.load(f)}
        except (json.JSONDecodeError, IOError):
            pass
        return default
    
    def _save_config(self) -> None:
        """Sauvegarde la configuration."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def get_available_ascii_arts(self) -> Dict[str, str]:
        """Retourne tous les ASCII arts disponibles (défaut + personnalisés)."""
        arts = dict(DEFAULT_ASCII_ARTS)
        
        # Charger les ASCII personnalisés
        if self.custom_ascii_path.exists():
            for file in self.custom_ascii_path.glob("*.txt"):
                name = file.stem
                try:
                    arts[f"custom:{name}"] = file.read_text(encoding="utf-8")
                except IOError:
                    pass
        
        return arts
    
    def get_current_ascii(self) -> str:
        """Retourne l'ASCII art actuel."""
        current = self.config.get("current_ascii", "default")
        arts = self.get_available_ascii_arts()
        return arts.get(current, arts.get("default", ""))
    
    def set_ascii(self, name: str) -> bool:
        """Définit l'ASCII art à utiliser."""
        arts = self.get_available_ascii_arts()
        if name in arts:
            self.config["current_ascii"] = name
            self._save_config()
            return True
        return False
    
    def add_custom_ascii(self, name: str, content: str) -> bool:
        """Ajoute un ASCII art personnalisé."""
        if not name or not content:
            return False
        
        # Nettoyer le nom
        safe_name = "".join(c for c in name if c.isalnum() or c in "-_")
        
        file_path = self.custom_ascii_path / f"{safe_name}.txt"
        try:
            file_path.write_text(content, encoding="utf-8")
            return True
        except IOError:
            return False
    
    def remove_custom_ascii(self, name: str) -> bool:
        """Supprime un ASCII art personnalisé."""
        if not name.startswith("custom:"):
            return False
        
        real_name = name[7:]  # Enlever "custom:"
        file_path = self.custom_ascii_path / f"{real_name}.txt"
        
        if file_path.exists():
            file_path.unlink()
            # Si c'était l'ASCII actuel, revenir au défaut
            if self.config.get("current_ascii") == name:
                self.config["current_ascii"] = "default"
                self._save_config()
            return True
        return False
    
    def set_custom_welcome(self, message: str) -> None:
        """Définit un message de bienvenue personnalisé."""
        self.config["custom_welcome"] = message
        self._save_config()
    
    def get_custom_welcome(self) -> str:
        """Retourne le message de bienvenue personnalisé."""
        return self.config.get("custom_welcome", "")
    
    def preview_ascii(self, name: str) -> Optional[str]:
        """Prévisualise un ASCII art."""
        arts = self.get_available_ascii_arts()
        return arts.get(name)


def manage_themes(program):
    """Interface de gestion des thèmes."""
    from program import Program
    
    theme_manager = ThemeManager(os.path.join(program.current_path, "data"))
    
    while True:
        Program.clear_screen()
        print("\n" + "=" * 50)
        print("         PERSONNALISATION DU DASHBOARD")
        print("=" * 50)
        
        # Afficher l'ASCII actuel
        current = theme_manager.config.get("current_ascii", "default")
        print(f"\nASCII actuel: {current}")
        print("-" * 40)
        print(theme_manager.get_current_ascii())
        print("-" * 40)
        
        arts = theme_manager.get_available_ascii_arts()
        
        print("\n  1. Changer l'ASCII art")
        print("  2. Prévisualiser un ASCII")
        print("  3. Ajouter un ASCII personnalisé")
        print("  4. Supprimer un ASCII personnalisé")
        print("  5. Message de bienvenue personnalisé")
        print("  R. Retour")
        
        choice = input("\nChoix: ").strip().lower()
        
        if choice == "1":
            print("\nASCII arts disponibles:")
            art_names = list(arts.keys())
            for i, name in enumerate(art_names, 1):
                marker = "▶" if name == current else " "
                print(f"  {marker} {i}. {name}")
            
            idx = input("\nNuméro de l'ASCII à utiliser: ").strip()
            try:
                selected = art_names[int(idx) - 1]
                if theme_manager.set_ascii(selected):
                    print(f"\nASCII changé pour: {selected}")
                else:
                    print("Erreur lors du changement.")
            except (ValueError, IndexError):
                print("Choix invalide.")
            input("\nAppuyez sur Entrée...")
        
        elif choice == "2":
            print("\nASCII arts disponibles:")
            art_names = list(arts.keys())
            for i, name in enumerate(art_names, 1):
                print(f"  {i}. {name}")
            
            idx = input("\nNuméro à prévisualiser: ").strip()
            try:
                selected = art_names[int(idx) - 1]
                preview = theme_manager.preview_ascii(selected)
                if preview:
                    print(f"\n--- {selected} ---")
                    print(preview)
                    print("-" * 40)
            except (ValueError, IndexError):
                print("Choix invalide.")
            input("\nAppuyez sur Entrée...")
        
        elif choice == "3":
            print("\n--- Ajouter un ASCII personnalisé ---")
            name = input("Nom de l'ASCII (sans espaces): ").strip()
            if not name:
                print("Nom invalide.")
                input("\nAppuyez sur Entrée...")
                continue
            
            print("\nEntrez votre ASCII art (tapez 'FIN' sur une ligne seule pour terminer):")
            lines = []
            while True:
                line = input()
                if line.strip().upper() == "FIN":
                    break
                lines.append(line)
            
            content = "\n".join(lines)
            if theme_manager.add_custom_ascii(name, content):
                print(f"\nASCII '{name}' ajouté avec succès!")
            else:
                print("Erreur lors de l'ajout.")
            input("\nAppuyez sur Entrée...")
        
        elif choice == "4":
            custom_arts = [n for n in arts.keys() if n.startswith("custom:")]
            if not custom_arts:
                print("\nAucun ASCII personnalisé trouvé.")
            else:
                print("\nASCII personnalisés:")
                for i, name in enumerate(custom_arts, 1):
                    print(f"  {i}. {name}")
                
                idx = input("\nNuméro à supprimer: ").strip()
                try:
                    selected = custom_arts[int(idx) - 1]
                    if theme_manager.remove_custom_ascii(selected):
                        print(f"\n'{selected}' supprimé.")
                    else:
                        print("Erreur lors de la suppression.")
                except (ValueError, IndexError):
                    print("Choix invalide.")
            input("\nAppuyez sur Entrée...")
        
        elif choice == "5":
            current_msg = theme_manager.get_custom_welcome()
            print(f"\nMessage actuel: {current_msg or '(aucun)'}")
            new_msg = input("Nouveau message (vide pour effacer): ").strip()
            theme_manager.set_custom_welcome(new_msg)
            print("Message mis à jour!")
            input("\nAppuyez sur Entrée...")
        
        elif choice == "r":
            break
