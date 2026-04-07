# program.py
import os
from script import Script as s
from plugins import PluginManager, HookType
from themes import ThemeManager

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
        # Déclencher le hook ON_STARTUP
        self.plugin_manager.trigger_hook(HookType.ON_STARTUP)
        s.run_autostart(self)

    def ascii_dashboard(self):
        """Affiche un tableau de bord ASCII personnalisable."""
        # Afficher l'ASCII art (personnalisable via themes)
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
            self.clear_screen()
            self.ascii_dashboard()
            
            # Déclencher le hook avant affichage du menu
            self.plugin_manager.trigger_hook(HookType.ON_MENU_DISPLAY)
            
            print("  0. Exit")
            print("  1. Executer Un Script    [E]")
            print("  2. Nouveau Script        [N]")
            print("  3. Éditer Un Script      [D]")
            print("  4. Ouvrir Un Script      [O]")
            print("  5. Auto-Start            [A]")
            print("  6. Options & Paramètres  [P]")
            print("  7. Plugins               [L]")
            print("  8. Personnalisation      [T]")
            
            # Afficher les éléments de menu des plugins
            for item in self.plugin_manager.menu_items:
                print(f"  {item['key']}. {item['label']}")
            
            imenu = input("\n>> ").strip().lower()
            
            # Déclencher le hook après choix
            self.plugin_manager.trigger_hook(HookType.ON_MENU_CHOICE, choice=imenu)

            match imenu:
                case "0" | "exit" | "q":
                    self.plugin_manager.trigger_hook(HookType.ON_SHUTDOWN)
                    self.clear_screen()
                    print("\n>> Au revoir <<\n")
                    exit(0)
                case "1" | "e":
                    s.execute_script(self)
                case "2" | "n":
                    s.create_script(self)
                case "3" | "d":
                    s.edit_script(self)
                case "4" | "o":
                    s.open_script(self)
                case "5" | "a":
                    s.manage_autostart(self)
                case "6" | "p":
                    s.option(self)
                case "7" | "l":
                    self.manage_plugins()
                case "8" | "t":
                    from themes import manage_themes
                    manage_themes(self)
                case _:
                    # Vérifier les commandes des plugins
                    handled = False
                    for item in self.plugin_manager.menu_items:
                        if imenu == item['key'].lower():
                            item['handler']()
                            handled = True
                            break
                    if not handled:
                        print("Choix invalide. Réessayez.")
                        input("\nAppuyez sur Entrée...")
    
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
