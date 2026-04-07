# navigation.py
"""
Système de navigation avancé pour le Gestionnaire de Scripts.
Supporte la navigation statique (input texte) et dynamique (flèches/vim).
Compatible Windows et Linux.
"""
import os
import sys
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Tuple
from enum import Enum, auto
from dataclasses import dataclass


# ============================================================
#                    GESTION DU TERMINAL
# ============================================================

class TerminalHandler:
    """Gestion cross-platform du terminal pour la saisie de touches."""
    
    def __init__(self):
        self._is_windows = os.name == 'nt'
        self._old_settings = None
    
    def setup_raw_mode(self) -> bool:
        """Active le mode raw pour capturer les touches individuellement."""
        try:
            if self._is_windows:
                # Windows n'a pas besoin de setup spécial pour msvcrt
                return True
            else:
                # Linux/Mac - désactiver le buffering
                import termios
                import tty
                fd = sys.stdin.fileno()
                self._old_settings = termios.tcgetattr(fd)
                tty.setraw(fd)
                return True
        except Exception:
            return False
    
    def restore_mode(self) -> None:
        """Restaure le mode normal du terminal."""
        try:
            if not self._is_windows and self._old_settings:
                import termios
                fd = sys.stdin.fileno()
                termios.tcsetattr(fd, termios.TCSADRAIN, self._old_settings)
        except Exception:
            pass
    
    def get_key(self) -> str:
        """
        Lit une touche du clavier.
        Retourne une chaîne représentant la touche.
        """
        try:
            if self._is_windows:
                import msvcrt
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    # Touches spéciales Windows (flèches, F1-F12, etc.)
                    if key in (b'\x00', b'\xe0'):
                        key2 = msvcrt.getch()
                        return self._decode_windows_special(key2)
                    return key.decode('utf-8', errors='ignore')
                return ''
            else:
                import select
                # Vérifier si une touche est disponible
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)
                    # Séquences d'échappement (flèches, etc.)
                    if key == '\x1b':
                        # Lire les caractères suivants
                        if select.select([sys.stdin], [], [], 0.05)[0]:
                            key += sys.stdin.read(1)
                            if key == '\x1b[' and select.select([sys.stdin], [], [], 0.05)[0]:
                                key += sys.stdin.read(1)
                        return self._decode_ansi_sequence(key)
                    return key
                return ''
        except Exception:
            return ''
    
    def _decode_windows_special(self, key: bytes) -> str:
        """Décode les touches spéciales Windows."""
        mapping = {
            b'H': 'UP',
            b'P': 'DOWN',
            b'K': 'LEFT',
            b'M': 'RIGHT',
            b'G': 'HOME',
            b'O': 'END',
            b'I': 'PAGEUP',
            b'Q': 'PAGEDOWN',
            b'S': 'DELETE',
            b'R': 'INSERT',
            b';': 'F1',
            b'<': 'F2',
            b'=': 'F3',
            b'>': 'F4',
            b'?': 'F5',
            b'@': 'F6',
            b'A': 'F7',
            b'B': 'F8',
            b'C': 'F9',
            b'D': 'F10',
        }
        return mapping.get(key, 'UNKNOWN')
    
    def _decode_ansi_sequence(self, seq: str) -> str:
        """Décode les séquences ANSI."""
        mapping = {
            '\x1b[A': 'UP',
            '\x1b[B': 'DOWN',
            '\x1b[C': 'RIGHT',
            '\x1b[D': 'LEFT',
            '\x1b[H': 'HOME',
            '\x1b[F': 'END',
            '\x1b[5~': 'PAGEUP',
            '\x1b[6~': 'PAGEDOWN',
            '\x1b[3~': 'DELETE',
            '\x1b[2~': 'INSERT',
            '\x1bOP': 'F1',
            '\x1bOQ': 'F2',
            '\x1bOR': 'F3',
            '\x1bOS': 'F4',
            '\x1b[15~': 'F5',
            '\x1b[17~': 'F6',
            '\x1b[18~': 'F7',
            '\x1b[19~': 'F8',
            '\x1b[20~': 'F9',
            '\x1b[21~': 'F10',
        }
        return mapping.get(seq, seq)
    
    def kbhit(self) -> bool:
        """Vérifie si une touche a été pressée."""
        try:
            if self._is_windows:
                import msvcrt
                return msvcrt.kbhit()
            else:
                import select
                return bool(select.select([sys.stdin], [], [], 0)[0])
        except Exception:
            return False


