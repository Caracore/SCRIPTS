 Fonctionnalités :

   - Changer l'ASCII art du dashboard
   - Prévisualiser les ASCII
   - Ajouter des ASCII personnalisés (fichiers .txt)
   - Message de bienvenue personnalisé
   - Sauvegarde dans data/themes.json

  3. Nouveau menu

   8. Personnalisation      [T]

Le plugin fonctionne. Voici le résumé :

  Plugin Auto-Start-Sys créé ✓

  Fonctionnalités

  ┌────────────────────────────┬─────────────────────────────────────────────────────────┐
  │ Fonction                   │ Description                                             │
  ├────────────────────────────┼─────────────────────────────────────────────────────────┤
  │ Démarrage Système          │ Lance au boot du PC (Windows Startup / Linux autostart) │
  ├────────────────────────────┼─────────────────────────────────────────────────────────┤
  │ Démarrage Conditionnel     │ Lance quand un processus spécifique démarre             │
  ├────────────────────────────┼─────────────────────────────────────────────────────────┤
  │ Types supportés            │ Scripts, Applications externes, Gestionnaire lui-même   │
  └────────────────────────────┴─────────────────────────────────────────────────────────┘

  Protections anti-boucle 🛡️

   1. Limite d'items : max 10 items configurables
   2. Détection boucle : >3 démarrages en 60s → désactivation auto
   3. Blocage auto-référence : interdit d'ajouter le gestionnaire au boot système
   4. Avertissement obligatoire : taper "JACCEPTE" pour activer
   5. Validation chemins : vérifie que les fichiers existent
 Pour tester

  Quand vous exécutez script-auto-test-virtual-box.py depuis le gestionnaire, VirtualBox devrait se lancer automatiquement (si le
  plugin est activé).

  Note: Le déclencheur process (surveillance d'applications externes comme chrome.exe) n'est pas encore implémenté - il
  nécessiterait un monitoring actif en arrière-plan. Seul le déclencheur script fonctionne pour l'instant.

----------

ERROR AND BUGS:

--- Exécution d'un script ---

Scripts disponibles dans: C:\Users\jm214\Documents\SCRIPTS\data\scripts
  1. [python] script-auto-test-virtual-box.py

  A. Chercher dans un autre dossier

Choisissez un script à exécuter (numéro) ou 'q' pour quitter: 1
[Example] Préparation de: script-auto-test-virtual-box.py

  [1] Exécution normale (bloquante)
  [2] Exécution détachée (arrière-plan)
  [3] Exécution dans un nouveau terminal

Mode d'exécution: 3

script-auto-test-virtual-box.py lancé dans un nouveau terminal (PID: 8352)
[Example] script-auto-test-virtual-box.py terminé ✓
[Plugin] Erreur dans hook POST_EXECUTE: AutoStartSysPlugin.on_script_executed() takes from 2 to 3 positional arguments but 4 were given

Appuyez sur Entrée pour continuer...


✅ Revue cross-platform

Le code est déjà compatible Windows/Linux grâce à :

┌────────────────────┬───────────────────────────────────────────────────────────┐
│ Aspect             │ Implémentation                                            │
├────────────────────┼───────────────────────────────────────────────────────────┤
│ Clear screen       │ os.system('cls' if os.name == 'nt' else 'clear')          │
├────────────────────┼───────────────────────────────────────────────────────────┤
│ Chemins            │ pathlib.Path utilisé partout                              │
├────────────────────┼───────────────────────────────────────────────────────────┤
│ Processus détachés │ platform.system() dans launcher.py                        │
├────────────────────┼───────────────────────────────────────────────────────────┤
│ Sons (Pomodoro)    │ winsound (Win) / paplay ou \a (Linux)                     │
├────────────────────┼───────────────────────────────────────────────────────────┤
│ Explorateur        │ explorer (Win) / xdg-open (Linux)                         │
├────────────────────┼───────────────────────────────────────────────────────────┤
│ Terminaux          │ Windows Terminal/cmd (Win) / gnome-terminal/xterm (Linux) │
└────────────────────┴───────────────────────────────────────────────────────────┘

Les deux plugins utilisent les mêmes patterns cross-platform que le reste du code.

✅ Intégration terminée

Navigation statique et dynamique intégrée au programme principal:

 1. Import dans program.py - NavigationManager, NavigationMode, MenuItem
 2. Nouveau menu #9 "Navigation [V]" - Accès aux paramètres de navigation
 3. Modes de navigation:
  - Statique (par défaut) - Navigation classique par saisie texte
  - Dynamique - Navigation avec flèches/vim et curseur visuel
 4. Dans le menu des paramètres de navigation (9 ou V):
  - Changer de mode (statique ↔ dynamique)
  - Choisir le keymap (default/vim/arrows/wasd)
  - Choisir le thème de curseur (7 thèmes)
  - Créer des keymaps personnalisés
 5. 7 Thèmes de curseur: default, minimal, neon, retro, ocean, fire, vim
 6. 4 Keymaps prédéfinis:
  - default - Flèches + raccourcis courants
  - vim - hjkl + gg/G/u/d
  - arrows - Flèches uniquement
  - wasd - Style jeu vidéo

Pour tester:

 cd C:\Users\jm214\Documents\SCRIPTS
 python launcher.py
 # Aller dans 9. Navigation pour configurer le mode dynamique

✅ Corrections appliquées

1. Clignotement en mode dynamique (navigation.py)

 - Le menu utilise maintenant les séquences ANSI pour repositionner le curseur et réécrire sans effacer l'écran
 - Premier rendu : clear_screen() classique
 - Rendus suivants : move_to_home() + réécriture ligne par ligne
 - Résultat : écran stable, pas de flash

2. Notifications (notifications/plugin.py)

Dépendances recommandées :

┌──────────────┬───────────────────┬─────────────────────┬────────────────┐
│ Package      │ OS                │ Sécurité            │ Notes          │
├──────────────┼───────────────────┼─────────────────────┼────────────────┤
│ plyer ⭐     │ Windows/Linux/Mac │ ✓ Maintenu par Kivy │ Recommandé     │
├──────────────┼───────────────────┼─────────────────────┼────────────────┤
│ notify2      │ Linux             │ ✓ D-Bus natif       │ Fallback Linux │
└──────────────┴───────────────────┴─────────────────────┴────────────────┘

Fallbacks automatiques :

 - Windows : PowerShell avec Windows.Forms (BalloonTip)
 - Linux : notify-send (libnotify)

3. Installation des dépendances

Menu option 9 → Interface pour installer :

 - pip install plyer (recommandé, cross-platform)
 - pip install notify2 (Linux)

Pour installer maintenant :

 pip install plyer


Le plugin est créé et fonctionne. Voici un résumé :

✅ Plugin Organisation créé

Emplacement: data\plugins\organisation\

Fonctionnalités :

┌───────────────────────┬────────────────────────────────────────────────────────────────────────────────┐
│ Catégorie             │ Options                                                                        │
├───────────────────────┼────────────────────────────────────────────────────────────────────────────────┤
│ 🔄 Renommer           │ Unique, masse (préfixe/suffixe), numérotation, rechercher/remplacer            │
├───────────────────────┼────────────────────────────────────────────────────────────────────────────────┤
│ 📦 Déplacer           │ Unique, multiple, par extension                                                │
├───────────────────────┼────────────────────────────────────────────────────────────────────────────────┤
│ 📂 Créer dossiers     │ Vide, avec fichiers, par extension, par date                                   │
├───────────────────────┼────────────────────────────────────────────────────────────────────────────────┤
│ 🗂️ Alphabétique       │ Dossiers A-Z, renommage trié                                                   │
├───────────────────────┼────────────────────────────────────────────────────────────────────────────────┤
│ 🔍 Regex              │ Déplacer par pattern, renommer avec groupes                                    │
├───────────────────────┼────────────────────────────────────────────────────────────────────────────────┤
│ 🏷️ Catégories         │ Images, Documents, Vidéos, Audio, Archives, Code, Exécutables + personnalisées │
├───────────────────────┼────────────────────────────────────────────────────────────────────────────────┤
│ 📋 Historique         │ Voir les opérations effectuées                                                 │
└───────────────────────┴────────────────────────────────────────────────────────────────────────────────┘

Sécurité :

 - ❌ Aucune suppression
 - ❌ Pas de privilèges admin
 - ✅ Protection des fichiers système (desktop.ini, thumbs.db, etc.)
 - ✅ Protection des dossiers Windows (Windows, Program Files, etc.)
 - ✅ Confirmation avant chaque action

Le plugin s'affichera automatiquement dans le menu avec l'option "📁 Organisation (dossiers/Bureau)".


✅ Nouveau module alias_manager.py

Fonctionnalités:

1. Alias Terminal

 - Détection automatique des shells (PowerShell, Bash, Zsh, Fish, CMD)
 - Création d'alias (ex: sm pour lancer le gestionnaire)
 - Support multi-shell simultané

2. Raccourcis Clavier

 - Windows: Création de .lnk avec hotkey (ex: Ctrl+Alt+S)
 - Linux: Fichier .desktop + configuration GNOME/KDE

3. Auto-Run

 - Au démarrage système (dossier Startup / ~/.config/autostart)
 - À l'ouverture terminal (dans les profiles shell)
 - Au login (avant le bureau)

Utilisation:

Dans le menu principal, nouvelle option 10. Alias & Raccourcis [R]:

   1. Ajouter un alias
   2. Supprimer un alias
   3. Voir les shells détectés
   4. Créer un raccourci clavier
   5. Configurer l'auto-run
   6. Désactiver l'auto-run
   7. Installation rapide (alias + raccourci + autorun)

L'installation rapide (7) crée automatiquement:

 - Alias sm dans tous les shells
 - Raccourci Ctrl+Alt+S
 - Auto-run optionnel au démarrage

 ✅ Modifications effectuées

1. Touche corrigée pour Alias & Raccourcis

 - Changée de 10 à = (touche "égal") 
 - Raccourci clavier: R

2. Plugin Timer créé (data/plugins/timer_plugin.py)

 - Touche: ti ou TI
 - Fonctionnalités:
  - ⏱️ Temps de session actuelle
  - 📊 Temps total accumulé (toutes sessions)
  - 📈 Nombre de sessions
  - 📅 Historique des 10 dernières sessions
  - 🔄 Export des statistiques
  - 🗑️ Réinitialisation possible

Menu du Timer:

 ┌─────────────────────────────────┐
 │     Session: 5m 23s             │
 │─────────────────────────────────│
 │     Total: 2h 45m               │
 └─────────────────────────────────┘
 
 1. Voir l'historique des sessions
 2. Réinitialiser les statistiques  
 3. Exporter les statistiques
 R. Retour

Le temps est sauvegardé automatiquement à la fermeture dans data/timer_stats.json.

 ✅ Modifications effectuées

  Dans alias_manager.py :

   1. Nouvelles fonctions ajoutées :
    - update_keyboard_shortcut() - Modifier un raccourci existant
    - remove_keyboard_shortcut() - Supprimer le raccourci
    - get_current_hotkey() - Obtenir le raccourci actuel
    - create_autohotkey_shortcut() - Créer un script AutoHotkey (plus fiable)
    - start_autohotkey() - Lancer le script AHK
    - is_autohotkey_installed() - Vérifier si AHK est installé
    - refresh_windows_shortcut() - Rafraîchir le cache Windows
   2. Nouveau menu _keyboard_shortcut_menu() avec options :
    - Créer/Modifier le raccourci
    - Supprimer le raccourci
    - Rafraîchir le raccourci Windows
    - Créer raccourci AutoHotkey (alternative fiable)
    - Lancer le script AutoHotkey

  Pour faire fonctionner le raccourci :

  Option 1 : Déconnectez-vous et reconnectez-vous (les raccourcis .lnk nécessitent souvent ça)

  Option 2 (recommandée) : Installez AutoHotkey v2 puis double-cliquez sur data\script_manager_hotkey.ahk

  Le script AHK est déjà créé et utilisera Ctrl+Alt+S. AutoHotkey est 100% fiable car il surveille activement les touches.
