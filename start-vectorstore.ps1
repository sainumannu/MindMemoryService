#!/usr/bin/env pwsh
# Script di avvio per VectorStore Service

param(
    [string]$Port = "8090",
    [string]$ServiceHost = "127.0.0.1",
    [switch]$Debug,
    [switch]$NewWindow
)

# Se -NewWindow non è specificato e siamo in una finestra integrata, apri in una nuova finestra
if (-not $NewWindow) {
    $scriptPath = $MyInvocation.MyCommand.Path
    if ($scriptPath) {
        $args = @('-NoExit', '-NoProfile', '-File', $scriptPath, '-NewWindow')
        if ($Debug) { $args += '-Debug' }
        Start-Process powershell -ArgumentList $args -WorkingDirectory (Split-Path $scriptPath -Parent)
        exit 0
    }
}

Write-Host "🚀 Avvio VectorStore Service..." -ForegroundColor Green
Write-Host "   Porta: $Port" -ForegroundColor Gray
Write-Host "   Host: $ServiceHost" -ForegroundColor Gray


# Usa la directory dello script come root
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptRoot

# Verifica che main.py esista
if (-not (Test-Path "$scriptRoot\main.py")) {
    Write-Host "❌ File main.py non trovato in $scriptRoot" -ForegroundColor Red
    Read-Host "Premi Enter per uscire"
    exit 1
}

# Verifica che Python sia disponibile
try {
    $pythonVersion = python --version 2>&1
    Write-Host "   Python: $pythonVersion" -ForegroundColor Gray
} catch {
    Write-Host "❌ Python non trovato nel PATH" -ForegroundColor Red
    Write-Host "💡 Installa Python o aggiungilo al PATH" -ForegroundColor Yellow
    Read-Host "Premi Enter per uscire"
    exit 1
}

# Verifica che requirements.txt sia soddisfatto
if (Test-Path "$scriptRoot\requirements.txt") {
    Write-Host "   Controllo dipendenze..." -ForegroundColor Gray
    $pipCheck = pip check 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Alcune dipendenze potrebbero mancare" -ForegroundColor Yellow
        Write-Host "   Esegui: pip install -r requirements.txt" -ForegroundColor Gray
    }
}

# Imposta variabili d'ambiente (compatibilità, NON usare HOST)
$env:PORT = $Port
$env:VECTORSTORE_SERVICE_PORT = $Port
$env:VECTORSTORE_SERVICE_HOST = $ServiceHost
$env:VECTORSTORE_HOST = $ServiceHost


if ($Debug) {
    $env:LOG_LEVEL = "DEBUG"
    Write-Host "   Debug: Abilitato" -ForegroundColor Yellow
}


Write-Host "Comando: python main.py" -ForegroundColor Yellow
python main.py
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    Write-Host "❌ Errore avvio VectorStore Service (exit code $exitCode)" -ForegroundColor Red
    Write-Host "💡 Suggerimenti:" -ForegroundColor Yellow
    Write-Host "   - Verifica che Python sia installato e nel PATH" -ForegroundColor Gray
    Write-Host "   - Controlla che le dipendenze siano installate: pip install -r requirements.txt" -ForegroundColor Gray
    Write-Host "   - Assicurati che la porta $Port non sia già in uso" -ForegroundColor Gray
    Write-Host "   - Verifica configurazioni ChromaDB e variabili d'ambiente" -ForegroundColor Gray
    Read-Host "Premi Enter per uscire"
}