# ============================================================
#                    STYLES DE CURSEUR
# ============================================================

class CursorStyle(Enum):
    """Styles de curseur disponibles."""
    BLOCK = "block"
    UNDERLINE = "underline"
    BAR = "bar"
    BLOCK_BLINK = "block_blink"
    UNDERLINE_BLINK = "underline_blink"
    BAR_BLINK = "bar_blink"


@dataclass
class CursorTheme:
    """Thème de curseur personnalisable."""
    name: str
    style: CursorStyle
    color: str  # Code couleur ANSI ou nom
    selected_bg: str  # Couleur de fond pour l'élément sélectionné
    selected_fg: str  # Couleur de texte pour l'élément sélectionné
    indicator: str  # Caractère indicateur (▶, >, →, etc.)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "style": self.style.value,
            "color": self.color,
            "selected_bg": self.selected_bg,
            "selected_fg": self.selected_fg,
            "indicator": self.indicator
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CursorTheme':
        return cls(
            name=data.get("name", "default"),
            style=CursorStyle(data.get("style", "block")),
            color=data.get("color", "cyan"),
            selected_bg=data.get("selected_bg", "blue"),
            selected_fg=data.get("selected_fg", "white"),
            indicator=data.get("indicator", "▶")
        )


# Thèmes de curseur prédéfinis
CURSOR_THEMES = {
    "default": CursorTheme(
        name="default",
        style=CursorStyle.BLOCK,
        color="cyan",
        selected_bg="44",  # Bleu
        selected_fg="97",  # Blanc brillant
        indicator="▶"
    ),
    "minimal": CursorTheme(
        name="minimal",
        style=CursorStyle.UNDERLINE,
        color="white",
        selected_bg="0",
        selected_fg="96",  # Cyan brillant
        indicator=">"
    ),
    "neon": CursorTheme(
        name="neon",
        style=CursorStyle.BAR_BLINK,
        color="magenta",
        selected_bg="45",  # Magenta
        selected_fg="97",
        indicator="→"
    ),
    "retro": CursorTheme(
        name="retro",
        style=CursorStyle.BLOCK_BLINK,
        color="green",
        selected_bg="42",  # Vert
        selected_fg="30",  # Noir
        indicator="█"
    ),
    "ocean": CursorTheme(
        name="ocean",
        style=CursorStyle.UNDERLINE_BLINK,
        color="blue",
        selected_bg="46",  # Cyan
        selected_fg="30",
        indicator="◆"
    ),
    "fire": CursorTheme(
        name="fire",
        style=CursorStyle.BLOCK,
        color="red",
        selected_bg="41",  # Rouge
        selected_fg="97",
        indicator="🔥"
    ),
    "vim": CursorTheme(
        name="vim",
        style=CursorStyle.BLOCK,
        color="yellow",
        selected_bg="43",  # Jaune
        selected_fg="30",
        indicator="•"
    ),
}


# ============================================================
#                    KEYMAPS
# ============================================================

class NavigationMode(Enum):
    """Modes de navigation."""
    STATIC = "static"      # Navigation classique par input texte
    DYNAMIC = "dynamic"    # Navigation par flèches/vim


@dataclass
class KeyBinding:
    """Association touche -> action."""
    key: str
    action: str
    description: str


