

# Chiude tutti i processi che occupano la porta 8090 prima di avviare il servizio
$maxTries = 5
$waitSec = 2
$freed = $false
for ($try = 1; $try -le $maxTries; $try++) {
    $netstatOutput = netstat -ano | Select-String ":8090"
    if ($netstatOutput) {
        Write-Host "[INFO] Processi trovati su porta 8090 (tentativo $try/$maxTries):"
        $pids = $netstatOutput | ForEach-Object {
            $fields = ($_ -replace '\s+', ' ').Trim() -split ' '
            $fields[$fields.Length-1]
        } | Select-Object -Unique
        foreach ($procId in $pids) {
            if ($procId -and $procId -match '^\d+$') {
                try {
                    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
                    if ($proc) {
                        Write-Host ("  PID: " + $procId + " | Nome: " + $proc.ProcessName)
                    } else {
                        Write-Host ("  PID: " + $procId + " | (dettagli non disponibili)")
                    }
                    Stop-Process -Id $procId -Force -ErrorAction Stop
                    Write-Host ("[INFO] Arrestato processo PID " + $procId)
                } catch {
                    Write-Host ("[WARN] Impossibile arrestare PID " + $procId + ": " + $Error[0])
                }
            }
        }
        Start-Sleep -Seconds $waitSec
    } else {
        $freed = $true
        break
    }
}
if (-not $freed) {
    Write-Host "[ERRORE] Impossibile liberare la porta 8090 dopo $maxTries tentativi. Aborto."
    exit 1
} else {
    Write-Host "[INFO] Porta 8090 libera."
}



# Avvia il servizio in una nuova finestra PowerShell
$cmd = "cd `"$($PWD.Path)`"; python main.py"
Start-Process powershell -ArgumentList '-NoExit', '-Command', $cmd
