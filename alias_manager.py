#!/usr/bin/env python3
# alias_manager.py
"""
Gestionnaire d'alias et raccourcis pour le Script Manager.
Supporte:
- Alias terminal (bash, zsh, PowerShell, cmd)
- Raccourcis clavier Windows (via .lnk)
- Raccourcis clavier Linux (via .desktop + keybind)
"""
import os
import sys
import json
import platform
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Tuple


class AliasManager:
    """Gère les alias et raccourcis système."""
    
    DEFAULT_ALIAS = "sm"
    APP_NAME = "Script Manager"
    
    def __init__(self, app_path: str):
        self.app_path = Path(app_path).absolute()
        self.main_script = self.app_path / "main.py"
        self.config_file = self.app_path / "data" / "alias_config.json"
        self.system = platform.system()
        
        # Créer le dossier data si nécessaire
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Charge la configuration des alias."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {
            "aliases": [self.DEFAULT_ALIAS],
            "shortcuts": [],
            "autorun_enabled": False,
            "autorun_method": None  # "shell_profile", "startup", "login"
        }
    
    def _save_config(self):
        """Sauvegarde la configuration."""
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    # =========================================================================
    # DÉTECTION DES SHELLS ET PROFILES
    # =========================================================================
    
    def detect_shells(self) -> List[Dict]:
        """Détecte les shells disponibles et leurs fichiers de config."""
        shells = []
        home = Path.home()
        
        if self.system == "Windows":
            # PowerShell Core
            pwsh_profile = home / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
            if self._command_exists("pwsh"):
                shells.append({
                    "name": "PowerShell Core",
                    "command": "pwsh",
                    "profile": pwsh_profile,
                    "alias_format": 'function {alias} {{ Set-Location "{path}"; python main.py $args }}'
                })
            
            # Windows PowerShell
            ps_profile = home / "Documents" / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1"
            shells.append({
                "name": "Windows PowerShell",
                "command": "powershell",
                "profile": ps_profile,
                "alias_format": 'function {alias} {{ Set-Location "{path}"; python main.py $args }}'
            })
            
            # Git Bash
            gitbash_profile = home / ".bashrc"
            if (home / ".gitconfig").exists() or self._command_exists("git"):
                shells.append({
                    "name": "Git Bash",
                    "command": "bash",
                    "profile": gitbash_profile,
                    "alias_format": 'alias {alias}=\'cd "{path}" && python main.py\''
                })
            
            # CMD (via doskey dans un fichier autorun)
            cmd_autorun = home / "cmd_autorun.cmd"
            shells.append({
                "name": "CMD (doskey)",
                "command": "cmd",
                "profile": cmd_autorun,
                "alias_format": 'doskey {alias}=cd /d "{path}" $T python main.py $*',
                "special": "cmd_autorun"
            })
        
        else:  # Linux / macOS
            # Bash
            bashrc = home / ".bashrc"
            bash_profile = home / ".bash_profile"
            if bashrc.exists() or self._command_exists("bash"):
                shells.append({
                    "name": "Bash",
                    "command": "bash",
                    "profile": bashrc if bashrc.exists() else bash_profile,
                    "alias_format": 'alias {alias}=\'cd "{path}" && python3 main.py\''
                })
            
            # Zsh
            zshrc = home / ".zshrc"
            if zshrc.exists() or self._command_exists("zsh"):
                shells.append({
                    "name": "Zsh",
                    "command": "zsh",
                    "profile": zshrc,
                    "alias_format": 'alias {alias}=\'cd "{path}" && python3 main.py\''
                })
            
            # Fish
            fish_config = home / ".config" / "fish" / "config.fish"
            if fish_config.exists() or self._command_exists("fish"):
                shells.append({
                    "name": "Fish",
                    "command": "fish",
                    "profile": fish_config,
                    "alias_format": 'alias {alias} "cd {path}; and python3 main.py"'
                })
        
        return shells
    
    def _command_exists(self, cmd: str) -> bool:
        """Vérifie si une commande existe."""
        try:
            if self.system == "Windows":
                result = subprocess.run(["where", cmd], capture_output=True)
            else:
                result = subprocess.run(["which", cmd], capture_output=True)
            return result.returncode == 0
        except:
            return False
    
    # =========================================================================
    # GESTION DES ALIAS SHELL
    # =========================================================================
    
    def add_alias(self, alias: str, shells: List[Dict] = None) -> Dict[str, bool]:
        """
        Ajoute un alias dans les profils shell.
        
        Args:
            alias: Nom de l'alias (ex: "sm", "scripts")
            shells: Liste des shells cibles (ou tous si None)
        
        Returns:
            Dict avec le résultat pour chaque shell
        """
        if shells is None:
            shells = self.detect_shells()
        
        results = {}
        marker = f"# {self.APP_NAME} alias: {alias}"
        
        for shell in shells:
            profile = shell["profile"]
            alias_line = shell["alias_format"].format(
                alias=alias,
                path=str(self.app_path).replace("\\", "/") if self.system != "Windows" else str(self.app_path)
            )
            
            try:
                # Créer le dossier parent si nécessaire
                profile.parent.mkdir(parents=True, exist_ok=True)
                
                # Lire le contenu existant
                content = ""
                if profile.exists():
                    content = profile.read_text(encoding="utf-8")
                
                # Vérifier si l'alias existe déjà
                if marker in content:
                    results[shell["name"]] = True
                    continue
                
                # Gérer le cas spécial de CMD
                if shell.get("special") == "cmd_autorun":
                    self._setup_cmd_autorun(profile, alias_line, marker)
                    results[shell["name"]] = True
                    continue
                
                # Ajouter l'alias
                with open(profile, "a", encoding="utf-8") as f:
                    f.write(f"\n{marker}\n{alias_line}\n")
                
                results[shell["name"]] = True
                
            except Exception as e:
                results[shell["name"]] = False
                print(f"  [!] Erreur {shell['name']}: {e}")
        
        # Mettre à jour la config
        if alias not in self.config["aliases"]:
            self.config["aliases"].append(alias)
            self._save_config()
        
        return results
    
    def _setup_cmd_autorun(self, profile: Path, alias_line: str, marker: str):
        """Configure l'autorun pour CMD."""
        import winreg
        
        # Créer/mettre à jour le fichier batch
        content = ""
        if profile.exists():
            content = profile.read_text(encoding="utf-8")
        
        if marker not in content:
            with open(profile, "a", encoding="utf-8") as f:
                f.write(f"\n{marker}\n{alias_line}\n")
        
        # Configurer le registre pour AutoRun
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Command Processor",
                0,
                winreg.KEY_ALL_ACCESS
            )
        except WindowsError:
            key = winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Command Processor"
            )
        
        try:
            winreg.SetValueEx(key, "AutoRun", 0, winreg.REG_SZ, str(profile))
        finally:
            winreg.CloseKey(key)
    
    def remove_alias(self, alias: str) -> Dict[str, bool]:
        """Supprime un alias de tous les profils shell."""
        shells = self.detect_shells()
        results = {}
        marker = f"# {self.APP_NAME} alias: {alias}"
        
        for shell in shells:
            profile = shell["profile"]
            
            try:
                if not profile.exists():
                    results[shell["name"]] = True
                    continue
                
                content = profile.read_text(encoding="utf-8")
                lines = content.split("\n")
                new_lines = []
                skip_next = False
                
                for line in lines:
                    if marker in line:
                        skip_next = True
                        continue
                    if skip_next:
                        skip_next = False
                        continue
                    new_lines.append(line)
                
                profile.write_text("\n".join(new_lines), encoding="utf-8")
                results[shell["name"]] = True
                
            except Exception as e:
                results[shell["name"]] = False
        
        # Mettre à jour la config
        if alias in self.config["aliases"]:
            self.config["aliases"].remove(alias)
            self._save_config()
        
        return results
    
    def list_aliases(self) -> List[str]:
        """Liste tous les alias configurés."""
        return self.config.get("aliases", [])
    
    # =========================================================================
    # RACCOURCIS CLAVIER
    # =========================================================================
    
    def create_keyboard_shortcut(self, hotkey: str = None) -> bool:
        """
        Crée un raccourci clavier système.
        
        Args:
            hotkey: Raccourci (ex: "Ctrl+Alt+S")
        
        Returns:
            True si succès
        """
        if self.system == "Windows":
            return self._create_windows_shortcut(hotkey)
        else:
            return self._create_linux_shortcut(hotkey)
    
    def _create_windows_shortcut(self, hotkey: str = None) -> bool:
        """Crée un raccourci .lnk Windows avec hotkey optionnel."""
        try:
            import ctypes
            from ctypes import wintypes
            
            # Créer le raccourci dans le dossier Programmes du menu Démarrer
            start_menu = Path(os.environ.get(
                "APPDATA", 
                Path.home() / "AppData" / "Roaming"
            )) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            
            shortcut_path = start_menu / f"{self.APP_NAME}.lnk"
            
            # Utiliser PowerShell pour créer le raccourci
            python_exe = sys.executable
            ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{python_exe}"
