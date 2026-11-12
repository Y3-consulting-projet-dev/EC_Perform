# Lance EC Perform en local, accessible depuis les autres machines du réseau.
#
#   .\demarrer.ps1                 # MongoDB (WSL) + ONLYOFFICE (si Docker Desktop tourne) + API + frontend
#   .\demarrer.ps1 -SansOnlyoffice # sans le Document Server
#
# Prérequis (une seule fois) : .\infra\ouvrir-pare-feu.ps1 dans un PowerShell administrateur.
#
# Le script renseigne ONLYOFFICE_PUBLIC_URL dans backend/.env avec l'IP actuelle du poste : le
# navigateur des autres machines doit charger l'éditeur par cette adresse, pas par "localhost".

param([switch]$SansOnlyoffice)

$racine = $PSScriptRoot
$backend = Join-Path $racine 'backend'
$frontend = Join-Path $racine 'frontend'

function Etape($texte) { Write-Host "-> $texte" -ForegroundColor Cyan }
function Alerte($texte) { Write-Host "   $texte" -ForegroundColor Yellow }

# --- IP du poste sur le réseau local (interface de la route par défaut) ------------------------
$route = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue |
    Sort-Object { $_.RouteMetric + (Get-NetIPInterface -InterfaceIndex $_.InterfaceIndex -AddressFamily IPv4).InterfaceMetric } |
    Select-Object -First 1
$ip = $null
if ($route) {
    $ip = (Get-NetIPAddress -InterfaceIndex $route.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Select-Object -First 1).IPAddress
}
if (-not $ip) {
    Alerte "Aucune connexion réseau détectée : l'application ne sera joignable qu'en localhost."
    $ip = 'localhost'
}

# --- Pare-feu ----------------------------------------------------------------------------------
if (-not (Get-NetFirewallRule -Group 'EC Perform (réseau local)' -ErrorAction SilentlyContinue)) {
    Alerte "Pare-feu non configuré : les autres machines seront bloquées."
    Alerte "Lancer une fois, en administrateur : .\infra\ouvrir-pare-feu.ps1"
}

# --- backend/.env : URL publique d'ONLYOFFICE --------------------------------------------------
$envFichier = Join-Path $backend '.env'
$utf8 = New-Object System.Text.UTF8Encoding($false)
$contenu = [IO.File]::ReadAllText($envFichier, $utf8)
$ligne = "ONLYOFFICE_PUBLIC_URL=http://${ip}:8080"
if ($contenu -match '(?m)^ONLYOFFICE_PUBLIC_URL=.*$') {
    $contenu = $contenu -replace '(?m)^ONLYOFFICE_PUBLIC_URL=.*$', $ligne
} else {
    $contenu = $contenu.TrimEnd() + "`n$ligne`n"
}
[IO.File]::WriteAllText($envFichier, $contenu, $utf8)
Etape "backend/.env : $ligne"

# --- MongoDB (service utilisateur systemd dans WSL) --------------------------------------------
Etape "MongoDB (WSL)"
wsl -e bash -lc "systemctl --user is-active --quiet mongod || systemctl --user start mongod; systemctl --user is-active mongod"

# --- ONLYOFFICE (Docker Desktop) ---------------------------------------------------------------
if (-not $SansOnlyoffice) {
    Etape "ONLYOFFICE (Docker)"
    docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        Push-Location $racine
        docker compose up -d
        Pop-Location
    } else {
        Alerte "Docker Desktop n'est pas démarré : l'éditeur du rapport (Phase 6) sera indisponible."
    }
}

# --- API (WSL) et frontend (Windows), chacun dans sa fenêtre -----------------------------------
# Sans --reload : sur /mnt/d, WatchFiles scanne tout le virtualenv (démarrage très lent) et ne voit
# de toute façon pas les modifications faites depuis Windows. Relancer le script après un changement.
# wsl est lancé depuis une console PowerShell : lancé seul par Start-Process, wsl.exe plantait.
Etape "API FastAPI (nouvelle fenêtre, WSL)"
$cmdApi = "wsl --cd '$backend' -e ./virtualenv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
Start-Process powershell.exe -ArgumentList '-NoExit', '-Command', $cmdApi

Etape "Frontend Vite (nouvelle fenêtre)"
Start-Process powershell.exe -WorkingDirectory $frontend -ArgumentList '-NoExit', '-Command', 'npm run dev'

Write-Host ""
Write-Host "EC Perform démarre :" -ForegroundColor Green
Write-Host "   Sur ce poste       : http://localhost:5173"
Write-Host "   Autres machines    : http://${ip}:5173" -ForegroundColor Green
Write-Host "   API (contrôle)     : http://${ip}:5173/api/health  (relayée par Vite vers localhost:8000)"
Write-Host "   L'API met ~20 s à démarrer. Pour arrêter : fermer les deux fenêtres ouvertes." -ForegroundColor DarkGray