# Keymaps prédéfinis
DEFAULT_KEYMAPS = {
    "default": {
        "name": "Default",
        "description": "Navigation avec flèches",
        "bindings": {
            "UP": "move_up",
            "DOWN": "move_down",
            "LEFT": "back",
            "RIGHT": "select",
            "\r": "select",       # Enter
            "\n": "select",       # Enter (Linux)
            " ": "select",        # Espace
            "q": "quit",
            "Q": "quit",
            "\x1b": "back",       # Escape
            "ESCAPE": "back",
            "PAGEUP": "page_up",
            "PAGEDOWN": "page_down",
            "HOME": "go_first",
            "END": "go_last",
            "/": "search",
            "?": "help",
            "r": "refresh",
            "R": "refresh",
        }
    },
    "vim": {
        "name": "Vim",
        "description": "Navigation style Vim (hjkl)",
        "bindings": {
            "k": "move_up",
            "j": "move_down",
            "h": "back",
            "l": "select",
            "UP": "move_up",
            "DOWN": "move_down",
            "LEFT": "back",
            "RIGHT": "select",
            "\r": "select",
            "\n": "select",
            " ": "select",
            "q": "quit",
            "Q": "quit",
            "\x1b": "back",
            "gg": "go_first",
            "G": "go_last",
            "/": "search",
            "?": "help",
            "r": "refresh",
            "u": "page_up",
            "d": "page_down",
        }
    },
    "arrows": {
        "name": "Arrows Only",
        "description": "Navigation uniquement avec flèches",
        "bindings": {
            "UP": "move_up",
            "DOWN": "move_down",
            "LEFT": "back",
            "RIGHT": "select",
            "\r": "select",
            "\n": "select",
            "ESCAPE": "quit",
            "\x1b": "quit",
            "PAGEUP": "page_up",
            "PAGEDOWN": "page_down",
            "HOME": "go_first",
            "END": "go_last",
        }
    },
    "wasd": {
        "name": "WASD",
        "description": "Navigation style jeu vidéo",
        "bindings": {
            "w": "move_up",
            "W": "move_up",
            "s": "move_down",
            "S": "move_down",
            "a": "back",
            "A": "back",
            "d": "select",
            "D": "select",
            "UP": "move_up",
            "DOWN": "move_down",
            "LEFT": "back",
            "RIGHT": "select",
            "\r": "select",
            "\n": "select",
            " ": "select",
            "q": "quit",
            "Q": "quit",
            "\x1b": "back",
        }
    },
}


# ============================================================
#                    MENU ITEM
# ============================================================

@dataclass
class MenuItem:
    """Élément de menu navigable."""
    key: str           # Touche raccourci (pour mode statique)
    label: str         # Texte affiché
    handler: Optional[Callable] = None  # Fonction à exécuter
    submenu: Optional[List['MenuItem']] = None  # Sous-menu
    enabled: bool = True
    description: str = ""
    
    def __post_init__(self):
        if self.submenu is None:
            self.submenu = []


# ============================================================
#                    NAVIGATION MANAGER
# ============================================================

