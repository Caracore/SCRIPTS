#Requires AutoHotkey v2.0
; Script Manager - Raccourci clavier
; Hotkey: Ctrl+Alt+S
; Généré automatiquement

; ^!s pour lancer Script Manager
^!s::
{
    SetWorkingDir "C:/Users/jm214/Documents/SCRIPTS"
    Run '"C:/Users/jm214/AppData/Local/Programs/Python/Python312/python.exe" main.py',, "Min"
}
