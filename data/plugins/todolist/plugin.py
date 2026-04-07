# data/plugins/todolist/plugin.py
"""
Plugin Todolist - Gestionnaire de tâches.
Compatible Windows et Linux.
"""
import os
import sys
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

# Import relatif pour le système de plugins
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from plugins.base import Plugin, PluginMeta, HookType


class TaskPriority(Enum):
    """Priorités des tâches."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class TaskStatus(Enum):
    """Statuts des tâches."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class Task:
    """Représente une tâche."""
    
    def __init__(
        self,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        status: TaskStatus = TaskStatus.TODO,
        due_date: Optional[str] = None,
        tags: List[str] = None,
        task_id: str = None,
        created_at: str = None,
        completed_at: str = None
    ):
        self.id = task_id or str(uuid.uuid4())[:8]
        self.title = title
        self.description = description
        self.priority = priority
        self.status = status
        self.due_date = due_date
        self.tags = tags or []
        self.created_at = created_at or datetime.now().isoformat()
        self.completed_at = completed_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la tâche en dictionnaire."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "due_date": self.due_date,
            "tags": self.tags,
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Crée une tâche depuis un dictionnaire."""
        return cls(
            task_id=data.get("id"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            priority=TaskPriority(data.get("priority", 2)),
            status=TaskStatus(data.get("status", "todo")),
            due_date=data.get("due_date"),
            tags=data.get("tags", []),
            created_at=data.get("created_at"),
            completed_at=data.get("completed_at")
        )
    
    def get_priority_emoji(self) -> str:
        """Retourne l'emoji de priorité."""
        emojis = {
            TaskPriority.LOW: "🟢",
            TaskPriority.MEDIUM: "🟡",
            TaskPriority.HIGH: "🟠",
            TaskPriority.URGENT: "🔴"
        }
        return emojis.get(self.priority, "⚪")
    
    def get_status_emoji(self) -> str:
        """Retourne l'emoji de statut."""
        emojis = {
            TaskStatus.TODO: "⬜",
            TaskStatus.IN_PROGRESS: "🔄",
            TaskStatus.DONE: "✅",
            TaskStatus.CANCELLED: "❌"
        }
        return emojis.get(self.status, "⬜")


