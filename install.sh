#!/bin/bash
# install.sh - Installation rapide pour Linux/macOS

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="script-manager"
INSTALL_DIR="$HOME/.local/share/$APP_NAME"
BIN_DIR="$HOME/.local/bin"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          GESTIONNAIRE DE SCRIPTS - INSTALLATION          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Répertoire source: $SCRIPT_DIR"
echo "Répertoire cible:  $INSTALL_DIR"
echo ""

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "[ERREUR] Python 3 n'est pas installé."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "[OK] Python $PYTHON_VERSION détecté"

echo ""
echo "[1] Installation complète"
echo "[2] Installation portable (lien symbolique)"
echo "[3] Désinstaller"
echo "[Q] Quitter"
echo ""
read -p "Choix: " CHOICE

case $CHOICE in
    1)
        echo ""
        echo ">>> Installation complète..."
        
        # Créer les répertoires
        mkdir -p "$INSTALL_DIR"
        mkdir -p "$BIN_DIR"
        
        # Copier les fichiers
        cp -r "$SCRIPT_DIR/main.py" "$INSTALL_DIR/"
        cp -r "$SCRIPT_DIR/program.py" "$INSTALL_DIR/"
        cp -r "$SCRIPT_DIR/script.py" "$INSTALL_DIR/"
        cp -r "$SCRIPT_DIR/launcher.py" "$INSTALL_DIR/"
        cp -r "$SCRIPT_DIR/plugins" "$INSTALL_DIR/"
        cp -r "$SCRIPT_DIR/data" "$INSTALL_DIR/"
        
        echo "  [+] Fichiers copiés"
        
        # Créer le script de lancement
        cat > "$BIN_DIR/$APP_NAME" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
python3 main.py "\$@"
EOF
        chmod +x "$BIN_DIR/$APP_NAME"
        echo "  [+] Script de lancement créé"
        
        TARGET_DIR="$INSTALL_DIR"
        ;;
    
    2)
        echo ""
        echo ">>> Installation portable..."
        
        mkdir -p "$BIN_DIR"
        
        # Créer le script de lancement
        cat > "$BIN_DIR/$APP_NAME" << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
python3 main.py "\$@"
EOF
        chmod +x "$BIN_DIR/$APP_NAME"
        echo "  [+] Script de lancement créé"
        
        TARGET_DIR="$SCRIPT_DIR"
        ;;
    
    3)
        echo ""
        echo ">>> Désinstallation..."
        
        if [ -d "$INSTALL_DIR" ]; then
            rm -rf "$INSTALL_DIR"
            echo "  [-] $INSTALL_DIR supprimé"
        fi
        
        if [ -f "$BIN_DIR/$APP_NAME" ]; then
            rm "$BIN_DIR/$APP_NAME"
            echo "  [-] $BIN_DIR/$APP_NAME supprimé"
        fi
        
        echo ""
        echo "[OK] Désinstallation terminée!"
        exit 0
        ;;
    
    *)
        echo "Installation annulée."
        exit 0
        ;;
esac

# Vérifier si BIN_DIR est dans le PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "[!] $BIN_DIR n'est pas dans votre PATH."
    echo "    Ajoutez cette ligne à votre ~/.bashrc ou ~/.zshrc:"
    echo ""
    echo "    export PATH=\"\$PATH:$BIN_DIR\""
    echo ""
    
    read -p "Ajouter automatiquement? (o/n): " ADD_PATH
    if [ "$ADD_PATH" = "o" ]; then
        # Détecter le shell
        if [ -f "$HOME/.zshrc" ]; then
            echo "" >> "$HOME/.zshrc"
            echo "# Gestionnaire de Scripts" >> "$HOME/.zshrc"
            echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$HOME/.zshrc"
            echo "  [+] Ajouté à ~/.zshrc"
        elif [ -f "$HOME/.bashrc" ]; then
            echo "" >> "$HOME/.bashrc"
            echo "# Gestionnaire de Scripts" >> "$HOME/.bashrc"
            echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$HOME/.bashrc"
            echo "  [+] Ajouté à ~/.bashrc"
        fi
    fi
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              INSTALLATION TERMINÉE!                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Lancez le gestionnaire avec: $APP_NAME"
echo "  Répertoire: $TARGET_DIR"
echo ""
echo "  (Redémarrez votre terminal si la commande n'est pas reconnue)"
echo ""
