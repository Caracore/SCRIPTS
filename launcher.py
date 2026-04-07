# launcher.py
"""
Module de lancement détaché - Permet d'ouvrir des éditeurs/programmes
sans bloquer le gestionnaire de scripts.
"""
import os
import sys
import subprocess
from typing import Optional, List
import platform


class DetachedLauncher:
    """Lance des processus détachés du terminal parent."""
    
    @staticmethod
    def launch(command: List[str], cwd: Optional[str] = None) -> Optional[int]:
        """
        Lance une commande de manière détachée.
        Le processus continue même si le terminal parent est fermé.
        
        Args:
            command: Liste des arguments de la commande
            cwd: Répertoire de travail (optionnel)
        
        Returns:
            PID du processus lancé, ou None en cas d'erreur
        """
        try:
            if platform.system() == "Windows":
                # Windows: utiliser CREATE_NEW_PROCESS_GROUP et DETACHED_PROCESS
                DETACHED_PROCESS = 0x00000008
                CREATE_NEW_PROCESS_GROUP = 0x00000200
                CREATE_NO_WINDOW = 0x08000000
                
                process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            else:
                # Unix: utiliser start_new_session et double fork
                process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    preexec_fn=os.setpgrp if hasattr(os, 'setpgrp') else None
                )
            
            return process.pid
            
        except Exception as e:
            print(f"[Launcher] Erreur: {e}")
            return None
    
    @staticmethod
    def open_file_detached(filepath: str, editor: Optional[str] = None) -> Optional[int]:
        """
        Ouvre un fichier dans un éditeur de manière détachée.
        
        Args:
            filepath: Chemin du fichier à ouvrir
            editor: Éditeur à utiliser (optionnel, utilise le défaut système sinon)
        
        Returns:
            PID du processus lancé
        """
        filepath = os.path.abspath(filepath)
        
        if editor:
            # Utiliser l'éditeur spécifié
            return DetachedLauncher.launch([editor, filepath])
        
        # Utiliser l'éditeur par défaut du système
        if platform.system() == "Windows":
            try:
                # os.startfile est déjà détaché sur Windows
                os.startfile(filepath)
                return 0  # Pas de PID disponible avec startfile
            except Exception as e:
                print(f"[Launcher] Erreur startfile: {e}")
                return None
        
        elif platform.system() == "Darwin":  # macOS
            return DetachedLauncher.launch(["open", filepath])
        
        else:  # Linux et autres
            return DetachedLauncher.launch(["xdg-open", filepath])
    
    @staticmethod
    def run_script_detached(
        script_path: str,
        interpreter: List[str],
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None
    ) -> Optional[int]:
        """
        Exécute un script de manière détachée.
        
        Args:
            script_path: Chemin du script
            interpreter: Commande de l'interpréteur (ex: ["python"])
            args: Arguments supplémentaires
            cwd: Répertoire de travail
        
        Returns:
            PID du processus lancé
        """
        script_path = os.path.abspath(script_path)
        command = interpreter + [script_path]
        if args:
            command.extend(args)
        
        return DetachedLauncher.launch(command, cwd=cwd)
    
    @staticmethod
    def open_terminal_with_script(
        script_path: str,
        interpreter: List[str],
        terminal: Optional[str] = None
    ) -> Optional[int]:
        """
        Ouvre un nouveau terminal et exécute le script dedans.
        Le terminal reste ouvert après l'exécution.
        
        Args:
            script_path: Chemin du script
            interpreter: Commande de l'interpréteur
            terminal: Terminal à utiliser (optionnel)
        
        Returns:
            PID du processus lancé
        """
        script_path = os.path.abspath(script_path)
        
        if platform.system() == "Windows":
            # Windows: utiliser cmd ou Windows Terminal
            if terminal and "wt" in terminal.lower():
                # Windows Terminal
                cmd = ["wt", "-d", os.path.dirname(script_path), 
                       "cmd", "/k"] + interpreter + [script_path]
            else:
                # CMD classique
                cmd_str = " ".join(interpreter + [f'"{script_path}"'])
                cmd = ["cmd", "/k", cmd_str]
            return DetachedLauncher.launch(cmd)
        
        elif platform.system() == "Darwin":  # macOS
            script_cmd = " ".join(interpreter + [f'"{script_path}"'])
            return DetachedLauncher.launch([
                "osascript", "-e",
                f'tell app "Terminal" to do script "{script_cmd}"'
            ])
        
        else:  # Linux
            script_cmd = " ".join(interpreter + [f'"{script_path}"'])
            terminals = terminal or os.environ.get("TERMINAL", "")
            
            if "gnome-terminal" in terminals:
                return DetachedLauncher.launch([
                    "gnome-terminal", "--", "bash", "-c", 
                    f'{script_cmd}; exec bash'
                ])
            elif "konsole" in terminals:
                return DetachedLauncher.launch([
                    "konsole", "-e", "bash", "-c",
                    f'{script_cmd}; exec bash'
                ])
            else:
                # Fallback: xterm
                return DetachedLauncher.launch([
                    "xterm", "-hold", "-e", script_cmd
                ])
    
    @staticmethod
    def open_folder_detached(folder_path: str) -> Optional[int]:
        """
        Ouvre un dossier dans l'explorateur de fichiers de manière détachée.
        """
        folder_path = os.path.abspath(folder_path)
        
        if platform.system() == "Windows":
            return DetachedLauncher.launch(["explorer", folder_path])
        elif platform.system() == "Darwin":
            return DetachedLauncher.launch(["open", folder_path])
        else:
            return DetachedLauncher.launch(["xdg-open", folder_path])

    @staticmethod
    def open_tui_editor(filepath: str, editor: str) -> Optional[int]:
        """
        Ouvre un fichier dans un éditeur TUI (terminal) dans une nouvelle fenêtre.
        
        Args:
            filepath: Chemin du fichier à ouvrir
            editor: Commande de l'éditeur TUI (nvim, vim, nano, etc.)
        
        Returns:
            PID du processus lancé
        """
        filepath = os.path.abspath(filepath)
        
        if platform.system() == "Windows":
            # Windows: ouvrir dans un nouveau cmd ou Windows Terminal
            # Essayer d'abord Windows Terminal, sinon cmd
            try:
                # Vérifier si Windows Terminal est disponible
                wt_check = subprocess.run(
                    ["where", "wt"], 
                    capture_output=True, 
                    text=True
                )
                if wt_check.returncode == 0:
                    # Windows Terminal disponible
                    return DetachedLauncher.launch([
                        "wt", "-d", os.path.dirname(filepath),
                        editor, filepath
                    ])
            except Exception:
                pass
            
            # Fallback: cmd classique
            return DetachedLauncher.launch([
                "cmd", "/c", "start", "cmd", "/k", editor, filepath
            ])
        
        elif platform.system() == "Darwin":  # macOS
            # Ouvrir dans Terminal.app
            cmd_str = f'{editor} "{filepath}"'
            return DetachedLauncher.launch([
                "osascript", "-e",
                f'tell app "Terminal" to do script "{cmd_str}"'
            ])
        
        else:  # Linux
            # Essayer différents terminaux
            terminals = [
                ("gnome-terminal", ["gnome-terminal", "--", editor, filepath]),
                ("konsole", ["konsole", "-e", editor, filepath]),
                ("xfce4-terminal", ["xfce4-terminal", "-e", f"{editor} {filepath}"]),
                ("xterm", ["xterm", "-e", editor, filepath]),
            ]
            
            for term_name, term_cmd in terminals:
                try:
                    check = subprocess.run(
                        ["which", term_name],
                        capture_output=True
                    )
                    if check.returncode == 0:
                        return DetachedLauncher.launch(term_cmd)
                except Exception:
                    continue
            
            # Fallback ultime
            return DetachedLauncher.launch(["xterm", "-e", editor, filepath])


# Alias pour rétrocompatibilité
def detached_open(filepath: str, editor: Optional[str] = None) -> Optional[int]:
    """Ouvre un fichier de manière détachée."""
    return DetachedLauncher.open_file_detached(filepath, editor)


def detached_run(
    script_path: str,
    interpreter: List[str],
    args: Optional[List[str]] = None
) -> Optional[int]:
    """Exécute un script de manière détachée."""
    return DetachedLauncher.run_script_detached(script_path, interpreter, args)