class NavigationManager:
    """Gestionnaire de navigation avancé."""
    
    CONFIG_FILE = "navigation.json"
    
    # Codes ANSI pour les couleurs et styles
    ANSI = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "italic": "\033[3m",
        "underline": "\033[4m",
        "blink": "\033[5m",
        "reverse": "\033[7m",
        "hidden": "\033[8m",
        # Couleurs de texte
        "black": "\033[30m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        # Couleurs de fond
        "bg_black": "\033[40m",
        "bg_red": "\033[41m",
        "bg_green": "\033[42m",
        "bg_yellow": "\033[43m",
        "bg_blue": "\033[44m",
        "bg_magenta": "\033[45m",
        "bg_cyan": "\033[46m",
        "bg_white": "\033[47m",
        # Curseur
        "cursor_hide": "\033[?25l",
        "cursor_show": "\033[?25h",
        "cursor_block": "\033[2 q",
        "cursor_underline": "\033[4 q",
        "cursor_bar": "\033[6 q",
        "cursor_block_blink": "\033[1 q",
        "cursor_underline_blink": "\033[3 q",
        "cursor_bar_blink": "\033[5 q",
        # Effacement
        "clear_line": "\033[2K",
        "clear_screen": "\033[2J",
        "move_home": "\033[H",
    }
    
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.config_path = self.data_path / self.CONFIG_FILE
        self.terminal = TerminalHandler()
        
        # Configuration
        self.config = self._load_config()
        self.mode = NavigationMode(self.config.get("mode", "static"))
        self.current_keymap = self.config.get("keymap", "default")
        self.current_theme = self.config.get("theme", "default")
        
        # État
        self.selected_index = 0
        self.scroll_offset = 0
        self.visible_items = 10
        self.search_query = ""
        self.in_search_mode = False
    
    def _load_config(self) -> Dict[str, Any]:
        """Charge la configuration."""
        default = {
            "mode": "static",
            "keymap": "default",
            "theme": "default",
            "custom_keymaps": {},
            "custom_themes": {},
            "visible_items": 10,
            "show_shortcuts": True,
            "show_description": True,
            "animation_speed": 50,  # ms
        }
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return {**default, **json.load(f)}
        except (json.JSONDecodeError, IOError):
            pass
        return default
    
    def save_config(self) -> None:
        """Sauvegarde la configuration."""
        self.config["mode"] = self.mode.value
        self.config["keymap"] = self.current_keymap
        self.config["theme"] = self.current_theme
        
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except IOError:
            pass
    
    def get_theme(self) -> CursorTheme:
        """Retourne le thème actuel."""
        if self.current_theme in CURSOR_THEMES:
            return CURSOR_THEMES[self.current_theme]
        custom = self.config.get("custom_themes", {}).get(self.current_theme)
        if custom:
            return CursorTheme.from_dict(custom)
        return CURSOR_THEMES["default"]
    
    def get_keymap(self) -> Dict[str, str]:
        """Retourne le keymap actuel."""
        if self.current_keymap in DEFAULT_KEYMAPS:
            return DEFAULT_KEYMAPS[self.current_keymap]["bindings"]
        custom = self.config.get("custom_keymaps", {}).get(self.current_keymap)
        if custom:
            return custom.get("bindings", {})
        return DEFAULT_KEYMAPS["default"]["bindings"]
    
    def set_cursor_style(self, style: CursorStyle) -> None:
        """Applique un style de curseur."""
        style_codes = {
            CursorStyle.BLOCK: self.ANSI["cursor_block"],
            CursorStyle.UNDERLINE: self.ANSI["cursor_underline"],
            CursorStyle.BAR: self.ANSI["cursor_bar"],
            CursorStyle.BLOCK_BLINK: self.ANSI["cursor_block_blink"],
            CursorStyle.UNDERLINE_BLINK: self.ANSI["cursor_underline_blink"],
            CursorStyle.BAR_BLINK: self.ANSI["cursor_bar_blink"],
        }
        code = style_codes.get(style, "")
        if code:
            print(code, end="", flush=True)
    
    def hide_cursor(self) -> None:
        """Cache le curseur."""
        print(self.ANSI["cursor_hide"], end="", flush=True)
    
    def show_cursor(self) -> None:
        """Affiche le curseur."""
        print(self.ANSI["cursor_show"], end="", flush=True)
    
    def move_cursor(self, row: int, col: int) -> None:
        """Déplace le curseur à une position."""
        print(f"\033[{row};{col}H", end="", flush=True)
    
    def clear_screen(self) -> None:
        """Efface l'écran."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def clear_screen_ansi(self) -> None:
        """Efface l'écran avec ANSI (sans clignotement)."""
        # Move cursor to home position and clear screen
        print(f"{self.ANSI['move_home']}{self.ANSI['clear_screen']}", end="", flush=True)
    
    def move_to_home(self) -> None:
        """Déplace le curseur en haut à gauche."""
        print(self.ANSI['move_home'], end="", flush=True)
    
    def clear_line(self) -> None:
        """Efface la ligne courante."""
        print(self.ANSI['clear_line'], end="", flush=True)
    
    def render_menu_item(self, item: MenuItem, index: int, is_selected: bool) -> str:
        """Rend un élément de menu."""
        theme = self.get_theme()
        show_shortcuts = self.config.get("show_shortcuts", True)
        
        # Construire la ligne
        if is_selected:
            # Élément sélectionné avec couleurs
            bg = f"\033[{theme.selected_bg}m"
            fg = f"\033[{theme.selected_fg}m"
            indicator = f" {theme.indicator} "
            line = f"{bg}{fg}{indicator}{item.label}{self.ANSI['reset']}"
        else:
            # Élément normal
            indicator = "   "
            if show_shortcuts and item.key:
                shortcut = f"[{item.key}] "
            else:
                shortcut = ""
            
            if not item.enabled:
                line = f"{self.ANSI['dim']}{indicator}{shortcut}{item.label}{self.ANSI['reset']}"
            else:
                line = f"{indicator}{shortcut}{item.label}"
        
        return line
    
    def render_menu(self, items: List[MenuItem], title: str = "", footer: str = "", use_ansi_clear: bool = False) -> None:
        """Affiche le menu complet."""
        if use_ansi_clear:
            # Rendu sans clignotement : repositionne et réécrit
            self.move_to_home()
        else:
            self.clear_screen()
        
        theme = self.get_theme()
        
        # Appliquer le style de curseur
        self.set_cursor_style(theme.style)
        
        # Calculer la largeur du terminal pour effacer correctement les lignes
        try:
            terminal_width = os.get_terminal_size().columns
        except OSError:
            terminal_width = 80
        
        lines_output = []
        
        # Titre
        if title:
            lines_output.append("")
            lines_output.append(f"{self.ANSI['bold']}{title}{self.ANSI['reset']}")
            lines_output.append("")
        
        # Calculer la fenêtre visible
        visible = self.config.get("visible_items", 10)
        total = len(items)
        
        # Ajuster le scroll si nécessaire
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + visible:
            self.scroll_offset = self.selected_index - visible + 1
        
        # Indicateur de scroll haut
        if self.scroll_offset > 0:
            lines_output.append(f"   {self.ANSI['dim']}▲ {self.scroll_offset} éléments au-dessus{self.ANSI['reset']}")
        else:
            lines_output.append("")  # Ligne vide pour garder le même nombre de lignes
        
        # Afficher les éléments visibles
        start = self.scroll_offset
        end = min(start + visible, total)
        
        for i in range(start, end):
            item = items[i]
            is_selected = (i == self.selected_index)
            line = self.render_menu_item(item, i, is_selected)
            lines_output.append(line)
        
        # Remplir les lignes manquantes pour garder une hauteur fixe
        for _ in range(visible - (end - start)):
            lines_output.append("")
        
        # Indicateur de scroll bas
        remaining = total - end
        if remaining > 0:
            lines_output.append(f"   {self.ANSI['dim']}▼ {remaining} éléments en dessous{self.ANSI['reset']}")
        else:
            lines_output.append("")
        
        # Mode de recherche
        if self.in_search_mode:
            lines_output.append("")
            lines_output.append(f"{self.ANSI['yellow']}Recherche: {self.search_query}_{self.ANSI['reset']}")
        else:
            lines_output.append("")
            lines_output.append("")
        
        # Footer
        if footer:
            lines_output.append("")
            lines_output.append(f"{self.ANSI['dim']}{footer}{self.ANSI['reset']}")
        
        # Info navigation
        if self.mode == NavigationMode.DYNAMIC:
            keymap_name = DEFAULT_KEYMAPS.get(self.current_keymap, {}).get("name", self.current_keymap)
            lines_output.append("")
            lines_output.append(f"{self.ANSI['dim']}Navigation: {keymap_name} | Thème: {self.current_theme}{self.ANSI['reset']}")
        
        # Afficher toutes les lignes en effaçant le reste de chaque ligne
        for line in lines_output:
            # Effacer la ligne puis écrire le contenu
            print(f"{self.ANSI['clear_line']}{line}")
    
    def navigate_menu(
        self,
        items: List[MenuItem],
        title: str = "",
        footer: str = "",
        allow_back: bool = True
    ) -> Optional[MenuItem]:
        """
        Navigation interactive dans un menu.
        
        Args:
            items: Liste des éléments de menu
            title: Titre du menu
            footer: Texte de pied de page
            allow_back: Autoriser le retour arrière
        
        Returns:
            L'élément sélectionné ou None si annulé
        """
        if self.mode == NavigationMode.STATIC:
            return self._navigate_static(items, title, footer)
        else:
            return self._navigate_dynamic(items, title, footer, allow_back)
    
    def _navigate_static(
        self,
        items: List[MenuItem],
        title: str,
        footer: str
    ) -> Optional[MenuItem]:
        """Navigation statique classique."""
        self.clear_screen()
        
        if title:
            print(f"\n{title}\n")
        
        # Afficher les éléments
        for i, item in enumerate(items, 1):
            shortcut = f"[{item.key}]" if item.key else f"[{i}]"
            enabled = "" if item.enabled else " (désactivé)"
            print(f"  {shortcut} {item.label}{enabled}")
        
        if footer:
            print(f"\n{footer}")
        
        # Saisie
        choice = input("\n>> ").strip().lower()
        
        # Chercher par touche ou numéro
        for i, item in enumerate(items):
            if choice == item.key.lower() or choice == str(i + 1):
                if item.enabled:
                    return item
        
        return None
    
    def _navigate_dynamic(
        self,
        items: List[MenuItem],
        title: str,
        footer: str,
        allow_back: bool
    ) -> Optional[MenuItem]:
        """Navigation dynamique avec clavier."""
        if not items:
            return None
        
        self.selected_index = 0
        self.scroll_offset = 0
        keymap = self.get_keymap()
        key_buffer = ""
        first_render = True
        
        try:
            self.terminal.setup_raw_mode()
            self.hide_cursor()
            
            while True:
                # Premier rendu : clear complet, puis repositionnement ANSI
                if first_render:
                    self.clear_screen()
                    self.render_menu(items, title, footer, use_ansi_clear=False)
                    first_render = False
                else:
                    # Rendus suivants : sans clignotement
                    self.render_menu(items, title, footer, use_ansi_clear=True)
                
                # Attendre une touche
                time.sleep(0.03)  # Délai réduit pour meilleure réactivité
                
                key = self.terminal.get_key()
                if not key:
                    continue
                
                # Buffer pour les séquences multi-touches (comme 'gg')
                key_buffer += key
                
                # Chercher l'action dans le keymap
                action = keymap.get(key_buffer) or keymap.get(key)
                
                # Vérifier les raccourcis directs (lettres/chiffres)
                if not action and len(key) == 1:
                    for item in items:
                        if item.key.lower() == key.lower() and item.enabled:
                            self.show_cursor()
                            self.terminal.restore_mode()
                            return item
                
                if action:
                    key_buffer = ""  # Reset le buffer
                    
                    if action == "move_up":
                        self.selected_index = max(0, self.selected_index - 1)
                    
                    elif action == "move_down":
                        self.selected_index = min(len(items) - 1, self.selected_index + 1)
                    
                    elif action == "select":
                        item = items[self.selected_index]
                        if item.enabled:
                            self.show_cursor()
                            self.terminal.restore_mode()
                            return item
                    
                    elif action == "back" and allow_back:
                        self.show_cursor()
                        self.terminal.restore_mode()
                        return None
                    
                    elif action == "quit":
                        self.show_cursor()
                        self.terminal.restore_mode()
                        return MenuItem(key="quit", label="Quit", handler=None)
                    
                    elif action == "go_first":
                        self.selected_index = 0
                        self.scroll_offset = 0
                    
                    elif action == "go_last":
                        self.selected_index = len(items) - 1
                    
                    elif action == "page_up":
                        visible = self.config.get("visible_items", 10)
                        self.selected_index = max(0, self.selected_index - visible)
                    
                    elif action == "page_down":
                        visible = self.config.get("visible_items", 10)
                        self.selected_index = min(len(items) - 1, self.selected_index + visible)
                    
                    elif action == "search":
                        self.in_search_mode = True
                        self.search_query = ""
                    
                    elif action == "help":
                        self._show_help()
                    
                    elif action == "refresh":
                        pass  # Juste redessiner
                
                # Reset buffer si pas de match après un certain temps
                if len(key_buffer) > 2:
                    key_buffer = ""
        
        except KeyboardInterrupt:
            pass
        finally:
            self.show_cursor()
            self.terminal.restore_mode()
        
        return None
    
    def _show_help(self) -> None:
        """Affiche l'aide des raccourcis."""
        self.clear_screen()
        keymap = self.get_keymap()
        keymap_name = DEFAULT_KEYMAPS.get(self.current_keymap, {}).get("name", self.current_keymap)
        
        print(f"\n{self.ANSI['bold']}=== AIDE - Keymap: {keymap_name} ==={self.ANSI['reset']}\n")
        
        actions = {}
        for key, action in keymap.items():
            if action not in actions:
                actions[action] = []
            # Rendre la touche lisible
            if key == "\r" or key == "\n":
                display_key = "Enter"
            elif key == " ":
                display_key = "Espace"
            elif key == "\x1b":
                display_key = "Echap"
            elif len(key) == 1:
                display_key = key
            else:
                display_key = key
            actions[action].append(display_key)
        
        for action, keys in sorted(actions.items()):
            keys_str = ", ".join(keys)
            print(f"  {action:<15} : {keys_str}")
        
        print(f"\n{self.ANSI['dim']}Appuyez sur une touche pour continuer...{self.ANSI['reset']}")
        
        # Attendre une touche
        try:
            self.terminal.setup_raw_mode()
            while not self.terminal.get_key():
                time.sleep(0.1)
        finally:
            self.terminal.restore_mode()


