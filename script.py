# script.py
import os
import subprocess
import json
from launcher import DetachedLauncher

class Script:
    CONFIG_FILE = "config.json"
    # Langages supportés avec extensions et commandes d'exécution
    LANGUAGES = {
        "python": {"ext": ".py", "cmd": ["python"], "template": "#!/usr/bin/env python3\n# {name}\nprint('Bonjour depuis', __file__)\n"},
        "bash": {"ext": ".sh", "cmd": ["bash"], "template": "#!/bin/bash\n# {name}\necho \"Bonjour depuis $0\"\n"},
        "powershell": {"ext": ".ps1", "cmd": ["powershell", "-File"], "template": "# {name}\nWrite-Host \"Bonjour depuis $PSCommandPath\"\n"},
        "javascript": {"ext": ".js", "cmd": ["node"], "template": "// {name}\nconsole.log('Bonjour depuis', __filename);\n"},
        "batch": {"ext": ".bat", "cmd": ["cmd", "/c"], "template": "@echo off\nREM {name}\necho Bonjour depuis %~f0\n"},
        "lua": {"ext": ".lua", "cmd": ["lua"], "template": "-- {name}\nprint('Bonjour depuis ' .. arg[0])\n"},
    }

    @staticmethod
    def get_config_path(program):
        """Retourne le chemin du fichier de configuration."""
        return os.path.join(program.current_path, "data", Script.CONFIG_FILE)

    # Éditeurs prédéfinis avec leurs commandes
    # "tui": True indique un éditeur terminal qui nécessite une fenêtre console
    EDITORS = {
        "vscode": {"cmd": "code", "name": "Visual Studio Code", "tui": False},
        "codium": {"cmd": "codium", "name": "VSCodium", "tui": False},
        "nvim": {"cmd": "nvim", "name": "Neovim", "tui": True},
        "vim": {"cmd": "vim", "name": "Vim", "tui": True},
        "nano": {"cmd": "nano", "name": "Nano", "tui": True},
        "notepad++": {"cmd": "notepad++", "name": "Notepad++", "tui": False},
        "sublime": {"cmd": "subl", "name": "Sublime Text", "tui": False},
        "atom": {"cmd": "atom", "name": "Atom", "tui": False},
        "emacs": {"cmd": "emacs", "name": "Emacs", "tui": True},
        "notepad": {"cmd": "notepad", "name": "Notepad", "tui": False},
        "system": {"cmd": None, "name": "Éditeur système par défaut", "tui": False},
    }

    @staticmethod
    def load_config(program):
        """Charge la configuration depuis le fichier JSON."""
        config_path = Script.get_config_path(program)
        default_config = {
            "autostart": {"enabled": False, "scripts": []},
            "editor": "system",  # Éditeur par défaut: système
            "first_run_complete": False,
            "ascii_enabled": True
        }
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # Assurer la compatibilité avec les anciennes configs
                    if "editor" not in config:
                        config["editor"] = "system"
                    if "first_run_complete" not in config:
                        config["first_run_complete"] = False
                    if "ascii_enabled" not in config:
                        config["ascii_enabled"] = True
                    return config
        except (json.JSONDecodeError, IOError):
            pass
        return default_config

    @staticmethod
    def save_config(program, config):
        """Sauvegarde la configuration dans le fichier JSON."""
        config_path = Script.get_config_path(program)
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    @staticmethod
    def run_autostart(program):
        """Exécute les scripts configurés au démarrage avec accord utilisateur."""
        config = Script.load_config(program)
        autostart = config.get("autostart", {})
        
        if not autostart.get("enabled", False):
            return
        
        scripts = autostart.get("scripts", [])
        if not scripts:
            return
        
        print("\n" + "=" * 50)
        print("        SCRIPTS AUTO-START DÉTECTÉS")
        print("=" * 50)
        print(f"\n{len(scripts)} script(s) configuré(s) pour l'auto-démarrage:\n")
        
        for i, script_info in enumerate(scripts, 1):
            status = "✓" if os.path.exists(script_info["path"]) else "✗"
            print(f"  {i}. [{status}] {script_info['name']}")
        
        print("\n  [O] Exécuter tous les scripts")
        print("  [S] Sélectionner lesquels exécuter")
        print("  [N] Ne pas exécuter (passer)")
        
        choice = input("\nVotre choix: ").strip().lower()
        
        if choice == 'o':
            Script._execute_autostart_scripts(scripts)
        elif choice == 's':
            Script._select_and_execute_autostart(scripts)
        else:
            print("Auto-start ignoré.")
        
        input("\nAppuyez sur Entrée pour continuer...")

    @staticmethod
    def _execute_autostart_scripts(scripts):
        """Exécute une liste de scripts."""
        for script_info in scripts:
            path = script_info["path"]
            name = script_info["name"]
            
            if not os.path.exists(path):
                print(f"[ERREUR] Script introuvable: {name}")
                continue
            
            lang, info = Script.get_language_for_file(name)
            if not lang:
                print(f"[ERREUR] Langage non supporté: {name}")
                continue
            
            print(f"\n>>> Exécution: {name} ({lang})")
            print("-" * 40)
            try:
                subprocess.run(info["cmd"] + [path], check=True)
                print(f"[OK] {name} terminé")
            except subprocess.CalledProcessError as e:
                print(f"[ERREUR] {name}: {e}")
            except FileNotFoundError:
                print(f"[ERREUR] Interpréteur '{info['cmd'][0]}' non trouvé")

    @staticmethod
    def _select_and_execute_autostart(scripts):
        """Permet de sélectionner quels scripts exécuter."""
        print("\nEntrez les numéros des scripts à exécuter (séparés par des virgules):")
        selection = input(">> ").strip()
        
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(",")]
            selected = [scripts[i] for i in indices if 0 <= i < len(scripts)]
            if selected:
                Script._execute_autostart_scripts(selected)
            else:
                print("Aucun script sélectionné.")
        except (ValueError, IndexError):
            print("Sélection invalide.")

    @staticmethod
    def manage_autostart(program):
        """Gère les scripts auto-start."""
        while True:
            config = Script.load_config(program)
            autostart = config.get("autostart", {"enabled": False, "scripts": []})
            
            print("\n--- Gestion Auto-Start ---")
            status = "ACTIVÉ ✓" if autostart.get("enabled") else "DÉSACTIVÉ ✗"
            print(f"\nStatut: {status}")
            print(f"Scripts configurés: {len(autostart.get('scripts', []))}")
            
            if autostart.get("scripts"):
                print("\nScripts auto-start:")
                for i, s in enumerate(autostart["scripts"], 1):
                    exists = "✓" if os.path.exists(s["path"]) else "✗"
                    print(f"  {i}. [{exists}] {s['name']}")
            
            print("\n  1. Activer/Désactiver l'auto-start")
            print("  2. Ajouter un script")
            print("  3. Retirer un script")
            print("  4. Retour")
            
            choice = input("\nChoix: ").strip()
            
            if choice == "1":
                autostart["enabled"] = not autostart.get("enabled", False)
                config["autostart"] = autostart
                Script.save_config(program, config)
                new_status = "activé" if autostart["enabled"] else "désactivé"
                print(f"Auto-start {new_status}.")
            
            elif choice == "2":
                script = Script.select_script(program, "ajouter à l'auto-start")
                if script:
                    script_path = os.path.join(program.scripts_path, script)
                    # Vérifier si déjà présent
                    existing = [s["path"] for s in autostart.get("scripts", [])]
                    if script_path in existing:
                        print(f"{script} est déjà dans l'auto-start.")
                    else:
                        autostart.setdefault("scripts", []).append({
                            "name": script,
                            "path": script_path
                        })
                        config["autostart"] = autostart
                        Script.save_config(program, config)
                        print(f"{script} ajouté à l'auto-start.")
            
            elif choice == "3":
                scripts_list = autostart.get("scripts", [])
                if not scripts_list:
                    print("Aucun script à retirer.")
                else:
                    print("\nScript à retirer:")
                    for i, s in enumerate(scripts_list, 1):
                        print(f"  {i}. {s['name']}")
                    idx = input("Numéro (ou 'q' pour annuler): ").strip()
                    if idx.lower() != 'q':
                        try:
                            removed = scripts_list.pop(int(idx) - 1)
                            config["autostart"] = autostart
                            Script.save_config(program, config)
                            print(f"{removed['name']} retiré de l'auto-start.")
                        except (ValueError, IndexError):
                            print("Choix invalide.")
            
            elif choice == "4":
                break

    @staticmethod
    def get_supported_extensions():
        """Retourne toutes les extensions supportées."""
        return tuple(lang["ext"] for lang in Script.LANGUAGES.values())

    @staticmethod
    def get_language_for_file(filename):
        """Retourne le langage correspondant à un fichier."""
        for lang, info in Script.LANGUAGES.items():
            if filename.endswith(info["ext"]):
                return lang, info
        return None, None

    @staticmethod
    def list_scripts(path):
        """Liste tous les scripts supportés dans un dossier."""
        extensions = Script.get_supported_extensions()
        if not os.path.isdir(path):
            return []
        return [f for f in os.listdir(path) if f.endswith(extensions)]

    @staticmethod
    def select_script(program, action="sélectionner"):
        """Affiche et permet de sélectionner un script."""
        scripts = Script.list_scripts(program.scripts_path)
        if not scripts:
            print(f"Aucun script trouvé dans {program.scripts_path}")
            input("\nAppuyez sur Entrée pour continuer...")
            return None
        
        print(f"\nScripts disponibles dans: {program.scripts_path}")
        for i, script in enumerate(scripts, 1):
            lang, _ = Script.get_language_for_file(script)
            print(f"  {i}. [{lang}] {script}")
        
        print(f"\n  A. Chercher dans un autre dossier")
        choice = input(f"\nChoisissez un script à {action} (numéro) ou 'q' pour quitter: ").strip()
        
        if choice.lower() == 'q':
            return None
        if choice.lower() == 'a':
            new_path = input("Chemin du dossier: ").strip()
            if os.path.isdir(new_path):
                program.scripts_path = new_path
                return Script.select_script(program, action)
            else:
                print("Chemin invalide.")
                return None
        try:
            return scripts[int(choice) - 1]
        except (ValueError, IndexError):
            print("Choix invalide.")
            return None

    @staticmethod
    def execute_script(program, detached=False):
        """Exécute un script sélectionné."""
        print(f"\n--- Exécution d'un script ---")
        script = Script.select_script(program, "exécuter")
        if not script:
            return
        
        lang, info = Script.get_language_for_file(script)
        script_path = os.path.join(program.scripts_path, script)
        
        # Hook PRE_EXECUTE (si plugin_manager existe)
        if hasattr(program, 'plugin_manager'):
            from plugins import HookType
            results = program.plugin_manager.trigger_hook(
                HookType.PRE_EXECUTE, script, script_path
            )
            # Si un plugin retourne False, annuler l'exécution
            if False in results:
                print("Exécution annulée par un plugin.")
                input("\nAppuyez sur Entrée pour continuer...")
                return
        
        print(f"\n  [1] Exécution normale (bloquante)")
        print(f"  [2] Exécution détachée (arrière-plan)")
        print(f"  [3] Exécution dans un nouveau terminal")
        mode = input("\nMode d'exécution: ").strip()
        
        return_code = 0
        
        if mode == "2":
            # Exécution détachée
            pid = DetachedLauncher.run_script_detached(script_path, info["cmd"])
            if pid:
                print(f"\n{script} lancé en arrière-plan (PID: {pid})")
                print("Le script continue son exécution indépendamment.")
            else:
                print(f"Erreur lors du lancement détaché.")
                return_code = 1
        
        elif mode == "3":
            # Nouveau terminal
            pid = DetachedLauncher.open_terminal_with_script(script_path, info["cmd"])
            if pid:
                print(f"\n{script} lancé dans un nouveau terminal (PID: {pid})")
            else:
                print(f"Erreur lors de l'ouverture du terminal.")
                return_code = 1
        
        else:
            # Exécution normale bloquante
            print(f"\nExécution de {script} ({lang})...")
            print("-" * 40)
            try:
                result = subprocess.run(info["cmd"] + [script_path])
                return_code = result.returncode
            except subprocess.CalledProcessError as e:
                print(f"Erreur lors de l'exécution: {e}")
                return_code = e.returncode
            except FileNotFoundError:
                print(f"Interpréteur '{info['cmd'][0]}' non trouvé.")
                return_code = 1
        
        # Hook POST_EXECUTE
        if hasattr(program, 'plugin_manager'):
            from plugins import HookType
            program.plugin_manager.trigger_hook(
                HookType.POST_EXECUTE, script, script_path, return_code
            )
        
        input("\nAppuyez sur Entrée pour continuer...")

    @staticmethod
    def select_language():
        """Permet de choisir un langage de script."""
        print("\nLangages disponibles:")
        langs = list(Script.LANGUAGES.keys())
        for i, lang in enumerate(langs, 1):
            ext = Script.LANGUAGES[lang]["ext"]
            print(f"  {i}. {lang.capitalize()} ({ext})")
        
        choice = input("\nChoisissez un langage (numéro) ou 'q' pour quitter: ").strip()
        if choice.lower() == 'q':
            return None, None
        try:
            lang = langs[int(choice) - 1]
            return lang, Script.LANGUAGES[lang]
        except (ValueError, IndexError):
            print("Choix invalide.")
            return None, None

    @staticmethod
    def create_script(program):
        """Crée un nouveau script dans le langage choisi."""
        print("\n--- Création d'un nouveau script ---")
        
        lang, info = Script.select_language()
        if not lang:
            return
        
        name = input(f"Nom du script (sans extension {info['ext']}): ").strip()
        if not name:
            print("Nom invalide.")
            return
        
        filename = name + info["ext"]
        path = os.path.join(program.scripts_path, filename)
        
        if os.path.exists(path):
            print(f"Le fichier {filename} existe déjà.")
            return
        
        os.makedirs(program.scripts_path, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(info["template"].format(name=name))
        
        print(f"Script créé: {path}")
        
        edit = input("Voulez-vous l'éditer maintenant? (o/n): ").strip().lower()
        if edit == 'o':
            Script._open_in_editor(path, program=program)
        
        input("\nAppuyez sur Entrée pour continuer...")

    @staticmethod
    def edit_script(program):
        """Édite un script existant."""
        print("\n--- Édition d'un script ---")
        script = Script.select_script(program, "éditer")
        if not script:
            return
        
        script_path = os.path.join(program.scripts_path, script)
        Script._open_in_editor(script_path, program=program)
        input("\nAppuyez sur Entrée pour continuer...")

    @staticmethod
    def _open_in_editor(path, detached=True, program=None):
        """Ouvre un fichier dans l'éditeur configuré."""
        try:
            editor_cmd = None
            is_tui = False
            
            # Récupérer l'éditeur configuré si program est fourni
            if program:
                config = Script.load_config(program)
                editor_key = config.get("editor", "system")
                
                if config.get("editor_custom", False):
                    # Commande personnalisée - vérifier si c'est un éditeur TUI
                    editor_cmd = editor_key
                    is_tui = config.get("editor_tui", False)
                elif editor_key in Script.EDITORS:
                    editor_cmd = Script.EDITORS[editor_key]["cmd"]
                    is_tui = Script.EDITORS[editor_key].get("tui", False)
            
            if is_tui:
                # Éditeur TUI : ouvrir dans un nouveau terminal
                pid = DetachedLauncher.open_tui_editor(path, editor_cmd)
                if pid is not None:
                    print(f"Ouverture de {path} avec {editor_cmd} dans un terminal")
                    print("Le gestionnaire reste actif pendant l'édition.")
                else:
                    print(f"Erreur lors de l'ouverture de {path}")
            elif detached:
                # Ouverture détachée - le gestionnaire continue à fonctionner
                pid = DetachedLauncher.open_file_detached(path, editor=editor_cmd)
                if pid is not None:
                    editor_name = editor_cmd if editor_cmd else "éditeur système"
                    print(f"Ouverture de {path} avec {editor_name}")
                    print("Le gestionnaire reste actif pendant l'édition.")
                else:
                    print(f"Erreur lors de l'ouverture de {path}")
            else:
                # Ancien comportement bloquant
                if editor_cmd:
                    subprocess.run([editor_cmd, path])
                elif os.name == 'nt':  # Windows
                    os.startfile(path)
                else:  # Linux/Mac
                    subprocess.run(["xdg-open", path])
                print(f"Ouverture de {path} dans l'éditeur...")
        except Exception as e:
            print(f"Erreur lors de l'ouverture: {e}")

    @staticmethod
    def open_script(program):
        """Ouvre le dossier scripts dans l'explorateur ou liste dans le terminal."""
        print("\n--- Ouvrir les Scripts ---")
        print("  1. Ouvrir dans l'explorateur (UI)")
        print("  2. Lister dans le terminal")
        print("  R. Retour")
        
        choice = input("\nChoix: ").strip().lower()
        
        if choice == "1":
            Script.open_folder(program.scripts_path)
            print(f"Ouverture de: {program.scripts_path}")
        elif choice == "2":
            Script.list_scripts_terminal(program)
        elif choice == "r":
            return
        else:
            print("Choix invalide.")
        
        input("\nAppuyez sur Entrée pour continuer...")

    @staticmethod
    def list_scripts_terminal(program):
        """Liste les scripts dans le terminal."""
        scripts = Script.list_scripts(program.scripts_path)
        
        if not scripts:
            print("\nAucun script trouvé.")
            return
        
        print(f"\n--- Scripts dans {program.scripts_path} ---\n")
        
        # Grouper par extension
        by_ext = {}
        for script in scripts:
            ext = os.path.splitext(script)[1].lower()
            if ext not in by_ext:
                by_ext[ext] = []
            by_ext[ext].append(script)
        
        # Afficher avec numérotation
        total = 0
        for ext, files in sorted(by_ext.items()):
            lang_name = next((k for k, v in Script.LANGUAGES.items() if v["ext"] == ext), ext)
            print(f"  [{lang_name.upper()}]")
            for f in sorted(files):
                total += 1
                size = os.path.getsize(os.path.join(program.scripts_path, f))
                size_str = f"{size} B" if size < 1024 else f"{size/1024:.1f} KB"
                print(f"    {total:3}. {f} ({size_str})")
            print()
        
        print(f"Total: {total} script(s)")

    @staticmethod
    def open_folder(path, detached=True):
        """Ouvre un dossier dans l'explorateur de fichiers."""
        try:
            if detached:
                pid = DetachedLauncher.open_folder_detached(path)
                if pid is not None:
                    print(f"Ouverture du dossier: {path}")
                else:
                    print(f"Erreur lors de l'ouverture du dossier: {path}")
            else:
                if os.name == 'nt':  # Windows
                    subprocess.run(["explorer", path])
                else:  # Linux
                    subprocess.run(["nautilus", path])
                print(f"Ouverture du dossier: {path}")
        except FileNotFoundError:
            # Fallback pour Linux si nautilus n'est pas installé
            try:
                subprocess.run(["xdg-open", path])
            except Exception as e:
                print(f"Erreur lors de l'ouverture du dossier: {e}")

    @staticmethod
    def option(program):
        """Affiche les options et paramètres."""
        config = Script.load_config(program)
        current_editor = config.get("editor", "system")
        editor_info = Script.EDITORS.get(current_editor, Script.EDITORS["system"])
        ascii_status = "Activé" if config.get("ascii_enabled", True) else "Désactivé"
        
        print("\n--- Options & Paramètres ---")
        print(f"  1. Chemin scripts: {program.scripts_path}")
        print(f"  2. Cible: {program.target}")
        print(f"  3. Langages supportés: {', '.join(Script.LANGUAGES.keys())}")
        print(f"  4. Éditeur: {editor_info['name']} ({current_editor})")
        print(f"  5. ASCII Art: {ascii_status}")
        print(f"\n  C. Changer le chemin des scripts")
        print(f"  E. Changer l'éditeur de fichiers")
        print(f"  A. Activer/Désactiver ASCII Art")
        print(f"  F. Ouvrir le dossier scripts dans l'explorateur")
        print(f"  W. Relancer l'assistant de configuration")
        print(f"  R. Retour")
        
        choice = input("\nChoix: ").strip().lower()
        if choice == "c":
            new_path = input("Nouveau chemin: ").strip()
            if os.path.isdir(new_path):
                program.scripts_path = new_path
                print(f"Chemin mis à jour: {new_path}")
            else:
                create = input("Ce dossier n'existe pas. Le créer? (o/n): ").strip().lower()
                if create == 'o':
                    os.makedirs(new_path, exist_ok=True)
                    program.scripts_path = new_path
                    print(f"Dossier créé: {new_path}")
        elif choice == "e":
            Script._select_editor(program)
        elif choice == "a":
            config["ascii_enabled"] = not config.get("ascii_enabled", True)
            Script.save_config(program, config)
            status = "activé" if config["ascii_enabled"] else "désactivé"
            print(f"ASCII Art {status}.")
        elif choice == "f":
            Script.open_folder(program.scripts_path)
        elif choice == "w":
            config["first_run_complete"] = False
            Script.save_config(program, config)
            Script.first_run_setup(program)
        
        input("\nAppuyez sur Entrée pour continuer...")

    @staticmethod
    def _select_editor(program):
        """Permet de choisir l'éditeur de fichiers."""
        config = Script.load_config(program)
        current_editor = config.get("editor", "system")
        
        print("\n--- Choix de l'éditeur ---")
        print(f"Éditeur actuel: {Script.EDITORS.get(current_editor, {}).get('name', current_editor)}\n")
        
        editors_list = list(Script.EDITORS.keys())
        for i, editor_key in enumerate(editors_list, 1):
            editor = Script.EDITORS[editor_key]
            marker = " ✓" if editor_key == current_editor else ""
            cmd_info = f"({editor['cmd']})" if editor['cmd'] else "(défaut OS)"
            print(f"  {i}. {editor['name']} {cmd_info}{marker}")
        
        print(f"\n  P. Personnalisé (commande custom)")
        print(f"  R. Retour")
        
        choice = input("\nChoix: ").strip().lower()
        
        if choice == "r":
            return
        elif choice == "p":
            custom_cmd = input("Commande de l'éditeur (ex: nvim, code, subl): ").strip()
            if custom_cmd:
                config["editor"] = custom_cmd
                config["editor_custom"] = True
                # Demander si c'est un éditeur TUI
                is_tui = input("Est-ce un éditeur terminal (nvim, vim, nano)? (o/n): ").strip().lower()
                config["editor_tui"] = is_tui == 'o'
                Script.save_config(program, config)
                print(f"Éditeur personnalisé configuré: {custom_cmd}")
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(editors_list):
                    selected = editors_list[idx]
                    config["editor"] = selected
                    config["editor_custom"] = False
                    Script.save_config(program, config)
                    print(f"Éditeur configuré: {Script.EDITORS[selected]['name']}")
                else:
                    print("Choix invalide.")
            except ValueError:
                print("Choix invalide.")

    @staticmethod
    def is_first_run(program):
        """Vérifie si c'est la première exécution du gestionnaire."""
        config = Script.load_config(program)
        return not config.get("first_run_complete", False)

    @staticmethod
    def first_run_setup(program):
        """Assistant de configuration pour la première utilisation."""
        from program import Program
        Program.clear_screen()
        
        print("\n" + "=" * 60)
        print("        🎉 BIENVENUE DANS LE GESTIONNAIRE DE SCRIPTS 🎉")
        print("=" * 60)
        print("\nC'est votre première utilisation !")
        print("Configurons rapidement vos préférences.\n")
        
        config = Script.load_config(program)
        
        # === Étape 1: Éditeur ===
        print("-" * 40)
        print("ÉTAPE 1/3 : Choix de l'éditeur")
        print("-" * 40)
        print("\nQuel éditeur souhaitez-vous utiliser pour éditer vos scripts?\n")
        
        editors_list = list(Script.EDITORS.keys())
        for i, editor_key in enumerate(editors_list, 1):
            editor = Script.EDITORS[editor_key]
            cmd_info = f"({editor['cmd']})" if editor['cmd'] else "(défaut OS)"
            tui_info = " [Terminal]" if editor.get('tui', False) else ""
            print(f"  {i}. {editor['name']} {cmd_info}{tui_info}")
        
        print(f"\n  P. Personnalisé (commande custom)")
        
        choice = input("\nVotre choix [1-11 ou P]: ").strip().lower()
        
        if choice == "p":
            custom_cmd = input("Commande de l'éditeur: ").strip()
            if custom_cmd:
                config["editor"] = custom_cmd
                config["editor_custom"] = True
                is_tui = input("Est-ce un éditeur terminal (o/n)? ").strip().lower()
                config["editor_tui"] = is_tui == 'o'
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(editors_list):
                    config["editor"] = editors_list[idx]
                    config["editor_custom"] = False
            except ValueError:
                config["editor"] = "system"
        
        # === Étape 2: ASCII Art ===
        Program.clear_screen()
        print("\n" + "-" * 40)
        print("ÉTAPE 2/3 : Affichage ASCII Art")
        print("-" * 40)
        
        # Afficher un exemple d'ASCII art
        ascii_art = program.theme_manager.get_current_ascii()
        if ascii_art:
            print("\nExemple d'ASCII art actuel:\n")
            print(ascii_art)
        
        print("\nVoulez-vous afficher l'ASCII art dans le menu principal?\n")
        print("  1. Oui (recommandé)")
        print("  2. Non")
        
        ascii_choice = input("\nVotre choix [1/2]: ").strip()
        config["ascii_enabled"] = ascii_choice != "2"
        
        # === Étape 3: Thème ===
        Program.clear_screen()
        print("\n" + "-" * 40)
        print("ÉTAPE 3/3 : Personnalisation")
        print("-" * 40)
        print("\nVous pourrez personnaliser davantage via:")
        print("  • Menu 8 (Personnalisation) - ASCII art, thèmes")
        print("  • Menu 6 (Options) - Éditeur, chemins")
        print("  • Menu 7 (Plugins) - Extensions")
        
        input("\nAppuyez sur Entrée pour terminer la configuration...")
        
        # Marquer comme configuré
        config["first_run_complete"] = True
        Script.save_config(program, config)
        
        Program.clear_screen()
        print("\n" + "=" * 60)
        print("        ✅ CONFIGURATION TERMINÉE !")
        print("=" * 60)
        
        editor_name = config.get("editor", "system")
        if editor_name in Script.EDITORS:
            editor_name = Script.EDITORS[editor_name]["name"]
        
        print(f"\n  • Éditeur: {editor_name}")
        print(f"  • ASCII Art: {'Activé' if config.get('ascii_enabled', True) else 'Désactivé'}")
        print(f"  • Dossier scripts: {program.scripts_path}")
        
        print("\nVous pouvez modifier ces paramètres à tout moment")
        print("dans le menu Options & Paramètres (6/P).\n")
        
        input("Appuyez sur Entrée pour démarrer...")
