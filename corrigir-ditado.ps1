# Correcao do ditado (Win+H) que encerra sozinho 0,5 s depois de comecar.
#
# Causa: em dictate.py, o relogio "ultimo texto reconhecido" (last_text_at) nao
# era zerado no inicio de cada ditado. Entao, em qualquer ditado comecado mais
# de 30 s depois do anterior, a primeira checagem (0,5 s depois) ja achava que
# havia 30 s de silencio e encerrava a sessao. Resultado: o Win+H "nao faz nada".
# O primeiro ditado depois de abrir o app funcionava; os seguintes nao.
#
# Este script: faz backup, insere a linha que zera o relogio, confere a sintaxe
# e reinicia o ditado. Se algo der errado, restaura o backup.
#
# A correcao e a mesma que o app novo (winh-dictate\winh\app.py) ja tem na
# linha 173: ao comecar a gravacao, marcar o relogio como "agora".

$ErrorActionPreference = "Stop"

$alvo       = "C:\Users\junio\.dsh\voice-stt\winh\dictate.py"
$pythonExe  = "C:\Users\junio\.dsh\voice-stt\.venv\Scripts\python.exe"
$pythonwExe = "C:\Users\junio\.dsh\voice-stt\.venv\Scripts\pythonw.exe"
$pasta      = Split-Path -Parent $alvo

function Diz([string]$texto) { Write-Host $texto }

Diz "== Correcao do ditado (Win+H) =="
if (-not (Test-Path $alvo)) { Diz "ERRO: nao achei $alvo"; exit 1 }
if (-not (Test-Path $pythonExe)) { Diz "ERRO: nao achei o python do ambiente"; exit 1 }

$bruto = [System.IO.File]::ReadAllText($alvo)
if ($bruto -match '            self\.last_text_at = time\.time\(\)') {
    Diz "O arquivo JA esta corrigido. Nada a fazer alem de reiniciar."
} else {
    $eol = if ($bruto -match "`r`n") { "`r`n" } else { "`n" }
    $linhas = @($bruto -split "`r?`n")

    $indice = -1
    for ($i = 0; $i -lt $linhas.Count; $i++) {
        if ($linhas[$i] -match '^\s+self\.state = self\.RECORDING\s*$') { $indice = $i; break }
    }
    if ($indice -lt 0) { Diz "ERRO: nao achei o ponto de correcao (self.state = self.RECORDING)"; exit 1 }
    Diz ("Ponto de correcao na linha " + ($indice + 1))

    $marca = Join-Path $pasta ("dictate.py.bak-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    Copy-Item $alvo $marca -Force
    Diz ("Backup: " + $marca)

    $inserir = "            self.last_text_at = time.time()"
    $novas = New-Object System.Collections.ArrayList
    for ($i = 0; $i -lt $linhas.Count; $i++) {
        [void]$novas.Add($linhas[$i])
        if ($i -eq $indice) { [void]$novas.Add($inserir) }
    }
    $textoNovo = ($novas -join $eol)
    [System.IO.File]::WriteAllText($alvo, $textoNovo, (New-Object System.Text.UTF8Encoding($false)))
    Diz "Linha inserida."

    $anterior = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $teste = & $pythonExe -m py_compile $alvo 2>&1
    $codigo = $LASTEXITCODE
    $ErrorActionPreference = $anterior
    if ($codigo -ne 0) {
        Diz "ERRO de sintaxe depois da correcao. Restaurando o backup..."
        Copy-Item $marca $alvo -Force
        Diz ($teste | Out-String)
        exit 1
    }
    Diz "Sintaxe conferida: OK"
}

Diz ""
Diz "Reiniciando o ditado..."
$processos = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" -ErrorAction SilentlyContinue
$achou = $false
foreach ($p in $processos) {
    if ($p.CommandLine -and $p.CommandLine -like "*dictate.py*") {
        Diz ("  encerrando pid " + $p.ProcessId)
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        $achou = $true
    }
}
if ($achou) { Start-Sleep -Seconds 2 }
Start-Process -FilePath $pythonwExe -ArgumentList ("`"" + $alvo + "`"") -WorkingDirectory $pasta -WindowStyle Hidden
Start-Sleep -Seconds 3

$novo = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -like "*dictate.py*" }
if ($novo) {
    Diz ("Ditado rodando de novo (pid " + ($novo | Select-Object -First 1).ProcessId + ").")
} else {
    Diz "AVISO: o processo nao apareceu. Abra o start-winh.cmd."
}

Diz ""
Diz "Teste agora: aperte Win+H, fale uma frase, espere o texto aparecer."
Diz "Aperte Win+H de novo, espere 40 segundos e repita - e esse segundo teste"
Diz "que falhava antes."
