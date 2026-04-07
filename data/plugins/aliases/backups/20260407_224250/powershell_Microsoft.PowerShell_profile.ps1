# Alias pour lancer Neovim
Set-Alias -Name n -Value nvim -Option AllScope

# Alias pour lister les fichiers (comme 'ls' sous Linux)
Set-Alias -Name ls -Value Get-ChildItem -Option AllScope

# Alias pour quitter
Set-Alias -Name e -Value Exit -Option AllScope
Set-Alias -Name e -Value exit -Option AllScope


# Alias pour remonter d'un dossier
Set-Alias -Name .. -Value 'Set-Location ..' -Option AllScope

# Alias pour remonter de deux dossiers
Set-Alias -Name ... -Value 'Set-Location ..\..' -Option AllScope

# Alias pour 'explorer .' (ouvrir l'explorateur de fichiers)
Set-Alias -Name x -Value 'ii .' -Option AllScope

# Alias New Item pour créer un nouveau fichier
# Exemple: new monfichier.txt -ItemType File
Set-Alias -Name new -Value New-Item -Option AllScope


# Fonctions 
# Fonction pour remonter de N dossiers (ex: ... 3)
Function up {
    param([int]$n = 1)
    Set-Location ("..\" * $n)
}

# Fonction pour 'explorer .'
Function ii {
    Invoke-Item .
}

function touch {
    param([string]$fileName)
    if (Test-Path $fileName) {
        (Get-Item $fileName).LastWriteTime = Get-Date
    } else {
        New-Item -ItemType File $fileName | Out-Null
    }
}

# ==================================================
# ==================================================

# ==================================================
# ==================================================

# ==================================================
# Aliases gérés par Script Manager
# ==================================================
# None
function s { py main.py $args }
# ==================================================
# Fin des aliases Script Manager
# ==================================================
