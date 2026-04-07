# auto_start_sys/plugin.py
"""
Plugin Auto-Start-Sys - Gestion du démarrage automatique système
Permet de lancer des scripts/applications au démarrage de l'ordinateur
ou conditionnellement à l'ouverture d'un programme spécifique.
"""
import os
import sys
import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import de la base plugin
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from plugins.base import Plugin, PluginMeta, HookType


class AutoStartSysPlugin(Plugin):
    """Plugin pour gérer le démarrage automatique au niveau système."""
    
    CONFIG_FILE = "auto_start_sys.json"
    MAX_STARTUP_ITEMS = 10  # Limite de sécurité
    LOOP_DETECTION_FILE = ".autostart_loop_guard"
    MAX_RAPID_STARTS = 3  # Max démarrages en 60 secondes
    RAPID_START_WINDOW = 60  # Fenêtre de détection en secondes
    
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="auto-start-sys",
            version="1.0.0",
            author="Script Manager",
            description="Démarrage automatique au boot système ou conditionnel",
            homepage="",
            license="MIT"
        )
    
    def on_load(self, program: Any) -> bool:
        """Initialise le plugin."""
        self.program = program
        self.config_path = Path(program.current_path) / "data" / self.CONFIG_FILE
        self.config = self._load_config()
        self.loop_guard_path = Path(program.current_path) / "data" / self.LOOP_DETECTION_FILE
        return True
    
    def on_unload(self, program: Any) -> None:
        """Nettoie à la fermeture."""
        pass
    
    def _load_config(self) -> Dict[str, Any]:
        """Charge la configuration du plugin."""
        default = {
            "startup_items": [],      # Items au démarrage système
            "conditional_items": [],  # Items conditionnels
            "enabled": False,         # Plugin activé globalement
            "warnings_acknowledged": False,
            "startup_history": []     # Historique pour détection boucle
        }
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    return {**default, **loaded}
        except (json.JSONDecodeError, IOError):
            pass
        return default
    
    def _save_config(self) -> None:
        """Sauvegarde la configuration."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def _get_item_hash(self, item: Dict) -> str:
        """Génère un hash unique pour un item."""
        key = f"{item.get('type', '')}{item.get('path', '')}{item.get('name', '')}"
        return hashlib.md5(key.encode()).hexdigest()[:8]
    
    def _check_loop_danger(self) -> bool:
        """
        Vérifie si on risque une boucle infinie.
        Retourne True si danger détecté.
        """
        import time
        current_time = time.time()
        
        # Nettoyer l'historique ancien
        history = self.config.get("startup_history", [])
        history = [t for t in history if current_time - t < self.RAPID_START_WINDOW]
        
        # Vérifier si trop de démarrages rapides
        if len(history) >= self.MAX_RAPID_STARTS:
            return True
        
        # Ajouter le démarrage actuel
        history.append(current_time)
        self.config["startup_history"] = history
        self._save_config()
        
        return False
    
    def _is_self_reference(self, item: Dict) -> bool:
        """Vérifie si l'item pointe vers le gestionnaire lui-même."""
        if item.get("type") == "manager":
            return True
        
        path = item.get("path", "")
        manager_path = str(Path(self.program.current_path) / "main.py")
        
        if path and os.path.normpath(path) == os.path.normpath(manager_path):
            return True
        
        return False
    
    def _validate_item(self, item: Dict) -> tuple[bool, str]:
        """
        Valide un item avant ajout.
        Retourne (valide, message_erreur).
        """
        # Vérifier limite
        total_items = len(self.config.get("startup_items", [])) + \
                      len(self.config.get("conditional_items", []))
        if total_items >= self.MAX_STARTUP_ITEMS:
            return False, f"Limite atteinte ({self.MAX_STARTUP_ITEMS} items max)"
        
        # Vérifier chemin existe
        path = item.get("path", "")
        if path and not os.path.exists(path):
            return False, f"Chemin introuvable: {path}"
        
        # Pour le gestionnaire lui-même, on autorise SEULEMENT avec --autostart
        # Le flag --autostart active la protection anti-boucle dans main.py
        if item.get("trigger") == "system" and self._is_self_reference(item):
            if not item.get("use_autostart_flag", False):
                return False, "Le gestionnaire doit utiliser le flag --autostart pour la protection anti-boucle!"
        
        return True, ""
    
    def get_menu_items(self) -> List[Dict[str, Any]]:
        """Ajoute l'entrée menu."""
        return [{
            "key": "Y",
            "label": "Auto-Start Système    [Y]",
            "handler": self.show_menu
        }]
    
    def get_hooks(self) -> Dict[HookType, Any]:
        """Enregistre les hooks."""
        return {
            HookType.ON_STARTUP: self.on_startup_hook,
            HookType.POST_EXECUTE: self.on_script_executed
        }
    
    def on_script_executed(self, script_name: str, script_path: str = None, return_code: int = 0, **kwargs) -> None:
        """
        Hook appelé après l'exécution d'un script.
        Vérifie si ce script est un déclencheur conditionnel.
        
        Args:
            script_name: Nom du script exécuté (ex: "mon-script.py")
            script_path: Chemin complet du script (optionnel)
            return_code: Code de retour du script (0 = succès)
        """
        if not self.config.get("enabled", False):
            return
        
        conditional_items = self.config.get("conditional_items", [])
        
        for item in conditional_items:
            if not item.get("active", True):
                continue
            
            if item.get("trigger_type") != "script":
                continue
            
            trigger_name = item.get("trigger_name", "")
            
            # Comparaison flexible: avec ou sans extension, sensible à la casse
            script_base = os.path.splitext(script_name)[0]
            trigger_base = os.path.splitext(trigger_name)[0]
            
            # Match si le nom correspond (avec ou sans extension)
            if script_name == trigger_name or script_base == trigger_base:
                self._launch_conditional_item(item)
    
    def on_startup_hook(self) -> None:
        """Hook appelé au démarrage du gestionnaire."""
        if not self.config.get("enabled", False):
            return
        
        # Vérifier détection de boucle
        if self._check_loop_danger():
            print("\n" + "!" * 60)
            print("⚠️  ALERTE SÉCURITÉ: Démarrages trop rapides détectés!")
            print("    Auto-Start-Sys désactivé pour éviter une boucle.")
            print("!" * 60)
            self.config["enabled"] = False
            self._save_config()
            input("\nAppuyez sur Entrée...")
            return
    
    def _launch_conditional_item(self, item: Dict) -> None:
        """
        Lance un item conditionnel (cible déclenchée).
        
        Args:
            item: Configuration de l'item à lancer
        """
        import subprocess
        
        item_type = item.get("type", "script")
        path = item.get("path", "")
        name = item.get("name", "?")
        
        print(f"\n🚀 Déclenchement conditionnel: {name}")
        
        try:
            if item_type == "manager":
                # Lancer le gestionnaire
                subprocess.Popen(
                    ["python", os.path.join(self.program.current_path, "main.py")],
                    cwd=self.program.current_path,
                    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
                )
            elif item_type == "script":
                # Lancer un script selon son extension
                ext = os.path.splitext(path)[1].lower()
                if ext == ".py":
                    subprocess.Popen(
                        ["python", path],
                        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
                    )
                elif ext == ".ps1":
                    subprocess.Popen(
                        ["powershell", "-ExecutionPolicy", "Bypass", "-File", path],
                        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
                    )
                elif ext == ".bat" or ext == ".cmd":
                    subprocess.Popen(
                        ["cmd", "/c", path],
                        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
                    )
                elif ext == ".sh":
                    subprocess.Popen(["bash", path])
                else:
                    subprocess.Popen([path], shell=True)
            elif item_type == "application":
                # Lancer une application externe
                if os.name == 'nt':
                    subprocess.Popen([path], creationflags=subprocess.CREATE_NEW_CONSOLE)
                else:
                    subprocess.Popen([path])
            
            print(f"   ✓ Lancé avec succès!")
            
        except Exception as e:
            print(f"   ❌ Erreur lors du lancement: {e}")
    
    def show_menu(self) -> None:
        """Affiche le menu principal du plugin."""
        while True:
            self.program.clear_screen()
            status = "✓ ACTIVÉ" if self.config.get("enabled") else "○ DÉSACTIVÉ"
            
            print("\n" + "=" * 55)
            print("        AUTO-START SYSTÈME - Démarrage Automatique")
            print("=" * 55)
            print(f"\nStatut: {status}")
            
            # Avertissement si activé
            if self.config.get("enabled"):
                print("\n" + "!" * 55)
                print("⚠️  ATTENTION: Le démarrage automatique est ACTIVÉ")
                print("   Les items configurés se lanceront automatiquement.")
                print("!" * 55)
            
            startup_count = len(self.config.get("startup_items", []))
            conditional_count = len(self.config.get("conditional_items", []))
            
            print(f"\n📊 Statistiques:")
            print(f"   • Items démarrage système: {startup_count}")
            print(f"   • Items conditionnels: {conditional_count}")
            print(f"   • Limite max: {self.MAX_STARTUP_ITEMS}")
            
            print("\n--- Menu ---")
            print("  1. Gérer démarrage SYSTÈME (boot PC)")
            print("  2. Gérer démarrage CONDITIONNEL")
            print("  3. Voir tous les items configurés")
            print("  4. Activer/Désactiver le plugin")
            print("  5. Réinitialiser la configuration")
            print("  R. Retour")
            
            choice = input("\nChoix: ").strip().lower()
            
            if choice == "1":
                self._manage_system_startup()
            elif choice == "2":
                self._manage_conditional_startup()
            elif choice == "3":
                self._view_all_items()
            elif choice == "4":
                self._toggle_plugin()
            elif choice == "5":
                self._reset_config()
            elif choice == "r":
                break
    
    def _show_warning(self) -> bool:
        """
        Affiche l'avertissement de sécurité.
        Retourne True si l'utilisateur accepte.
        """
        if self.config.get("warnings_acknowledged"):
            return True
        
        print("\n" + "!" * 60)
        print("⚠️  AVERTISSEMENT DE SÉCURITÉ - LISEZ ATTENTIVEMENT ⚠️")
        print("!" * 60)
        print("""
Ce plugin permet de lancer automatiquement des programmes
au démarrage de votre ordinateur ou de façon conditionnelle.

RISQUES POTENTIELS:
  • Boucle infinie si mal configuré
  • Ralentissement du démarrage système
  • Exécution de scripts non voulus
  • Consommation de ressources

PROTECTIONS EN PLACE:
  ✓ Limite de {max_items} items maximum
  ✓ Détection de boucles (>{max_rapid} démarrages/{window}s)
  ✓ Blocage de l'auto-référence au gestionnaire
  ✓ Validation des chemins avant ajout
        """.format(
            max_items=self.MAX_STARTUP_ITEMS,
            max_rapid=self.MAX_RAPID_STARTS,
            window=self.RAPID_START_WINDOW
        ))
        print("!" * 60)
        
        confirm = input("\nTapez 'JACCEPTE' pour continuer: ").strip()
        if confirm == "JACCEPTE":
            self.config["warnings_acknowledged"] = True
            self._save_config()
            return True
        
        print("Opération annulée.")
        return False
    
    def _toggle_plugin(self) -> None:
        """Active ou désactive le plugin."""
        if not self.config.get("enabled"):
            if not self._show_warning():
                input("\nAppuyez sur Entrée...")
                return
            
            self.config["enabled"] = True
            print("\n✓ Auto-Start-Sys ACTIVÉ")
        else:
            self.config["enabled"] = False
            print("\n○ Auto-Start-Sys DÉSACTIVÉ")
        
        self._save_config()
        input("\nAppuyez sur Entrée...")
    
    def _manage_system_startup(self) -> None:
        """Gère les items au démarrage système."""
        while True:
            self.program.clear_screen()
            print("\n--- Démarrage SYSTÈME (au boot du PC) ---\n")
            
            items = self.config.get("startup_items", [])
            
            if items:
                for i, item in enumerate(items, 1):
                    status = "✓" if item.get("active", True) else "○"
                    item_type = item.get("type", "script")
                    name = item.get("name", "Sans nom")
                    print(f"  {i}. [{status}] [{item_type.upper()}] {name}")
                    if item.get("path"):
                        print(f"      → {item['path']}")
            else:
                print("  Aucun item configuré.")
            
            print("\n  A. Ajouter un item")
            print("  S. Supprimer un item")
            print("  T. Activer/Désactiver un item")
            print("  I. Installer dans le système")
            print("  U. Désinstaller du système")
            print("  R. Retour")
            
            choice = input("\nChoix: ").strip().lower()
            
            if choice == "a":
                self._add_startup_item("system")
            elif choice == "s":
                self._remove_item("startup_items")
            elif choice == "t":
                self._toggle_item("startup_items")
            elif choice == "i":
                self._install_system_startup()
            elif choice == "u":
                self._uninstall_system_startup()
            elif choice == "r":
                break
    
    def _manage_conditional_startup(self) -> None:
        """Gère les items conditionnels."""
        while True:
            self.program.clear_screen()
            print("\n--- Démarrage CONDITIONNEL ---")
            print("(Lance une CIBLE quand un DÉCLENCHEUR est exécuté)\n")
            print("📖 Aide:")
            print("   • CIBLE = l'app/script à lancer automatiquement")
            print("   • DÉCLENCHEUR = le script qui déclenche le lancement")
            print("   • Nom du script = nom exact avec extension (ex: mon-script.py)\n")
            
            items = self.config.get("conditional_items", [])
            
            if items:
                for i, item in enumerate(items, 1):
                    status = "✓" if item.get("active", True) else "○"
                    item_type = item.get("type", "script")
                    name = item.get("name", "Sans nom")
                    trigger = item.get("trigger_name", "?")
                    trigger_type = item.get("trigger_type", "?")
                    print(f"  {i}. [{status}] [{item_type.upper()}] {name}")
                    print(f"      └─ Déclencheur ({trigger_type}): {trigger}")
            else:
                print("  Aucun item conditionnel configuré.")
            
            print("\n  A. Ajouter un déclencheur")
            print("  S. Supprimer un item")
            print("  T. Activer/Désactiver un item")
            print("  R. Retour")
            
            choice = input("\nChoix: ").strip().lower()
            
            if choice == "a":
                self._add_startup_item("conditional")
            elif choice == "s":
                self._remove_item("conditional_items")
            elif choice == "t":
                self._toggle_item("conditional_items")
            elif choice == "r":
                break
    
    def _add_startup_item(self, trigger_type: str) -> None:
        """Ajoute un nouvel item de démarrage."""
        if not self._show_warning():
            input("\nAppuyez sur Entrée...")
            return
        
        print("\n--- Ajouter un item ---")
        print("  1. Script du gestionnaire")
        print("  2. Application externe")
        print("  3. Le gestionnaire de scripts lui-même")
        
        type_choice = input("\nType: ").strip()
        
        item = {"active": True, "trigger": trigger_type}
        
        if type_choice == "1":
            # Script du gestionnaire
            from script import Script
            scripts = Script.list_scripts(self.program.scripts_path)
            if not scripts:
                print("Aucun script disponible.")
                input("\nAppuyez sur Entrée...")
                return
            
            print("\nScripts disponibles:")
            for i, s in enumerate(scripts, 1):
                print(f"  {i}. {s}")
            
            idx = input("\nNuméro du script: ").strip()
            try:
                script = scripts[int(idx) - 1]
                item["type"] = "script"
                item["name"] = script
                item["path"] = os.path.join(self.program.scripts_path, script)
            except (ValueError, IndexError):
                print("Choix invalide.")
                input("\nAppuyez sur Entrée...")
                return
        
        elif type_choice == "2":
            # Application externe
            app_path = input("Chemin de l'application: ").strip()
            if not app_path:
                return
            item["type"] = "application"
            item["name"] = os.path.basename(app_path)
            item["path"] = app_path
        
        elif type_choice == "3":
            # Le gestionnaire lui-même
            item["type"] = "manager"
            item["name"] = "Gestionnaire de Scripts"
            item["path"] = str(Path(self.program.current_path) / "main.py")
            item["use_autostart_flag"] = True  # Activer la protection anti-boucle
        
        else:
            print("Choix invalide.")
            input("\nAppuyez sur Entrée...")
            return
        
        # Si conditionnel, demander le déclencheur
        if trigger_type == "conditional":
            print("\n--- Déclencheur (ce qui déclenche le lancement) ---")
            print("  1. Ouverture d'une application (process)")
            print("  2. Exécution d'un script du gestionnaire")
            
            trig_choice = input("\nType de déclencheur: ").strip()
            
            if trig_choice == "1":
                print("\n💡 Entrez le nom du processus (ex: chrome.exe, notepad.exe)")
                print("   Note: Cette fonctionnalité nécessite un monitoring actif.")
                trigger_app = input("Nom du processus déclencheur: ").strip()
                item["trigger_type"] = "process"
                item["trigger_name"] = trigger_app
            elif trig_choice == "2":
                print("\n💡 Entrez le nom EXACT du script avec son extension")
                print("   Exemple: mon-script.py, backup.ps1, test.bat")
                print("   (Ce sont les scripts dans data/scripts/)")
                trigger_script = input("Nom du script déclencheur: ").strip()
                item["trigger_type"] = "script"
                item["trigger_name"] = trigger_script
            else:
                print("Choix invalide.")
                input("\nAppuyez sur Entrée...")
                return
        
        # Validation
        valid, error = self._validate_item(item)
        if not valid:
            print(f"\n❌ ERREUR: {error}")
            input("\nAppuyez sur Entrée...")
            return
        
        # Avertissement spécial pour le gestionnaire au boot système
        if item.get("type") == "manager" and trigger_type == "system":
            print("\n" + "=" * 55)
            print("  ℹ️  GESTIONNAIRE AU DÉMARRAGE SYSTÈME")
            print("=" * 55)
            print("""
Le gestionnaire sera lancé avec le flag --autostart qui active
une protection anti-boucle automatique:

  ✓ Détection si déjà en cours d'exécution
  ✓ Fermeture automatique si lancé 2 fois
  ✓ Fichier de verrouillage avec timeout de 30s

Cela permet de lancer le gestionnaire au boot en toute sécurité.
""")
            confirm = input("Continuer? (o/n): ").strip().lower()
            if confirm != "o":
                return
        
        # Ajouter l'item
        item["id"] = self._get_item_hash(item)
        
        if trigger_type == "system":
            self.config.setdefault("startup_items", []).append(item)
        else:
            self.config.setdefault("conditional_items", []).append(item)
        
        self._save_config()
        print(f"\n✓ Item '{item['name']}' ajouté avec succès!")
        input("\nAppuyez sur Entrée...")
    
    def _remove_item(self, list_key: str) -> None:
        """Supprime un item."""
        items = self.config.get(list_key, [])
        if not items:
            print("Aucun item à supprimer.")
            input("\nAppuyez sur Entrée...")
            return
        
        idx = input("Numéro de l'item à supprimer: ").strip()
        try:
            removed = items.pop(int(idx) - 1)
            self.config[list_key] = items
            self._save_config()
            print(f"✓ Item '{removed.get('name', '?')}' supprimé.")
        except (ValueError, IndexError):
            print("Choix invalide.")
        
        input("\nAppuyez sur Entrée...")
    
    def _toggle_item(self, list_key: str) -> None:
        """Active/désactive un item."""
        items = self.config.get(list_key, [])
        if not items:
            print("Aucun item à modifier.")
            input("\nAppuyez sur Entrée...")
            return
        
        idx = input("Numéro de l'item: ").strip()
        try:
            item = items[int(idx) - 1]
            item["active"] = not item.get("active", True)
            self._save_config()
            status = "activé" if item["active"] else "désactivé"
            print(f"✓ Item '{item.get('name', '?')}' {status}.")
        except (ValueError, IndexError):
            print("Choix invalide.")
        
        input("\nAppuyez sur Entrée...")
    
    def _view_all_items(self) -> None:
        """Affiche tous les items configurés."""
        self.program.clear_screen()
        print("\n" + "=" * 55)
        print("           TOUS LES ITEMS CONFIGURÉS")
        print("=" * 55)
        
        startup = self.config.get("startup_items", [])
        conditional = self.config.get("conditional_items", [])
        
        print(f"\n📌 DÉMARRAGE SYSTÈME ({len(startup)} items):")
        if startup:
            for item in startup:
                status = "✓" if item.get("active", True) else "○"
                print(f"  [{status}] {item.get('name', '?')} ({item.get('type', '?')})")
        else:
            print("  (aucun)")
        
        print(f"\n🔗 CONDITIONNELS ({len(conditional)} items):")
        if conditional:
            for item in conditional:
                status = "✓" if item.get("active", True) else "○"
                trigger = item.get("trigger_name", "?")
                print(f"  [{status}] {item.get('name', '?')} → quand {trigger}")
        else:
            print("  (aucun)")
        
        input("\nAppuyez sur Entrée...")
    
    def _reset_config(self) -> None:
        """Réinitialise la configuration."""
        print("\n⚠️  Cette action va supprimer TOUS les items configurés!")
        confirm = input("Tapez 'RESET' pour confirmer: ").strip()
        
        if confirm == "RESET":
            self.config = {
                "startup_items": [],
                "conditional_items": [],
                "enabled": False,
                "warnings_acknowledged": False,
                "startup_history": []
            }
            self._save_config()
            self._uninstall_system_startup()
            print("\n✓ Configuration réinitialisée.")
        else:
            print("Annulé.")
        
        input("\nAppuyez sur Entrée...")
    
    def _install_system_startup(self) -> None:
        """Installe les items dans le démarrage système."""
        items = [i for i in self.config.get("startup_items", []) if i.get("active", True)]
        
        if not items:
            print("Aucun item actif à installer.")
            input("\nAppuyez sur Entrée...")
            return
        
        if not self._show_warning():
            input("\nAppuyez sur Entrée...")
            return
        
        print("\n--- Installation dans le démarrage système ---")
        
        if os.name == "nt":
            # Windows: utiliser le dossier Startup
            startup_folder = os.path.join(
                os.environ.get("APPDATA", ""),
                "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
            )
            
            for item in items:
                self._create_windows_shortcut(item, startup_folder)
            
            print(f"\n✓ {len(items)} item(s) installé(s) dans:")
            print(f"  {startup_folder}")
        
        else:
            # Linux: créer un fichier .desktop dans autostart
            autostart_dir = os.path.expanduser("~/.config/autostart")
            os.makedirs(autostart_dir, exist_ok=True)
            
            for item in items:
                self._create_linux_desktop_entry(item, autostart_dir)
            
            print(f"\n✓ {len(items)} item(s) installé(s) dans:")
            print(f"  {autostart_dir}")
        
        input("\nAppuyez sur Entrée...")
    
    def _create_windows_shortcut(self, item: Dict, folder: str) -> None:
        """Crée un raccourci Windows."""
        try:
            import subprocess
            
            name = f"AutoStart_{item.get('id', 'item')}"
            shortcut_path = os.path.join(folder, f"{name}.bat")
            
            path = item.get("path", "")
            item_type = item.get("type", "script")
            
            if item_type == "manager":
                # IMPORTANT: Utiliser --autostart pour activer la protection anti-boucle
                cmd = f'@echo off\ncd /d "{self.program.current_path}"\npython main.py --autostart'
            elif item_type == "script":
                # Déterminer la commande selon l'extension
                ext = os.path.splitext(path)[1].lower()
                if ext == ".py":
                    cmd = f'@echo off\npython "{path}"'
                elif ext == ".ps1":
                    cmd = f'@echo off\npowershell -ExecutionPolicy Bypass -File "{path}"'
                elif ext == ".bat":
                    cmd = f'@echo off\ncall "{path}"'
                else:
                    cmd = f'@echo off\n"{path}"'
            else:
                cmd = f'@echo off\nstart "" "{path}"'
            
            with open(shortcut_path, "w", encoding="utf-8") as f:
                f.write(cmd)
            
            print(f"  ✓ Créé: {shortcut_path}")
            
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
    
    def _create_linux_desktop_entry(self, item: Dict, folder: str) -> None:
        """Crée une entrée .desktop pour Linux."""
        try:
            name = f"autostart_{item.get('id', 'item')}"
            desktop_path = os.path.join(folder, f"{name}.desktop")
            
            path = item.get("path", "")
            item_type = item.get("type", "script")
            
            if item_type == "manager":
                # IMPORTANT: Utiliser --autostart pour activer la protection anti-boucle
                exec_cmd = f"python3 {self.program.current_path}/main.py --autostart"
            elif item_type == "script":
                ext = os.path.splitext(path)[1].lower()
                if ext == ".py":
                    exec_cmd = f"python3 {path}"
                elif ext == ".sh":
                    exec_cmd = f"bash {path}"
                else:
                    exec_cmd = path
            else:
                exec_cmd = path
            
            # Déterminer le terminal à utiliser
            terminal_cmd = self._get_linux_terminal()
            
            content = f"""[Desktop Entry]
Type=Application
Name={item.get('name', 'AutoStart Item')}
Exec={terminal_cmd} -e "bash -c '{exec_cmd}; exec bash'"
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=Auto-Start-Sys Plugin
Terminal=false
"""
            
            with open(desktop_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            os.chmod(desktop_path, 0o755)
            print(f"  ✓ Créé: {desktop_path}")
            
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
    
    def _get_linux_terminal(self) -> str:
        """Détecte et retourne le terminal disponible sur Linux."""
        import shutil
        
        # Liste des terminaux courants, dans l'ordre de préférence
        terminals = [
            "gnome-terminal",
            "konsole",
            "xfce4-terminal", 
            "mate-terminal",
            "lxterminal",
            "terminator",
            "tilix",
            "xterm",
            "x-terminal-emulator"
        ]
        
        for term in terminals:
            if shutil.which(term):
                return term
        
        # Fallback par défaut
        return "xterm"
    
    def _uninstall_system_startup(self) -> None:
        """Désinstalle les items du démarrage système."""
        print("\n--- Désinstallation du démarrage système ---")
        
        removed = 0
        
        if os.name == "nt":
            startup_folder = os.path.join(
                os.environ.get("APPDATA", ""),
                "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
            )
            
            for f in os.listdir(startup_folder):
                if f.startswith("AutoStart_") and f.endswith(".bat"):
                    try:
                        os.remove(os.path.join(startup_folder, f))
                        print(f"  ✓ Supprimé: {f}")
                        removed += 1
                    except Exception as e:
                        print(f"  ❌ Erreur: {e}")
        
        else:
            autostart_dir = os.path.expanduser("~/.config/autostart")
            if os.path.exists(autostart_dir):
                for f in os.listdir(autostart_dir):
                    if f.startswith("autostart_") and f.endswith(".desktop"):
                        try:
                            os.remove(os.path.join(autostart_dir, f))
                            print(f"  ✓ Supprimé: {f}")
                            removed += 1
                        except Exception as e:
                            print(f"  ❌ Erreur: {e}")
        
        if removed == 0:
            print("  Aucun item à désinstaller.")
        else:
            print(f"\n✓ {removed} item(s) désinstallé(s).")
        
        input("\nAppuyez sur Entrée...")


# Point d'entrée pour le chargement du plugin
def get_plugin():
    return AutoStartSysPlugin()
