# main.py
import os
from program import Program #as p

if __name__ == "__main__":
    # Initialisation du programme
    program = Program(
        name="Gestionnaire de Scripts",
        current_path=os.getcwd(),
        target="Scripts Python"
    )
    program.menu()