$Shortcut.Arguments = "main.py"
$Shortcut.WorkingDirectory = "{self.app_path}"
$Shortcut.Description = "{self.APP_NAME}"
$Shortcut.IconLocation = "{python_exe},0"
'''
            if hotkey:
                # Convertir le hotkey au format Windows
                # Ctrl+Alt+S -> "Ctrl+Alt+S"
                ps_script += f'$Shortcut.Hotkey = "{hotkey}"\n'
            
            ps_script += "$Shortcut.Save()"
            
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True
            )
            
            if result.returncode == 0:
                # Sauvegarder dans la config
                shortcut_info = {
                    "type": "windows_shortcut",
                    "path": str(shortcut_path),
                    "hotkey": hotkey
                }
                if shortcut_info not in self.config["shortcuts"]:
                    self.config["shortcuts"].append(shortcut_info)
                    self._save_config()
                return True
            
            return False
            
        except Exception as e:
            print(f"[!] Erreur création raccourci: {e}")
            return False
    
    def _create_linux_shortcut(self, hotkey: str = None) -> bool:
        """Crée un fichier .desktop et configure le raccourci clavier."""
        try:
            # Créer le fichier .desktop
            applications_dir = Path.home() / ".local" / "share" / "applications"
            applications_dir.mkdir(parents=True, exist_ok=True)
            
            desktop_file = applications_dir / "script-manager.desktop"
            python_exe = sys.executable or "python3"
            
            desktop_content = f"""[Desktop Entry]
Type=Application
Name={self.APP_NAME}
Comment=Gestionnaire de Scripts Python
Exec={python_exe} {self.main_script}
Path={self.app_path}
Terminal=true
Icon=utilities-terminal
Categories=Development;Utility;
Keywords=scripts;python;manager;
"""
            desktop_file.write_text(desktop_content)
            desktop_file.chmod(0o755)
            
            # Configurer le raccourci clavier si spécifié
            if hotkey:
                self._set_linux_keybind(hotkey, str(desktop_file))
            
            # Sauvegarder dans la config
            shortcut_info = {
                "type": "linux_desktop",
                "path": str(desktop_file),
                "hotkey": hotkey
            }
            if shortcut_info not in self.config["shortcuts"]:
                self.config["shortcuts"].append(shortcut_info)
                self._save_config()
            
            return True
            
        except Exception as e:
            print(f"[!] Erreur création raccourci: {e}")
            return False
    
    def _set_linux_keybind(self, hotkey: str, command: str):
        """Configure un raccourci clavier sous Linux (GNOME/KDE)."""
        # Détecter l'environnement de bureau
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        
        if "gnome" in desktop or "unity" in desktop:
            self._set_gnome_keybind(hotkey, command)
        elif "kde" in desktop or "plasma" in desktop:
            self._set_kde_keybind(hotkey, command)
        else:
            print(f"  [!] Environnement de bureau non supporté pour les raccourcis: {desktop}")
            print(f"      Configurez manuellement: {hotkey} -> {command}")
    
    def _set_gnome_keybind(self, hotkey: str, command: str):
        """Configure un raccourci GNOME."""
        try:
            import uuid
            keybind_id = str(uuid.uuid4())
            
            # Convertir le hotkey (Ctrl+Alt+S -> <Control><Alt>s)
            gnome_hotkey = hotkey.replace("Ctrl", "<Control>").replace("Alt", "<Alt>").replace("Shift", "<Shift>")
            gnome_hotkey = gnome_hotkey.replace("+", "").replace(" ", "")
            
            path = f"/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom{keybind_id}/"
            
            commands = [
                f"gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings \"['{path}']\"",
                f"gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:{path} name 'Script Manager'",
                f"gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:{path} command 'gtk-launch script-manager'",
                f"gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:{path} binding '{gnome_hotkey}'"
            ]
            
            for cmd in commands:
                subprocess.run(cmd, shell=True, capture_output=True)
                
        except Exception as e:
            print(f"  [!] Erreur configuration GNOME: {e}")
    
    def _set_kde_keybind(self, hotkey: str, command: str):
        """Configure un raccourci KDE Plasma."""
        try:
            # KDE utilise kwriteconfig5
            subprocess.run([
                "kwriteconfig5", "--file", "kglobalshortcutsrc",
                "--group", "script-manager.desktop",
                "--key", "_launch",
                f"{hotkey},none,Script Manager"
            ], capture_output=True)
        except Exception as e:
            print(f"  [!] Erreur configuration KDE: {e}")
    
    def update_keyboard_shortcut(self, new_hotkey: str) -> bool:
        """
        Met à jour le raccourci clavier existant.
        
        Args:
            new_hotkey: Nouveau raccourci (ex: "Ctrl+Alt+M") ou None pour supprimer
        
        Returns:
            True si succès
        """
        if self.system == "Windows":
            return self._update_windows_shortcut(new_hotkey)
        else:
            return self._update_linux_shortcut(new_hotkey)
    
    def _update_windows_shortcut(self, new_hotkey: str) -> bool:
        """Met à jour ou supprime le hotkey du raccourci Windows."""
        try:
            start_menu = Path(os.environ.get(
                "APPDATA", 
                Path.home() / "AppData" / "Roaming"
            )) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            
            shortcut_path = start_menu / f"{self.APP_NAME}.lnk"
            
            if not shortcut_path.exists():
                print("[!] Raccourci non trouvé. Créez-le d'abord.")
                return False
            
            # Mettre à jour via PowerShell
            python_exe = sys.executable
            ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{python_exe}"
$Shortcut.Arguments = "main.py"
$Shortcut.WorkingDirectory = "{self.app_path}"
$Shortcut.Description = "{self.APP_NAME}"
$Shortcut.IconLocation = "{python_exe},0"
$Shortcut.Hotkey = "{new_hotkey if new_hotkey else ''}"
$Shortcut.Save()
'''
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True
            )
            
            if result.returncode == 0:
                # Mettre à jour la config
                for shortcut in self.config.get("shortcuts", []):
                    if shortcut.get("type") == "windows_shortcut":
                        shortcut["hotkey"] = new_hotkey
                self._save_config()
                return True
            
            return False
            
        except Exception as e:
            print(f"[!] Erreur mise à jour raccourci: {e}")
            return False
    
    def _update_linux_shortcut(self, new_hotkey: str) -> bool:
        """Met à jour le raccourci Linux."""
        # Pour Linux, on recrée simplement le raccourci
        return self._create_linux_shortcut(new_hotkey)
    
    def remove_keyboard_shortcut(self) -> bool:
        """Supprime le raccourci clavier."""
        if self.system == "Windows":
            return self._remove_windows_shortcut()
        else:
            return self._remove_linux_shortcut()
    
    def _remove_windows_shortcut(self) -> bool:
        """Supprime le raccourci Windows."""
        try:
            start_menu = Path(os.environ.get(
                "APPDATA", 
                Path.home() / "AppData" / "Roaming"
            )) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            
            shortcut_path = start_menu / f"{self.APP_NAME}.lnk"
            
            if shortcut_path.exists():
                shortcut_path.unlink()
            
            # Supprimer aussi le script AHK si présent
            ahk_script = self.app_path / "data" / "script_manager_hotkey.ahk"
            if ahk_script.exists():
                ahk_script.unlink()
            
            # Mettre à jour la config
            self.config["shortcuts"] = [
                s for s in self.config.get("shortcuts", [])
                if s.get("type") not in ("windows_shortcut", "autohotkey")
            ]
            self._save_config()
            
            return True
            
        except Exception as e:
            print(f"[!] Erreur suppression: {e}")
            return False
    
    def _remove_linux_shortcut(self) -> bool:
        """Supprime le raccourci Linux."""
        try:
            desktop_file = Path.home() / ".local" / "share" / "applications" / "script-manager.desktop"
            if desktop_file.exists():
                desktop_file.unlink()
            
            self.config["shortcuts"] = [
                s for s in self.config.get("shortcuts", [])
                if s.get("type") != "linux_desktop"
            ]
            self._save_config()
            
            return True
        except Exception as e:
            print(f"[!] Erreur suppression: {e}")
            return False
    
    def get_current_hotkey(self) -> Optional[str]:
        """Retourne le raccourci clavier actuel."""
        for shortcut in self.config.get("shortcuts", []):
            if shortcut.get("hotkey"):
                return shortcut["hotkey"]
        return None
    
    def create_autohotkey_shortcut(self, hotkey: str) -> bool:
        """
        Crée un script AutoHotkey pour un raccourci fiable.
        
        AutoHotkey est plus fiable que les raccourcis .lnk Windows
        car il surveille activement les touches.
        
        Args:
            hotkey: Raccourci au format "Ctrl+Alt+S"
        
        Returns:
            True si succès
        """
        try:
            # Convertir le hotkey au format AHK
            ahk_hotkey = self._convert_to_ahk_hotkey(hotkey)
            
            python_exe = sys.executable.replace("\\", "/")
            app_path = str(self.app_path).replace("\\", "/")
            
            ahk_script = f'''#Requires AutoHotkey v2.0
; Script Manager - Raccourci clavier
; Hotkey: {hotkey}
; Généré automatiquement

; {ahk_hotkey} pour lancer Script Manager
{ahk_hotkey}::
{{
    SetWorkingDir "{app_path}"
    Run '"{python_exe}" main.py',, "Min"
}}
'''
            # Sauvegarder le script
            ahk_file = self.app_path / "data" / "script_manager_hotkey.ahk"
            ahk_file.write_text(ahk_script, encoding="utf-8")
            
            # Créer aussi un script de démarrage
            startup_bat = self.app_path / "data" / "start_hotkey.bat"
            startup_bat.write_text(f'''@echo off
start "" "{ahk_file}"
''', encoding="utf-8")
            
            # Sauvegarder dans la config
            shortcut_info = {
                "type": "autohotkey",
                "path": str(ahk_file),
                "hotkey": hotkey
            }
            
            # Supprimer l'ancien AHK shortcut s'il existe
            self.config["shortcuts"] = [
                s for s in self.config.get("shortcuts", [])
                if s.get("type") != "autohotkey"
            ]
            self.config["shortcuts"].append(shortcut_info)
            self._save_config()
            
            return True
            
        except Exception as e:
            print(f"[!] Erreur création AHK: {e}")
            return False
    
    def _convert_to_ahk_hotkey(self, hotkey: str) -> str:
        """Convertit un hotkey au format AutoHotkey v2."""
        # Ctrl+Alt+S -> ^!s
        # Ctrl+Shift+S -> ^+s
        ahk = hotkey
        ahk = ahk.replace("Ctrl+", "^").replace("Ctrl", "^")
        ahk = ahk.replace("Alt+", "!").replace("Alt", "!")
        ahk = ahk.replace("Shift+", "+").replace("Shift", "+")
        ahk = ahk.replace("Win+", "#").replace("Win", "#")
        ahk = ahk.replace("Super+", "#").replace("Super", "#")
        # La touche finale en minuscule
        if ahk and ahk[-1].isupper():
            ahk = ahk[:-1] + ahk[-1].lower()
        return ahk
    
    def start_autohotkey(self) -> bool:
        """Lance le script AutoHotkey."""
        try:
            ahk_file = self.app_path / "data" / "script_manager_hotkey.ahk"
            if not ahk_file.exists():
                print("[!] Script AHK non trouvé.")
                return False
            
            # Lancer le script
            subprocess.Popen(
                ["cmd", "/c", "start", "", str(ahk_file)],
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            return True
            
        except Exception as e:
            print(f"[!] Erreur lancement AHK: {e}")
            return False
    
    def is_autohotkey_installed(self) -> bool:
        """Vérifie si AutoHotkey est installé."""
        try:
            # Chercher autohotkey dans le PATH ou dans Program Files
            result = subprocess.run(
                ["where", "autohotkey"],
                capture_output=True
            )
            if result.returncode == 0:
                return True
            
            # Chercher dans les emplacements communs
            common_paths = [
                Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "AutoHotkey" / "v2" / "AutoHotkey.exe",
                Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "AutoHotkey" / "AutoHotkey.exe",
                Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "AutoHotkey" / "v2" / "AutoHotkey.exe",
            ]
            
            for path in common_paths:
                if path.exists():
                    return True
            
            return False
            
        except:
            return False
    
    def refresh_windows_shortcut(self) -> bool:
        """
        Rafraîchit le cache du raccourci Windows.
        
        Parfois les hotkeys des .lnk ne fonctionnent pas car Windows
        n'a pas indexé le raccourci. Cette fonction force le rafraîchissement.
        """
        try:
            # Recréer le raccourci pour forcer le rafraîchissement
            current_hotkey = self.get_current_hotkey()
            
            start_menu = Path(os.environ.get(
                "APPDATA", 
                Path.home() / "AppData" / "Roaming"
            )) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            
            shortcut_path = start_menu / f"{self.APP_NAME}.lnk"
            
            # Supprimer et recréer
            if shortcut_path.exists():
                shortcut_path.unlink()
            
            # Recréer avec le même hotkey
            result = self._create_windows_shortcut(current_hotkey)
            
            if result:
                # Notifier l'Explorer pour rafraîchir
                try:
                    import ctypes
                    SHCNE_ASSOCCHANGED = 0x08000000
                    SHCNF_IDLIST = 0x0000
                    ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
                except:
                    pass
            
            return result
            
        except Exception as e:
            print(f"[!] Erreur rafraîchissement: {e}")
            return False
    
    # =========================================================================
    # AUTO-RUN (Démarrage automatique)
    # =========================================================================
    
    def setup_autorun(self, method: str = "startup") -> bool:
        """
        Configure le démarrage automatique.
        
        Args:
            method: 
                - "startup": Au démarrage de Windows/session Linux
                - "shell_profile": À chaque ouverture de terminal
                - "login": Au login (avant le bureau)
        
        Returns:
            True si succès
        """
        if method == "startup":
            return self._setup_startup_autorun()
        elif method == "shell_profile":
            return self._setup_shell_autorun()
        elif method == "login":
            return self._setup_login_autorun()
        return False
    
    def _setup_startup_autorun(self) -> bool:
        """Configure le démarrage au lancement du système."""
        if self.system == "Windows":
            return self._windows_startup()
        else:
            return self._linux_autostart()
    
    def _windows_startup(self) -> bool:
        """Ajoute au démarrage Windows."""
        try:
            startup_folder = Path(os.environ.get(
                "APPDATA",
                Path.home() / "AppData" / "Roaming"
            )) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            
            bat_file = startup_folder / "ScriptManager.bat"
            
            # Créer un script batch qui lance dans un nouveau terminal
            bat_content = f'''@echo off
start "" /D "{self.app_path}" python main.py --autostart
'''
            bat_file.write_text(bat_content)
            
            self.config["autorun_enabled"] = True
            self.config["autorun_method"] = "startup"
            self._save_config()
            
            return True
            
        except Exception as e:
            print(f"[!] Erreur: {e}")
            return False
    
    def _linux_autostart(self) -> bool:
        """Ajoute aux applications de démarrage Linux."""
        try:
            autostart_dir = Path.home() / ".config" / "autostart"
            autostart_dir.mkdir(parents=True, exist_ok=True)
            
            desktop_file = autostart_dir / "script-manager-autostart.desktop"
            python_exe = sys.executable or "python3"
            
            content = f"""[Desktop Entry]
Type=Application
Name={self.APP_NAME}
Exec=gnome-terminal -- {python_exe} {self.main_script} --autostart
Path={self.app_path}
Terminal=false
Hidden=false
X-GNOME-Autostart-enabled=true
"""
            desktop_file.write_text(content)
            
            self.config["autorun_enabled"] = True
            self.config["autorun_method"] = "startup"
            self._save_config()
            
            return True
            
        except Exception as e:
            print(f"[!] Erreur: {e}")
            return False
    
    def _setup_shell_autorun(self) -> bool:
        """Configure l'auto-run à l'ouverture du terminal."""
        shells = self.detect_shells()
        marker = f"# {self.APP_NAME} autorun"
        autorun_cmd = f'cd "{self.app_path}" && python{"3" if self.system != "Windows" else ""} main.py --autostart'
        
        for shell in shells:
            if shell.get("special") == "cmd_autorun":
                continue
                
            profile = shell["profile"]
            
            try:
                profile.parent.mkdir(parents=True, exist_ok=True)
                
                content = ""
                if profile.exists():
                    content = profile.read_text(encoding="utf-8")
                
                if marker not in content:
                    with open(profile, "a", encoding="utf-8") as f:
                        f.write(f"\n{marker}\n{autorun_cmd}\n")
                        
            except Exception as e:
                print(f"  [!] {shell['name']}: {e}")
        
        self.config["autorun_enabled"] = True
        self.config["autorun_method"] = "shell_profile"
        self._save_config()
        
        return True
    
    def _setup_login_autorun(self) -> bool:
        """Configure l'auto-run au login (avant le bureau)."""
        if self.system != "Windows":
            # Linux: utiliser ~/.profile ou ~/.bash_login
            profile = Path.home() / ".profile"
            marker = f"# {self.APP_NAME} login autorun"
            cmd = f'gnome-terminal -- python3 "{self.main_script}" --autostart &'
            
            try:
                content = profile.read_text() if profile.exists() else ""
                if marker not in content:
                    with open(profile, "a") as f:
                        f.write(f"\n{marker}\n{cmd}\n")
                
                self.config["autorun_enabled"] = True
                self.config["autorun_method"] = "login"
                self._save_config()
                return True
            except Exception as e:
                print(f"[!] Erreur: {e}")
                return False
        
        # Windows: pas de distinction login/startup pour l'utilisateur
        return self._windows_startup()
    
    def disable_autorun(self) -> bool:
        """Désactive le démarrage automatique."""
        method = self.config.get("autorun_method")
        
        if self.system == "Windows":
            # Supprimer du dossier Startup
            startup_folder = Path(os.environ.get(
                "APPDATA",
                Path.home() / "AppData" / "Roaming"
            )) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            
            bat_file = startup_folder / "ScriptManager.bat"
            if bat_file.exists():
                bat_file.unlink()
        
        else:
            # Supprimer le fichier autostart
            autostart_file = Path.home() / ".config" / "autostart" / "script-manager-autostart.desktop"
            if autostart_file.exists():
                autostart_file.unlink()
        
        # Nettoyer les profils shell si nécessaire
        if method == "shell_profile":
            marker = f"# {self.APP_NAME} autorun"
            for shell in self.detect_shells():
                profile = shell["profile"]
                if profile.exists():
                    try:
                        content = profile.read_text()
                        lines = content.split("\n")
                        new_lines = []
                        skip_next = False
                        for line in lines:
                            if marker in line:
                                skip_next = True
                                continue
                            if skip_next:
                                skip_next = False
                                continue
                            new_lines.append(line)
                        profile.write_text("\n".join(new_lines))
                    except:
                        pass
        
        self.config["autorun_enabled"] = False
        self.config["autorun_method"] = None
        self._save_config()
        
        return True
    
    def is_autorun_enabled(self) -> Tuple[bool, Optional[str]]:
        """Vérifie si l'autorun est activé."""
        return self.config.get("autorun_enabled", False), self.config.get("autorun_method")


# =============================================================================
# MENU INTERACTIF
# =============================================================================

def alias_menu(program):
    """Menu de gestion des alias et raccourcis."""
    manager = AliasManager(program.current_path)
    
    while True:
        program.clear_screen()
        print("\n" + "=" * 55)
        print("        ALIAS & RACCOURCIS - CONFIGURATION")
        print("=" * 55)
        
        # Statut actuel
        aliases = manager.list_aliases()
        autorun_enabled, autorun_method = manager.is_autorun_enabled()
        
        print(f"\n  📝 Alias configurés: {', '.join(aliases) if aliases else 'Aucun'}")
        
        autorun_status = "Désactivé"
        if autorun_enabled:
            method_names = {
                "startup": "Démarrage système",
                "shell_profile": "Ouverture terminal",
                "login": "Login utilisateur"
            }
            autorun_status = f"Activé ({method_names.get(autorun_method, autorun_method)})"
        print(f"  🚀 Auto-Run: {autorun_status}")
        
        shortcuts = manager.config.get("shortcuts", [])
        if shortcuts:
            for s in shortcuts:
                if s.get("hotkey"):
                    print(f"  ⌨️  Raccourci: {s['hotkey']}")
        
        print("\n" + "-" * 55)
        print("\n  ALIAS TERMINAL")
        print("  1. Ajouter un alias")
        print("  2. Supprimer un alias")
        print("  3. Voir les shells détectés")
        
        print("\n  RACCOURCIS CLAVIER")
        print("  4. Gérer les raccourcis clavier")
        
        print("\n  AUTO-RUN")
        print("  5. Configurer l'auto-run")
        print("  6. Désactiver l'auto-run")
        
        print("\n  7. Installation rapide (alias + raccourci)")
        print("\n  R. Retour")
        
        choice = input("\n>> Choix: ").strip().lower()
        
        if choice == "1":
            _add_alias_menu(manager)
        elif choice == "2":
            _remove_alias_menu(manager)
        elif choice == "3":
            _show_shells(manager)
        elif choice == "4":
            _keyboard_shortcut_menu(manager)
        elif choice == "5":
            _setup_autorun_menu(manager)
        elif choice == "6":
            if manager.disable_autorun():
                print("\n[OK] Auto-run désactivé!")
            input("\nAppuyez sur Entrée...")
        elif choice == "7":
            _quick_setup(manager)
        elif choice == "r":
            break


def _add_alias_menu(manager: AliasManager):
    """Menu pour ajouter un alias."""
    print("\n--- AJOUTER UN ALIAS ---")
    print(f"Alias suggéré: {manager.DEFAULT_ALIAS}")
    
    alias = input("Nom de l'alias (ou Entrée pour défaut): ").strip()
    if not alias:
        alias = manager.DEFAULT_ALIAS
    
    # Valider le nom
    if not alias.isalnum() and "_" not in alias:
        print("[!] Nom invalide. Utilisez uniquement lettres, chiffres et _")
        input("\nAppuyez sur Entrée...")
        return
    
    print(f"\nAjout de l'alias '{alias}'...")
    results = manager.add_alias(alias)
    
    print("\nRésultats:")
    for shell, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {shell}")
    
    print(f"\n[OK] Alias '{alias}' configuré!")
    print("     Redémarrez votre terminal pour l'utiliser.")
    input("\nAppuyez sur Entrée...")


def _remove_alias_menu(manager: AliasManager):
    """Menu pour supprimer un alias."""
    aliases = manager.list_aliases()
    
    if not aliases:
        print("\nAucun alias configuré.")
        input("\nAppuyez sur Entrée...")
        return
    
    print("\n--- SUPPRIMER UN ALIAS ---")
    for i, alias in enumerate(aliases, 1):
        print(f"  {i}. {alias}")
    
    choice = input("\nNuméro ou nom de l'alias: ").strip()
    
    try:
        if choice.isdigit():
            alias = aliases[int(choice) - 1]
        else:
            alias = choice
        
        if alias not in aliases:
            print("[!] Alias non trouvé.")
            input("\nAppuyez sur Entrée...")
            return
        
        print(f"\nSuppression de '{alias}'...")
        manager.remove_alias(alias)
        print(f"[OK] Alias '{alias}' supprimé!")
        
    except (ValueError, IndexError):
        print("[!] Choix invalide.")
    
    input("\nAppuyez sur Entrée...")


def _show_shells(manager: AliasManager):
    """Affiche les shells détectés."""
    print("\n--- SHELLS DÉTECTÉS ---")
    
    shells = manager.detect_shells()
    
    if not shells:
        print("Aucun shell détecté.")
    else:
        for shell in shells:
            exists = "✓" if shell["profile"].exists() else "○"
            print(f"  {exists} {shell['name']}")
            print(f"      Profile: {shell['profile']}")
    
    input("\nAppuyez sur Entrée...")


def _keyboard_shortcut_menu(manager: AliasManager):
    """Menu complet de gestion des raccourcis clavier."""
    while True:
        print("\n" + "=" * 55)
        print("        RACCOURCIS CLAVIER")
        print("=" * 55)
        
        current_hotkey = manager.get_current_hotkey()
        print(f"\n  Raccourci actuel: {current_hotkey if current_hotkey else 'Aucun'}")
        
        # Vérifier les types de raccourcis configurés
        shortcuts = manager.config.get("shortcuts", [])
        has_lnk = any(s.get("type") == "windows_shortcut" for s in shortcuts)
        has_ahk = any(s.get("type") == "autohotkey" for s in shortcuts)
        
        if manager.system == "Windows":
            print("\n  Types de raccourcis:")
            if has_lnk:
                print("    • Raccourci Windows (.lnk) ✓")
            if has_ahk:
                print("    • AutoHotkey (.ahk) ✓")
        
        print("\n" + "-" * 55)
        print("\n  1. Créer/Modifier le raccourci")
        print("  2. Supprimer le raccourci")
        
        if manager.system == "Windows":
            print("\n  --- Options avancées (Windows) ---")
            print("  3. Rafraîchir le raccourci Windows")
            print("     (Essayer de réparer si le hotkey ne marche pas)")
            print("  4. Créer raccourci AutoHotkey (plus fiable)")
            if has_ahk:
                print("  5. Lancer le script AutoHotkey")
        
        print("\n  R. Retour")
        
        choice = input("\n>> Choix: ").strip().lower()
        
        if choice == "1":
            _create_or_modify_shortcut(manager)
        elif choice == "2":
            _remove_shortcut(manager)
        elif choice == "3" and manager.system == "Windows":
            _refresh_shortcut(manager)
        elif choice == "4" and manager.system == "Windows":
            _create_ahk_shortcut(manager)
        elif choice == "5" and manager.system == "Windows" and has_ahk:
            _launch_ahk(manager)
        elif choice == "r":
            break


def _create_or_modify_shortcut(manager: AliasManager):
    """Créer ou modifier un raccourci clavier."""
    current = manager.get_current_hotkey()
    
    print("\n--- CRÉER/MODIFIER UN RACCOURCI CLAVIER ---")
    
    if current:
        print(f"\nRaccourci actuel: {current}")
        print("(Laissez vide pour garder, ou entrez un nouveau)")
    
    if manager.system == "Windows":
        print("\nFormat: Ctrl+Alt+S, Ctrl+Shift+M, etc.")
    else:
        print("\nFormat: Ctrl+Alt+S, Super+S, etc.")
    
    print("\nExemples suggérés:")
    print("  • Ctrl+Alt+S  (Scripts)")
    print("  • Ctrl+Alt+M  (Manager)")
    print("  • Ctrl+Shift+S")
    print("  • Win+S (ou Super+S)")
    
    hotkey = input("\nNouveau raccourci: ").strip()
    
    if not hotkey and current:
        print("\nRaccourci inchangé.")
        input("\nAppuyez sur Entrée...")
        return
    
    if hotkey and not any(mod in hotkey for mod in ["Ctrl", "Alt", "Shift", "Super", "Win"]):
        print("[!] Le raccourci doit contenir un modificateur (Ctrl, Alt, Shift, Win)")
        input("\nAppuyez sur Entrée...")
        return
    
    # Normaliser Win -> désambiguïser pour le format
    hotkey = hotkey.replace("Win+", "Ctrl+Alt+").replace("Win", "")  # Simplification
    
    print("\nMise à jour du raccourci...")
    
    if current:
        # Mettre à jour
        if manager.update_keyboard_shortcut(hotkey if hotkey else None):
            print("[OK] Raccourci mis à jour!")
            if hotkey:
                print(f"     Nouveau raccourci: {hotkey}")
        else:
            print("[!] Échec de la mise à jour.")
    else:
        # Créer
        if manager.create_keyboard_shortcut(hotkey if hotkey else None):
            print("[OK] Raccourci créé!")
            if hotkey:
                print(f"     Utilisez {hotkey} pour lancer le gestionnaire.")
            if manager.system == "Windows":
                print("     Le raccourci apparaît dans le menu Démarrer.")
                print("\n⚠️  Note: Si le raccourci ne fonctionne pas,")
                print("     utilisez l'option AutoHotkey (plus fiable).")
        else:
            print("[!] Échec de la création du raccourci.")
    
    input("\nAppuyez sur Entrée...")


def _remove_shortcut(manager: AliasManager):
    """Supprimer le raccourci clavier."""
    print("\n--- SUPPRIMER LE RACCOURCI ---")
    
    current = manager.get_current_hotkey()
    if not current:
        print("\nAucun raccourci configuré.")
        input("\nAppuyez sur Entrée...")
        return
    
    print(f"\nRaccourci actuel: {current}")
    confirm = input("Supprimer ce raccourci? (o/n): ").strip().lower()
    
    if confirm == 'o':
        if manager.remove_keyboard_shortcut():
            print("\n[OK] Raccourci supprimé!")
        else:
            print("\n[!] Échec de la suppression.")
    else:
        print("\nAnnulé.")
    
    input("\nAppuyez sur Entrée...")


def _refresh_shortcut(manager: AliasManager):
    """Rafraîchir le raccourci Windows."""
    print("\n--- RAFRAÎCHIR LE RACCOURCI ---")
    print("\nCette opération va:")
    print("  1. Supprimer le raccourci existant")
    print("  2. Le recréer avec les mêmes paramètres")
    print("  3. Notifier Windows pour rafraîchir le cache")
    
    confirm = input("\nContinuer? (o/n): ").strip().lower()
    
    if confirm == 'o':
        print("\nRafraîchissement...")
        if manager.refresh_windows_shortcut():
            print("\n[OK] Raccourci rafraîchi!")
            print("\n⚠️  Si ça ne fonctionne toujours pas:")
            print("    1. Déconnectez-vous et reconnectez-vous")
            print("    2. Ou utilisez l'option AutoHotkey (100% fiable)")
        else:
            print("\n[!] Échec du rafraîchissement.")
    else:
        print("\nAnnulé.")
    
    input("\nAppuyez sur Entrée...")


def _create_ahk_shortcut(manager: AliasManager):
    """Créer un raccourci AutoHotkey."""
    print("\n--- RACCOURCI AUTOHOTKEY ---")
    print("\nAutoHotkey est une alternative plus fiable aux raccourcis")
    print("Windows car il surveille activement les touches.")
    
    # Vérifier si AHK est installé
    if not manager.is_autohotkey_installed():
        print("\n⚠️  AutoHotkey n'est pas détecté sur votre système.")
        print("    Téléchargez-le sur: https://www.autohotkey.com/")
        print("\n    Le script sera créé quand même, vous pourrez")
        print("    l'exécuter après avoir installé AutoHotkey.")
    
    current = manager.get_current_hotkey()
    default = current if current else "Ctrl+Alt+S"
    
    print(f"\nRaccourci par défaut: {default}")
    hotkey = input(f"Raccourci (Entrée pour {default}): ").strip()
    
    if not hotkey:
        hotkey = default
    
    if not any(mod in hotkey for mod in ["Ctrl", "Alt", "Shift", "Win", "Super"]):
        print("[!] Le raccourci doit contenir un modificateur")
        input("\nAppuyez sur Entrée...")
        return
    
    print("\nCréation du script AutoHotkey...")
    
    if manager.create_autohotkey_shortcut(hotkey):
        ahk_file = manager.app_path / "data" / "script_manager_hotkey.ahk"
        print("\n[OK] Script AutoHotkey créé!")
        print(f"     Fichier: {ahk_file}")
        print(f"     Raccourci: {hotkey}")
        
        print("\n  Pour activer le raccourci:")
        print("    1. Installez AutoHotkey v2 si pas déjà fait")
        print("    2. Double-cliquez sur le fichier .ahk")
        print("    3. Ou utilisez l'option 'Lancer le script AHK'")
        
        # Proposer de le lancer maintenant
        if manager.is_autohotkey_installed():
            launch = input("\nLancer le script maintenant? (o/n): ").strip().lower()
            if launch == 'o':
                if manager.start_autohotkey():
                    print("\n[OK] Script lancé! Le raccourci est actif.")
                else:
                    print("\n[!] Échec du lancement.")
    else:
        print("\n[!] Échec de la création.")
    
    input("\nAppuyez sur Entrée...")


def _launch_ahk(manager: AliasManager):
    """Lancer le script AutoHotkey."""
    print("\n--- LANCER AUTOHOTKEY ---")
    
    if manager.start_autohotkey():
        print("\n[OK] Script AutoHotkey lancé!")
        print("     Le raccourci clavier est maintenant actif.")
        print("\n     Pour l'arrêter: clic droit sur l'icône AHK")
        print("     dans la barre des tâches > Exit")
    else:
        print("\n[!] Échec du lancement.")
        print("     Vérifiez qu'AutoHotkey est installé.")
    
    input("\nAppuyez sur Entrée...")


def _create_shortcut_menu(manager: AliasManager):
    """Menu pour créer un raccourci clavier."""
    print("\n--- CRÉER UN RACCOURCI CLAVIER ---")
    
    if manager.system == "Windows":
        print("Format Windows: Ctrl+Alt+S, Ctrl+Shift+M, etc.")
    else:
        print("Format Linux: Ctrl+Alt+S, Super+S, etc.")
    
    print("\nExemples suggérés:")
    print("  • Ctrl+Alt+S  (Scripts)")
    print("  • Ctrl+Alt+M  (Manager)")
    print("  • Ctrl+Shift+S")
    
    hotkey = input("\nRaccourci (ou Entrée pour aucun): ").strip()
    
    if hotkey and not any(mod in hotkey for mod in ["Ctrl", "Alt", "Shift", "Super"]):
        print("[!] Le raccourci doit contenir un modificateur (Ctrl, Alt, Shift)")
        input("\nAppuyez sur Entrée...")
        return
    
    print("\nCréation du raccourci...")
    
    if manager.create_keyboard_shortcut(hotkey if hotkey else None):
        print("[OK] Raccourci créé!")
        if hotkey:
            print(f"     Utilisez {hotkey} pour lancer le gestionnaire.")
        if manager.system == "Windows":
            print("     Le raccourci apparaît dans le menu Démarrer.")
    else:
        print("[!] Échec de la création du raccourci.")
    
    input("\nAppuyez sur Entrée...")


def _setup_autorun_menu(manager: AliasManager):
    """Menu pour configurer l'auto-run."""
    print("\n--- CONFIGURER L'AUTO-RUN ---")
    print("\nQuand voulez-vous lancer le gestionnaire automatiquement?")
    print()
    print("  1. Au démarrage du système (Recommandé)")
    print("     → Le gestionnaire s'ouvre quand Windows/Linux démarre")
    print()
    print("  2. À l'ouverture d'un terminal")
    print("     → Le gestionnaire s'ouvre à chaque nouveau terminal")
    print()
    print("  3. Au login utilisateur")
    print("     → Le gestionnaire s'ouvre après la connexion")
    print()
    print("  R. Retour")
    
    choice = input("\n>> Choix: ").strip().lower()
    
    methods = {
        "1": "startup",
        "2": "shell_profile", 
        "3": "login"
    }
    
    if choice in methods:
        method = methods[choice]
        print(f"\nConfiguration de l'auto-run ({method})...")
        
        if manager.setup_autorun(method):
            print("[OK] Auto-run configuré!")
            print("     Le gestionnaire démarrera automatiquement.")
        else:
            print("[!] Échec de la configuration.")
        
        input("\nAppuyez sur Entrée...")


def _quick_setup(manager: AliasManager):
    """Installation rapide avec les paramètres par défaut."""
    print("\n" + "=" * 55)
    print("        INSTALLATION RAPIDE")
    print("=" * 55)
    
    print("\nCette option va:")
    print(f"  1. Créer l'alias '{manager.DEFAULT_ALIAS}' dans tous vos shells")
    print("  2. Créer un raccourci dans le menu (Ctrl+Alt+S)")
    print("  3. Configurer l'auto-run au démarrage (optionnel)")
    
    confirm = input("\nContinuer? (o/n): ").strip().lower()
    if confirm != 'o':
        print("Annulé.")
        input("\nAppuyez sur Entrée...")
        return
    
    print("\n>>> Création de l'alias...")
    results = manager.add_alias(manager.DEFAULT_ALIAS)
    for shell, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {shell}")
    
    print("\n>>> Création du raccourci clavier...")
    if manager.create_keyboard_shortcut("Ctrl+Alt+S"):
        print("  ✓ Raccourci Ctrl+Alt+S créé")
    else:
        print("  ✗ Échec raccourci")
    
    autorun = input("\n>>> Activer l'auto-run au démarrage? (o/n): ").strip().lower()
    if autorun == 'o':
        if manager.setup_autorun("startup"):
            print("  ✓ Auto-run configuré")
        else:
            print("  ✗ Échec auto-run")
    
    print("\n" + "=" * 55)
    print("        INSTALLATION TERMINÉE!")
    print("=" * 55)
    print(f"\n  • Tapez '{manager.DEFAULT_ALIAS}' dans un terminal")
    print("  • Ou utilisez Ctrl+Alt+S")
    print("\n  (Redémarrez votre terminal pour appliquer)")
    
    input("\nAppuyez sur Entrée...")


if __name__ == "__main__":
    # Test standalone
    print("Test du gestionnaire d'alias")
    manager = AliasManager(os.getcwd())
    
    print("\nShells détectés:")
    for shell in manager.detect_shells():
        print(f"  - {shell['name']}: {shell['profile']}")
