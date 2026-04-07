# plugins/notifications/plugin.py
"""
Plugin Notifications - Système de notifications Windows et Terminal.
Permet de notifier les actions du gestionnaire en arrière-plan ou en actif.
"""
import os
import sys
import json
import time
import threading
import queue
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from enum import Enum, auto
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from plugins.base import Plugin, PluginMeta, HookType


class NotificationType(Enum):
    """Types de notifications."""
    INFO = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()
    SCRIPT_START = auto()
    SCRIPT_END = auto()
    PLUGIN_EVENT = auto()


class NotificationChannel(Enum):
    """Canaux de notification disponibles."""
    WINDOWS = "windows"      # Toast notifications Windows
    TERMINAL = "terminal"    # Affichage dans le terminal
    BOTH = "both"            # Les deux
    NONE = "none"            # Désactivé


class NotificationsPlugin(Plugin):
    """Plugin de notifications multi-canal."""
    
    CONFIG_FILE = "notifications.json"
    
    # Icônes pour le terminal
    ICONS = {
        NotificationType.INFO: "ℹ️",
        NotificationType.SUCCESS: "✅",
        NotificationType.WARNING: "⚠️",
        NotificationType.ERROR: "❌",
        NotificationType.SCRIPT_START: "▶️",
        NotificationType.SCRIPT_END: "⏹️",
        NotificationType.PLUGIN_EVENT: "🔌",
    }
    
    # Couleurs ANSI pour le terminal
    COLORS = {
        NotificationType.INFO: "\033[36m",      # Cyan
        NotificationType.SUCCESS: "\033[32m",   # Vert
        NotificationType.WARNING: "\033[33m",   # Jaune
        NotificationType.ERROR: "\033[31m",     # Rouge
        NotificationType.SCRIPT_START: "\033[35m",  # Magenta
        NotificationType.SCRIPT_END: "\033[34m",    # Bleu
        NotificationType.PLUGIN_EVENT: "\033[90m",  # Gris
    }
    RESET = "\033[0m"
    
    def __init__(self):
        self.program = None
        self.config_path = None
        self.config: Dict[str, Any] = {}
        self._notification_queue: queue.Queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_worker = threading.Event()
        self._history: List[Dict] = []
        self._windows_notifier = None
    
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="notifications",
            version="1.0.0",
            author="Script Manager",
            description="Notifications Windows et Terminal pour les actions du gestionnaire",
            homepage="",
            license="MIT"
        )
    
    def on_load(self, program: Any) -> bool:
        """Initialise le plugin."""
        self.program = program
        self.config_path = Path(program.current_path) / "data" / self.CONFIG_FILE
        self.config = self._load_config()
        
        # Initialiser le notifier Windows si disponible
        self._init_windows_notifier()
        
        # Démarrer le worker de notifications
        self._start_worker()
        
        return True
    
    def on_unload(self, program: Any) -> None:
        """Arrête le plugin."""
        self._stop_worker_thread()
        self._save_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Charge la configuration."""
        default = {
            "enabled": True,
            "channel": "both",  # windows, terminal, both, none
            "settings": {
                "windows": {
                    "enabled": True,
                    "sound": True,
                    "duration": 5,  # secondes
                    "app_name": "Gestionnaire de Scripts"
                },
                "terminal": {
                    "enabled": True,
                    "colors": True,
                    "timestamp": True,
                    "compact": False,  # Mode compact (1 ligne)
                    "pause": False  # Pause bloquante après affichage
                }
            },
            "filters": {
                "show_info": True,
                "show_success": True,
                "show_warning": True,
                "show_error": True,
                "show_script_events": True,
                "show_plugin_events": False
            },
            "quiet_hours": {
                "enabled": False,
                "start": "22:00",
                "end": "08:00"
            },
            "history_max": 100
        }
        try:
            if self.config_path and self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Fusion profonde
                    return self._deep_merge(default, loaded)
        except (json.JSONDecodeError, IOError):
            pass
        return default
    
    def _deep_merge(self, default: Dict, loaded: Dict) -> Dict:
        """Fusionne récursivement deux dictionnaires."""
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def _save_config(self) -> None:
        """Sauvegarde la configuration."""
        if not self.config_path:
            return
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except IOError:
            pass
    
    def _init_windows_notifier(self) -> None:
        """Initialise le système de notifications."""
        self._notifier_type = "fallback"
        
        try:
            # Priorité 1: plyer (cross-platform, bien maintenu, sûr)
            try:
                from plyer import notification as plyer_notification
                self._windows_notifier = plyer_notification
                self._notifier_type = "plyer"
                return
            except ImportError:
                pass
            
            # Priorité 2: win10toast (Windows uniquement)
            if os.name == 'nt':
                try:
                    from win10toast import ToastNotifier
                    self._windows_notifier = ToastNotifier()
                    self._notifier_type = "win10toast"
                    return
                except ImportError:
                    pass
            
            # Priorité 3: notify2 (Linux avec D-Bus)
            if os.name != 'nt':
                try:
                    import notify2
                    notify2.init("Gestionnaire de Scripts")
                    self._windows_notifier = notify2
                    self._notifier_type = "notify2"
                    return
                except (ImportError, Exception):
                    pass
            
            # Fallback: PowerShell (Windows) ou notify-send (Linux)
            self._notifier_type = "fallback"
            
        except Exception:
            self._notifier_type = "fallback"
    
    def get_menu_items(self) -> List[Dict[str, Any]]:
        """Ajoute l'entrée menu."""
        return [{
            "key": "Z",
            "label": "Notifications         [Z]",
            "handler": self.show_menu
        }]
    
    def get_hooks(self) -> Dict[HookType, Any]:
        """Enregistre les hooks pour capturer les événements."""
        return {
            HookType.ON_STARTUP: self._on_startup,
            HookType.ON_SHUTDOWN: self._on_shutdown,
            HookType.PRE_EXECUTE: self._on_pre_execute,
            HookType.POST_EXECUTE: self._on_post_execute,
            HookType.POST_CREATE: self._on_post_create,
        }
    
    # ==================== HOOKS ====================
    
    def _on_startup(self) -> None:
        """Notification au démarrage."""
        if self.config.get("enabled"):
            self.notify(
                "Gestionnaire démarré",
                "Le gestionnaire de scripts est prêt.",
                NotificationType.INFO
            )
    
    def _on_shutdown(self) -> None:
        """Notification à la fermeture."""
        if self.config.get("enabled"):
            self.notify(
                "Fermeture",
                "Le gestionnaire de scripts se ferme.",
                NotificationType.INFO,
                immediate=True  # Pas de queue, direct
            )
    
    def _on_pre_execute(self, script_name: str = "", **kwargs) -> None:
        """Notification avant exécution d'un script."""
        if not self._should_show(NotificationType.SCRIPT_START):
            return
        self.notify(
            "Script en cours",
            f"Exécution de: {script_name}",
            NotificationType.SCRIPT_START
        )
    
    def _on_post_execute(self, script_name: str = "", return_code: int = 0, **kwargs) -> None:
        """Notification après exécution d'un script."""
        if not self._should_show(NotificationType.SCRIPT_END):
            return
        
        if return_code == 0:
            self.notify(
                "Script terminé",
                f"{script_name} - Succès ✓",
                NotificationType.SUCCESS
            )
        else:
            self.notify(
                "Script terminé avec erreur",
                f"{script_name} - Code: {return_code}",
                NotificationType.ERROR
            )
    
    def _on_post_create(self, script_name: str = "", **kwargs) -> None:
        """Notification après création d'un script."""
        if not self._should_show(NotificationType.SUCCESS):
            return
        self.notify(
            "Script créé",
            f"Nouveau script: {script_name}",
            NotificationType.SUCCESS
        )
    
    # ==================== NOTIFICATION CORE ====================
    
    def notify(
        self,
        title: str,
        message: str,
        notif_type: NotificationType = NotificationType.INFO,
        immediate: bool = False
    ) -> None:
        """
        Envoie une notification.
        
        Args:
            title: Titre de la notification
            message: Corps du message
            notif_type: Type de notification
            immediate: Si True, envoie immédiatement (pas de queue)
        """
        if not self.config.get("enabled", True):
            return
        
        if not self._should_show(notif_type):
            return
        
        if self._is_quiet_hours():
            return
        
        notification = {
            "title": title,
            "message": message,
            "type": notif_type,
            "timestamp": datetime.now().isoformat()
        }
        
        # Ajouter à l'historique
        self._add_to_history(notification)
        
        if immediate:
            self._send_notification(notification)
        else:
            self._notification_queue.put(notification)
    
    def _should_show(self, notif_type: NotificationType) -> bool:
        """Vérifie si ce type de notification doit être affiché."""
        filters = self.config.get("filters", {})
        
        type_filter_map = {
            NotificationType.INFO: "show_info",
            NotificationType.SUCCESS: "show_success",
            NotificationType.WARNING: "show_warning",
            NotificationType.ERROR: "show_error",
            NotificationType.SCRIPT_START: "show_script_events",
            NotificationType.SCRIPT_END: "show_script_events",
            NotificationType.PLUGIN_EVENT: "show_plugin_events",
        }
        
        filter_key = type_filter_map.get(notif_type, "show_info")
        return filters.get(filter_key, True)
    
    def _is_quiet_hours(self) -> bool:
        """Vérifie si on est dans les heures silencieuses."""
        quiet = self.config.get("quiet_hours", {})
        if not quiet.get("enabled", False):
            return False
        
        try:
            now = datetime.now().time()
            start = datetime.strptime(quiet.get("start", "22:00"), "%H:%M").time()
            end = datetime.strptime(quiet.get("end", "08:00"), "%H:%M").time()
            
            if start <= end:
                return start <= now <= end
            else:
                # Passe minuit (ex: 22:00 - 08:00)
                return now >= start or now <= end
        except ValueError:
            return False
    
    def _add_to_history(self, notification: Dict) -> None:
        """Ajoute une notification à l'historique."""
        # Convertir le type enum en string pour JSON
        notif_copy = notification.copy()
        notif_copy["type"] = notification["type"].name
        
        self._history.insert(0, notif_copy)
        
        # Limiter la taille
        max_history = self.config.get("history_max", 100)
        self._history = self._history[:max_history]
    
    def _start_worker(self) -> None:
        """Démarre le thread worker pour les notifications."""
        if self._worker_thread and self._worker_thread.is_alive():
            return
        
        self._stop_worker.clear()
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="NotificationWorker"
        )
        self._worker_thread.start()
    
    def _stop_worker_thread(self) -> None:
        """Arrête le worker."""
        self._stop_worker.set()
        # Débloquer le worker s'il attend
        self._notification_queue.put(None)
        if self._worker_thread:
            self._worker_thread.join(timeout=2)
    
    def _worker_loop(self) -> None:
        """Boucle du worker de notifications."""
        while not self._stop_worker.is_set():
            try:
                notification = self._notification_queue.get(timeout=1)
                if notification is None:
                    continue
                self._send_notification(notification)
            except queue.Empty:
                continue
            except Exception:
                pass
    
    def _send_notification(self, notification: Dict) -> None:
        """Envoie une notification sur les canaux configurés."""
        channel = self.config.get("channel", "both")
        
        # Jouer le son si activé
        self._play_notification_sound(notification.get("type", NotificationType.INFO))
        
        if channel in ["terminal", "both"]:
            self._send_terminal_notification(notification)
        
        if channel in ["windows", "both"] and os.name == 'nt':
            self._send_windows_notification(notification)
    
    def _play_notification_sound(self, notif_type: NotificationType) -> None:
        """Joue un son de notification."""
        settings = self.config.get("settings", {}).get("windows", {})
        if not settings.get("sound", True):
            return
        
        try:
            if os.name == 'nt':
                import winsound
                # Sons Windows selon le type
                sound_map = {
                    NotificationType.INFO: 'SystemAsterisk',
                    NotificationType.SUCCESS: 'SystemExclamation',
                    NotificationType.WARNING: 'SystemHand',
                    NotificationType.ERROR: 'SystemHand',
                    NotificationType.SCRIPT_START: 'SystemAsterisk',
                    NotificationType.SCRIPT_END: 'SystemExclamation',
                    NotificationType.PLUGIN_EVENT: 'SystemAsterisk',
                }
                sound = sound_map.get(notif_type, 'SystemAsterisk')
                winsound.PlaySound(sound, winsound.SND_ALIAS | winsound.SND_ASYNC)
            else:
                # Linux: utiliser paplay ou aplay si disponible
                import subprocess
                import shutil
                if shutil.which("paplay"):
                    # PulseAudio
                    subprocess.Popen(
                        ["paplay", "/usr/share/sounds/freedesktop/stereo/message.oga"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                elif shutil.which("aplay"):
                    # ALSA fallback
                    subprocess.Popen(
                        ["aplay", "-q", "/usr/share/sounds/alsa/Front_Center.wav"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
        except Exception:
            pass  # Son non critique
    
    def _send_terminal_notification(self, notification: Dict) -> None:
        """Affiche une notification dans le terminal."""
        settings = self.config.get("settings", {}).get("terminal", {})
        if not settings.get("enabled", True):
            return
        
        notif_type = notification["type"]
        title = notification["title"]
        message = notification["message"]
        timestamp = notification.get("timestamp", "")
        
        icon = self.ICONS.get(notif_type, "•")
        
        # Formatage
        if settings.get("colors", True):
            color = self.COLORS.get(notif_type, "")
            reset = self.RESET
        else:
            color = ""
            reset = ""
        
        # Construire le message
        if settings.get("compact", False):
            # Mode compact: une seule ligne
            time_str = ""
            if settings.get("timestamp", True) and timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = f"[{dt.strftime('%H:%M:%S')}] "
                except ValueError:
                    pass
            output = f"{color}{time_str}{icon} {title}: {message}{reset}"
        else:
            # Mode détaillé
            output = f"\n{color}{'─' * 50}{reset}"
            if settings.get("timestamp", True) and timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    output += f"\n{color}  {dt.strftime('%H:%M:%S')}{reset}"
                except ValueError:
                    pass
            output += f"\n{color}  {icon} {title}{reset}"
            output += f"\n{color}  {message}{reset}"
            output += f"\n{color}{'─' * 50}{reset}"
        
        print(output)
        
        # Pause bloquante si activée
        if settings.get("pause", False):
            input("  Appuyez sur Entrée pour continuer...")
    
    def _send_windows_notification(self, notification: Dict) -> None:
        """Envoie une notification système (Windows/Linux)."""
        settings = self.config.get("settings", {}).get("windows", {})
        if not settings.get("enabled", True):
            return
        
        title = notification["title"]
        message = notification["message"]
        app_name = settings.get("app_name", "Gestionnaire de Scripts")
        duration = settings.get("duration", 5)
        
        try:
            # Priorité 1: BurntToast (Windows - plus fiable)
            if os.name == 'nt' and self._try_burnttoast(title, message, app_name):
                return
            
            # Priorité 2: Plyer
            if self._notifier_type == "plyer":
                self._windows_notifier.notify(
                    title=f"{app_name}: {title}",
                    message=message,
                    app_name=app_name,
                    timeout=duration
                )
                return
            
            # Priorité 3: win10toast
            if self._notifier_type == "win10toast":
                self._windows_notifier.show_toast(
                    title=f"{app_name}: {title}",
                    msg=message,
                    duration=duration,
                    threaded=True
                )
                return
            
            # Priorité 4: notify2 (Linux)
            if self._notifier_type == "notify2":
                n = self._windows_notifier.Notification(
                    f"{app_name}: {title}",
                    message
                )
                n.timeout = duration * 1000
                n.show()
                return
            
            # Fallback natif
            if os.name == 'nt':
                self._send_powershell_notification(title, message, app_name)
            else:
                self._send_linux_notification(title, message, app_name, duration)
                
        except Exception:
            pass
    
    def _try_burnttoast(self, title: str, message: str, app_name: str) -> bool:
        """Essaie d'envoyer via BurntToast (PowerShell). Retourne True si succès."""
        import subprocess
        
        # Échapper les guillemets
        title_safe = title.replace("'", "''").replace('"', '`"')
        message_safe = message.replace("'", "''").replace('"', '`"')
        app_safe = app_name.replace("'", "''").replace('"', '`"')
        
        ps_script = f'''
        $ErrorActionPreference = "SilentlyContinue"
        if (Get-Module -ListAvailable -Name BurntToast) {{
            Import-Module BurntToast -ErrorAction SilentlyContinue
            New-BurntToastNotification -Text "{app_safe}: {title_safe}", "{message_safe}" -ErrorAction SilentlyContinue
            exit 0
        }}
        exit 1
        '''
        
        try:
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _send_linux_notification(self, title: str, message: str, app_name: str, duration: int) -> None:
        """Envoie une notification via notify-send (Linux fallback)."""
        import subprocess
        import shutil
        
        # Vérifier si notify-send est disponible
        if not shutil.which("notify-send"):
            return
        
        try:
            subprocess.run(
                [
                    "notify-send",
                    f"{app_name}: {title}",
                    message,
                    "-t", str(duration * 1000),  # timeout en ms
                    "-a", app_name
                ],
                capture_output=True,
                timeout=5
            )
        except Exception:
            pass
    
    def _send_powershell_notification(self, title: str, message: str, app_name: str) -> None:
        """Envoie une notification via PowerShell (fallback)."""
        import subprocess
        
        # Échapper les caractères spéciaux pour PowerShell
        title = title.replace("'", "''").replace('"', '`"').replace('$', '`$')
        message = message.replace("'", "''").replace('"', '`"').replace('$', '`$')
        app_name = app_name.replace("'", "''").replace('"', '`"').replace('$', '`$')
        
        # Utiliser BurntToast si disponible, sinon notification basique
        ps_script = f'''
        $ErrorActionPreference = "SilentlyContinue"
        
        # Méthode 1: BurntToast (recommandé)
        if (Get-Module -ListAvailable -Name BurntToast) {{
            Import-Module BurntToast
            New-BurntToastNotification -Text "{app_name}: {title}", "{message}"
            exit 0
        }}
        
        # Méthode 2: Utiliser Windows.Forms pour un balloon tip
        Add-Type -AssemblyName System.Windows.Forms
        $balloon = New-Object System.Windows.Forms.NotifyIcon
        $balloon.Icon = [System.Drawing.SystemIcons]::Information
        $balloon.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info
        $balloon.BalloonTipTitle = "{app_name}: {title}"
        $balloon.BalloonTipText = "{message}"
        $balloon.Visible = $true
        $balloon.ShowBalloonTip(5000)
        Start-Sleep -Milliseconds 5500
        $balloon.Dispose()
        '''
        
        try:
            subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
        except Exception:
            pass
    
    # ==================== API PUBLIQUE ====================
    
    def info(self, title: str, message: str) -> None:
        """Raccourci pour notification info."""
        self.notify(title, message, NotificationType.INFO)
    
    def success(self, title: str, message: str) -> None:
        """Raccourci pour notification succès."""
        self.notify(title, message, NotificationType.SUCCESS)
    
    def warning(self, title: str, message: str) -> None:
        """Raccourci pour notification warning."""
        self.notify(title, message, NotificationType.WARNING)
    
    def error(self, title: str, message: str) -> None:
        """Raccourci pour notification erreur."""
        self.notify(title, message, NotificationType.ERROR)
    
    # ==================== INTERFACE UTILISATEUR ====================
    
    def _clear_screen(self) -> None:
        """Nettoie l'écran."""
        if self.program:
            self.program.clear_screen()
    
    def show_menu(self) -> None:
        """Menu principal des notifications."""
        while True:
            self._clear_screen()
            print("\n" + "=" * 55)
            print("           GESTIONNAIRE DE NOTIFICATIONS")
            print("=" * 55)
            
            # Statut
            enabled = self.config.get("enabled", True)
            channel = self.config.get("channel", "both")
            status = "🟢 ACTIVÉ" if enabled else "⚪ DÉSACTIVÉ"
            
            channel_names = {
                "windows": "Système uniquement",
                "terminal": "Terminal uniquement",
                "both": "Système + Terminal",
                "none": "Aucun"
            }
            
            print(f"\nStatut: {status}")
            print(f"Canal: {channel_names.get(channel, channel)}")
            
            # Infos notifier
            notifier_info = {
                "plyer": "✓ plyer (recommandé)",
                "win10toast": "✓ win10toast",
                "notify2": "✓ notify2 (D-Bus)",
                "fallback": "⚠ Fallback natif"
            }
            print(f"Notifier: {notifier_info.get(self._notifier_type, self._notifier_type)}")
            
            # Heures silencieuses
            quiet = self.config.get("quiet_hours", {})
            if quiet.get("enabled"):
                print(f"Heures silencieuses: {quiet.get('start')} - {quiet.get('end')}")
            
            print(f"\nHistorique: {len(self._history)} notification(s)")
            
            print("\n" + "-" * 55)
            print("  1. Activer/Désactiver")
            print("  2. Choisir le canal")
            print("  3. Paramètres Système")
            print("  4. Paramètres Terminal")
            print("  5. Filtres de notifications")
            print("  6. Heures silencieuses")
            print("  7. Voir l'historique")
            print("  8. Tester les notifications")
            print("  9. Installer dépendances (plyer)")
            print("  R. Retour")
            
            choice = input("\nChoix: ").strip().lower()
            
            if choice == "1":
                self._toggle_enabled()
            elif choice == "2":
                self._choose_channel()
            elif choice == "3":
                self._configure_windows()
            elif choice == "4":
                self._configure_terminal()
            elif choice == "5":
                self._configure_filters()
            elif choice == "6":
                self._configure_quiet_hours()
            elif choice == "7":
                self._show_history()
            elif choice == "8":
                self._test_notifications()
            elif choice == "9":
                self._install_win10toast()
            elif choice == "r":
                break
    
    def _toggle_enabled(self) -> None:
        """Active/désactive les notifications."""
        self.config["enabled"] = not self.config.get("enabled", True)
        self._save_config()
        status = "activées" if self.config["enabled"] else "désactivées"
        print(f"\n✓ Notifications {status}")
        input("\nAppuyez sur Entrée...")
    
    def _choose_channel(self) -> None:
        """Choisit le canal de notification."""
        print("\n--- Choisir le canal ---")
        print("  1. Windows + Terminal (les deux)")
        print("  2. Windows uniquement")
        print("  3. Terminal uniquement")
        print("  4. Aucun (désactivé)")
        
        choice = input("\nChoix: ").strip()
        
        channels = {"1": "both", "2": "windows", "3": "terminal", "4": "none"}
        if choice in channels:
            self.config["channel"] = channels[choice]
            self._save_config()
            print(f"\n✓ Canal défini: {channels[choice]}")
        
        input("\nAppuyez sur Entrée...")
    
    def _configure_windows(self) -> None:
        """Configure les notifications Windows."""
        settings = self.config.setdefault("settings", {}).setdefault("windows", {})
        
        print("\n--- Paramètres Windows ---")
        print(f"  1. Activé: {'Oui' if settings.get('enabled', True) else 'Non'}")
        print(f"  2. Son: {'Oui' if settings.get('sound', True) else 'Non'}")
        print(f"  3. Durée: {settings.get('duration', 5)} secondes")
        print(f"  4. Nom de l'app: {settings.get('app_name', 'Gestionnaire de Scripts')}")
        
        choice = input("\nOption à modifier (ou Entrée): ").strip()
        
        if choice == "1":
            settings["enabled"] = not settings.get("enabled", True)
        elif choice == "2":
            settings["sound"] = not settings.get("sound", True)
        elif choice == "3":
            try:
                dur = int(input("Durée (1-30 secondes): "))
                if 1 <= dur <= 30:
                    settings["duration"] = dur
            except ValueError:
                pass
        elif choice == "4":
            name = input("Nom de l'application: ").strip()
            if name:
                settings["app_name"] = name
        
        self._save_config()
        input("\nAppuyez sur Entrée...")
    
    def _configure_terminal(self) -> None:
        """Configure les notifications terminal."""
        settings = self.config.setdefault("settings", {}).setdefault("terminal", {})
        
        print("\n--- Paramètres Terminal ---")
        print(f"  1. Activé: {'Oui' if settings.get('enabled', True) else 'Non'}")
        print(f"  2. Couleurs: {'Oui' if settings.get('colors', True) else 'Non'}")
        print(f"  3. Horodatage: {'Oui' if settings.get('timestamp', True) else 'Non'}")
        print(f"  4. Mode compact: {'Oui' if settings.get('compact', False) else 'Non'}")
        print(f"  5. Pause bloquante: {'Oui' if settings.get('pause', False) else 'Non'}")
        
        choice = input("\nOption à modifier (ou Entrée): ").strip()
        
        if choice == "1":
            settings["enabled"] = not settings.get("enabled", True)
        elif choice == "2":
            settings["colors"] = not settings.get("colors", True)
        elif choice == "3":
            settings["timestamp"] = not settings.get("timestamp", True)
        elif choice == "4":
            settings["compact"] = not settings.get("compact", False)
        elif choice == "5":
            settings["pause"] = not settings.get("pause", False)
        
        self._save_config()
        input("\nAppuyez sur Entrée...")
    
    def _configure_filters(self) -> None:
        """Configure les filtres de notifications."""
        filters = self.config.setdefault("filters", {})
        
        print("\n--- Filtres de notifications ---")
        options = [
            ("show_info", "Informations"),
            ("show_success", "Succès"),
            ("show_warning", "Avertissements"),
            ("show_error", "Erreurs"),
            ("show_script_events", "Événements scripts"),
            ("show_plugin_events", "Événements plugins"),
        ]
        
        for i, (key, label) in enumerate(options, 1):
            status = "✓" if filters.get(key, True) else "✗"
            print(f"  {i}. [{status}] {label}")
        
        choice = input("\nToggle (numéro ou Entrée): ").strip()
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                key = options[idx][0]
                filters[key] = not filters.get(key, True)
                self._save_config()
        except ValueError:
            pass
        
        input("\nAppuyez sur Entrée...")
    
    def _configure_quiet_hours(self) -> None:
        """Configure les heures silencieuses."""
        quiet = self.config.setdefault("quiet_hours", {})
        
        print("\n--- Heures silencieuses ---")
        print(f"  1. Activé: {'Oui' if quiet.get('enabled', False) else 'Non'}")
        print(f"  2. Début: {quiet.get('start', '22:00')}")
        print(f"  3. Fin: {quiet.get('end', '08:00')}")
        
        choice = input("\nOption à modifier (ou Entrée): ").strip()
        
        if choice == "1":
            quiet["enabled"] = not quiet.get("enabled", False)
        elif choice == "2":
            time_str = input("Heure de début (HH:MM): ").strip()
            try:
                datetime.strptime(time_str, "%H:%M")
                quiet["start"] = time_str
            except ValueError:
                print("Format invalide.")
        elif choice == "3":
            time_str = input("Heure de fin (HH:MM): ").strip()
            try:
                datetime.strptime(time_str, "%H:%M")
                quiet["end"] = time_str
            except ValueError:
                print("Format invalide.")
        
        self._save_config()
        input("\nAppuyez sur Entrée...")
    
    def _show_history(self) -> None:
        """Affiche l'historique des notifications."""
        print("\n--- Historique des notifications ---")
        
        if not self._history:
            print("  Aucune notification dans l'historique.")
        else:
            for notif in self._history[:20]:
                try:
                    dt = datetime.fromisoformat(notif.get("timestamp", ""))
                    time_str = dt.strftime("%H:%M:%S")
                except ValueError:
                    time_str = "??:??:??"
                
                notif_type = notif.get("type", "INFO")
                title = notif.get("title", "")
                print(f"  [{time_str}] {notif_type}: {title}")
        
        input("\nAppuyez sur Entrée...")
    
    def _test_notifications(self) -> None:
        """Teste les différents types de notifications."""
        print("\n--- Test des notifications ---")
        print("  1. Tester INFO")
        print("  2. Tester SUCCESS")
        print("  3. Tester WARNING")
        print("  4. Tester ERROR")
        print("  5. Tester TOUS")
        
        choice = input("\nChoix: ").strip()
        
        tests = {
            "1": (NotificationType.INFO, "Test Info", "Ceci est une notification d'information."),
            "2": (NotificationType.SUCCESS, "Test Succès", "Opération réussie avec succès!"),
            "3": (NotificationType.WARNING, "Test Avertissement", "Attention, quelque chose nécessite votre attention."),
            "4": (NotificationType.ERROR, "Test Erreur", "Une erreur s'est produite."),
        }
        
        if choice == "5":
            for notif_type, title, message in tests.values():
                self.notify(title, message, notif_type)
                time.sleep(0.5)
        elif choice in tests:
            notif_type, title, message = tests[choice]
            self.notify(title, message, notif_type)
        
        input("\nAppuyez sur Entrée...")
    
    def _install_win10toast(self) -> None:
        """Installe les dépendances de notification (plyer recommandé)."""
        print("\n--- Installation des dépendances ---")
        print("\n╭─────────────────────────────────────────────────────╮")
        print("│  Bibliothèques de notifications recommandées       │")
        print("├─────────────────────────────────────────────────────┤")
        print("│  📦 plyer        - Cross-platform (recommandé)     │")
        print("│                   Windows, Linux, macOS            │")
        print("│                   Maintenu par Kivy, sûr, stable   │")
        print("│                                                     │")
        print("│  📦 notify2      - Linux uniquement (D-Bus)        │")
        print("│                   Nécessite libnotify              │")
        print("╰─────────────────────────────────────────────────────╯")
        
        print("\n  1. Installer plyer (recommandé - tous OS)")
        print("  2. Installer notify2 (Linux uniquement)")
        print("  3. Installer les deux")
        print("  R. Retour")
        
        choice = input("\nChoix: ").strip().lower()
        
        if choice == "r":
            return
        
        import subprocess
        packages = []
        
        if choice == "1":
            packages = ["plyer"]
        elif choice == "2":
            packages = ["notify2"]
        elif choice == "3":
            packages = ["plyer", "notify2"]
        else:
            return
        
        for pkg in packages:
            print(f"\n📥 Installation de {pkg}...")
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", pkg],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode == 0:
                    print(f"  ✓ {pkg} installé avec succès!")
                else:
                    print(f"  ❌ Erreur: {result.stderr[:200]}")
            except subprocess.TimeoutExpired:
                print(f"  ❌ Timeout lors de l'installation de {pkg}")
            except Exception as e:
                print(f"  ❌ Erreur: {e}")
        
        # Réinitialiser le notifier
        print("\n🔄 Réinitialisation du notifier...")
        self._init_windows_notifier()
        print(f"  Notifier actif: {self._notifier_type}")
        
        input("\nAppuyez sur Entrée...")