# ============================================================
#                    SETTINGS UI
# ============================================================

def navigation_settings_menu(nav_manager: NavigationManager) -> None:
    """Menu de configuration de la navigation."""
    while True:
        nav_manager.clear_screen()
        
        print("\n" + "=" * 55)
        print("           ⚙️  PARAMÈTRES DE NAVIGATION")
        print("=" * 55)
        
        mode_display = "Dynamique (flèches/vim)" if nav_manager.mode == NavigationMode.DYNAMIC else "Statique (saisie texte)"
        
        print(f"\n📍 Configuration actuelle:")
        print(f"   Mode: {mode_display}")
        print(f"   Keymap: {nav_manager.current_keymap}")
        print(f"   Thème curseur: {nav_manager.current_theme}")
        
        print("\n" + "-" * 55)
        print("  1. 🔄 Changer le mode de navigation")
        print("  2. ⌨️  Changer le keymap")
        print("  3. 🎨 Changer le thème du curseur")
        print("  4. ✏️  Créer un keymap personnalisé")
        print("  5. 🖌️  Créer un thème personnalisé")
        print("  6. 👁️  Prévisualiser la navigation")
        print("  R. Retour")
        
        choice = input("\nChoix: ").strip().lower()
        
        if choice == "1":
            _change_mode(nav_manager)
        elif choice == "2":
            _change_keymap(nav_manager)
        elif choice == "3":
            _change_theme(nav_manager)
        elif choice == "4":
            _create_custom_keymap(nav_manager)
        elif choice == "5":
            _create_custom_theme(nav_manager)
        elif choice == "6":
            _preview_navigation(nav_manager)
        elif choice == "r":
            break


