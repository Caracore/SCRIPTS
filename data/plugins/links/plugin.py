# plugins/links/plugin.py
"""
Plugin Links - Gestion de liens rapides depuis le gestionnaire de scripts.
Permet d'ajouter, modifier, supprimer et ouvrir des liens web.
"""
import json
import webbrowser
from pathlib import Path
from typing import Any, Dict, List

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from plugins.base import Plugin, PluginMeta, HookType


class LinksPlugin(Plugin):
    """Plugin pour gérer des liens rapides."""
    
    LINKS_FILE = "links.json"
    
    def __init__(self):
        self.program = None
        self.links_path = None
        self.links: List[Dict[str, str]] = []
    
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="links",
            version="1.0.0",
            author="Script Manager",
            description="Gestion de liens rapides - ajouter, modifier, ouvrir des URLs",
            homepage="",
            license="MIT"
        )
    
    def on_load(self, program: Any) -> bool:
        """Charge le plugin et les liens sauvegardés."""
        self.program = program
        
        # Chemin du fichier de liens
        data_path = Path(program.current_path) / "data"
        data_path.mkdir(parents=True, exist_ok=True)
        self.links_path = data_path / self.LINKS_FILE
        
        # Charger les liens existants
        self._load_links()
        return True
    
    def on_unload(self, program: Any) -> None:
        """Sauvegarde les liens avant déchargement."""
        self._save_links()
    
    def get_menu_items(self) -> List[Dict[str, Any]]:
        """Ajoute l'entrée de menu pour les liens."""
        return [
            {
                "key": "K",
                "label": "Liens Rapides         [K]",
                "handler": self.manage_links
            }
        ]
    
    def get_hooks(self) -> Dict[HookType, Any]:
        """Enregistre les hooks."""
        return {
            HookType.ON_SHUTDOWN: self._on_shutdown
        }
    
    def _on_shutdown(self) -> None:
        """Sauvegarde les liens à la fermeture."""
        self._save_links()
    
    def _load_links(self) -> None:
        """Charge les liens depuis le fichier JSON."""
        try:
            if self.links_path and self.links_path.exists():
                with open(self.links_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.links = data.get("links", [])
        except (json.JSONDecodeError, IOError) as e:
            print(f"[Links] Erreur de chargement: {e}")
            self.links = []
    
    def _save_links(self) -> None:
        """Sauvegarde les liens dans le fichier JSON."""
        if not self.links_path:
            return
        try:
            with open(self.links_path, "w", encoding="utf-8") as f:
                json.dump({"links": self.links}, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[Links] Erreur de sauvegarde: {e}")
    
    def _clear_screen(self) -> None:
        """Nettoie l'écran."""
        if self.program:
            self.program.clear_screen()
    
    def manage_links(self) -> None:
        """Interface principale de gestion des liens."""
        while True:
            self._clear_screen()
            print("\n" + "=" * 50)
            print("           GESTION DES LIENS RAPIDES")
            print("=" * 50)
            
            if self.links:
                print(f"\n{len(self.links)} lien(s) enregistré(s):\n")
                for i, link in enumerate(self.links, 1):
                    name = link.get("name", "Sans nom")
                    url = link.get("url", "")
                    category = link.get("category", "")
                    cat_display = f" [{category}]" if category else ""
                    print(f"  {i}. {name}{cat_display}")
                    print(f"      {url}")
            else:
                print("\nAucun lien enregistré.")
            
            print("\n" + "-" * 50)
            print("  1. Ouvrir un lien        [O]")
            print("  2. Ajouter un lien       [A]")
            print("  3. Modifier un lien      [M]")
            print("  4. Supprimer un lien     [S]")
            print("  5. Ouvrir tous les liens [T]")
            print("  6. Rechercher            [F]")
            print("  7. Importer/Exporter     [I]")
            print("  R. Retour")
            
            choice = input("\nChoix: ").strip().lower()
            
            if choice in ["1", "o"]:
                self._open_link()
            elif choice in ["2", "a"]:
                self._add_link()
            elif choice in ["3", "m"]:
                self._edit_link()
            elif choice in ["4", "s"]:
                self._delete_link()
            elif choice in ["5", "t"]:
                self._open_all_links()
            elif choice in ["6", "f"]:
                self._search_links()
            elif choice in ["7", "i"]:
                self._import_export_menu()
            elif choice == "r":
                break
    
    def _open_link(self) -> None:
        """Ouvre un lien dans le navigateur."""
        if not self.links:
            print("\nAucun lien à ouvrir.")
            input("\nAppuyez sur Entrée...")
            return
        
        self._display_links_numbered()
        idx = input("\nNuméro du lien à ouvrir (ou 'q' pour annuler): ").strip()
        
        if idx.lower() == 'q':
            return
        
        try:
            link = self.links[int(idx) - 1]
            url = link.get("url", "")
            if url:
                print(f"\nOuverture de: {url}")
                webbrowser.open(url)
            else:
                print("\nURL invalide.")
        except (ValueError, IndexError):
            print("\nChoix invalide.")
        
        input("\nAppuyez sur Entrée...")
    
    def _add_link(self) -> None:
        """Ajoute un nouveau lien."""
        print("\n--- Ajouter un nouveau lien ---")
        
        name = input("Nom du lien: ").strip()
        if not name:
            print("Nom requis.")
            input("\nAppuyez sur Entrée...")
            return
        
        url = input("URL: ").strip()
        if not url:
            print("URL requise.")
            input("\nAppuyez sur Entrée...")
            return
        
        # Ajouter http:// si pas de protocole
        if not url.startswith(("http://", "https://", "file://")):
            url = "https://" + url
        
        category = input("Catégorie (optionnel): ").strip()
        description = input("Description (optionnel): ").strip()
        
        new_link = {
            "name": name,
            "url": url,
            "category": category,
            "description": description
        }
        
        self.links.append(new_link)
        self._save_links()
        
        print(f"\n✓ Lien '{name}' ajouté avec succès!")
        
        # Proposer d'ouvrir le lien
        if input("Ouvrir maintenant? (o/n): ").strip().lower() == 'o':
            webbrowser.open(url)
        
        input("\nAppuyez sur Entrée...")
    
    def _edit_link(self) -> None:
        """Modifie un lien existant."""
        if not self.links:
            print("\nAucun lien à modifier.")
            input("\nAppuyez sur Entrée...")
            return
        
        self._display_links_numbered()
        idx = input("\nNuméro du lien à modifier (ou 'q' pour annuler): ").strip()
        
        if idx.lower() == 'q':
            return
        
        try:
            index = int(idx) - 1
            link = self.links[index]
            
            print(f"\n--- Modification de '{link.get('name', '')}' ---")
            print("(Laissez vide pour garder la valeur actuelle)\n")
            
            # Nom
            new_name = input(f"Nom [{link.get('name', '')}]: ").strip()
            if new_name:
                link["name"] = new_name
            
            # URL
            new_url = input(f"URL [{link.get('url', '')}]: ").strip()
            if new_url:
                if not new_url.startswith(("http://", "https://", "file://")):
                    new_url = "https://" + new_url
                link["url"] = new_url
            
            # Catégorie
            new_category = input(f"Catégorie [{link.get('category', '')}]: ").strip()
            if new_category:
                link["category"] = new_category
            
            # Description
            new_desc = input(f"Description [{link.get('description', '')}]: ").strip()
            if new_desc:
                link["description"] = new_desc
            
            self.links[index] = link
            self._save_links()
            
            print(f"\n✓ Lien modifié avec succès!")
            
        except (ValueError, IndexError):
            print("\nChoix invalide.")
        
        input("\nAppuyez sur Entrée...")
    
    def _delete_link(self) -> None:
        """Supprime un lien."""
        if not self.links:
            print("\nAucun lien à supprimer.")
            input("\nAppuyez sur Entrée...")
            return
        
        self._display_links_numbered()
        idx = input("\nNuméro du lien à supprimer (ou 'q' pour annuler): ").strip()
        
        if idx.lower() == 'q':
            return
        
        try:
            index = int(idx) - 1
            link = self.links[index]
            
            confirm = input(f"Supprimer '{link.get('name', '')}' ? (o/n): ").strip().lower()
            if confirm == 'o':
                self.links.pop(index)
                self._save_links()
                print("\n✓ Lien supprimé!")
            else:
                print("\nSuppression annulée.")
                
        except (ValueError, IndexError):
            print("\nChoix invalide.")
        
        input("\nAppuyez sur Entrée...")
    
    def _open_all_links(self) -> None:
        """Ouvre tous les liens dans le navigateur avec protection de sécurité."""
        import time
        
        # Limites de sécurité
        MAX_LINKS_NO_CONFIRM = 5      # Pas de warning en dessous
        MAX_LINKS_WARNING = 15        # Warning entre 5 et 15
        MAX_LINKS_CRITICAL = 30       # Limite critique avec délai
        MAX_LINKS_ABSOLUTE = 50       # Limite absolue
        DELAY_BETWEEN_LINKS = 0.3     # Délai entre ouvertures (secondes)
        DELAY_CRITICAL = 1.0          # Délai pour beaucoup de liens
        
        if not self.links:
            print("\nAucun lien à ouvrir.")
            input("\nAppuyez sur Entrée...")
            return
        
        # Filtrer par catégorie si demandé
        categories = list(set(l.get("category", "") for l in self.links if l.get("category")))
        
        if categories:
            print("\nCatégories disponibles:")
            print("  0. Tous les liens")
            for i, cat in enumerate(categories, 1):
                count = sum(1 for l in self.links if l.get("category") == cat)
                print(f"  {i}. {cat} ({count} liens)")
            
            choice = input("\nChoix (ou Entrée pour tous): ").strip()
            
            if choice and choice != "0":
                try:
                    selected_cat = categories[int(choice) - 1]
                    links_to_open = [l for l in self.links if l.get("category") == selected_cat]
                except (ValueError, IndexError):
                    links_to_open = self.links
            else:
                links_to_open = self.links
        else:
            links_to_open = self.links
        
        count = len(links_to_open)
        
        # === PROTECTION DE SÉCURITÉ ===
        
        # Limite absolue
        if count > MAX_LINKS_ABSOLUTE:
            print(f"\n⛔ LIMITE DE SÉCURITÉ: Maximum {MAX_LINKS_ABSOLUTE} liens autorisés.")
            print(f"   Vous essayez d'ouvrir {count} liens.")
            print(f"\n   Utilisez les catégories ou la recherche pour réduire la sélection.")
            input("\nAppuyez sur Entrée...")
            return
        
        # Warning critique (30+ liens)
        if count > MAX_LINKS_CRITICAL:
            print(f"\n⚠️  ATTENTION: Vous allez ouvrir {count} liens!")
            print(f"   Cela peut:")
            print(f"   • Ralentir considérablement votre système")
            print(f"   • Consommer beaucoup de mémoire RAM")
            print(f"   • Saturer votre navigateur")
            print(f"\n   Un délai de {DELAY_CRITICAL}s sera appliqué entre chaque lien.")
            confirm = input(f"\n⚠️  Êtes-vous VRAIMENT sûr? Tapez 'OUI' pour confirmer: ").strip()
            if confirm != "OUI":
                print("\n❌ Opération annulée.")
                input("\nAppuyez sur Entrée...")
                return
            delay = DELAY_CRITICAL
        
        # Warning modéré (15-30 liens)
        elif count > MAX_LINKS_WARNING:
            print(f"\n⚠️  Vous allez ouvrir {count} liens.")
            print(f"   Cela peut ralentir votre navigateur.")
            confirm = input(f"\nContinuer? (o/N): ").strip().lower()
            if confirm != 'o':
                print("\n❌ Opération annulée.")
                input("\nAppuyez sur Entrée...")
                return
            delay = DELAY_BETWEEN_LINKS
        
        # Warning léger (5-15 liens)
        elif count > MAX_LINKS_NO_CONFIRM:
            confirm = input(f"\nOuvrir {count} lien(s)? (o/N): ").strip().lower()
            if confirm != 'o':
                return
            delay = DELAY_BETWEEN_LINKS
        
        # Peu de liens (< 5)
        else:
            confirm = input(f"\nOuvrir {count} lien(s)? (o/N): ").strip().lower()
            if confirm != 'o':
                return
            delay = 0.1  # Délai minimal
        
        # === OUVERTURE DES LIENS ===
        print(f"\n🔗 Ouverture de {count} lien(s)...")
        if count > MAX_LINKS_NO_CONFIRM:
            print(f"   (Délai de {delay}s entre chaque lien)")
        
        opened = 0
        errors = 0
        
        for i, link in enumerate(links_to_open, 1):
            url = link.get("url", "")
            name = link.get("name", url)
            
            if url:
                try:
                    print(f"  [{i}/{count}] {name[:40]}{'...' if len(name) > 40 else ''}")
                    webbrowser.open(url)
                    opened += 1
                    
                    # Délai entre les ouvertures (sauf pour le dernier)
                    if i < count and delay > 0:
                        time.sleep(delay)
                        
                except Exception as e:
                    print(f"  ❌ Erreur: {name} - {e}")
                    errors += 1
        
        # Résumé
        print(f"\n✓ {opened} lien(s) ouvert(s)")
        if errors > 0:
            print(f"⚠️  {errors} erreur(s)")
        
        input("\nAppuyez sur Entrée...")
    
    def _search_links(self) -> None:
        """Recherche dans les liens."""
        query = input("\nRecherche: ").strip().lower()
        if not query:
            return
        
        results = []
        for link in self.links:
            searchable = f"{link.get('name', '')} {link.get('url', '')} {link.get('category', '')} {link.get('description', '')}".lower()
            if query in searchable:
                results.append(link)
        
        if results:
            print(f"\n{len(results)} résultat(s) trouvé(s):\n")
            for i, link in enumerate(results, 1):
                name = link.get("name", "Sans nom")
                url = link.get("url", "")
                print(f"  {i}. {name}")
                print(f"      {url}")
            
            choice = input("\nOuvrir un lien? (numéro ou 'n'): ").strip()
            if choice.lower() != 'n' and choice.isdigit():
                try:
                    link = results[int(choice) - 1]
                    webbrowser.open(link.get("url", ""))
                except (ValueError, IndexError):
                    pass
        else:
            print("\nAucun résultat.")
        
        input("\nAppuyez sur Entrée...")
    
    def _import_export_menu(self) -> None:
        """Menu import/export."""
        print("\n--- Import / Export ---")
        print("  1. Exporter les liens (JSON)")
        print("  2. Exporter les liens (HTML)")
        print("  3. Importer des liens (JSON)")
        print("  R. Retour")
        
        choice = input("\nChoix: ").strip().lower()
        
        if choice == "1":
            self._export_json()
        elif choice == "2":
            self._export_html()
        elif choice == "3":
            self._import_json()
    
    def _export_json(self) -> None:
        """Exporte les liens en JSON."""
        if not self.links:
            print("\nAucun lien à exporter.")
            input("\nAppuyez sur Entrée...")
            return
        
        export_path = Path(self.program.current_path) / "data" / "links_export.json"
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump({"links": self.links}, f, indent=2, ensure_ascii=False)
            print(f"\n✓ Liens exportés vers: {export_path}")
        except IOError as e:
            print(f"\nErreur d'export: {e}")
        
        input("\nAppuyez sur Entrée...")
    
    def _export_html(self) -> None:
        """Exporte les liens en HTML (bookmarks)."""
        if not self.links:
            print("\nAucun lien à exporter.")
            input("\nAppuyez sur Entrée...")
            return
        
        export_path = Path(self.program.current_path) / "data" / "links_bookmarks.html"
        
        html = ['<!DOCTYPE NETSCAPE-Bookmark-file-1>']
        html.append('<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">')
        html.append('<TITLE>Bookmarks</TITLE>')
        html.append('<H1>Bookmarks</H1>')
        html.append('<DL><p>')
        
        # Grouper par catégorie
        categories = {}
        for link in self.links:
            cat = link.get("category", "Sans catégorie")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(link)
        
        for cat, cat_links in categories.items():
            html.append(f'  <DT><H3>{cat}</H3>')
            html.append('  <DL><p>')
            for link in cat_links:
                name = link.get("name", "")
                url = link.get("url", "")
                html.append(f'    <DT><A HREF="{url}">{name}</A>')
            html.append('  </DL><p>')
        
        html.append('</DL><p>')
        
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                f.write('\n'.join(html))
            print(f"\n✓ Bookmarks exportés vers: {export_path}")
        except IOError as e:
            print(f"\nErreur d'export: {e}")
        
        input("\nAppuyez sur Entrée...")
    
    def _import_json(self) -> None:
        """Importe des liens depuis un fichier JSON."""
        import_path = input("Chemin du fichier JSON: ").strip()
        if not import_path:
            return
        
        path = Path(import_path)
        if not path.exists():
            print(f"\nFichier introuvable: {import_path}")
            input("\nAppuyez sur Entrée...")
            return
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            imported = data.get("links", [])
            if not imported:
                print("\nAucun lien trouvé dans le fichier.")
                input("\nAppuyez sur Entrée...")
                return
            
            print(f"\n{len(imported)} lien(s) trouvé(s).")
            mode = input("Mode: (1) Remplacer tout / (2) Ajouter: ").strip()
            
            if mode == "1":
                self.links = imported
            else:
                # Éviter les doublons par URL
                existing_urls = {l.get("url") for l in self.links}
                for link in imported:
                    if link.get("url") not in existing_urls:
                        self.links.append(link)
            
            self._save_links()
            print(f"\n✓ Import réussi! {len(self.links)} lien(s) au total.")
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"\nErreur d'import: {e}")
        
        input("\nAppuyez sur Entrée...")
    
    def _display_links_numbered(self) -> None:
        """Affiche les liens numérotés."""
        print("\nLiens disponibles:")
        for i, link in enumerate(self.links, 1):
            name = link.get("name", "Sans nom")
            cat = link.get("category", "")
            cat_display = f" [{cat}]" if cat else ""
            print(f"  {i}. {name}{cat_display}")
