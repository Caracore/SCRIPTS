# plugins/monitoring/plugin.py
"""
Plugin Monitoring - Surveillance légère des applications et processus.
Permet de surveiller si des applications sont en cours d'exécution.
"""
import os
import sys
import json
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from plugins.base import Plugin, PluginMeta, HookType


class MonitoringPlugin(Plugin):
    """Plugin de monitoring léger pour les applications."""
    
    CONFIG_FILE = "monitoring.json"
    CHECK_INTERVAL = 10  # Secondes entre chaque vérification
    
    def __init__(self):
        self.program = None
        self.config_path = None
        self.config: Dict[str, Any] = {}
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        self._process_cache: Dict[str, bool] = {}
        self._last_check = 0
    
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="monitoring",
            version="1.0.0",
            author="Script Manager",
            description="Monitoring léger des applications - surveillance CPU/RAM minimale",
            homepage="",
            license="MIT"
        )
    
    def on_load(self, program: Any) -> bool:
        """Initialise le plugin."""
        self.program = program
        self.config_path = Path(program.current_path) / "data" / self.CONFIG_FILE
        self.config = self._load_config()
        
        # Démarrer le monitoring si activé
        if self.config.get("auto_start", False):
            self._start_background_monitor()
        
        return True
    
    def on_unload(self, program: Any) -> None:
        """Arrête le monitoring à la fermeture."""
        self._stop_background_monitor()
        self._save_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Charge la configuration."""
        default = {
            "monitored_apps": [],  # Liste des apps à surveiller
            "auto_start": False,   # Démarrer le monitoring automatiquement
            "check_interval": 10,  # Intervalle en secondes
            "notify_on_change": True,  # Notifier quand une app démarre/s'arrête
            "history": [],         # Historique des changements d'état
            "max_history": 50      # Limite de l'historique
        }
        try:
            if self.config_path and self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return {**default, **json.load(f)}
        except (json.JSONDecodeError, IOError):
            pass
        return default
    
    def _save_config(self) -> None:
        """Sauvegarde la configuration."""
        if not self.config_path:
            return
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except IOError:
            pass
    
    def get_menu_items(self) -> List[Dict[str, Any]]:
        """Ajoute l'entrée menu."""
        return [{
            "key": "M",
            "label": "Monitoring Apps       [M]",
            "handler": self.show_menu
        }]
    
    def get_hooks(self) -> Dict[HookType, Any]:
        """Enregistre les hooks."""
        return {
            HookType.ON_STARTUP: self._on_startup,
            HookType.ON_SHUTDOWN: self._on_shutdown
        }
    
    def _on_startup(self) -> None:
        """Hook au démarrage."""
        if self.config.get("auto_start", False):
            self._start_background_monitor()
    
    def _on_shutdown(self) -> None:
        """Hook à la fermeture."""
        self._stop_background_monitor()
    
    # ==================== MONITORING CORE ====================
    
    def _get_running_processes(self) -> Dict[str, List[int]]:
        """
        Récupère la liste des processus en cours.
        Retourne {nom_process: [liste_pids]}
        Optimisé pour être léger.
        """
        processes = {}
        
        try:
            if os.name == 'nt':
                # Windows - utiliser tasklist (léger)
                import subprocess
                result = subprocess.run(
                    ['tasklist', '/FO', 'CSV', '/NH'],
                    capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.replace('"', '').split(',')
                        if len(parts) >= 2:
                            name = parts[0].lower()
                            try:
                                pid = int(parts[1])
                                if name not in processes:
                                    processes[name] = []
                                processes[name].append(pid)
                            except ValueError:
                                pass
            else:
                # Linux/Mac - utiliser ps
                import subprocess
                result = subprocess.run(
                    ['ps', '-eo', 'pid,comm'],
                    capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.strip().split('\n')[1:]:
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            pid = int(parts[0])
                            name = parts[1].lower()
                            if name not in processes:
                                processes[name] = []
                            processes[name].append(pid)
                        except ValueError:
                            pass
        except Exception:
            pass
        
        return processes
    
    def is_app_running(self, app_name: str) -> tuple[bool, List[int]]:
        """
        Vérifie si une application est en cours d'exécution.
        Retourne (is_running, list_of_pids)
        """
        processes = self._get_running_processes()
        app_lower = app_name.lower()
        
        # Chercher correspondance exacte ou partielle
        for proc_name, pids in processes.items():
            if app_lower in proc_name or proc_name in app_lower:
                return True, pids
        
        return False, []
    
    def get_monitored_status(self) -> List[Dict[str, Any]]:
        """Récupère le statut de toutes les apps surveillées."""
        results = []
        for app in self.config.get("monitored_apps", []):
            name = app.get("name", "")
            is_running, pids = self.is_app_running(name)
            results.append({
                "name": name,
                "display_name": app.get("display_name", name),
                "running": is_running,
                "pids": pids,
                "notify": app.get("notify", True)
            })
        return results
    
    def _start_background_monitor(self) -> None:
        """Démarre le monitoring en arrière-plan."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        
        self._stop_monitoring.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="MonitoringThread"
        )
        self._monitor_thread.start()
    
    def _stop_background_monitor(self) -> None:
        """Arrête le monitoring en arrière-plan."""
        self._stop_monitoring.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
            self._monitor_thread = None
    
    def _monitor_loop(self) -> None:
        """Boucle de monitoring (thread séparé)."""
        interval = self.config.get("check_interval", self.CHECK_INTERVAL)
        
        while not self._stop_monitoring.is_set():
            try:
                self._check_apps()
            except Exception:
                pass
            self._stop_monitoring.wait(interval)
    
    def _check_apps(self) -> None:
        """Vérifie l'état des apps et détecte les changements."""
        for app in self.config.get("monitored_apps", []):
            name = app.get("name", "")
            if not name:
                continue
            
            is_running, pids = self.is_app_running(name)
            was_running = self._process_cache.get(name, None)
            
            # Détecter changement d'état
            if was_running is not None and was_running != is_running:
                self._on_state_change(app, is_running)
            
            self._process_cache[name] = is_running
    
    def _on_state_change(self, app: Dict, is_running: bool) -> None:
        """Appelé quand une app change d'état (démarre/s'arrête)."""
        if not self.config.get("notify_on_change", True):
            return
        
        name = app.get("display_name", app.get("name", ""))
        status = "DÉMARRÉ" if is_running else "ARRÊTÉ"
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Ajouter à l'historique
        history = self.config.get("history", [])
        history.insert(0, {
            "app": name,
            "status": status,
            "time": timestamp
        })
        
        # Limiter l'historique
        max_history = self.config.get("max_history", 50)
        self.config["history"] = history[:max_history]
        self._save_config()
        
        # Exécuter action si configurée
        action = app.get("on_start" if is_running else "on_stop")
        if action:
            self._execute_action(action)
    
    def _execute_action(self, action: Dict) -> None:
        """Exécute une action configurée."""
        action_type = action.get("type")
        
        if action_type == "script":
            # Lancer un script
            script_path = action.get("path")
            if script_path and os.path.exists(script_path):
                import subprocess
                subprocess.Popen(
                    [sys.executable, script_path],
                    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
                )
        
        elif action_type == "command":
            # Exécuter une commande
            cmd = action.get("command")
            if cmd:
                import subprocess
                subprocess.Popen(cmd, shell=True)
    
    # ==================== INTERFACE UTILISATEUR ====================
    
    def _clear_screen(self) -> None:
        """Nettoie l'écran."""
        if self.program:
            self.program.clear_screen()
    
    def show_menu(self) -> None:
        """Menu principal du monitoring."""
        while True:
            self._clear_screen()
            print("\n" + "=" * 55)
            print("           MONITORING DES APPLICATIONS")
            print("=" * 55)
            
            # Statut du monitoring
            is_active = self._monitor_thread and self._monitor_thread.is_alive()
            status = "🟢 ACTIF" if is_active else "⚪ INACTIF"
            print(f"\nStatut monitoring: {status}")
            print(f"Intervalle: {self.config.get('check_interval', 10)}s")
            print(f"Auto-démarrage: {'Oui' if self.config.get('auto_start') else 'Non'}")
            
            # Liste des apps surveillées
            apps = self.config.get("monitored_apps", [])
            print(f"\n📊 Applications surveillées ({len(apps)}):")
            
            if apps:
                statuses = self.get_monitored_status()
                for i, s in enumerate(statuses, 1):
                    running = "🟢 En cours" if s['running'] else "🔴 Arrêté"
                    pids = f" (PID: {', '.join(map(str, s['pids'][:3]))})" if s['pids'] else ""
                    print(f"  {i}. {s['display_name']}: {running}{pids}")
            else:
                print("  Aucune application configurée")
            
            print("\n" + "-" * 55)
            print("  1. Démarrer/Arrêter monitoring")
            print("  2. Ajouter une application")
            print("  3. Supprimer une application")
            print("  4. Voir l'historique")
            print("  5. Vérifier une app manuellement")
            print("  6. Configurer les paramètres")
            print("  7. Statistiques système")
            print("  R. Retour")
            
            choice = input("\nChoix: ").strip().lower()
            
            if choice == "1":
                self._toggle_monitoring()
            elif choice == "2":
                self._add_app()
            elif choice == "3":
                self._remove_app()
            elif choice == "4":
                self._show_history()
            elif choice == "5":
                self._manual_check()
            elif choice == "6":
                self._configure()
            elif choice == "7":
                self._show_system_stats()
            elif choice == "r":
                break
    
    def _toggle_monitoring(self) -> None:
        """Active/désactive le monitoring."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._stop_background_monitor()
            print("\n⚪ Monitoring arrêté.")
        else:
            self._start_background_monitor()
            print("\n🟢 Monitoring démarré.")
        input("\nAppuyez sur Entrée...")
    
    def _add_app(self) -> None:
        """Ajoute une application à surveiller."""
        print("\n--- Ajouter une application ---")
        
        name = input("Nom du processus (ex: chrome.exe, firefox): ").strip()
        if not name:
            return
        
        display_name = input(f"Nom d'affichage [{name}]: ").strip() or name
        
        # Vérifier si déjà présent
        existing = [a.get("name", "").lower() for a in self.config.get("monitored_apps", [])]
        if name.lower() in existing:
            print("\n⚠️ Cette application est déjà surveillée.")
            input("\nAppuyez sur Entrée...")
            return
        
        app = {
            "name": name,
            "display_name": display_name,
            "notify": True
        }
        
        # Vérifier si l'app tourne actuellement
        is_running, pids = self.is_app_running(name)
        if is_running:
            print(f"\n✓ '{name}' est actuellement en cours d'exécution (PID: {pids})")
        else:
            print(f"\n○ '{name}' n'est pas en cours d'exécution")
        
        self.config.setdefault("monitored_apps", []).append(app)
        self._process_cache[name] = is_running
        self._save_config()
        
        print(f"\n✓ '{display_name}' ajouté à la surveillance!")
        input("\nAppuyez sur Entrée...")
    
    def _remove_app(self) -> None:
        """Retire une application de la surveillance."""
        apps = self.config.get("monitored_apps", [])
        if not apps:
            print("\nAucune application à retirer.")
            input("\nAppuyez sur Entrée...")
            return
        
        print("\nApplications surveillées:")
        for i, app in enumerate(apps, 1):
            print(f"  {i}. {app.get('display_name', app.get('name'))}")
        
        idx = input("\nNuméro à retirer (ou 'q'): ").strip()
        if idx.lower() == 'q':
            return
        
        try:
            app = apps.pop(int(idx) - 1)
            self._save_config()
            print(f"\n✓ '{app.get('display_name', app.get('name'))}' retiré!")
        except (ValueError, IndexError):
            print("\nChoix invalide.")
        
        input("\nAppuyez sur Entrée...")
    
    def _show_history(self) -> None:
        """Affiche l'historique des changements d'état."""
        history = self.config.get("history", [])
        
        print("\n--- Historique des changements ---")
        if history:
            for event in history[:20]:
                print(f"  [{event.get('time')}] {event.get('app')}: {event.get('status')}")
        else:
            print("  Aucun événement enregistré")
        
        input("\nAppuyez sur Entrée...")
    
    def _manual_check(self) -> None:
        """Vérifie manuellement si une app est en cours."""
        name = input("\nNom du processus à vérifier: ").strip()
        if not name:
            return
        
        print(f"\nRecherche de '{name}'...")
        is_running, pids = self.is_app_running(name)
        
        if is_running:
            print(f"✓ '{name}' est EN COURS D'EXÉCUTION")
            print(f"  PID(s): {', '.join(map(str, pids))}")
        else:
            print(f"✗ '{name}' n'est PAS en cours d'exécution")
        
        input("\nAppuyez sur Entrée...")
    
    def _configure(self) -> None:
        """Configure les paramètres du monitoring."""
        print("\n--- Configuration ---")
        print(f"  1. Intervalle de vérification: {self.config.get('check_interval', 10)}s")
        print(f"  2. Auto-démarrage: {'Oui' if self.config.get('auto_start') else 'Non'}")
        print(f"  3. Notifications: {'Oui' if self.config.get('notify_on_change') else 'Non'}")
        print("  R. Retour")
        
        choice = input("\nOption à modifier: ").strip().lower()
        
        if choice == "1":
            try:
                interval = int(input("Nouvel intervalle (5-300 secondes): "))
                if 5 <= interval <= 300:
                    self.config["check_interval"] = interval
                    self._save_config()
                    print(f"✓ Intervalle défini à {interval}s")
            except ValueError:
                print("Valeur invalide.")
        
        elif choice == "2":
            self.config["auto_start"] = not self.config.get("auto_start", False)
            self._save_config()
            status = "activé" if self.config["auto_start"] else "désactivé"
            print(f"✓ Auto-démarrage {status}")
        
        elif choice == "3":
            self.config["notify_on_change"] = not self.config.get("notify_on_change", True)
            self._save_config()
            status = "activées" if self.config["notify_on_change"] else "désactivées"
            print(f"✓ Notifications {status}")
        
        input("\nAppuyez sur Entrée...")
    
    def _show_system_stats(self) -> None:
        """Affiche des statistiques système basiques."""
        print("\n--- Statistiques Système ---")
        
        try:
            processes = self._get_running_processes()
            total_processes = sum(len(pids) for pids in processes.values())
            unique_apps = len(processes)
            
            print(f"\n  Processus actifs: {total_processes}")
            print(f"  Applications uniques: {unique_apps}")
            
            # Top 10 des processus les plus courants
            sorted_procs = sorted(processes.items(), key=lambda x: len(x[1]), reverse=True)[:10]
            print("\n  Top 10 processus (par nombre d'instances):")
            for name, pids in sorted_procs:
                print(f"    • {name}: {len(pids)} instance(s)")
            
        except Exception as e:
            print(f"\n  Erreur: {e}")
        
        input("\nAppuyez sur Entrée...")