def _change_mode(nav: NavigationManager) -> None:
    """Change le mode de navigation."""
    print("\nModes disponibles:")
    print("  1. Statique (saisie texte classique)")
    print("  2. Dynamique (navigation avec flèches/vim)")
    
    choice = input("\nChoix: ").strip()
    
    if choice == "1":
        nav.mode = NavigationMode.STATIC
        print("\n✅ Mode statique activé.")
    elif choice == "2":
        nav.mode = NavigationMode.DYNAMIC
        print("\n✅ Mode dynamique activé.")
    
    nav.save_config()
    input("\nAppuyez sur Entrée...")


def _change_keymap(nav: NavigationManager) -> None:
    """Change le keymap."""
    print("\nKeymaps disponibles:")
    
    keymaps = list(DEFAULT_KEYMAPS.keys())
    custom = list(nav.config.get("custom_keymaps", {}).keys())
    all_keymaps = keymaps + custom
    
    for i, km in enumerate(all_keymaps, 1):
        if km in DEFAULT_KEYMAPS:
            info = DEFAULT_KEYMAPS[km]
            current = " ◀" if km == nav.current_keymap else ""
            print(f"  {i}. {info['name']} - {info['description']}{current}")
        else:
            current = " ◀" if km == nav.current_keymap else ""
            print(f"  {i}. {km} (personnalisé){current}")
    
    choice = input("\nNuméro: ").strip()
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(all_keymaps):
            nav.current_keymap = all_keymaps[idx]
            nav.save_config()
            print(f"\n✅ Keymap '{nav.current_keymap}' activé.")
    except (ValueError, IndexError):
        print("\n❌ Choix invalide.")
    
    input("\nAppuyez sur Entrée...")


