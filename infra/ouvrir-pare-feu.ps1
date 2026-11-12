# Ouvre les ports d'EC Perform aux machines du réseau local (à lancer UNE fois, en administrateur).
#
#   5173 : frontend (Vite, Node sous Windows), qui relaie aussi l'API sous /api
#   8080 : ONLYOFFICE Document Server (Docker Desktop)
#
# L'API (port 8000, dans WSL) n'est pas exposée : Vite la joint en localhost. Les autres machines
# n'ont donc pas à traverser le pare-feu Hyper-V de WSL.
# Les règles n'acceptent que les adresses de réseau privé (10/8, 172.16/12, 192.168/16),
# tous profils confondus (le Wi-Fi est classé "Public" sur ce poste).
#
# Suppression : .\infra\ouvrir-pare-feu.ps1 -Supprimer

param([switch]$Supprimer)

$ErrorActionPreference = 'Stop'

$estAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $estAdmin) {
    Write-Host "Ce script doit être lancé dans un PowerShell ouvert en tant qu'administrateur." -ForegroundColor Red
    exit 1
}

$groupe = 'EC Perform (réseau local)'
$reseauxPrives = @('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')
$ports = @(
    @{ Port = 5173; Nom = 'Frontend + API (Vite)' },
    @{ Port = 8080; Nom = 'ONLYOFFICE' }
)

# Nettoyage des règles existantes, y compris l'ancienne règle Hyper-V du port 8000 (idempotent).
Get-NetFirewallRule -Group $groupe -ErrorAction SilentlyContinue | Remove-NetFirewallRule
Get-NetFirewallHyperVRule -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like 'EC-Perform-*' } | Remove-NetFirewallHyperVRule

if ($Supprimer) {
    Write-Host "Règles EC Perform supprimées." -ForegroundColor Green
    exit 0
}

foreach ($p in $ports) {
    New-NetFirewallRule -DisplayName "EC Perform - $($p.Nom) ($($p.Port))" -Group $groupe `
        -Direction Inbound -Protocol TCP -LocalPort $p.Port -Action Allow -Profile Any `
        -RemoteAddress $reseauxPrives | Out-Null
}

Write-Host "Ports 5173 et 8080 ouverts au réseau local." -ForegroundColor Green