class TodolistPlugin(Plugin):
    """
    Plugin Todolist - Gestionnaire de tâches.
    
    Fonctionnalités:
    - Création, modification, suppression de tâches
    - Priorités et statuts
    - Tags et filtrage
    - Dates d'échéance
    - Export/Import
    """
    
    def __init__(self):
        self._program = None
        self._data_file = None
        self._tasks: List[Task] = []
    
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="todolist",
            version="1.0.0",
            author="Gestionnaire de Scripts",
            description="Gestionnaire de tâches avec priorités et tags",
            homepage="",
            license="MIT"
        )
    
    def on_load(self, program: Any) -> bool:
        """Initialise le plugin."""
        self._program = program
        data_path = Path(program.current_path) / "data" / "plugins" / "todolist"
        data_path.mkdir(parents=True, exist_ok=True)
        self._data_file = data_path / "tasks.json"
        self._load_tasks()
        return True
    
    def on_unload(self, program: Any) -> None:
        """Sauvegarde les tâches."""
        self._save_tasks()
    
    def get_hooks(self) -> Dict[HookType, Any]:
        return {
            HookType.ON_STARTUP: self._on_startup,
            HookType.ON_SHUTDOWN: self._on_shutdown
        }
    
    def get_menu_items(self) -> List[Dict[str, Any]]:
        return [
            {"key": "W", "label": "Todo List           [W]", "handler": self.show_menu}
        ]
    
    def _on_startup(self) -> None:
        """Hook au démarrage - affiche les tâches urgentes."""
        urgent = self._get_urgent_tasks()
        if urgent:
            print(f"\n⚠️  {len(urgent)} tâche(s) urgente(s) en attente!")
    
    def _on_shutdown(self) -> None:
        """Hook à la fermeture."""
        self._save_tasks()
    
    def _load_tasks(self) -> None:
        """Charge les tâches depuis le fichier."""
        try:
            if self._data_file and self._data_file.exists():
                with open(self._data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._tasks = [Task.from_dict(t) for t in data.get("tasks", [])]
        except (json.JSONDecodeError, IOError) as e:
            print(f"[Todolist] Erreur chargement: {e}")
            self._tasks = []
    
    def _save_tasks(self) -> None:
        """Sauvegarde les tâches."""
        try:
            if self._data_file:
                data = {"tasks": [t.to_dict() for t in self._tasks]}
                with open(self._data_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[Todolist] Erreur sauvegarde: {e}")
    
    def _get_urgent_tasks(self) -> List[Task]:
        """Retourne les tâches urgentes non terminées."""
        return [
            t for t in self._tasks
            if t.status in [TaskStatus.TODO, TaskStatus.IN_PROGRESS]
            and t.priority == TaskPriority.URGENT
        ]
    
    def _get_pending_tasks(self) -> List[Task]:
        """Retourne les tâches non terminées."""
        return [
            t for t in self._tasks
            if t.status in [TaskStatus.TODO, TaskStatus.IN_PROGRESS]
        ]
    
    def _clear_screen(self) -> None:
        """Nettoie l'écran (cross-platform)."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_menu(self) -> None:
        """Affiche le menu principal."""
        while True:
            self._clear_screen()
            pending = self._get_pending_tasks()
            
            print("\n" + "=" * 50)
            print("           📝 TODO LIST")
            print("=" * 50)
            
            # Résumé
            total = len(self._tasks)
            done = len([t for t in self._tasks if t.status == TaskStatus.DONE])
            print(f"\n📊 {done}/{total} tâches terminées")
            
            # Liste des tâches en attente
            if pending:
                print(f"\n📋 Tâches en cours ({len(pending)}):")
                for i, task in enumerate(pending[:10], 1):
                    status = task.get_status_emoji()
                    priority = task.get_priority_emoji()
                    title = task.title[:35] + "..." if len(task.title) > 35 else task.title
                    print(f"   {i}. {status} {priority} {title}")
                if len(pending) > 10:
                    print(f"   ... et {len(pending) - 10} autres")
            else:
                print("\n✨ Aucune tâche en attente!")
            
            print("\n  1. ➕ Nouvelle tâche")
            print("  2. 📋 Voir toutes les tâches")
            print("  3. ✅ Marquer comme terminée")
            print("  4. 🔄 Changer le statut")
            print("  5. ✏️  Modifier une tâche")
            print("  6. 🗑️  Supprimer une tâche")
            print("  7. 🔍 Filtrer/Rechercher")
            print("  8. 📊 Statistiques")
            print("  R. Retour")
            
            choice = input("\nChoix: ").strip().lower()
            
            if choice == "1":
                self._add_task()
            elif choice == "2":
                self._show_all_tasks()
            elif choice == "3":
                self._mark_done()
            elif choice == "4":
                self._change_status()
            elif choice == "5":
                self._edit_task()
            elif choice == "6":
                self._delete_task()
            elif choice == "7":
                self._filter_tasks()
            elif choice == "8":
                self._show_stats()
            elif choice == "r":
                break
    
    def _add_task(self) -> None:
        """Ajoute une nouvelle tâche."""
        self._clear_screen()
        print("\n" + "=" * 50)
        print("           ➕ NOUVELLE TÂCHE")
        print("=" * 50)
        
        # Titre (obligatoire)
        title = input("\nTitre: ").strip()
        if not title:
            print("❌ Le titre est obligatoire.")
            input("\nAppuyez sur Entrée...")
            return
        
        # Description (optionnelle)
        description = input("Description (optionnel): ").strip()
        
        # Priorité
        print("\nPriorité:")
        print("  1. 🟢 Basse")
        print("  2. 🟡 Moyenne (défaut)")
        print("  3. 🟠 Haute")
        print("  4. 🔴 Urgente")
        
        prio_choice = input("Choix (1-4): ").strip()
        priority_map = {
            "1": TaskPriority.LOW,
            "2": TaskPriority.MEDIUM,
            "3": TaskPriority.HIGH,
            "4": TaskPriority.URGENT
        }
        priority = priority_map.get(prio_choice, TaskPriority.MEDIUM)
        
        # Tags (optionnels)
        tags_input = input("\nTags (séparés par virgule, optionnel): ").strip()
        tags = [t.strip() for t in tags_input.split(",") if t.strip()] if tags_input else []
        
        # Date d'échéance (optionnelle)
        due_date = input("Date d'échéance (YYYY-MM-DD, optionnel): ").strip()
        if due_date:
            try:
                datetime.strptime(due_date, "%Y-%m-%d")
            except ValueError:
                print("⚠️  Format de date invalide, ignoré.")
                due_date = None
        else:
            due_date = None
        
        # Créer la tâche
        task = Task(
            title=title,
            description=description,
            priority=priority,
            tags=tags,
            due_date=due_date
        )
        
        self._tasks.append(task)
        self._save_tasks()
        
        print(f"\n✅ Tâche '{title}' ajoutée avec succès!")
        input("\nAppuyez sur Entrée...")
    
    def _show_all_tasks(self, tasks: List[Task] = None, title: str = "TOUTES LES TÂCHES") -> None:
        """Affiche toutes les tâches."""
        self._clear_screen()
        tasks = tasks if tasks is not None else self._tasks
        
        print("\n" + "=" * 60)
        print(f"           📋 {title}")
        print("=" * 60)
        
        if not tasks:
            print("\n📭 Aucune tâche.")
            input("\nAppuyez sur Entrée...")
            return
        
        # Tri par priorité puis par statut
        sorted_tasks = sorted(
            tasks,
            key=lambda t: (t.status.value != "todo", -t.priority.value)
        )
        
        print(f"\n{'#':<4} {'Stat':<5} {'Prio':<5} {'Titre':<30} {'Tags':<15}")
        print("-" * 60)
        
        for i, task in enumerate(sorted_tasks, 1):
            status = task.get_status_emoji()
            priority = task.get_priority_emoji()
            title = task.title[:28] + ".." if len(task.title) > 28 else task.title
            tags = ", ".join(task.tags[:2]) if task.tags else "-"
            if len(tags) > 13:
                tags = tags[:11] + ".."
            
            print(f"{i:<4} {status:<5} {priority:<5} {title:<30} {tags:<15}")
            
            # Afficher la description si présente
            if task.description:
                desc = task.description[:55] + "..." if len(task.description) > 55 else task.description
                print(f"     └─ {desc}")
        
        print("-" * 60)
        print(f"Total: {len(tasks)} tâche(s)")
        
        input("\nAppuyez sur Entrée...")
    
    def _select_task(self, filter_status: List[TaskStatus] = None) -> Optional[Task]:
        """Permet de sélectionner une tâche."""
        tasks = self._tasks
        if filter_status:
            tasks = [t for t in tasks if t.status in filter_status]
        
        if not tasks:
            print("\n📭 Aucune tâche disponible.")
            return None
        
        print("\nTâches:")
        for i, task in enumerate(tasks, 1):
            status = task.get_status_emoji()
            priority = task.get_priority_emoji()
            print(f"  {i}. {status} {priority} {task.title}")
        
        choice = input("\nNuméro de la tâche (ou R pour annuler): ").strip().lower()
        
        if choice == "r":
            return None
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(tasks):
                return tasks[idx]
        except ValueError:
            pass
        
        print("❌ Choix invalide.")
        return None
    
    def _mark_done(self) -> None:
        """Marque une tâche comme terminée."""
        self._clear_screen()
        print("\n" + "=" * 50)
        print("           ✅ MARQUER COMME TERMINÉE")
        print("=" * 50)
        
        pending = [t for t in self._tasks if t.status in [TaskStatus.TODO, TaskStatus.IN_PROGRESS]]
        
        task = self._select_task([TaskStatus.TODO, TaskStatus.IN_PROGRESS])
        if task:
            task.status = TaskStatus.DONE
            task.completed_at = datetime.now().isoformat()
            self._save_tasks()
            print(f"\n✅ '{task.title}' marquée comme terminée!")
        
        input("\nAppuyez sur Entrée...")
    
    def _change_status(self) -> None:
        """Change le statut d'une tâche."""
        self._clear_screen()
        print("\n" + "=" * 50)
        print("           🔄 CHANGER LE STATUT")
        print("=" * 50)
        
        task = self._select_task()
        if not task:
            input("\nAppuyez sur Entrée...")
            return
        
        print(f"\nTâche: {task.title}")
        print(f"Statut actuel: {task.get_status_emoji()} {task.status.value}")
        
        print("\nNouveau statut:")
        print("  1. ⬜ À faire")
        print("  2. 🔄 En cours")
        print("  3. ✅ Terminée")
        print("  4. ❌ Annulée")
        
        choice = input("\nChoix: ").strip()
        
        status_map = {
            "1": TaskStatus.TODO,
            "2": TaskStatus.IN_PROGRESS,
            "3": TaskStatus.DONE,
            "4": TaskStatus.CANCELLED
        }
        
        if choice in status_map:
            task.status = status_map[choice]
            if task.status == TaskStatus.DONE:
                task.completed_at = datetime.now().isoformat()
            self._save_tasks()
            print(f"\n✅ Statut mis à jour!")
        else:
            print("❌ Choix invalide.")
        
        input("\nAppuyez sur Entrée...")
    
    def _edit_task(self) -> None:
        """Modifie une tâche."""
        self._clear_screen()
        print("\n" + "=" * 50)
        print("           ✏️  MODIFIER UNE TÂCHE")
        print("=" * 50)
        
        task = self._select_task()
        if not task:
            input("\nAppuyez sur Entrée...")
            return
        
        print(f"\nModification de: {task.title}")
        print("(Appuyez sur Entrée pour garder la valeur actuelle)")
        
        # Titre
        new_title = input(f"\nNouveau titre [{task.title}]: ").strip()
        if new_title:
            task.title = new_title
        
        # Description
        new_desc = input(f"Nouvelle description [{task.description or '-'}]: ").strip()
        if new_desc:
            task.description = new_desc
        
        # Priorité
        print(f"\nPriorité actuelle: {task.get_priority_emoji()}")
        print("  1. 🟢 Basse | 2. 🟡 Moyenne | 3. 🟠 Haute | 4. 🔴 Urgente")
        new_prio = input("Nouvelle priorité (1-4, Entrée pour garder): ").strip()
        
        priority_map = {
            "1": TaskPriority.LOW,
            "2": TaskPriority.MEDIUM,
            "3": TaskPriority.HIGH,
            "4": TaskPriority.URGENT
        }
        if new_prio in priority_map:
            task.priority = priority_map[new_prio]
        
        # Tags
        current_tags = ", ".join(task.tags) if task.tags else "-"
        new_tags = input(f"Tags [{current_tags}]: ").strip()
        if new_tags:
            task.tags = [t.strip() for t in new_tags.split(",") if t.strip()]
        
        self._save_tasks()
        print("\n✅ Tâche mise à jour!")
        input("\nAppuyez sur Entrée...")
    
    def _delete_task(self) -> None:
        """Supprime une tâche."""
        self._clear_screen()
        print("\n" + "=" * 50)
        print("           🗑️  SUPPRIMER UNE TÂCHE")
        print("=" * 50)
        
        task = self._select_task()
        if not task:
            input("\nAppuyez sur Entrée...")
            return
        
        confirm = input(f"\n⚠️  Supprimer '{task.title}'? (o/N): ").strip().lower()
        
        if confirm == "o":
            self._tasks.remove(task)
            self._save_tasks()
            print("\n✅ Tâche supprimée!")
        else:
            print("\n❌ Suppression annulée.")
        
        input("\nAppuyez sur Entrée...")
    
    def _filter_tasks(self) -> None:
        """Filtre et recherche dans les tâches."""
        while True:
            self._clear_screen()
            print("\n" + "=" * 50)
            print("           🔍 FILTRER / RECHERCHER")
            print("=" * 50)
            
            print("\n  1. Par statut")
            print("  2. Par priorité")
            print("  3. Par tag")
            print("  4. Recherche par titre")
            print("  5. Tâches en retard")
            print("  R. Retour")
            
            choice = input("\nChoix: ").strip().lower()
            
            if choice == "1":
                self._filter_by_status()
            elif choice == "2":
                self._filter_by_priority()
            elif choice == "3":
                self._filter_by_tag()
            elif choice == "4":
                self._search_by_title()
            elif choice == "5":
                self._show_overdue()
            elif choice == "r":
                break
    
    def _filter_by_status(self) -> None:
        """Filtre par statut."""
        print("\nStatut:")
        print("  1. ⬜ À faire")
        print("  2. 🔄 En cours")
        print("  3. ✅ Terminées")
        print("  4. ❌ Annulées")
        
        choice = input("\nChoix: ").strip()
        
        status_map = {
            "1": TaskStatus.TODO,
            "2": TaskStatus.IN_PROGRESS,
            "3": TaskStatus.DONE,
            "4": TaskStatus.CANCELLED
        }
        
        if choice in status_map:
            status = status_map[choice]
            filtered = [t for t in self._tasks if t.status == status]
            self._show_all_tasks(filtered, f"TÂCHES - {status.value.upper()}")
    
    def _filter_by_priority(self) -> None:
        """Filtre par priorité."""
        print("\nPriorité:")
        print("  1. 🟢 Basse")
        print("  2. 🟡 Moyenne")
        print("  3. 🟠 Haute")
        print("  4. 🔴 Urgente")
        
        choice = input("\nChoix: ").strip()
        
        priority_map = {
            "1": TaskPriority.LOW,
            "2": TaskPriority.MEDIUM,
            "3": TaskPriority.HIGH,
            "4": TaskPriority.URGENT
        }
        
        if choice in priority_map:
            priority = priority_map[choice]
            filtered = [t for t in self._tasks if t.priority == priority]
            self._show_all_tasks(filtered, f"PRIORITÉ {priority.name}")
    
    def _filter_by_tag(self) -> None:
        """Filtre par tag."""
        # Collecter tous les tags uniques
        all_tags = set()
        for task in self._tasks:
            all_tags.update(task.tags)
        
        if not all_tags:
            print("\n📭 Aucun tag défini.")
            input("\nAppuyez sur Entrée...")
            return
        
        print("\nTags disponibles:")
        tags_list = sorted(all_tags)
        for i, tag in enumerate(tags_list, 1):
            count = len([t for t in self._tasks if tag in t.tags])
            print(f"  {i}. {tag} ({count})")
        
        choice = input("\nNuméro du tag: ").strip()
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(tags_list):
                tag = tags_list[idx]
                filtered = [t for t in self._tasks if tag in t.tags]
                self._show_all_tasks(filtered, f"TAG: {tag}")
        except ValueError:
            print("❌ Choix invalide.")
            input("\nAppuyez sur Entrée...")
    
    def _search_by_title(self) -> None:
        """Recherche par titre."""
        query = input("\nRecherche: ").strip().lower()
        
        if query:
            filtered = [
                t for t in self._tasks
                if query in t.title.lower() or query in t.description.lower()
            ]
            self._show_all_tasks(filtered, f"RECHERCHE: '{query}'")
    
    def _show_overdue(self) -> None:
        """Affiche les tâches en retard."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        overdue = [
            t for t in self._tasks
            if t.due_date and t.due_date < today
            and t.status in [TaskStatus.TODO, TaskStatus.IN_PROGRESS]
        ]
        
        self._show_all_tasks(overdue, "TÂCHES EN RETARD")
    
    def _show_stats(self) -> None:
        """Affiche les statistiques."""
        self._clear_screen()
        print("\n" + "=" * 50)
        print("           📊 STATISTIQUES")
        print("=" * 50)
        
        total = len(self._tasks)
        todo = len([t for t in self._tasks if t.status == TaskStatus.TODO])
        in_progress = len([t for t in self._tasks if t.status == TaskStatus.IN_PROGRESS])
        done = len([t for t in self._tasks if t.status == TaskStatus.DONE])
        cancelled = len([t for t in self._tasks if t.status == TaskStatus.CANCELLED])
        
        print(f"\n📈 Vue d'ensemble:")
        print(f"   • Total: {total} tâches")
        print(f"   • ⬜ À faire: {todo}")
        print(f"   • 🔄 En cours: {in_progress}")
        print(f"   • ✅ Terminées: {done}")
        print(f"   • ❌ Annulées: {cancelled}")
        
        if total > 0:
            completion_rate = (done / total) * 100
            print(f"\n📊 Taux de complétion: {completion_rate:.1f}%")
            
            # Barre de progression
            filled = int(completion_rate / 5)
            bar = "█" * filled + "░" * (20 - filled)
            print(f"   [{bar}]")
        
        # Par priorité
        print(f"\n🎯 Par priorité:")
        for priority in TaskPriority:
            count = len([t for t in self._tasks if t.priority == priority and t.status != TaskStatus.DONE])
            emoji = {
                TaskPriority.LOW: "🟢",
                TaskPriority.MEDIUM: "🟡",
                TaskPriority.HIGH: "🟠",
                TaskPriority.URGENT: "🔴"
            }.get(priority, "⚪")
            print(f"   {emoji} {priority.name}: {count} en attente")
        
        # Tags les plus utilisés
        all_tags = {}
        for task in self._tasks:
            for tag in task.tags:
                all_tags[tag] = all_tags.get(tag, 0) + 1
        
        if all_tags:
            print(f"\n🏷️  Tags populaires:")
            sorted_tags = sorted(all_tags.items(), key=lambda x: -x[1])[:5]
            for tag, count in sorted_tags:
                print(f"   • {tag}: {count}")
        
        input("\nAppuyez sur Entrée...")