def _change_theme(nav: NavigationManager) -> None:
    """Change le thème du curseur."""
    print("\nThèmes de curseur disponibles:")
    
    themes = list(CURSOR_THEMES.keys())
    custom = list(nav.config.get("custom_themes", {}).keys())
    all_themes = themes + custom
    
    for i, theme_name in enumerate(all_themes, 1):
        if theme_name in CURSOR_THEMES:
            theme = CURSOR_THEMES[theme_name]
        else:
            theme = CursorTheme.from_dict(nav.config["custom_themes"][theme_name])
        
        current = " ◀" if theme_name == nav.current_theme else ""
        print(f"  {i}. {theme.indicator} {theme_name} ({theme.style.value}){current}")
    
    choice = input("\nNuméro: ").strip()
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(all_themes):
            nav.current_theme = all_themes[idx]
            nav.save_config()
            print(f"\n✅ Thème '{nav.current_theme}' activé.")
    except (ValueError, IndexError):
        print("\n❌ Choix invalide.")
    
    input("\nAppuyez sur Entrée...")


def _create_custom_keymap(nav: NavigationManager) -> None:
    """Crée un keymap personnalisé."""
    print("\n--- Créer un keymap personnalisé ---")
    
    name = input("Nom du keymap: ").strip()
    if not name:
        return
    
    print("\nPartir d'un keymap existant?")
    print("  1. default")
    print("  2. vim")
    print("  3. arrows")
    print("  4. wasd")
    print("  5. Partir de zéro")
    
    base_choice = input("\nChoix: ").strip()
    
    base_keymaps = {
        "1": "default",
        "2": "vim",
        "3": "arrows",
        "4": "wasd"
    }
    
    if base_choice in base_keymaps:
        bindings = DEFAULT_KEYMAPS[base_keymaps[base_choice]]["bindings"].copy()
    else:
        bindings = {}
    
    print("\nEntrez les raccourcis (vide pour terminer):")
    print("Format: touche=action (ex: k=move_up)")
    print("Actions: move_up, move_down, select, back, quit, go_first, go_last, page_up, page_down, search, help, refresh")
    
    while True:
        binding = input(">>> ").strip()
        if not binding:
            break
        
        if "=" in binding:
            key, action = binding.split("=", 1)
            bindings[key] = action
            print(f"  ✓ {key} → {action}")
    
    # Sauvegarder
    if "custom_keymaps" not in nav.config:
        nav.config["custom_keymaps"] = {}
    
    nav.config["custom_keymaps"][name] = {
        "name": name,
        "description": "Keymap personnalisé",
        "bindings": bindings
    }
    
    nav.save_config()
    print(f"\n✅ Keymap '{name}' créé avec {len(bindings)} raccourcis!")
    input("\nAppuyez sur Entrée...")


