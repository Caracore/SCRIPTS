# main.py
import os
import sys
import time
from pathlib import Path

def check_autostart_lock(current_path: str) -> bool:
    """
    Vérifie si le gestionnaire est déjà lancé (protection anti-boucle).
    Retourne True si OK de continuer, False si doit s'arrêter.
    """
    lock_file = Path(current_path) / "data" / ".manager_lock"
    lock_timeout = 30  # Secondes avant expiration du lock
    
    try:
        if lock_file.exists():
            # Lire le timestamp du lock
            with open(lock_file, "r") as f:
                data = f.read().strip().split("|")
                if len(data) >= 2:
                    lock_time = float(data[0])
                    lock_pid = int(data[1])
                    
                    # Vérifier si le lock est récent
                    if time.time() - lock_time < lock_timeout:
                        # Vérifier si le process existe encore
                        try:
                            if os.name == 'nt':
                                import ctypes
                                kernel32 = ctypes.windll.kernel32
                                handle = kernel32.OpenProcess(0x1000, False, lock_pid)
                                if handle:
                                    kernel32.CloseHandle(handle)
                                    # Process existe, c'est une boucle!
                                    return False
                            else:
                                os.kill(lock_pid, 0)  # Vérifie si le process existe
                                return False
                        except (OSError, PermissionError):
                            pass  # Process n'existe plus, lock obsolète
        
        # Créer/mettre à jour le lock
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_file, "w") as f:
            f.write(f"{time.time()}|{os.getpid()}")
        
        return True
        
    except Exception as e:
        print(f"[Warning] Lock check failed: {e}")
        return True  # En cas d'erreur, on continue


def release_lock(current_path: str):
    """Libère le fichier lock à la fermeture."""
    lock_file = Path(current_path) / "data" / ".manager_lock"
    try:
        if lock_file.exists():
            lock_file.unlink()
    except:
        pass


def main():
    from program import Program
    
    current_path = os.getcwd()
    
    # Vérifier si lancé en mode autostart
    is_autostart = "--autostart" in sys.argv or "-a" in sys.argv
    
    if is_autostart:
        print("\n🚀 Démarrage automatique du Gestionnaire de Scripts...")
        
        # Protection anti-boucle stricte pour autostart
        if not check_autostart_lock(current_path):
            print("\n" + "=" * 55)
            print("⚠️  PROTECTION ANTI-BOUCLE ACTIVÉE")
            print("=" * 55)
            print("\nLe gestionnaire est déjà en cours d'exécution.")
            print("Fermeture automatique pour éviter une boucle infinie.")
            print("\nSi ce n'est pas normal, supprimez le fichier:")
            print(f"  {Path(current_path) / 'data' / '.manager_lock'}")
            time.sleep(3)
            sys.exit(0)
        
        print("✓ Vérification anti-boucle OK\n")
    
    try:
        # Initialisation du programme
        program = Program(
            name="Gestionnaire de Scripts",
            current_path=current_path,
            target="Scripts Python"
        )
        program.menu()
    finally:
        # Libérer le lock à la fermeture
        release_lock(current_path)


if __name__ == "__main__":
    main()

