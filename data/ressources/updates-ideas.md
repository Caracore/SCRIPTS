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