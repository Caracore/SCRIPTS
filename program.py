# program.py
import os
from script import Script as s
from plugins import PluginManager, HookType
from themes import ThemeManager
from navigation import NavigationManager, NavigationMode, MenuItem, navigation_settings_menu
from alias_manager import alias_menu

class Program:
    def __init__(self, name, current_path, target, scripts_path=None):
        self.name = name
        self.current_path = current_path
        self.target = target
        # Par défaut: ./data/scripts
        self.scripts_path = scripts_path or os.path.join(current_path, "data", "scripts")
        # Créer le dossier scripts s'il n'existe pas
        os.makedirs(self.scripts_path, exist_ok=True)
        
        # Initialiser le gestionnaire de thèmes
        self.theme_manager = ThemeManager(os.path.join(current_path, "data"))
        
        # Initialiser le gestionnaire de navigation
        self.nav_manager = NavigationManager(os.path.join(current_path, "data"))
        
        # Initialiser le gestionnaire de plugins
        self.plugin_manager = PluginManager(self)
        self.plugin_manager.load_all()

    @staticmethod
    def clear_screen():
        """Nettoie le terminal."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def startup(self):
        """Exécute les opérations au démarrage."""
        self.clear_screen()
        
        # Vérifier si c'est la première utilisation
        if s.is_first_run(self):
            s.first_run_setup(self)
        
        # Déclencher le hook ON_STARTUP
        self.plugin_manager.trigger_hook(HookType.ON_STARTUP)
        s.run_autostart(self)

    def ascii_dashboard(self):
        """Affiche un tableau de bord ASCII personnalisable."""
        # Charger la config pour vérifier si ASCII est activé
        config = s.load_config(self)
        
        # Afficher l'ASCII art si activé
        if config.get("ascii_enabled", True):
            ascii_art = self.theme_manager.get_current_ascii()
            if ascii_art:
                print(ascii_art)
        
        # Message de bienvenue personnalisé ou par défaut
        custom_welcome = self.theme_manager.get_custom_welcome()
        if custom_welcome:
            print(f"{custom_welcome}")
        else:
            print(f"Bienvenue dans {self.name}!")
        
        print(f"Dossier scripts: {self.scripts_path}")
        
        # Afficher les langages (natifs + plugins)
        all_langs = self.plugin_manager.get_all_languages()
        print(f"Langages: {', '.join(all_langs.keys())}\n")

    def menu(self):
        """Affiche le menu principal et gère les choix."""
        # Exécuter l'auto-start au premier lancement
        self.startup()
        
        while True:
            # Construire les items de menu
            menu_items = self._build_menu_items()
            
            # Utiliser le mode de navigation configuré
            if self.nav_manager.mode == NavigationMode.DYNAMIC:
                self._menu_dynamic(menu_items)
            else:
                self._menu_static(menu_items)
    
    def _build_menu_items(self) -> list:
        """Construit la liste des éléments de menu."""
        items = [
            MenuItem(key="0", label="Exit", handler=self._exit),
            MenuItem(key="1", label="Executer Un Script    [E]", handler=lambda: s.execute_script(self)),
            MenuItem(key="2", label="Nouveau Script        [N]", handler=lambda: s.create_script(self)),
            MenuItem(key="3", label="Éditer Un Script      [D]", handler=lambda: s.edit_script(self)),
            MenuItem(key="4", label="Parcourir Scripts     [O]", handler=lambda: s.open_script(self)),
            MenuItem(key="5", label="Auto-Start            [A]", handler=lambda: s.manage_autostart(self)),
            MenuItem(key="6", label="Options & Paramètres  [S]", handler=lambda: s.option(self)),
            MenuItem(key="7", label="Plugins               [L]", handler=self.manage_plugins),
            MenuItem(key="8", label="Personnalisation      [T]", handler=self._personalization_menu),
            MenuItem(key="9", label="Navigation            [V]", handler=lambda: navigation_settings_menu(self.nav_manager)),
            MenuItem(key="=", label="Alias & Raccourcis    [R]", handler=lambda: alias_menu(self)),
        ]
        
        # Ajouter les éléments des plugins
        for plugin_item in self.plugin_manager.menu_items:
            items.append(MenuItem(
                key=plugin_item['key'],
                label=plugin_item['label'],
                handler=plugin_item['handler']
            ))
        
        return items
    
    def _personalization_menu(self):
        """Menu de personnalisation."""
        from themes import manage_themes
        manage_themes(self)
    
    def _exit(self):
        """Quitte le programme."""
        self.plugin_manager.trigger_hook(HookType.ON_SHUTDOWN)
        self.clear_screen()
        print("\n>> Au revoir <<\n")
        exit(0)
    
    def _menu_static(self, menu_items: list):
        """Menu en mode statique (navigation classique)."""
        self.clear_screen()
        self.ascii_dashboard()
        
        # Déclencher le hook avant affichage du menu
        self.plugin_manager.trigger_hook(HookType.ON_MENU_DISPLAY)
        
        # Afficher les items
        for item in menu_items:
            print(f"  {item.key}. {item.label}")
        
        imenu = input("\n>> ").strip().lower()
        
        # Déclencher le hook après choix
        self.plugin_manager.trigger_hook(HookType.ON_MENU_CHOICE, choice=imenu)
        
        # Trouver et exécuter l'item correspondant
        for item in menu_items:
            if imenu == item.key.lower() or imenu in self._get_shortcuts(item.key):
                if item.handler:
                    item.handler()
                return
        
        print("Choix invalide. Réessayez.")
        input("\nAppuyez sur Entrée...")
    
    def _get_shortcuts(self, key: str) -> list:
        """Retourne les raccourcis alternatifs pour une touche."""
        shortcuts = {
            "0": ["exit", "q", "quit"],
            "1": ["e"],
            "2": ["n"],
            "3": ["d"],
            "4": ["o"],
            "5": ["a"],
            "6": ["s"],
            "7": ["l"],
            "8": ["t"],
            "9": ["v"],
            "=": ["r"],
        }
        return shortcuts.get(key, [])
    
    def _menu_dynamic(self, menu_items: list):
        """Menu en mode dynamique (navigation flèches/vim)."""
        # Construire l'en-tête avec ASCII art
        self.clear_screen()
        
        # Charger la config pour vérifier si ASCII est activé
        config = s.load_config(self)
        header = ""
        
        if config.get("ascii_enabled", True):
            ascii_art = self.theme_manager.get_current_ascii()
            if ascii_art:
                header = ascii_art + "\n"
        
        # Message de bienvenue
        custom_welcome = self.theme_manager.get_custom_welcome()
        if custom_welcome:
            header += f"{custom_welcome}\n"
        else:
            header += f"Bienvenue dans {self.name}!\n"
        
        header += f"Dossier scripts: {self.scripts_path}\n"
        
        # Langages
        all_langs = self.plugin_manager.get_all_languages()
        header += f"Langages: {', '.join(all_langs.keys())}"
        
        # Déclencher le hook
        self.plugin_manager.trigger_hook(HookType.ON_MENU_DISPLAY)
        
        # Navigation dynamique
        footer = "↑↓ Naviguer | Enter Sélectionner | ? Aide | Q Quitter"
        result = self.nav_manager.navigate_menu(menu_items, title=header, footer=footer, allow_back=False)
        
        # Déclencher le hook après choix
        if result:
            self.plugin_manager.trigger_hook(HookType.ON_MENU_CHOICE, choice=result.key)
            
            if result.key == "quit" or result.key == "0":
                self._exit()
            elif result.handler:
                result.handler()
    
    def manage_plugins(self):
        """Gère les plugins installés."""
        while True:
            self.clear_screen()
            print("\n" + "=" * 50)
            print("           GESTION DES PLUGINS")
            print("=" * 50)
            
            plugins = self.plugin_manager.list_plugins()
            
            if plugins:
                print(f"\n{len(plugins)} plugin(s) trouvé(s):\n")
                for i, p in enumerate(plugins, 1):
                    status = "✓ Actif" if p['loaded'] else "○ Inactif"
                    enabled = "" if p['enabled'] else " [Désactivé]"
                    name = p.get('name', 'Inconnu')
                    version = p.get('version', '?')
                    desc = p.get('description', '')
                    print(f"  {i}. [{status}] {name} v{version}{enabled}")
                    if desc:
                        print(f"      {desc}")
            else:
                print("\nAucun plugin installé.")
                print(f"Placez vos plugins dans: {self.plugin_manager.plugins_path}")
            
            print("\n  1. Recharger tous les plugins")
            print("  2. Activer/Désactiver un plugin")
            print("  3. Voir les détails d'un plugin")
            print("  4. Ouvrir le dossier plugins")
            print("  R. Retour")
            
            choice = input("\nChoix: ").strip().lower()
            
            if choice == "1":
                print("\nRechargement des plugins...")
                # Décharger tous les plugins
                for name in list(self.plugin_manager.plugins.keys()):
                    self.plugin_manager.unload_plugin(name)
                # Recharger
                self.plugin_manager.load_all()
                input("\nAppuyez sur Entrée...")
            
            elif choice == "2" and plugins:
                idx = input("Numéro du plugin: ").strip()
                try:
                    plugin = plugins[int(idx) - 1]
                    name = plugin['name']
                    if plugin['enabled']:
                        self.plugin_manager.disable_plugin(name)
                        print(f"Plugin '{name}' désactivé.")
                    else:
                        self.plugin_manager.enable_plugin(name)
                        # Recharger le plugin
                        p = self.plugin_manager.load_plugin(plugin['path'])
                        if p:
                            self.plugin_manager.register_plugin(p)
                        print(f"Plugin '{name}' activé.")
                except (ValueError, IndexError):
                    print("Choix invalide.")
                input("\nAppuyez sur Entrée...")
            
            elif choice == "3" and plugins:
                idx = input("Numéro du plugin: ").strip()
                try:
                    plugin = plugins[int(idx) - 1]
                    print(f"\n{'='*40}")
                    print(f"Nom: {plugin.get('name', 'Inconnu')}")
                    print(f"Version: {plugin.get('version', '?')}")
                    print(f"Auteur: {plugin.get('author', 'Inconnu')}")
                    print(f"Description: {plugin.get('description', '-')}")
                    print(f"Licence: {plugin.get('license', '-')}")
                    print(f"Homepage: {plugin.get('homepage', '-')}")
                    print(f"Chemin: {plugin.get('path', '-')}")
                    print(f"Statut: {'Chargé' if plugin['loaded'] else 'Non chargé'}")
                except (ValueError, IndexError):
                    print("Choix invalide.")
                input("\nAppuyez sur Entrée...")
            
            elif choice == "4":
                from launcher import DetachedLauncher
                DetachedLauncher.open_folder_detached(str(self.plugin_manager.plugins_path))
                print(f"Ouverture de: {self.plugin_manager.plugins_path}")
                input("\nAppuyez sur Entrée...")
            
            elif choice == "r":
                break
