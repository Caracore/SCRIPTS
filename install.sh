#!/bin/bash
# install.sh - Installation rapide pour Linux/macOS

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="script-manager"
INSTALL_DIR="$HOME/.local/share/$APP_NAME"
BIN_DIR="$HOME/.local/bin"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          GESTIONNAIRE DE SCRIPTS - INSTALLATION          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Répertoire source: $SCRIPT_DIR"
echo "Répertoire cible:  $INSTALL_DIR"
echo ""

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERREUR] Python 3 n'est pas installé.${NC}"
    echo ""
    echo "Installez Python avec:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  Fedora:        sudo dnf install python3 python3-pip"
    echo "  Arch:          sudo pacman -S python python-pip"
    echo "  macOS:         brew install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}[OK]${NC} Python $PYTHON_VERSION détecté"

# Vérifier pip
if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
    echo -e "${YELLOW}[!]${NC} pip n'est pas installé."
    echo "    Installez-le avec: python3 -m ensurepip --upgrade"
fi

echo ""
echo "[1] Installation complète (avec dépendances)"
echo "[2] Installation portable (avec dépendances)"
echo "[3] Installer uniquement les dépendances"
echo "[4] Désinstaller"
echo "[Q] Quitter"
echo ""
read -p "Choix: " CHOICE

# Fonction d'installation des dépendances
install_deps() {
    echo ""
    echo ">>> Installation des dépendances Python..."
    echo ""
    
    # Déterminer la commande pip
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
    else
        PIP_CMD="python3 -m pip"
    fi
    
    # Mettre à jour pip
    echo "  [*] Mise à jour de pip..."
    $PIP_CMD install --upgrade pip --quiet 2>/dev/null || true
    
    # Dépendances requises
    echo "  [*] Installation de plyer (notifications)..."
    if $PIP_CMD install plyer --quiet 2>/dev/null; then
        echo -e "  ${GREEN}[+]${NC} plyer installé"
    else
        echo -e "  ${YELLOW}[!]${NC} Erreur lors de l'installation de plyer"
    fi
    
    # Dépendances optionnelles
    echo "  [*] Installation de colorama (couleurs terminal)..."
    $PIP_CMD install colorama --quiet 2>/dev/null && echo -e "  ${GREEN}[+]${NC} colorama installé" || true
    
    echo "  [*] Installation de psutil (monitoring système)..."
    $PIP_CMD install psutil --quiet 2>/dev/null && echo -e "  ${GREEN}[+]${NC} psutil installé" || true
    
    echo "  [*] Installation de requests (requêtes HTTP)..."
    $PIP_CMD install requests --quiet 2>/dev/null && echo -e "  ${GREEN}[+]${NC} requests installé" || true
    
    # Dépendances système pour les notifications (Linux)
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo ""
        echo "  [*] Vérification des dépendances système..."
        
        if ! command -v notify-send &> /dev/null; then
            echo -e "  ${YELLOW}[!]${NC} notify-send non trouvé (notifications bureau)"
            echo "      Installez avec: sudo apt install libnotify-bin"
        else
            echo -e "  ${GREEN}[+]${NC} notify-send disponible"
        fi
    fi
    
    echo ""
    echo -e "${GREEN}[OK]${NC} Dépendances installées!"
}

case $CHOICE in
    1)
        install_deps
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
        cp -r "$SCRIPT_DIR/navigation.py" "$INSTALL_DIR/"
        cp -r "$SCRIPT_DIR/themes.py" "$INSTALL_DIR/"
        cp -r "$SCRIPT_DIR/alias_manager.py" "$INSTALL_DIR/"
        cp -r "$SCRIPT_DIR/plugins" "$INSTALL_DIR/"
        cp -r "$SCRIPT_DIR/data" "$INSTALL_DIR/"
        
        echo -e "  ${GREEN}[+]${NC} Fichiers copiés"
        
        # Créer le script de lancement
        cat > "$BIN_DIR/$APP_NAME" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
python3 main.py "\$@"
EOF
        chmod +x "$BIN_DIR/$APP_NAME"
        echo -e "  ${GREEN}[+]${NC} Script de lancement créé"
        
        TARGET_DIR="$INSTALL_DIR"
        ;;
    
    2)
        install_deps
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
        echo -e "  ${GREEN}[+]${NC} Script de lancement créé"
        
        TARGET_DIR="$SCRIPT_DIR"
        ;;
    
    3)
        install_deps
        echo ""
        echo -e "${GREEN}[OK]${NC} Dépendances installées!"
        echo ""
        echo "Vous pouvez maintenant lancer le gestionnaire avec:"
        echo "  cd $SCRIPT_DIR && python3 main.py"
        exit 0
        ;;
    
    4)
        echo ""
        echo ">>> Désinstallation..."
        
        if [ -d "$INSTALL_DIR" ]; then
            rm -rf "$INSTALL_DIR"
            echo -e "  ${RED}[-]${NC} $INSTALL_DIR supprimé"
        fi
        
        if [ -f "$BIN_DIR/$APP_NAME" ]; then
            rm "$BIN_DIR/$APP_NAME"
            echo -e "  ${RED}[-]${NC} $BIN_DIR/$APP_NAME supprimé"
        fi
        
        echo ""
        echo -e "${GREEN}[OK]${NC} Désinstallation terminée!"
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
    echo -e "${YELLOW}[!]${NC} $BIN_DIR n'est pas dans votre PATH."
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
            echo -e "  ${GREEN}[+]${NC} Ajouté à ~/.zshrc"
        elif [ -f "$HOME/.bashrc" ]; then
            echo "" >> "$HOME/.bashrc"
            echo "# Gestionnaire de Scripts" >> "$HOME/.bashrc"
            echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$HOME/.bashrc"
            echo -e "  ${GREEN}[+]${NC} Ajouté à ~/.bashrc"
        fi
    fi
fi

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              INSTALLATION TERMINÉE!                      ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Lancez le gestionnaire avec: $APP_NAME"
echo "  Répertoire: $TARGET_DIR"
echo ""
echo "  (Redémarrez votre terminal si la commande n'est pas reconnue)"
echo ""
