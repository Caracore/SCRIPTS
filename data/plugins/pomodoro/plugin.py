# data/plugins/pomodoro/plugin.py
"""
Plugin Pomodoro - Technique de gestion du temps.
Compatible Windows et Linux.
Affichage dynamique du timer et persistance entre les menus.
"""
import os
import sys
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import relatif pour le système de plugins
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from plugins.base import Plugin, PluginMeta, HookType


class PomodoroPlugin(Plugin):
    """
    Plugin Pomodoro - Minuteur de productivité.
    
    Fonctionnalités:
    - Minuteur Pomodoro configurable (25 min par défaut)
    - Pauses courtes (5 min) et longues (15 min)
    - Notifications sonores (cross-platform)
    - Statistiques de sessions
    - Affichage dynamique avec mise à jour en temps réel
    - Persistance du timer entre les navigations
    """
    
    DEFAULT_SETTINGS = {
        "work_duration": 25,      # minutes
        "short_break": 5,         # minutes
        "long_break": 15,         # minutes
        "long_break_after": 4,    # sessions
        "sound_enabled": True,
        "auto_start_break": False,
        "show_in_menu": True      # Afficher le statut dans le menu principal
    }
    
    def __init__(self):
        self._program = None
        self._timer_thread = None
        self._is_running = False
        self._is_paused = False
        self._remaining_seconds = 0
        self._current_mode = "work"  # work, short_break, long_break
        self._sessions_completed = 0
        self._stop_event = threading.Event()
        self._data_file = None
        self._stats = {}
        self._timer_finished = False  # Indique si le timer vient de finir
        self._last_status = ""  # Cache du dernier statut pour optimisation
        self._lock = threading.Lock()  # Protection thread-safe
    
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="pomodoro",
            version="1.0.0",
            author="Gestionnaire de Scripts",
            description="Technique Pomodoro - Minuteur de productivité",
            homepage="",
            license="MIT"
        )
    
    def on_load(self, program: Any) -> bool:
        """Initialise le plugin."""
        self._program = program
        data_path = Path(program.current_path) / "data" / "plugins" / "pomodoro"
        data_path.mkdir(parents=True, exist_ok=True)
        self._data_file = data_path / "stats.json"
        self._load_stats()
        return True
    
    def on_unload(self, program: Any) -> None:
        """Arrête le timer si en cours."""
        self.stop_timer()
        self._save_stats()
    
    def get_hooks(self) -> Dict[HookType, Any]:
        return {
            HookType.ON_SHUTDOWN: self._on_shutdown,
            HookType.ON_MENU_DISPLAY: self._on_menu_display  # Afficher le statut dans le menu
        }
    
    def get_menu_items(self) -> List[Dict[str, Any]]:
        return [
            {"key": "P", "label": "Pomodoro Timer      [P]", "handler": self.show_menu}
        ]
    
    def get_settings_schema(self) -> Dict[str, Any]:
        return {
            "work_duration": {
                "type": "integer",
                "default": 25,
                "description": "Durée d'une session de travail (minutes)"
            },
            "short_break": {
                "type": "integer",
                "default": 5,
                "description": "Durée d'une pause courte (minutes)"
            },
            "long_break": {
                "type": "integer",
                "default": 15,
                "description": "Durée d'une pause longue (minutes)"
            },
            "long_break_after": {
                "type": "integer",
                "default": 4,
                "description": "Pause longue après N sessions"
            },
            "sound_enabled": {
                "type": "boolean",
                "default": True,
                "description": "Activer les notifications sonores"
            }
        }
    
    def _on_shutdown(self) -> None:
        """Hook appelé à la fermeture."""
        self.stop_timer()
        self._save_stats()
    
    def _on_menu_display(self) -> None:
        """Hook appelé avant l'affichage du menu principal."""
        settings = self._get_settings()
        if not settings.get("show_in_menu", True):
            return
        
        # Afficher le statut du timer si actif
        if self._is_running or self._timer_finished:
            status = self.get_status()
            print(f"\n{status}")
            
            # Réinitialiser le flag de fin de timer après affichage
            if self._timer_finished:
                self._timer_finished = False
                mode_labels = {
                    "work": "Session de travail terminée! 🎉",
                    "short_break": "Pause courte terminée!",
                    "long_break": "Pause longue terminée!"
                }
                msg = mode_labels.get(self._current_mode, "Timer terminé!")
                print(f"    ✅ {msg}")
    
    def _load_stats(self) -> None:
        """Charge les statistiques."""
        try:
            if self._data_file and self._data_file.exists():
                with open(self._data_file, "r", encoding="utf-8") as f:
                    self._stats = json.load(f)
        except (json.JSONDecodeError, IOError):
            self._stats = {}
        
        if "total_sessions" not in self._stats:
            self._stats = {
                "total_sessions": 0,
                "total_minutes": 0,
                "daily": {},
                "streak": 0,
                "last_session_date": None
            }
    
    def _save_stats(self) -> None:
        """Sauvegarde les statistiques."""
        try:
            if self._data_file:
                with open(self._data_file, "w", encoding="utf-8") as f:
                    json.dump(self._stats, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[Pomodoro] Erreur sauvegarde stats: {e}")
    
    def _get_settings(self) -> Dict[str, Any]:
        """Récupère les paramètres du plugin."""
        if self._program:
            saved = self._program.plugin_manager.get_plugin_settings("pomodoro")
            return {**self.DEFAULT_SETTINGS, **saved}
        return self.DEFAULT_SETTINGS.copy()
    
    def _play_sound(self) -> None:
        """Joue un son de notification (cross-platform)."""
        settings = self._get_settings()
        if not settings.get("sound_enabled", True):
            return
        
        try:
            if os.name == 'nt':
                # Windows - utilise winsound
                import winsound
                winsound.Beep(1000, 500)
                time.sleep(0.2)
                winsound.Beep(1200, 500)
            else:
                # Linux/Mac - utilise le terminal bell ou paplay
                # Essayer d'abord paplay (PulseAudio)
                sound_file = "/usr/share/sounds/freedesktop/stereo/complete.oga"
                if os.path.exists(sound_file):
                    os.system(f'paplay "{sound_file}" 2>/dev/null &')
                else:
                    # Fallback: terminal bell
                    print('\a', end='', flush=True)
        except Exception:
            # Fallback silencieux
            print('\a', end='', flush=True)
    
    def _format_time(self, seconds: int) -> str:
        """Formate les secondes en MM:SS."""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"
    
    def _timer_loop(self, duration_minutes: int, mode: str) -> None:
        """Boucle principale du timer."""
        with self._lock:
            self._remaining_seconds = duration_minutes * 60
            self._current_mode = mode
            self._is_running = True
            self._is_paused = False
            self._timer_finished = False
        self._stop_event.clear()
        
        while self._remaining_seconds > 0 and not self._stop_event.is_set():
            if not self._is_paused:
                time.sleep(1)
                if not self._is_paused and not self._stop_event.is_set():
                    with self._lock:
                        self._remaining_seconds -= 1
            else:
                time.sleep(0.1)
        
        if not self._stop_event.is_set():
            # Timer terminé normalement
            with self._lock:
                self._timer_finished = True
            self._play_sound()
            if mode == "work":
                self._sessions_completed += 1
                self._record_session(duration_minutes)
        
        with self._lock:
            self._is_running = False
    
    def _record_session(self, duration: int) -> None:
        """Enregistre une session terminée."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        self._stats["total_sessions"] += 1
        self._stats["total_minutes"] += duration
        
        if today not in self._stats.get("daily", {}):
            self._stats["daily"] = self._stats.get("daily", {})
            self._stats["daily"][today] = {"sessions": 0, "minutes": 0}
        
        self._stats["daily"][today]["sessions"] += 1
        self._stats["daily"][today]["minutes"] += duration
        
        # Mise à jour du streak
        last_date = self._stats.get("last_session_date")
        if last_date:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            if last_date == yesterday:
                self._stats["streak"] += 1
            elif last_date != today:
                self._stats["streak"] = 1
        else:
            self._stats["streak"] = 1
        
        self._stats["last_session_date"] = today
        self._save_stats()
    
    def start_timer(self, mode: str = "work") -> None:
        """Démarre un timer."""
        if self._is_running:
            print("\n⚠️  Un timer est déjà en cours!")
            return
        
        settings = self._get_settings()
        
        if mode == "work":
            duration = settings["work_duration"]
            emoji = "🍅"
            label = "TRAVAIL"
        elif mode == "short_break":
            duration = settings["short_break"]
            emoji = "☕"
            label = "PAUSE COURTE"
        else:  # long_break
            duration = settings["long_break"]
            emoji = "🌴"
            label = "PAUSE LONGUE"
        
        print(f"\n{emoji} {label} - {duration} minutes")
        print("Le timer continue en arrière-plan.\n")
        
        self._timer_thread = threading.Thread(
            target=self._timer_loop,
            args=(duration, mode),
            daemon=True
        )
        self._timer_thread.start()
    
    def stop_timer(self) -> None:
        """Arrête le timer en cours."""
        if self._is_running:
            self._stop_event.set()
            self._is_running = False
            print("\n⏹️  Timer arrêté.")
    
    def pause_timer(self) -> None:
        """Met en pause ou reprend le timer."""
        if not self._is_running:
            print("\n⚠️  Aucun timer en cours.")
            return
        
        self._is_paused = not self._is_paused
        if self._is_paused:
            print("\n⏸️  Timer en pause.")
        else:
            print("\n▶️  Timer repris.")
    
    def get_status(self) -> str:
        """Retourne le statut actuel du timer."""
        with self._lock:
            if not self._is_running:
                return "⏹️  Aucun timer actif"
            
            mode_labels = {
                "work": "🍅 Travail",
                "short_break": "☕ Pause courte",
                "long_break": "🌴 Pause longue"
            }
            
            mode = mode_labels.get(self._current_mode, "⏱️")
            time_str = self._format_time(self._remaining_seconds)
            pause_str = " (PAUSE)" if self._is_paused else ""
            
            return f"{mode} - {time_str}{pause_str}"
    
    def get_progress_bar(self, width: int = 30) -> str:
        """Retourne une barre de progression du timer."""
        if not self._is_running:
            return ""
        
        settings = self._get_settings()
        total_seconds = {
            "work": settings["work_duration"] * 60,
            "short_break": settings["short_break"] * 60,
            "long_break": settings["long_break"] * 60
        }.get(self._current_mode, settings["work_duration"] * 60)
        
        with self._lock:
            elapsed = total_seconds - self._remaining_seconds
        progress = min(elapsed / total_seconds, 1.0) if total_seconds > 0 else 0
        
        filled = int(width * progress)
        empty = width - filled
        bar = "█" * filled + "░" * empty
        percent = int(progress * 100)
        
        return f"[{bar}] {percent}%"
    
    def _display_dynamic_timer(self) -> None:
        """Affiche le timer de manière dynamique avec mise à jour en temps réel."""
        settings = self._get_settings()
        self._clear_screen()
        
        print("\n" + "=" * 50)
        print("        🍅 POMODORO - MODE FOCUS 🍅")
        print("=" * 50)
        print("\nLe timer est actif. Concentrez-vous!")
        print("\nCommandes:")
        print("  [ESPACE] Pause/Reprendre")
        print("  [S] Arrêter")
        print("  [R] Retour au menu (timer continue)")
        print("\n" + "-" * 50)
        
        last_seconds = -1
        
        while self._is_running:
            with self._lock:
                current_seconds = self._remaining_seconds
                is_paused = self._is_paused
            
            # Mettre à jour uniquement si les secondes ont changé
            if current_seconds != last_seconds:
                # Repositionner le curseur pour la mise à jour (ligne 10)
                print(f"\033[10;1H\033[2K", end="")  # Aller ligne 10, effacer ligne
                
                status = self.get_status()
                progress = self.get_progress_bar(40)
                
                print(f"\n{status}")
                print(f"{progress}")
                print(f"\nSessions complétées: {self._sessions_completed}")
                
                if is_paused:
                    print("\n⏸️  EN PAUSE - Appuyez sur ESPACE pour reprendre")
                else:
                    print("\n▶️  EN COURS - Restez concentré!")
                
                last_seconds = current_seconds
            
            # Vérifier les touches (non bloquant)
            if os.name == 'nt':
                import msvcrt
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key == b' ':  # Espace
                        self._toggle_pause()
                    elif key.lower() == b's':
                        self.stop_timer()
                        return
                    elif key.lower() == b'r':
                        return  # Retour au menu, timer continue
            else:
                import select
                if select.select([sys.stdin], [], [], 0)[0]:
                    key = sys.stdin.read(1)
                    if key == ' ':
                        self._toggle_pause()
                    elif key.lower() == 's':
                        self.stop_timer()
                        return
                    elif key.lower() == 'r':
                        return
            
            time.sleep(0.1)  # Polling rapide pour réactivité
        
        # Timer terminé
        self._clear_screen()
        print("\n" + "=" * 50)
        print("        🎉 TIMER TERMINÉ! 🎉")
        print("=" * 50)
        
        mode_messages = {
            "work": "Excellent travail! Prenez une pause.",
            "short_break": "Pause terminée! Retour au travail.",
            "long_break": "Pause longue terminée! Prêt pour une nouvelle session?"
        }
        print(f"\n{mode_messages.get(self._current_mode, 'Timer terminé!')}")
        input("\nAppuyez sur Entrée...")
    
    def _toggle_pause(self) -> None:
        """Toggle pause sans message."""
        if self._is_running:
            with self._lock:
                self._is_paused = not self._is_paused
    
    def show_menu(self) -> None:
        """Affiche le menu Pomodoro avec affichage dynamique optionnel."""
        while True:
            self._clear_screen()
            settings = self._get_settings()
            
            print("\n" + "=" * 50)
            print("           🍅 POMODORO TIMER")
            print("=" * 50)
            
            # Statut actuel
            print(f"\nStatut: {self.get_status()}")
            if self._is_running:
                print(f"       {self.get_progress_bar()}")
            print(f"Sessions aujourd'hui: {self._get_today_sessions()}")
            print(f"Sessions totales: {self._sessions_completed} (cette session)")
            
            # Paramètres actuels
            print(f"\nConfiguration:")
            print(f"  • Travail: {settings['work_duration']} min")
            print(f"  • Pause courte: {settings['short_break']} min")
            print(f"  • Pause longue: {settings['long_break']} min")
            
            print("\n  1. 🍅 Démarrer Pomodoro (travail)")
            print("  2. ☕ Pause courte")
            print("  3. 🌴 Pause longue")
            
            if self._is_running:
                print("  4. ⏸️  Pause/Reprendre")
                print("  5. ⏹️  Arrêter")
                print("  W. 👁️  Mode Watch (affichage dynamique)")
            
            print("\n  6. 📊 Statistiques")
            print("  7. ⚙️  Paramètres")
            print("  R. Retour (timer continue en arrière-plan)")
            
            choice = input("\nChoix: ").strip().lower()
            
            if choice == "1":
                self.start_timer("work")
                print("\n💡 Conseil: Utilisez 'W' pour le mode Watch avec affichage dynamique")
                input("\nAppuyez sur Entrée...")
            elif choice == "2":
                self.start_timer("short_break")
                input("\nAppuyez sur Entrée...")
            elif choice == "3":
                self.start_timer("long_break")
                input("\nAppuyez sur Entrée...")
            elif choice == "4" and self._is_running:
                self.pause_timer()
                input("\nAppuyez sur Entrée...")
            elif choice == "5" and self._is_running:
                self.stop_timer()
                input("\nAppuyez sur Entrée...")
            elif choice == "w" and self._is_running:
                self._display_dynamic_timer()
            elif choice == "6":
                self._show_stats()
            elif choice == "7":
                self._show_settings()
            elif choice == "r":
                if self._is_running:
                    print("\n✓ Le timer continue en arrière-plan.")
                    print("  Vous verrez le statut dans le menu principal.")
                    time.sleep(1.5)
                break
    
    def _get_today_sessions(self) -> int:
        """Retourne le nombre de sessions aujourd'hui."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self._stats.get("daily", {}).get(today, {}).get("sessions", 0)
    
    def _show_stats(self) -> None:
        """Affiche les statistiques."""
        self._clear_screen()
        print("\n" + "=" * 50)
        print("           📊 STATISTIQUES POMODORO")
        print("=" * 50)
        
        settings = self._get_settings()
        total_sessions = self._stats.get("total_sessions", 0)
        total_minutes = self._stats.get("total_minutes", 0)
        streak = self._stats.get("streak", 0)
        
        print(f"\n📈 Totaux:")
        print(f"   • Sessions complétées: {total_sessions}")
        print(f"   • Temps total: {total_minutes // 60}h {total_minutes % 60}min")
        print(f"   • Série actuelle: {streak} jour(s)")
        
        # Derniers 7 jours
        print(f"\n📅 Derniers 7 jours:")
        daily = self._stats.get("daily", {})
        for i in range(6, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            day_data = daily.get(date, {"sessions": 0, "minutes": 0})
            sessions = day_data.get("sessions", 0)
            minutes = day_data.get("minutes", 0)
            bar = "█" * min(sessions, 10)
            print(f"   {date}: {bar} {sessions} sessions ({minutes} min)")
        
        input("\nAppuyez sur Entrée...")
    
    def _show_settings(self) -> None:
        """Menu des paramètres."""
        while True:
            self._clear_screen()
            settings = self._get_settings()
            
            print("\n" + "=" * 50)
            print("           ⚙️  PARAMÈTRES POMODORO")
            print("=" * 50)
            
            print(f"\n  1. Durée travail: {settings['work_duration']} min")
            print(f"  2. Pause courte: {settings['short_break']} min")
            print(f"  3. Pause longue: {settings['long_break']} min")
            print(f"  4. Pause longue après: {settings['long_break_after']} sessions")
            print(f"  5. Son: {'Activé' if settings['sound_enabled'] else 'Désactivé'}")
            print("\n  R. Retour")
            
            choice = input("\nChoix: ").strip().lower()
            
            if choice == "1":
                val = input("Durée travail (minutes): ").strip()
                try:
                    self._save_setting("work_duration", int(val))
                except ValueError:
                    print("Valeur invalide.")
            elif choice == "2":
                val = input("Durée pause courte (minutes): ").strip()
                try:
                    self._save_setting("short_break", int(val))
                except ValueError:
                    print("Valeur invalide.")
            elif choice == "3":
                val = input("Durée pause longue (minutes): ").strip()
                try:
                    self._save_setting("long_break", int(val))
                except ValueError:
                    print("Valeur invalide.")
            elif choice == "4":
                val = input("Pause longue après N sessions: ").strip()
                try:
                    self._save_setting("long_break_after", int(val))
                except ValueError:
                    print("Valeur invalide.")
            elif choice == "5":
                self._save_setting("sound_enabled", not settings['sound_enabled'])
                print(f"Son: {'Activé' if not settings['sound_enabled'] else 'Désactivé'}")
            elif choice == "r":
                break
            
            if choice in ["1", "2", "3", "4"]:
                input("\nAppuyez sur Entrée...")
    
    def _save_setting(self, key: str, value: Any) -> None:
        """Sauvegarde un paramètre."""
        if self._program:
            self._program.plugin_manager.set_plugin_setting("pomodoro", key, value)
            print(f"✓ Paramètre sauvegardé.")
    
    def _clear_screen(self) -> None:
        """Nettoie l'écran (cross-platform)."""
        os.system('cls' if os.name == 'nt' else 'clear')
