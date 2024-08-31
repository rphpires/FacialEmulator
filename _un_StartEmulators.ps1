# Defina o caminho para o arquivo .ps1
$arquivo = "initialize.txt"

$currentDir = Get-Location
# Verifica se a pasta "running" existe, se não, a cria
$runningPath = "running"
if (-not (Test-Path $runningPath)) {
    New-Item -Path $runningPath -ItemType Directory
}

# Lê cada linha do arquivo .ps1
Get-Content $arquivo | ForEach-Object {
    $dados = $_ -split ";"
    $ip = $dados[0].Trim()
    $port = $dados[1].Trim()
    $nome = $dados[2].Trim()

    # Cria uma pasta com o nome do item <port> dentro da pasta "running"
    $pastaRunning = Join-Path $runningPath $port
    if (-not (Test-Path $pastaRunning)) {
        New-Item -Path $pastaRunning -ItemType Directory
    }

    # Copia o arquivo facial_emulator.exe para dentro da pasta <port> e o renomeia
    $executavel = "facial_emulator.exe"
    $novoNome = "facial_emulator_$port.exe"
    $destino = Join-Path $pastaRunning $novoNome
    Copy-Item $executavel -Destination $destino

    # Cria o arquivo .bat para iniciar o executável
    $scriptPath = Join-Path $pastaRunning "start_$port.bat"
    $scriptName = "start_$port.bat"
    @"
@echo off
call $novoNome "$ip" "$port" "$nome"
"@ | Set-Content -Path $scriptPath -Encoding ASCII

    Set-Location $pastaRunning
    # Inicia o arquivo .bat em segundo plano
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c start $scriptName && exit" -WindowStyle Hidden

    Set-Location $currentDir
}

# Fecha o PowerShell sem esperar a conclusão dos processos iniciados
exit
