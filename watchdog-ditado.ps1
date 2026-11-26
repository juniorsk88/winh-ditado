# Vigia do ditado (Win+H): se o cliente sumir, ele volta sozinho.
#
# O servico do Whisper (porta 8178) ja tem um vigia. Este aqui cuida do outro
# lado: o programinha que escuta o Win+H. Foi ele que sumiu e deixou o atalho
# sem funcao.
#
# Instalar: rode Instalar-Watchdog.cmd (uma vez).
# Parar:    rode Parar-Watchdog.cmd.

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
$log = Join-Path $raiz "watchdog-ditado.log"
$pythonw = "C:\Users\junio\.dsh\voice-stt\.venv\Scripts\pythonw.exe"
$cliente = "C:\Users\junio\.dsh\voice-stt\winh\dictate.py"
$pasta = "C:\Users\junio\.dsh\voice-stt\winh"

function Registrar([string]$mensagem) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $mensagem" | Add-Content -Path $log -Encoding utf8
}

if (-not (Test-Path $pythonw)) { Registrar "ERRO: pythonw nao encontrado em $pythonw"; exit 1 }
if (-not (Test-Path $cliente)) { Registrar "ERRO: dictate.py nao encontrado em $cliente"; exit 1 }

function DitadoRodando {
    $processos = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" -ErrorAction SilentlyContinue
    foreach ($p in $processos) {
        if ($p.CommandLine -and $p.CommandLine -like "*dictate.py*") { return $true }
    }
    return $false
}

Registrar "vigia iniciado (pid $PID)"
$reinicios = @()

while ($true) {
    if (-not (DitadoRodando)) {
        $agora = Get-Date
        $reinicios = @($reinicios | Where-Object { ($agora - $_).TotalMinutes -lt 10 })
        if ($reinicios.Count -ge 3) {
            Registrar "3 reinicios em 10 minutos: parando o vigia para nao entrar em loop"
            break
        }
        Registrar "ditado ausente: iniciando de novo"
        Start-Process -FilePath $pythonw -ArgumentList "`"$cliente`"" -WorkingDirectory $pasta -WindowStyle Hidden
        $reinicios += $agora
        Start-Sleep -Seconds 8
    }
    Start-Sleep -Seconds 20
}