def _create_custom_theme(nav: NavigationManager) -> None:
    """Crée un thème de curseur personnalisé."""
    print("\n--- Créer un thème personnalisé ---")
    
    name = input("Nom du thème: ").strip()
    if not name:
        return
    
    print("\nStyle de curseur:")
    print("  1. block")
    print("  2. underline")
    print("  3. bar")
    print("  4. block_blink")
    print("  5. underline_blink")
    print("  6. bar_blink")
    
    style_map = {
        "1": CursorStyle.BLOCK,
        "2": CursorStyle.UNDERLINE,
        "3": CursorStyle.BAR,
        "4": CursorStyle.BLOCK_BLINK,
        "5": CursorStyle.UNDERLINE_BLINK,
        "6": CursorStyle.BAR_BLINK
    }
    
    style_choice = input("Choix [1-6]: ").strip()
    style = style_map.get(style_choice, CursorStyle.BLOCK)
    
    print("\nIndicateur de sélection (ex: ▶, >, →, ●):")
    indicator = input(">>> ").strip() or "▶"
    
    print("\nCouleur de fond sélection (41=rouge, 42=vert, 43=jaune, 44=bleu, 45=magenta, 46=cyan):")
    selected_bg = input("Code [44]: ").strip() or "44"
    
    print("\nCouleur de texte sélection (97=blanc, 30=noir):")
    selected_fg = input("Code [97]: ").strip() or "97"
    
    theme = CursorTheme(
        name=name,
        style=style,
        color="default",
        selected_bg=selected_bg,
        selected_fg=selected_fg,
        indicator=indicator
    )
    
    # Sauvegarder
    if "custom_themes" not in nav.config:
        nav.config["custom_themes"] = {}
    
    nav.config["custom_themes"][name] = theme.to_dict()
    nav.save_config()
    
    print(f"\n✅ Thème '{name}' créé!")
    input("\nAppuyez sur Entrée...")


def _preview_navigation(nav: NavigationManager) -> None:
    """Prévisualise la navigation."""
    items = [
        MenuItem(key="1", label="Élément 1 - Exemple", enabled=True),
        MenuItem(key="2", label="Élément 2 - Test", enabled=True),
        MenuItem(key="3", label="Élément 3 - Démo", enabled=True),
        MenuItem(key="4", label="Élément 4 - Option", enabled=True),
        MenuItem(key="5", label="Élément 5 - Configuration", enabled=True),
        MenuItem(key="6", label="Élément 6 - Paramètres", enabled=True),
        MenuItem(key="7", label="Élément 7 - (Désactivé)", enabled=False),
        MenuItem(key="8", label="Élément 8 - Action", enabled=True),
        MenuItem(key="R", label="Retour", enabled=True),
    ]
    
    if nav.mode == NavigationMode.STATIC:
        print("\n[Mode Statique - Aperçu]")
        print("Utilisez les touches/numéros pour naviguer.\n")
    else:
        print("\n[Mode Dynamique - Aperçu]")
        print("Utilisez les flèches ou raccourcis configurés.\n")
    
    result = nav.navigate_menu(
        items,
        title="=== PRÉVISUALISATION ===",
        footer="Sélectionnez un élément ou appuyez sur R pour revenir"
    )
    
    if result:
        print(f"\n✅ Sélectionné: {result.label}")
    else:
        print("\n❌ Annulé")
    
    input("\nAppuyez sur Entrée...")
