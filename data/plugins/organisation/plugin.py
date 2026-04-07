# data/plugins/organisation/plugin.py
"""
Plugin Organisation - Organise les dossiers et le Bureau.
Fonctionnalités:
- Renommer fichiers/dossiers
- Déplacer (stocker) fichiers/dossiers
- Créer des dossiers pour regrouper des fichiers
- Ranger par ordre alphabétique, regex ou catégories/tags

SÉCURITÉ: Aucune suppression, aucun privilège admin.
"""
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from plugins.base import Plugin, PluginMeta, HookType


class OrganisationPlugin(Plugin):
    """Plugin pour organiser les dossiers et le Bureau."""
    
    # Catégories prédéfinies avec leurs extensions
    CATEGORIES = {
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff"],
        "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx"],
        "Vidéos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"],
        "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
        "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
        "Code": [".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".h", ".json", ".xml"],
        "Exécutables": [".exe", ".msi", ".bat", ".cmd", ".ps1", ".sh"],
    }
    
    # Dossiers système à ne jamais toucher
    PROTECTED_FOLDERS = [
        "Windows", "Program Files", "Program Files (x86)", "ProgramData",
        "System Volume Information", "$Recycle.Bin", "Recovery", "PerfLogs"
    ]
    
    PROTECTED_FILES = [
        "desktop.ini", "thumbs.db", "ntuser.dat", "pagefile.sys", "hiberfil.sys"
    ]
    
    def __init__(self):
        self.program = None
        self.current_path = None
        self.history: List[Dict[str, Any]] = []  # Historique des opérations
    
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="organisation",
            version="1.0.0",
            author="SCRIPTS Manager",
            description="Organise les dossiers et le Bureau (renommer, déplacer, créer dossiers)",
            dependencies=[],
            license="MIT"
        )
    
    def on_load(self, program: Any) -> bool:
        """Chargement du plugin."""
        self.program = program
        self.current_path = program.current_path
        return True
    
    def on_unload(self, program: Any) -> None:
        """Déchargement du plugin."""
        pass
    
    def get_menu_items(self) -> List[Dict[str, Any]]:
        """Ajoute les options au menu."""
        return [
            {
                "key": "org",
                "label": "📁 Organisation (dossiers/Bureau)",
                "handler": self.show_organisation_menu
            }
        ]
    
    def get_settings_schema(self) -> Dict[str, Any]:
        """Schéma des paramètres du plugin."""
        return {
            "default_desktop_path": {
                "type": "string",
                "default": str(Path.home() / "Desktop"),
                "description": "Chemin du Bureau par défaut"
            },
            "create_undo_backup": {
                "type": "boolean",
                "default": True,
                "description": "Créer un backup pour annuler les opérations"
            }
        }
    
    # ==================== MENU PRINCIPAL ====================
    
    def show_organisation_menu(self) -> None:
        """Affiche le menu principal d'organisation."""
        while True:
            self._clear_screen()
            print("\n" + "=" * 60)
            print("📁 ORGANISATION - Gestionnaire de Fichiers/Dossiers")
            print("=" * 60)
            print("\n⚠️  Mode sécurisé: Pas de suppression, pas de fichiers système\n")
            
            print("1. 🔄 Renommer des fichiers/dossiers")
            print("2. 📦 Déplacer (stocker) des fichiers/dossiers")
            print("3. 📂 Créer des dossiers pour fichiers")
            print("4. 🗂️  Ranger par ordre alphabétique")
            print("5. 🔍 Ranger par expression régulière (regex)")
            print("6. 🏷️  Ranger par catégories/tags")
            print("7. 📋 Voir l'historique des opérations")
            print("8. ⬅️  Retour au menu principal")
            
            choice = input("\nVotre choix: ").strip()
            
            if choice == "1":
                self.rename_menu()
            elif choice == "2":
                self.move_menu()
            elif choice == "3":
                self.create_folder_menu()
            elif choice == "4":
                self.sort_alphabetical_menu()
            elif choice == "5":
                self.sort_regex_menu()
            elif choice == "6":
                self.sort_categories_menu()
            elif choice == "7":
                self.show_history()
            elif choice == "8":
                break
    
    # ==================== RENOMMER ====================
    
    def rename_menu(self) -> None:
        """Menu de renommage."""
        self._clear_screen()
        print("\n" + "=" * 60)
        print("🔄 RENOMMER des fichiers/dossiers")
        print("=" * 60)
        
        print("\n1. Renommer un élément unique")
        print("2. Renommer en masse (préfixe/suffixe)")
        print("3. Renommer avec numérotation")
        print("4. Rechercher et remplacer dans les noms")
        print("5. ⬅️  Retour")
        
        choice = input("\nVotre choix: ").strip()
        
        if choice == "1":
            self._rename_single()
        elif choice == "2":
            self._rename_batch_prefix_suffix()
        elif choice == "3":
            self._rename_with_numbers()
        elif choice == "4":
            self._rename_search_replace()
    
    def _rename_single(self) -> None:
        """Renomme un seul fichier/dossier."""
        target_path = self._select_path("Chemin du fichier/dossier à renommer")
        if not target_path:
            return
        
        print(f"\nNom actuel: {target_path.name}")
        new_name = input("Nouveau nom (sans chemin): ").strip()
        
        if not new_name:
            print("❌ Nom invalide")
            return
        
        if not self._is_safe_name(new_name):
            print("❌ Nom contient des caractères interdits")
            return
        
        new_path = target_path.parent / new_name
        
        if new_path.exists():
            print("❌ Un élément avec ce nom existe déjà")
            return
        
        if self._confirm_action(f"Renommer '{target_path.name}' en '{new_name}'"):
            try:
                target_path.rename(new_path)
                self._log_operation("rename", str(target_path), str(new_path))
                print(f"✅ Renommé avec succès!")
            except Exception as e:
                print(f"❌ Erreur: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def _rename_batch_prefix_suffix(self) -> None:
        """Renomme en ajoutant préfixe/suffixe."""
        folder_path = self._select_path("Chemin du dossier contenant les fichiers", folder_only=True)
        if not folder_path:
            return
        
        print("\n1. Ajouter un préfixe")
        print("2. Ajouter un suffixe")
        print("3. Les deux")
        
        choice = input("\nVotre choix: ").strip()
        
        prefix = ""
        suffix = ""
        
        if choice in ["1", "3"]:
            prefix = input("Préfixe à ajouter: ").strip()
        if choice in ["2", "3"]:
            suffix = input("Suffixe à ajouter (avant l'extension): ").strip()
        
        # Lister les fichiers
        items = [f for f in folder_path.iterdir() if not self._is_protected(f)]
        
        if not items:
            print("❌ Aucun fichier à traiter")
            return
        
        print(f"\n{len(items)} fichier(s) à renommer:")
        for item in items[:10]:
            stem = item.stem if item.is_file() else item.name
            ext = item.suffix if item.is_file() else ""
            new_name = f"{prefix}{stem}{suffix}{ext}"
            print(f"  {item.name} → {new_name}")
        if len(items) > 10:
            print(f"  ... et {len(items) - 10} autres")
        
        if self._confirm_action("Appliquer ces renommages"):
            count = 0
            for item in items:
                try:
                    stem = item.stem if item.is_file() else item.name
                    ext = item.suffix if item.is_file() else ""
                    new_name = f"{prefix}{stem}{suffix}{ext}"
                    new_path = item.parent / new_name
                    
                    if not new_path.exists():
                        item.rename(new_path)
                        self._log_operation("rename", str(item), str(new_path))
                        count += 1
                except Exception as e:
                    print(f"⚠️ Erreur pour {item.name}: {e}")
            
            print(f"✅ {count} fichier(s) renommé(s)")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def _rename_with_numbers(self) -> None:
        """Renomme avec numérotation séquentielle."""
        folder_path = self._select_path("Chemin du dossier contenant les fichiers", folder_only=True)
        if not folder_path:
            return
        
        base_name = input("Nom de base (ex: 'photo'): ").strip()
        start_num = input("Numéro de départ (défaut: 1): ").strip()
        start_num = int(start_num) if start_num.isdigit() else 1
        
        padding = input("Nombre de chiffres (ex: 3 pour 001, défaut: 3): ").strip()
        padding = int(padding) if padding.isdigit() else 3
        
        items = sorted([f for f in folder_path.iterdir() if f.is_file() and not self._is_protected(f)])
        
        if not items:
            print("❌ Aucun fichier à traiter")
            return
        
        print(f"\n{len(items)} fichier(s) à renommer:")
        for i, item in enumerate(items[:5]):
            num = str(start_num + i).zfill(padding)
            new_name = f"{base_name}_{num}{item.suffix}"
            print(f"  {item.name} → {new_name}")
        if len(items) > 5:
            print(f"  ... et {len(items) - 5} autres")
        
        if self._confirm_action("Appliquer ces renommages"):
            count = 0
            for i, item in enumerate(items):
                try:
                    num = str(start_num + i).zfill(padding)
                    new_name = f"{base_name}_{num}{item.suffix}"
                    new_path = item.parent / new_name
                    
                    if not new_path.exists():
                        item.rename(new_path)
                        self._log_operation("rename", str(item), str(new_path))
                        count += 1
                except Exception as e:
                    print(f"⚠️ Erreur pour {item.name}: {e}")
            
            print(f"✅ {count} fichier(s) renommé(s)")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def _rename_search_replace(self) -> None:
        """Rechercher et remplacer dans les noms."""
        folder_path = self._select_path("Chemin du dossier", folder_only=True)
        if not folder_path:
            return
        
        search = input("Texte à rechercher: ").strip()
        replace = input("Texte de remplacement: ").strip()
        
        if not search:
            print("❌ Texte de recherche vide")
            return
        
        items = [f for f in folder_path.iterdir() if search in f.name and not self._is_protected(f)]
        
        if not items:
            print(f"❌ Aucun fichier contenant '{search}'")
            return
        
        print(f"\n{len(items)} fichier(s) concerné(s):")
        for item in items[:10]:
            new_name = item.name.replace(search, replace)
            print(f"  {item.name} → {new_name}")
        
        if self._confirm_action("Appliquer ces remplacements"):
            count = 0
            for item in items:
                try:
                    new_name = item.name.replace(search, replace)
                    new_path = item.parent / new_name
                    
                    if not new_path.exists() and self._is_safe_name(new_name):
                        item.rename(new_path)
                        self._log_operation("rename", str(item), str(new_path))
                        count += 1
                except Exception as e:
                    print(f"⚠️ Erreur pour {item.name}: {e}")
            
            print(f"✅ {count} fichier(s) renommé(s)")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    # ==================== DÉPLACER ====================
    
    def move_menu(self) -> None:
        """Menu de déplacement."""
        self._clear_screen()
        print("\n" + "=" * 60)
        print("📦 DÉPLACER (stocker) des fichiers/dossiers")
        print("=" * 60)
        
        print("\n1. Déplacer un élément unique")
        print("2. Déplacer plusieurs éléments")
        print("3. Déplacer par extension")
        print("4. ⬅️  Retour")
        
        choice = input("\nVotre choix: ").strip()
        
        if choice == "1":
            self._move_single()
        elif choice == "2":
            self._move_multiple()
        elif choice == "3":
            self._move_by_extension()
    
    def _move_single(self) -> None:
        """Déplace un seul élément."""
        source = self._select_path("Fichier/dossier à déplacer")
        if not source:
            return
        
        dest_folder = self._select_path("Dossier de destination", folder_only=True)
        if not dest_folder:
            return
        
        dest_path = dest_folder / source.name
        
        if dest_path.exists():
            print("❌ Un élément avec ce nom existe déjà à la destination")
            return
        
        if self._confirm_action(f"Déplacer '{source.name}' vers '{dest_folder}'"):
            try:
                shutil.move(str(source), str(dest_path))
                self._log_operation("move", str(source), str(dest_path))
                print(f"✅ Déplacé avec succès!")
            except Exception as e:
                print(f"❌ Erreur: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def _move_multiple(self) -> None:
        """Déplace plusieurs éléments."""
        source_folder = self._select_path("Dossier source", folder_only=True)
        if not source_folder:
            return
        
        # Lister les éléments
        items = [f for f in source_folder.iterdir() if not self._is_protected(f)]
        if not items:
            print("❌ Aucun élément à déplacer")
            return
        
        print("\nÉléments disponibles:")
        for i, item in enumerate(items, 1):
            icon = "📁" if item.is_dir() else "📄"
            print(f"  {i}. {icon} {item.name}")
        
        selection = input("\nNuméros à déplacer (ex: 1,3,5 ou 1-5 ou * pour tout): ").strip()
        
        selected_items = self._parse_selection(selection, items)
        if not selected_items:
            print("❌ Sélection invalide")
            return
        
        dest_folder = self._select_path("Dossier de destination", folder_only=True)
        if not dest_folder:
            return
        
        print(f"\n{len(selected_items)} élément(s) à déplacer vers {dest_folder}")
        
        if self._confirm_action("Confirmer le déplacement"):
            count = 0
            for item in selected_items:
                try:
                    dest_path = dest_folder / item.name
                    if not dest_path.exists():
                        shutil.move(str(item), str(dest_path))
                        self._log_operation("move", str(item), str(dest_path))
                        count += 1
                    else:
                        print(f"⚠️ '{item.name}' existe déjà à la destination")
                except Exception as e:
                    print(f"⚠️ Erreur pour {item.name}: {e}")
            
            print(f"✅ {count} élément(s) déplacé(s)")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def _move_by_extension(self) -> None:
        """Déplace les fichiers par extension."""
        source_folder = self._select_path("Dossier source", folder_only=True)
        if not source_folder:
            return
        
        # Trouver les extensions présentes
        extensions = set()
        for f in source_folder.iterdir():
            if f.is_file() and not self._is_protected(f):
                extensions.add(f.suffix.lower())
        
        if not extensions:
            print("❌ Aucun fichier trouvé")
            return
        
        print("\nExtensions trouvées:")
        ext_list = sorted(extensions)
        for i, ext in enumerate(ext_list, 1):
            count = len([f for f in source_folder.iterdir() if f.suffix.lower() == ext])
            print(f"  {i}. {ext} ({count} fichier(s))")
        
        ext_choice = input("\nNuméro de l'extension (ou taper l'extension): ").strip()
        
        # Déterminer l'extension choisie
        if ext_choice.isdigit():
            idx = int(ext_choice) - 1
            if 0 <= idx < len(ext_list):
                target_ext = ext_list[idx]
            else:
                print("❌ Choix invalide")
                return
        else:
            target_ext = ext_choice if ext_choice.startswith(".") else f".{ext_choice}"
        
        # Fichiers à déplacer
        files_to_move = [f for f in source_folder.iterdir() 
                        if f.is_file() and f.suffix.lower() == target_ext.lower() 
                        and not self._is_protected(f)]
        
        if not files_to_move:
            print(f"❌ Aucun fichier avec l'extension {target_ext}")
            return
        
        dest_folder = self._select_path("Dossier de destination", folder_only=True)
        if not dest_folder:
            return
        
        print(f"\n{len(files_to_move)} fichier(s) {target_ext} à déplacer")
        
        if self._confirm_action("Confirmer le déplacement"):
            count = 0
            for f in files_to_move:
                try:
                    dest_path = dest_folder / f.name
                    if not dest_path.exists():
                        shutil.move(str(f), str(dest_path))
                        self._log_operation("move", str(f), str(dest_path))
                        count += 1
                except Exception as e:
                    print(f"⚠️ Erreur pour {f.name}: {e}")
            
            print(f"✅ {count} fichier(s) déplacé(s)")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    # ==================== CRÉER DOSSIERS ====================
    
    def create_folder_menu(self) -> None:
        """Menu de création de dossiers."""
        self._clear_screen()
        print("\n" + "=" * 60)
        print("📂 CRÉER des dossiers pour fichiers")
        print("=" * 60)
        
        print("\n1. Créer un dossier vide")
        print("2. Créer un dossier et y déplacer des fichiers")
        print("3. Créer des dossiers par extension")
        print("4. Créer des dossiers par date")
        print("5. ⬅️  Retour")
        
        choice = input("\nVotre choix: ").strip()
        
        if choice == "1":
            self._create_empty_folder()
        elif choice == "2":
            self._create_folder_and_move()
        elif choice == "3":
            self._create_folders_by_extension()
        elif choice == "4":
            self._create_folders_by_date()
    
    def _create_empty_folder(self) -> None:
        """Crée un dossier vide."""
        parent_path = self._select_path("Emplacement du nouveau dossier", folder_only=True)
        if not parent_path:
            return
        
        folder_name = input("Nom du nouveau dossier: ").strip()
        
        if not folder_name or not self._is_safe_name(folder_name):
            print("❌ Nom invalide")
            return
        
        new_folder = parent_path / folder_name
        
        if new_folder.exists():
            print("❌ Ce dossier existe déjà")
            return
        
        try:
            new_folder.mkdir(parents=True)
            self._log_operation("create_folder", "", str(new_folder))
            print(f"✅ Dossier '{folder_name}' créé!")
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def _create_folder_and_move(self) -> None:
        """Crée un dossier et y déplace des fichiers."""
        source_folder = self._select_path("Dossier source", folder_only=True)
        if not source_folder:
            return
        
        folder_name = input("Nom du nouveau dossier: ").strip()
        
        if not folder_name or not self._is_safe_name(folder_name):
            print("❌ Nom invalide")
            return
        
        new_folder = source_folder / folder_name
        
        if new_folder.exists():
            print("⚠️ Ce dossier existe déjà, les fichiers y seront ajoutés")
        
        # Lister les fichiers
        items = [f for f in source_folder.iterdir() if f.is_file() and not self._is_protected(f)]
        if not items:
            print("❌ Aucun fichier à déplacer")
            return
        
        print("\nFichiers disponibles:")
        for i, item in enumerate(items, 1):
            print(f"  {i}. {item.name}")
        
        selection = input("\nNuméros à déplacer (ex: 1,3,5 ou 1-5 ou * pour tout): ").strip()
        
        selected_items = self._parse_selection(selection, items)
        if not selected_items:
            print("❌ Sélection invalide")
            return
        
        if self._confirm_action(f"Créer '{folder_name}' et y déplacer {len(selected_items)} fichier(s)"):
            try:
                new_folder.mkdir(exist_ok=True)
                self._log_operation("create_folder", "", str(new_folder))
                
                count = 0
                for item in selected_items:
                    dest_path = new_folder / item.name
                    if not dest_path.exists():
                        shutil.move(str(item), str(dest_path))
                        self._log_operation("move", str(item), str(dest_path))
                        count += 1
                
                print(f"✅ Dossier créé et {count} fichier(s) déplacé(s)")
            except Exception as e:
                print(f"❌ Erreur: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def _create_folders_by_extension(self) -> None:
        """Crée des dossiers par extension et y déplace les fichiers."""
        source_folder = self._select_path("Dossier à organiser", folder_only=True)
        if not source_folder:
            return
        
        # Analyser les extensions
        files_by_ext: Dict[str, List[Path]] = {}
        for f in source_folder.iterdir():
            if f.is_file() and not self._is_protected(f):
                ext = f.suffix.lower() if f.suffix else "sans_extension"
                if ext not in files_by_ext:
                    files_by_ext[ext] = []
                files_by_ext[ext].append(f)
        
        if not files_by_ext:
            print("❌ Aucun fichier à organiser")
            return
        
        print("\nOrganisation prévue:")
        for ext, files in sorted(files_by_ext.items()):
            folder_name = ext[1:].upper() if ext.startswith(".") else ext
            print(f"  📁 {folder_name}/ → {len(files)} fichier(s)")
        
        if self._confirm_action("Créer ces dossiers et organiser les fichiers"):
            total_moved = 0
            for ext, files in files_by_ext.items():
                folder_name = ext[1:].upper() if ext.startswith(".") else ext
                new_folder = source_folder / folder_name
                
                try:
                    new_folder.mkdir(exist_ok=True)
                    
                    for f in files:
                        dest_path = new_folder / f.name
                        if not dest_path.exists():
                            shutil.move(str(f), str(dest_path))
                            self._log_operation("move", str(f), str(dest_path))
                            total_moved += 1
                except Exception as e:
                    print(f"⚠️ Erreur pour {folder_name}: {e}")
            
            print(f"✅ {total_moved} fichier(s) organisé(s)")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def _create_folders_by_date(self) -> None:
        """Crée des dossiers par date de modification."""
        source_folder = self._select_path("Dossier à organiser", folder_only=True)
        if not source_folder:
            return
        
        print("\nFormat des dossiers:")
        print("1. Par année (2024, 2025...)")
        print("2. Par année-mois (2024-01, 2024-02...)")
        print("3. Par année/mois (2024/01, 2024/02...)")
        
        format_choice = input("\nVotre choix: ").strip()
        
        # Analyser les fichiers
        files_by_date: Dict[str, List[Path]] = {}
        for f in source_folder.iterdir():
            if f.is_file() and not self._is_protected(f):
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                
                if format_choice == "1":
                    date_key = str(mtime.year)
                elif format_choice == "2":
                    date_key = f"{mtime.year}-{mtime.month:02d}"
                else:
                    date_key = f"{mtime.year}/{mtime.month:02d}"
                
                if date_key not in files_by_date:
                    files_by_date[date_key] = []
                files_by_date[date_key].append(f)
        
        if not files_by_date:
            print("❌ Aucun fichier à organiser")
            return
        
        print("\nOrganisation prévue:")
        for date_key, files in sorted(files_by_date.items()):
            print(f"  📁 {date_key}/ → {len(files)} fichier(s)")
        
        if self._confirm_action("Créer ces dossiers et organiser les fichiers"):
            total_moved = 0
            for date_key, files in files_by_date.items():
                new_folder = source_folder / date_key
                
                try:
                    new_folder.mkdir(parents=True, exist_ok=True)
                    
                    for f in files:
                        dest_path = new_folder / f.name
                        if not dest_path.exists():
                            shutil.move(str(f), str(dest_path))
                            self._log_operation("move", str(f), str(dest_path))
                            total_moved += 1
                except Exception as e:
                    print(f"⚠️ Erreur pour {date_key}: {e}")
            
            print(f"✅ {total_moved} fichier(s) organisé(s)")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    # ==================== RANGER ALPHABÉTIQUE ====================
    
    def sort_alphabetical_menu(self) -> None:
        """Menu de rangement alphabétique."""
        self._clear_screen()
        print("\n" + "=" * 60)
        print("🗂️  RANGER par ordre alphabétique")
        print("=" * 60)
        
        print("\n1. Créer des dossiers A-Z et ranger les fichiers")
        print("2. Renommer avec préfixe alphabétique trié")
        print("3. ⬅️  Retour")
        
        choice = input("\nVotre choix: ").strip()
        
        if choice == "1":
            self._sort_into_az_folders()
        elif choice == "2":
            self._sort_rename_alphabetically()
    
    def _sort_into_az_folders(self) -> None:
        """Crée des dossiers A-Z et y range les fichiers."""
        source_folder = self._select_path("Dossier à organiser", folder_only=True)
        if not source_folder:
            return
        
        # Analyser les fichiers
        files_by_letter: Dict[str, List[Path]] = {}
        for f in source_folder.iterdir():
            if f.is_file() and not self._is_protected(f):
                first_char = f.name[0].upper()
                if first_char.isalpha():
                    letter = first_char
                elif first_char.isdigit():
                    letter = "0-9"
                else:
                    letter = "#"
                
                if letter not in files_by_letter:
                    files_by_letter[letter] = []
                files_by_letter[letter].append(f)
        
        if not files_by_letter:
            print("❌ Aucun fichier à organiser")
            return
        
        print("\nOrganisation prévue:")
        for letter, files in sorted(files_by_letter.items()):
            print(f"  📁 {letter}/ → {len(files)} fichier(s)")
        
        if self._confirm_action("Créer ces dossiers et organiser les fichiers"):
            total_moved = 0
            for letter, files in files_by_letter.items():
                new_folder = source_folder / letter
                
                try:
                    new_folder.mkdir(exist_ok=True)
                    
                    for f in files:
                        dest_path = new_folder / f.name
                        if not dest_path.exists():
                            shutil.move(str(f), str(dest_path))
                            self._log_operation("move", str(f), str(dest_path))
                            total_moved += 1
                except Exception as e:
                    print(f"⚠️ Erreur pour {letter}: {e}")
            
            print(f"✅ {total_moved} fichier(s) organisé(s)")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def _sort_rename_alphabetically(self) -> None:
        """Renomme les fichiers avec un préfixe trié alphabétiquement."""
        source_folder = self._select_path("Dossier à organiser", folder_only=True)
        if not source_folder:
            return
        
        files = sorted([f for f in source_folder.iterdir() 
                       if f.is_file() and not self._is_protected(f)],
                      key=lambda x: x.name.lower())
        
        if not files:
            print("❌ Aucun fichier à organiser")
            return
        
        print(f"\n{len(files)} fichier(s) seront triés alphabétiquement:")
        for i, f in enumerate(files[:5], 1):
            new_name = f"{i:03d}_{f.name}"
            print(f"  {f.name} → {new_name}")
        if len(files) > 5:
            print(f"  ... et {len(files) - 5} autres")
        
        if self._confirm_action("Renommer avec numérotation triée"):
            count = 0
            for i, f in enumerate(files, 1):
                try:
                    new_name = f"{i:03d}_{f.name}"
                    new_path = f.parent / new_name
                    
                    if not new_path.exists():
                        f.rename(new_path)
                        self._log_operation("rename", str(f), str(new_path))
                        count += 1
                except Exception as e:
                    print(f"⚠️ Erreur pour {f.name}: {e}")
            
            print(f"✅ {count} fichier(s) renommé(s)")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    # ==================== RANGER PAR REGEX ====================
    
    def sort_regex_menu(self) -> None:
        """Menu de rangement par regex."""
        self._clear_screen()
        print("\n" + "=" * 60)
        print("🔍 RANGER par expression régulière (regex)")
        print("=" * 60)
        
        print("\n1. Déplacer les fichiers correspondant à un pattern")
        print("2. Renommer avec capture de groupes regex")
        print("3. Exemples de patterns courants")
        print("4. ⬅️  Retour")
        
        choice = input("\nVotre choix: ").strip()
        
        if choice == "1":
            self._sort_regex_move()
        elif choice == "2":
            self._sort_regex_rename()
        elif choice == "3":
            self._show_regex_examples()
    
    def _sort_regex_move(self) -> None:
        """Déplace les fichiers correspondant à un pattern regex."""
        source_folder = self._select_path("Dossier source", folder_only=True)
        if not source_folder:
            return
        
        print("\nExemples de patterns:")
        print("  .*\\d{4}.* → fichiers avec 4 chiffres")
        print("  ^IMG_.* → fichiers commençant par IMG_")
        print("  .*_(copy|copie)\\..* → fichiers avec _copy ou _copie")
        
        pattern = input("\nPattern regex: ").strip()
        
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            print(f"❌ Pattern invalide: {e}")
            input("\nAppuyez sur Entrée pour continuer...")
            return
        
        # Trouver les fichiers correspondants
        matching = [f for f in source_folder.iterdir() 
                   if f.is_file() and regex.search(f.name) and not self._is_protected(f)]
        
        if not matching:
            print("❌ Aucun fichier ne correspond au pattern")
            input("\nAppuyez sur Entrée pour continuer...")
            return
        
        print(f"\n{len(matching)} fichier(s) correspondent:")
        for f in matching[:10]:
            print(f"  {f.name}")
        if len(matching) > 10:
            print(f"  ... et {len(matching) - 10} autres")
        
        dest_folder = self._select_path("Dossier de destination", folder_only=True)
        if not dest_folder:
            return
        
        if self._confirm_action(f"Déplacer {len(matching)} fichier(s) vers {dest_folder}"):
            count = 0
            for f in matching:
                try:
                    dest_path = dest_folder / f.name
                    if not dest_path.exists():
                        shutil.move(str(f), str(dest_path))
                        self._log_operation("move", str(f), str(dest_path))
                        count += 1
                except Exception as e:
                    print(f"⚠️ Erreur pour {f.name}: {e}")
            
            print(f"✅ {count} fichier(s) déplacé(s)")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def _sort_regex_rename(self) -> None:
        """Renomme les fichiers avec capture de groupes regex."""
        source_folder = self._select_path("Dossier source", folder_only=True)
        if not source_folder:
            return
        
        print("\nExemple:")
        print("  Pattern: IMG_(\\d{4})(\\d{2})(\\d{2})_(\\d+)")
        print("  Remplacement: Photo_\\1-\\2-\\3_n\\4")
        print("  IMG_20240315_001.jpg → Photo_2024-03-15_n001.jpg")
        
        pattern = input("\nPattern de recherche (avec groupes): ").strip()
        replacement = input("Pattern de remplacement (avec \\1, \\2...): ").strip()
        
        try:
            regex = re.compile(pattern)
        except re.error as e:
            print(f"❌ Pattern invalide: {e}")
            input("\nAppuyez sur Entrée pour continuer...")
            return
        
        # Trouver et prévisualiser
        preview = []
        for f in source_folder.iterdir():
            if f.is_file() and not self._is_protected(f):
                match = regex.search(f.stem)
                if match:
                    new_stem = regex.sub(replacement, f.stem)
                    new_name = new_stem + f.suffix
                    if new_name != f.name:
                        preview.append((f, new_name))
        
        if not preview:
            print("❌ Aucun fichier ne correspond ou aucun changement")
            input("\nAppuyez sur Entrée pour continuer...")
            return
        
        print(f"\n{len(preview)} fichier(s) à renommer:")
        for f, new_name in preview[:10]:
            print(f"  {f.name} → {new_name}")
        if len(preview) > 10:
            print(f"  ... et {len(preview) - 10} autres")
        
        if self._confirm_action("Appliquer ces renommages"):
            count = 0
            for f, new_name in preview:
                try:
                    new_path = f.parent / new_name
                    if not new_path.exists():
                        f.rename(new_path)
                        self._log_operation("rename", str(f), str(new_path))
                        count += 1
                except Exception as e:
                    print(f"⚠️ Erreur pour {f.name}: {e}")
            
            print(f"✅ {count} fichier(s) renommé(s)")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def _show_regex_examples(self) -> None:
        """Affiche des exemples de patterns regex."""
        print("\n" + "=" * 60)
        print("📚 EXEMPLES DE PATTERNS REGEX")
        print("=" * 60)
        
        examples = [
            ("^IMG_.*", "Fichiers commençant par IMG_"),
            (".*\\.jpg$", "Fichiers .jpg (insensible à la casse avec -i)"),
            (".*\\d{8}.*", "Fichiers avec 8 chiffres consécutifs"),
            (".*_(copy|copie|backup).*", "Fichiers avec _copy, _copie ou _backup"),
            ("^[A-Z]{3}_\\d+", "3 lettres majuscules + _ + chiffres"),
            (".*\\(\\d+\\).*", "Fichiers avec (nombre) - ex: fichier (2).txt"),
            ("^\\d{4}-\\d{2}-\\d{2}", "Fichiers commençant par date YYYY-MM-DD"),
            (".*[_-]v?\\d+\\.\\d+.*", "Fichiers avec numéro de version"),
        ]
        
        for pattern, desc in examples:
            print(f"\n  {pattern}")
            print(f"    → {desc}")
        
        input("\n\nAppuyez sur Entrée pour continuer...")
    
    # ==================== RANGER PAR CATÉGORIES ====================
    
    def sort_categories_menu(self) -> None:
        """Menu de rangement par catégories."""
        self._clear_screen()
        print("\n" + "=" * 60)
        print("🏷️  RANGER par catégories/tags")
        print("=" * 60)
        
        print("\n1. Organiser par catégories prédéfinies")
        print("2. Créer une catégorie personnalisée")
        print("3. Voir les catégories disponibles")
        print("4. Organiser le Bureau")
        print("5. ⬅️  Retour")
        
        choice = input("\nVotre choix: ").strip()
        
        if choice == "1":
            self._sort_by_predefined_categories()
        elif choice == "2":
            self._create_custom_category()
        elif choice == "3":
            self._show_categories()
        elif choice == "4":
            self._organize_desktop()
    
    def _sort_by_predefined_categories(self) -> None:
        """Organise par catégories prédéfinies."""
        source_folder = self._select_path("Dossier à organiser", folder_only=True)
        if not source_folder:
            return
        
        # Analyser les fichiers
        files_by_category: Dict[str, List[Path]] = {}
        uncategorized: List[Path] = []
        
        for f in source_folder.iterdir():
            if f.is_file() and not self._is_protected(f):
                ext = f.suffix.lower()
                found = False
                
                for category, extensions in self.CATEGORIES.items():
                    if ext in extensions:
                        if category not in files_by_category:
                            files_by_category[category] = []
                        files_by_category[category].append(f)
                        found = True
                        break
                
                if not found:
                    uncategorized.append(f)
        
        if not files_by_category and not uncategorized:
            print("❌ Aucun fichier à organiser")
            return
        
        print("\nOrganisation prévue:")
        for category, files in sorted(files_by_category.items()):
            print(f"  📁 {category}/ → {len(files)} fichier(s)")
        if uncategorized:
            print(f"  📁 Autres/ → {len(uncategorized)} fichier(s) non catégorisé(s)")
        
        include_other = input("\nInclure les fichiers non catégorisés dans 'Autres'? (o/n): ").strip().lower()
        
        if self._confirm_action("Créer ces dossiers et organiser les fichiers"):
            total_moved = 0
            
            for category, files in files_by_category.items():
                new_folder = source_folder / category
                try:
                    new_folder.mkdir(exist_ok=True)
                    for f in files:
                        dest_path = new_folder / f.name
                        if not dest_path.exists():
                            shutil.move(str(f), str(dest_path))
                            self._log_operation("move", str(f), str(dest_path))
                            total_moved += 1
                except Exception as e:
                    print(f"⚠️ Erreur pour {category}: {e}")
            
            if include_other == "o" and uncategorized:
                other_folder = source_folder / "Autres"
                try:
                    other_folder.mkdir(exist_ok=True)
                    for f in uncategorized:
                        dest_path = other_folder / f.name
                        if not dest_path.exists():
                            shutil.move(str(f), str(dest_path))
                            self._log_operation("move", str(f), str(dest_path))
                            total_moved += 1
                except Exception as e:
                    print(f"⚠️ Erreur pour Autres: {e}")
            
            print(f"✅ {total_moved} fichier(s) organisé(s)")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def _create_custom_category(self) -> None:
        """Crée une catégorie personnalisée."""
        print("\n📝 Création d'une catégorie personnalisée")
        
        category_name = input("Nom de la catégorie: ").strip()
        if not category_name or not self._is_safe_name(category_name):
            print("❌ Nom invalide")
            return
        
        extensions = input("Extensions (séparées par des virgules, ex: .psd,.ai,.sketch): ").strip()
        ext_list = [e.strip().lower() if e.strip().startswith(".") else f".{e.strip().lower()}" 
                   for e in extensions.split(",") if e.strip()]
        
        if not ext_list:
            print("❌ Aucune extension spécifiée")
            return
        
        # Ajouter temporairement la catégorie
        self.CATEGORIES[category_name] = ext_list
        
        print(f"\n✅ Catégorie '{category_name}' créée avec les extensions: {', '.join(ext_list)}")
        print("Note: Cette catégorie est temporaire et sera perdue à la fermeture.")
        
        if input("\nOrganiser un dossier avec cette catégorie maintenant? (o/n): ").strip().lower() == "o":
            self._sort_by_predefined_categories()
        else:
            input("\nAppuyez sur Entrée pour continuer...")
    
    def _show_categories(self) -> None:
        """Affiche les catégories disponibles."""
        print("\n" + "=" * 60)
        print("📋 CATÉGORIES DISPONIBLES")
        print("=" * 60)
        
        for category, extensions in sorted(self.CATEGORIES.items()):
            print(f"\n🏷️  {category}")
            print(f"   Extensions: {', '.join(extensions)}")
        
        input("\n\nAppuyez sur Entrée pour continuer...")
    
    def _organize_desktop(self) -> None:
        """Organise le Bureau."""
        # Déterminer le chemin du Bureau
        desktop = Path.home() / "Desktop"
        if not desktop.exists():
            desktop = Path.home() / "Bureau"
        if not desktop.exists():
            desktop_input = input("Chemin du Bureau: ").strip()
            desktop = Path(desktop_input)
        
        if not desktop.exists() or not desktop.is_dir():
            print("❌ Bureau introuvable")
            return
        
        print(f"\n📂 Bureau détecté: {desktop}")
        
        # Compter les fichiers
        files = [f for f in desktop.iterdir() if f.is_file() and not self._is_protected(f)]
        folders = [f for f in desktop.iterdir() if f.is_dir() and not self._is_protected(f)]
        
        print(f"   {len(files)} fichier(s), {len(folders)} dossier(s)")
        
        if not files:
            print("❌ Aucun fichier à organiser sur le Bureau")
            return
        
        print("\nOptions:")
        print("1. Organiser par catégories (Images, Documents, etc.)")
        print("2. Organiser par extension")
        print("3. Tout déplacer dans un dossier 'Bureau_Organisé'")
        
        choice = input("\nVotre choix: ").strip()
        
        if choice == "1":
            # Réutiliser la logique des catégories
            files_by_category: Dict[str, List[Path]] = {}
            
            for f in files:
                ext = f.suffix.lower()
                found = False
                for category, extensions in self.CATEGORIES.items():
                    if ext in extensions:
                        if category not in files_by_category:
                            files_by_category[category] = []
                        files_by_category[category].append(f)
                        found = True
                        break
                if not found:
                    if "Autres" not in files_by_category:
                        files_by_category["Autres"] = []
                    files_by_category["Autres"].append(f)
            
            print("\nOrganisation prévue:")
            for cat, fs in sorted(files_by_category.items()):
                print(f"  📁 {cat}/ → {len(fs)} fichier(s)")
            
            if self._confirm_action("Organiser le Bureau"):
                total = 0
                for cat, fs in files_by_category.items():
                    folder = desktop / cat
                    folder.mkdir(exist_ok=True)
                    for f in fs:
                        dest = folder / f.name
                        if not dest.exists():
                            shutil.move(str(f), str(dest))
                            self._log_operation("move", str(f), str(dest))
                            total += 1
                print(f"✅ {total} fichier(s) organisé(s)")
        
        elif choice == "2":
            # Organiser par extension
            files_by_ext: Dict[str, List[Path]] = {}
            for f in files:
                ext = f.suffix.lower() or "sans_extension"
                if ext not in files_by_ext:
                    files_by_ext[ext] = []
                files_by_ext[ext].append(f)
            
            print("\nOrganisation prévue:")
            for ext, fs in sorted(files_by_ext.items()):
                folder_name = ext[1:].upper() if ext.startswith(".") else ext
                print(f"  📁 {folder_name}/ → {len(fs)} fichier(s)")
            
            if self._confirm_action("Organiser le Bureau"):
                total = 0
                for ext, fs in files_by_ext.items():
                    folder_name = ext[1:].upper() if ext.startswith(".") else ext
                    folder = desktop / folder_name
                    folder.mkdir(exist_ok=True)
                    for f in fs:
                        dest = folder / f.name
                        if not dest.exists():
                            shutil.move(str(f), str(dest))
                            self._log_operation("move", str(f), str(dest))
                            total += 1
                print(f"✅ {total} fichier(s) organisé(s)")
        
        elif choice == "3":
            org_folder = desktop / "Bureau_Organisé"
            if self._confirm_action(f"Tout déplacer vers {org_folder}"):
                org_folder.mkdir(exist_ok=True)
                total = 0
                for f in files:
                    dest = org_folder / f.name
                    if not dest.exists():
                        shutil.move(str(f), str(dest))
                        self._log_operation("move", str(f), str(dest))
                        total += 1
                print(f"✅ {total} fichier(s) déplacé(s)")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    # ==================== HISTORIQUE ====================
    
    def show_history(self) -> None:
        """Affiche l'historique des opérations."""
        self._clear_screen()
        print("\n" + "=" * 60)
        print("📋 HISTORIQUE DES OPÉRATIONS")
        print("=" * 60)
        
        if not self.history:
            print("\nAucune opération effectuée durant cette session.")
        else:
            print(f"\n{len(self.history)} opération(s):\n")
            for i, op in enumerate(self.history[-20:], 1):  # Dernières 20
                icon = {"rename": "🔄", "move": "📦", "create_folder": "📂"}.get(op["type"], "•")
                print(f"{i}. {icon} {op['type'].upper()}")
                if op["source"]:
                    print(f"   De: {op['source']}")
                print(f"   Vers: {op['dest']}")
                print(f"   À: {op['timestamp']}")
                print()
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    # ==================== UTILITAIRES ====================
    
    def _clear_screen(self) -> None:
        """Efface l'écran."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _select_path(self, prompt: str, folder_only: bool = False) -> Optional[Path]:
        """Demande un chemin à l'utilisateur."""
        print(f"\n{prompt}")
        print("(Tapez le chemin complet ou 'desktop' pour le Bureau)")
        
        path_input = input("> ").strip()
        
        if path_input.lower() == "desktop":
            path = Path.home() / "Desktop"
            if not path.exists():
                path = Path.home() / "Bureau"
        else:
            path = Path(path_input)
        
        if not path.exists():
            print(f"❌ Chemin introuvable: {path}")
            return None
        
        if folder_only and not path.is_dir():
            print("❌ Ce n'est pas un dossier")
            return None
        
        if self._is_protected(path):
            print("❌ Chemin protégé (fichier/dossier système)")
            return None
        
        return path
    
    def _is_protected(self, path: Path) -> bool:
        """Vérifie si un chemin est protégé."""
        name = path.name.lower()
        
        # Fichiers protégés
        if name in [f.lower() for f in self.PROTECTED_FILES]:
            return True
        
        # Dossiers protégés
        for part in path.parts:
            if part in self.PROTECTED_FOLDERS:
                return True
        
        # Fichiers cachés système
        if name.startswith("$") or name.startswith("."):
            return True
        
        return False
    
    def _is_safe_name(self, name: str) -> bool:
        """Vérifie si un nom est valide."""
        # Caractères interdits sur Windows
        forbidden = '<>:"/\\|?*'
        return all(c not in name for c in forbidden) and name.strip() != ""
    
    def _confirm_action(self, message: str) -> bool:
        """Demande confirmation à l'utilisateur."""
        response = input(f"\n⚠️  {message}? (o/n): ").strip().lower()
        return response in ["o", "oui", "y", "yes"]
    
    def _parse_selection(self, selection: str, items: List[Path]) -> List[Path]:
        """Parse une sélection (1,3,5 ou 1-5 ou *)."""
        if selection == "*":
            return items
        
        selected = []
        try:
            for part in selection.split(","):
                part = part.strip()
                if "-" in part:
                    start, end = part.split("-")
                    for i in range(int(start), int(end) + 1):
                        if 1 <= i <= len(items):
                            selected.append(items[i - 1])
                else:
                    i = int(part)
                    if 1 <= i <= len(items):
                        selected.append(items[i - 1])
        except ValueError:
            return []
        
        return selected
    
    def _log_operation(self, op_type: str, source: str, dest: str) -> None:
        """Enregistre une opération dans l'historique."""
        self.history.append({
            "type": op_type,
            "source": source,
            "dest": dest,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
