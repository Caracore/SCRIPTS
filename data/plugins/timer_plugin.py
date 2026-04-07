#!/usr/bin/env python3
# plugins/timer_plugin.py
"""
Plugin Timer - Compteur de temps d'utilisation du gestionnaire.
Affiche le temps de session actuelle et le temps total accumulé.
"""
import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, List, Callable

try:
    from plugins.base import Plugin, PluginMeta, HookType
except ImportError:
    from base import Plugin, PluginMeta, HookType


class TimerPlugin(Plugin):
    """Plugin de suivi du temps d'utilisation."""
    
    def __init__(self):
        self.session_start: Optional[float] = None
        self.data_file: Optional[Path] = None
        self.program = None
        self.stats = {
            "total_seconds": 0,
            "session_count": 0,
            "first_use": None,
            "last_use": None,
            "sessions": []  # Historique des 10 dernières sessions
        }
        self._hooks = {}
        self._menu_items = []
    
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="Timer",
            version="1.0.0",
            author="Script Manager",
            description="Compteur de temps d'utilisation (session + total)"
        )
    
    def on_load(self, program) -> bool:
        """Initialisation au chargement du plugin."""
        self.program = program
        self.data_file = Path(program.current_path) / "data" / "timer_stats.json"
        
        # Charger les statistiques existantes
        self._load_stats()
        
        # Démarrer le chrono de session
        self.session_start = time.time()
        
        # Enregistrer les hooks
        self._hooks = {
            HookType.ON_STARTUP: self._on_startup,
            HookType.ON_SHUTDOWN: self._on_shutdown,
        }
        
        # Ajouter l'entrée de menu
        self._menu_items = [{
            "key": "ti",
            "label": "Timer & Stats         [TI]",
            "handler": self._show_timer_menu
        }]
        
        return True
    
    def on_unload(self, program=None):
        """Sauvegarde à la fermeture."""
        self._save_session()
    
    def get_hooks(self) -> Dict[HookType, Callable]:
        """Retourne les hooks enregistrés."""
        return self._hooks
    
    def get_menu_items(self) -> List[Dict[str, Any]]:
        """Retourne les éléments de menu."""
        return self._menu_items
    
    def _load_stats(self):
        """Charge les statistiques depuis le fichier."""
        if self.data_file and self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.stats.update(loaded)
            except Exception as e:
                print(f"[Timer] Erreur chargement stats: {e}")
    
    def _save_stats(self):
        """Sauvegarde les statistiques."""
        if self.data_file:
            try:
                self.data_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.data_file, "w", encoding="utf-8") as f:
                    json.dump(self.stats, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[Timer] Erreur sauvegarde stats: {e}")
    
    def _save_session(self):
        """Enregistre la session actuelle."""
        if self.session_start is None:
            return
        
        session_duration = time.time() - self.session_start
        now = datetime.now().isoformat()
        
        # Mettre à jour les stats
        self.stats["total_seconds"] += session_duration
        self.stats["session_count"] += 1
        self.stats["last_use"] = now
        
        if self.stats["first_use"] is None:
            self.stats["first_use"] = now
        
        # Ajouter à l'historique (garder les 10 dernières)
        session_info = {
            "start": datetime.fromtimestamp(self.session_start).isoformat(),
            "end": now,
            "duration_seconds": round(session_duration, 1)
        }
        self.stats["sessions"].append(session_info)
        self.stats["sessions"] = self.stats["sessions"][-10:]  # Garder les 10 dernières
        
        self._save_stats()
    
    # =========================================================================
    # HOOKS
    # =========================================================================
    
    def _on_startup(self, **kwargs):
        """Hook au démarrage."""
        self.session_start = time.time()
    
    def _on_shutdown(self, **kwargs):
        """Hook à la fermeture."""
        self._save_session()
    
    # =========================================================================
    # UTILITAIRES
    # =========================================================================
    
    def _format_duration(self, seconds: float) -> str:
        """Formate une durée en format lisible."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
        else:
            days = int(seconds // 86400)
            hours = int((seconds % 86400) // 3600)
            return f"{days}j {hours}h"
    
    def _format_duration_long(self, seconds: float) -> str:
        """Formate une durée en format détaillé."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days} jour{'s' if days > 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} heure{'s' if hours > 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
        if secs > 0 or not parts:
            parts.append(f"{secs} seconde{'s' if secs != 1 else ''}")
        
        return ", ".join(parts)
    
    def get_session_time(self) -> float:
        """Retourne le temps de la session actuelle en secondes."""
        if self.session_start is None:
            return 0
        return time.time() - self.session_start
    
    def get_total_time(self) -> float:
        """Retourne le temps total (sessions précédentes + actuelle)."""
        return self.stats["total_seconds"] + self.get_session_time()
    
    # =========================================================================
    # MENU
    # =========================================================================
    
    def _show_timer_menu(self):
        """Affiche le menu Timer avec les statistiques."""
        while True:
            self.program.clear_screen()
            
            session_time = self.get_session_time()
            total_time = self.get_total_time()
            
            print("\n" + "=" * 55)
            print("               ⏱️  TIMER & STATISTIQUES")
            print("=" * 55)
            
            # Affichage du temps en gros
            print("\n" + " " * 10 + "┌" + "─" * 33 + "┐")
            print(" " * 10 + "│" + " " * 33 + "│")
            
            # Session actuelle
            session_str = self._format_duration(session_time)
            session_line = f"Session: {session_str}".center(33)
            print(" " * 10 + f"│{session_line}│")
            
            print(" " * 10 + "│" + " " * 33 + "│")
            print(" " * 10 + "│" + "─" * 33 + "│")
            print(" " * 10 + "│" + " " * 33 + "│")
            
            # Temps total
            total_str = self._format_duration(total_time)
            total_line = f"Total: {total_str}".center(33)
            print(" " * 10 + f"│{total_line}│")
            
            print(" " * 10 + "│" + " " * 33 + "│")
            print(" " * 10 + "└" + "─" * 33 + "┘")
            
            # Statistiques détaillées
            print("\n" + "-" * 55)
            print("  DÉTAILS")
            print("-" * 55)
            
            print(f"\n  📊 Sessions totales: {self.stats['session_count'] + 1}")
            print(f"  ⏱️  Temps total: {self._format_duration_long(total_time)}")
            print(f"  🕐 Session actuelle: {self._format_duration_long(session_time)}")
            
            if self.stats["first_use"]:
                try:
                    first = datetime.fromisoformat(self.stats["first_use"])
                    print(f"  📅 Première utilisation: {first.strftime('%d/%m/%Y %H:%M')}")
                except:
                    pass
            
            if self.stats["last_use"]:
                try:
                    last = datetime.fromisoformat(self.stats["last_use"])
                    print(f"  📅 Dernière session: {last.strftime('%d/%m/%Y %H:%M')}")
                except:
                    pass
            
            # Moyenne par session
            if self.stats["session_count"] > 0:
                avg = self.stats["total_seconds"] / self.stats["session_count"]
                print(f"  📈 Moyenne/session: {self._format_duration(avg)}")
            
            # Options
            print("\n" + "-" * 55)
            print("  1. Voir l'historique des sessions")
            print("  2. Réinitialiser les statistiques")
            print("  3. Exporter les statistiques")
            print("  R. Retour")
            
            choice = input("\n>> Choix: ").strip().lower()
            
            if choice == "1":
                self._show_history()
            elif choice == "2":
                self._reset_stats()
            elif choice == "3":
                self._export_stats()
            elif choice == "r":
                break
    
    def _show_history(self):
        """Affiche l'historique des sessions."""
        self.program.clear_screen()
        print("\n" + "=" * 55)
        print("          HISTORIQUE DES SESSIONS")
        print("=" * 55)
        
        sessions = self.stats.get("sessions", [])
        
        if not sessions:
            print("\n  Aucune session enregistrée.")
        else:
            print(f"\n  {len(sessions)} dernière(s) session(s):\n")
            
            for i, session in enumerate(reversed(sessions), 1):
                try:
                    start = datetime.fromisoformat(session["start"])
                    duration = self._format_duration(session["duration_seconds"])
                    print(f"  {i}. {start.strftime('%d/%m/%Y %H:%M')} - Durée: {duration}")
                except:
                    print(f"  {i}. Session invalide")
        
        # Session actuelle
        print(f"\n  → Session actuelle: {self._format_duration(self.get_session_time())}")
        
        input("\n  Appuyez sur Entrée...")
    
    def _reset_stats(self):
        """Réinitialise les statistiques."""
        print("\n⚠️  Cette action supprimera toutes les statistiques!")
        confirm = input("Confirmer la réinitialisation? (oui/non): ").strip().lower()
        
        if confirm == "oui":
            self.stats = {
                "total_seconds": 0,
                "session_count": 0,
                "first_use": None,
                "last_use": None,
                "sessions": []
            }
            self.session_start = time.time()  # Redémarrer le chrono
            self._save_stats()
            print("\n[OK] Statistiques réinitialisées!")
        else:
            print("\nAnnulé.")
        
        input("\nAppuyez sur Entrée...")
    
    def _export_stats(self):
        """Exporte les statistiques dans un fichier texte."""
        export_path = Path(self.program.current_path) / "data" / "timer_export.txt"
        
        try:
            session_time = self.get_session_time()
            total_time = self.get_total_time()
            
            content = f"""
╔══════════════════════════════════════════════════════════╗
║           STATISTIQUES DU GESTIONNAIRE DE SCRIPTS        ║
╚══════════════════════════════════════════════════════════╝

Exporté le: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}

RÉSUMÉ
------
Sessions totales: {self.stats['session_count'] + 1}
Temps total: {self._format_duration_long(total_time)}
Temps session actuelle: {self._format_duration_long(session_time)}

DATES
-----
Première utilisation: {self.stats.get('first_use', 'N/A')}
Dernière session: {self.stats.get('last_use', 'N/A')}

HISTORIQUE DES SESSIONS
-----------------------
"""
            for i, session in enumerate(reversed(self.stats.get("sessions", [])), 1):
                try:
                    start = datetime.fromisoformat(session["start"])
                    duration = self._format_duration(session["duration_seconds"])
                    content += f"{i}. {start.strftime('%d/%m/%Y %H:%M')} - Durée: {duration}\n"
                except:
                    pass
            
            export_path.write_text(content, encoding="utf-8")
            print(f"\n[OK] Exporté vers: {export_path}")
            
        except Exception as e:
            print(f"\n[!] Erreur: {e}")
        
        input("\nAppuyez sur Entrée...")


# Point d'entrée pour le chargement du plugin
def get_plugin():
    """Retourne l'instance du plugin."""
    return TimerPlugin()
