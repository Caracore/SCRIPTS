#!/usr/bin/env python3
# install.py
"""
Script d'installation du Gestionnaire de Scripts.
Fonctionne sur Windows et Linux.
"""
import os
import sys
import shutil
import platform
import subprocess
from pathlib import Path


class Installer:
    """Installateur cross-platform."""
    
    APP_NAME = "script-manager"
    DISPLAY_NAME = "Gestionnaire de Scripts"
    
    def __init__(self):
        self.system = platform.system()
        self.is_windows = self.system == "Windows"
        self.is_linux = self.system == "Linux"
        self.is_mac = self.system == "Darwin"
        
        self.source_dir = Path(__file__).parent.absolute()
        self.install_dir = self._get_install_dir()
        self.bin_dir = self._get_bin_dir()
    
    def _get_install_dir(self) -> Path:
        """Retourne le répertoire d'installation."""
        if self.is_windows:
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            return base / self.APP_NAME
        else:
            return Path.home() / ".local" / "share" / self.APP_NAME
    
    def _get_bin_dir(self) -> Path:
        """Retourne le répertoire des binaires/scripts."""
        if self.is_windows:
            return self.install_dir / "bin"
        else:
            return Path.home() / ".local" / "bin"
    
    def print_banner(self):
        """Affiche la bannière d'installation."""
        print(r"""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     _____ _____ ______ ___________ _____                 ║
║    /  ___/  __ \| ___ \_   _| ___ \_   _|                ║
║    \ `--.| /  \/| |_/ / | | | |_/ / | |                  ║
║     `--. \ |    |    /  | | |  __/  | |                  ║
║    /\__/ / \__/\| |\ \ _| |_| |     | |                  ║
║    \____/ \____/\_| \_|\___/\_|     \_/                  ║
║                                                          ║
║              INSTALLATION / DÉSINSTALLATION              ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
        """)
        print(f"  Système détecté: {self.system}")
        print(f"  Répertoire source: {self.source_dir}")
        print(f"  Répertoire cible: {self.install_dir}")
        print()
    
    def check_python(self) -> bool:
        """Vérifie la version de Python."""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 10):
            print(f"[ERREUR] Python 3.10+ requis (actuel: {version.major}.{version.minor})")
            return False
        print(f"[OK] Python {version.major}.{version.minor}.{version.micro}")
        return True
    
    def install(self):
        """Lance l'installation."""
        self.print_banner()
        
        if not self.check_python():
            return False
        
        print("\n[1] Installation complète (copie des fichiers)")
        print("[2] Installation portable (lien symbolique)")
        print("[3] Créer uniquement le raccourci/alias")
        print("[Q] Quitter")
        
        choice = input("\nChoix: ").strip().lower()
        
        if choice == "1":
            return self._full_install()
        elif choice == "2":
            return self._portable_install()
        elif choice == "3":
            return self._create_shortcut_only()
        else:
            print("Installation annulée.")
            return False
    
    def _full_install(self) -> bool:
        """Installation complète avec copie des fichiers."""
        print(f"\n>>> Installation dans {self.install_dir}...")
        
        # Créer le répertoire d'installation
        self.install_dir.mkdir(parents=True, exist_ok=True)
        
        # Fichiers à copier
        files_to_copy = [
            "main.py", "program.py", "script.py", "launcher.py"
        ]
        dirs_to_copy = ["plugins", "data"]
        
        # Copier les fichiers
        for f in files_to_copy:
            src = self.source_dir / f
            if src.exists():
                shutil.copy2(src, self.install_dir / f)
                print(f"  [+] {f}")
        
        # Copier les dossiers
        for d in dirs_to_copy:
            src = self.source_dir / d
            dst = self.install_dir / d
            if src.exists():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                print(f"  [+] {d}/")
        
        # Créer le script de lancement
        self._create_launcher_script()
        
        # Ajouter au PATH
        self._add_to_path()
        
        print(f"\n[OK] Installation terminée!")
        print(f"     Lancez avec: {self.APP_NAME}")
        return True
    
    def _portable_install(self) -> bool:
        """Installation portable avec lien symbolique."""
        print(f"\n>>> Installation portable...")
        
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        
        # Créer le script de lancement pointant vers la source
        self._create_launcher_script(portable=True)
        
        # Ajouter au PATH
        self._add_to_path()
        
        print(f"\n[OK] Installation portable terminée!")
        print(f"     Les fichiers restent dans: {self.source_dir}")
        print(f"     Lancez avec: {self.APP_NAME}")
        return True
    
    def _create_shortcut_only(self) -> bool:
        """Crée uniquement le raccourci."""
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        self._create_launcher_script(portable=True)
        self._add_to_path()
        print(f"\n[OK] Raccourci créé!")
        return True
    
    def _create_launcher_script(self, portable=False):
        """Crée le script de lancement."""
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        
        target_dir = self.source_dir if portable else self.install_dir
        
        if self.is_windows:
            # Script batch pour Windows
            bat_path = self.bin_dir / f"{self.APP_NAME}.bat"
            bat_content = f'''@echo off
cd /d "{target_dir}"
python main.py %*
'''
            bat_path.write_text(bat_content)
            print(f"  [+] {bat_path}")
            
            # Script PowerShell
            ps1_path = self.bin_dir / f"{self.APP_NAME}.ps1"
            ps1_content = f'''# {self.DISPLAY_NAME} Launcher
Set-Location "{target_dir}"
python main.py @args
'''
            ps1_path.write_text(ps1_content)
            print(f"  [+] {ps1_path}")
            
        else:
            # Script bash pour Linux/Mac
            sh_path = self.bin_dir / self.APP_NAME
            sh_content = f'''#!/bin/bash
# {self.DISPLAY_NAME} Launcher
cd "{target_dir}"
python3 main.py "$@"
'''
            sh_path.write_text(sh_content)
            sh_path.chmod(0o755)
            print(f"  [+] {sh_path}")
    
    def _add_to_path(self):
        """Ajoute le répertoire bin au PATH."""
        if self.is_windows:
            self._add_to_path_windows()
        else:
            self._add_to_path_unix()
    
    def _add_to_path_windows(self):
        """Ajoute au PATH Windows (utilisateur)."""
        import winreg
        
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Environment",
                0,
                winreg.KEY_ALL_ACCESS
            )
            
            try:
                current_path, _ = winreg.QueryValueEx(key, "Path")
            except WindowsError:
                current_path = ""
            
            bin_str = str(self.bin_dir)
            if bin_str not in current_path:
                new_path = f"{current_path};{bin_str}" if current_path else bin_str
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                print(f"  [+] Ajouté au PATH utilisateur")
                print("      Redémarrez votre terminal pour appliquer.")
            else:
                print(f"  [=] Déjà dans le PATH")
            
            winreg.CloseKey(key)
            
        except Exception as e:
            print(f"  [!] Impossible d'ajouter au PATH automatiquement: {e}")
            print(f"      Ajoutez manuellement: {self.bin_dir}")
    
    def _add_to_path_unix(self):
        """Ajoute au PATH Unix via .bashrc/.zshrc."""
        bin_str = str(self.bin_dir)
        
        # Vérifier si déjà dans PATH
        if bin_str in os.environ.get("PATH", ""):
            print(f"  [=] Déjà dans le PATH")
            return
        
        # Fichiers de configuration shell
        shell_configs = [
            Path.home() / ".bashrc",
            Path.home() / ".zshrc",
            Path.home() / ".profile"
        ]
        
        export_line = f'\nexport PATH="$PATH:{bin_str}"\n'
        
        for config in shell_configs:
            if config.exists():
                content = config.read_text()
                if bin_str not in content:
                    with open(config, "a") as f:
                        f.write(f"\n# {self.DISPLAY_NAME}")
                        f.write(export_line)
                    print(f"  [+] Ajouté à {config.name}")
                break
        else:
            print(f"  [!] Ajoutez manuellement au PATH: {bin_str}")
    
    def uninstall(self):
        """Désinstalle le gestionnaire."""
        self.print_banner()
        print(">>> Désinstallation...")
        
        confirm = input(f"Supprimer {self.install_dir}? (o/n): ").strip().lower()
        if confirm != 'o':
            print("Désinstallation annulée.")
            return False
        
        # Supprimer le répertoire d'installation
        if self.install_dir.exists() and self.install_dir != self.source_dir:
            shutil.rmtree(self.install_dir)
            print(f"  [-] {self.install_dir}")
        
        # Supprimer les scripts de lancement
        if self.is_windows:
            for ext in [".bat", ".ps1"]:
                script = self.bin_dir / f"{self.APP_NAME}{ext}"
                if script.exists():
                    script.unlink()
                    print(f"  [-] {script}")
        else:
            script = self.bin_dir / self.APP_NAME
            if script.exists():
                script.unlink()
                print(f"  [-] {script}")
        
        print("\n[OK] Désinstallation terminée!")
        print("     Note: Le PATH n'a pas été modifié.")
        return True


def main():
    installer = Installer()
    
    print("\n[I] Installer")
    print("[U] Désinstaller")
    print("[Q] Quitter")
    
    choice = input("\nAction: ").strip().lower()
    
    if choice == 'i':
        installer.install()
    elif choice == 'u':
        installer.uninstall()
    else:
        print("Au revoir!")


if __name__ == "__main__":
    main()
