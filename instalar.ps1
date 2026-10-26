# Instala tudo o que a skill reels-estilo-jornal-windows precisa. Rodar uma vez, no PowerShell:
#   powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\reels-estilo-jornal-windows\instalar.ps1"
# Criado por Pâmella Santos · @pamellasantosp
$ErrorActionPreference = 'Stop'
$S = $PSScriptRoot
Set-Location $S

function Tem($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function AtualizarPath {
  $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}

if (-not (Tem winget)) { throw 'Precisa do winget (App Installer da Microsoft Store). Instale e rode de novo.' }

# 1. ffmpeg e Python 3.12
if (-not (Tem ffmpeg)) {
  Write-Host 'Instalando ffmpeg...'
  winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements --silent
}
if (-not (Tem py) -and -not (Tem python)) {
  Write-Host 'Instalando Python 3.12...'
  winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements --silent
}
AtualizarPath
if (-not (Tem ffmpeg)) { throw 'O ffmpeg foi instalado, mas o Windows ainda não o enxerga. Feche e abra o PowerShell e rode o instalador de novo.' }

# 2. Ambiente Python da skill (numpy + Playwright com Chromium)
if (-not (Test-Path "$S\.venv\Scripts\python.exe")) {
  Write-Host 'Criando o ambiente Python da skill...'
  if (Tem py) { py -3.12 -m venv "$S\.venv" } else { python -m venv "$S\.venv" }
}
& "$S\.venv\Scripts\python.exe" -m pip install -q --upgrade pip
& "$S\.venv\Scripts\python.exe" -m pip install -q numpy playwright
& "$S\.venv\Scripts\python.exe" -m playwright install chromium

# 3. Transcrição: whisper.cpp (versão pronta para Windows) + modelo large-v3-turbo
$W = "$S\ferramentas\whisper"
if (-not (Get-ChildItem $W -Recurse -Include whisper-cli.exe, main.exe -ErrorAction SilentlyContinue)) {
  Write-Host 'Baixando o whisper.cpp...'
  # nem toda versão publica o pacote do Windows: procura nas mais recentes a primeira que tenha
  $pacote = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'whisper-bin-win-cpu-arm64.zip' } else { 'whisper-bin-x64.zip' }
  $rels = Invoke-RestMethod 'https://api.github.com/repos/ggml-org/whisper.cpp/releases?per_page=20' -Headers @{ 'User-Agent' = 'reels-estilo-jornal' }
  $asset = $rels | Where-Object { -not $_.draft } | ForEach-Object { $_.assets } | Where-Object { $_.name -eq $pacote } | Select-Object -First 1
  if (-not $asset) { throw "Não achei $pacote nas versões recentes do whisper.cpp." }
  New-Item -ItemType Directory -Force $W | Out-Null
  Invoke-WebRequest $asset.browser_download_url -OutFile "$W\whisper.zip"
  Expand-Archive "$W\whisper.zip" -DestinationPath $W -Force
  Remove-Item "$W\whisper.zip"
}
New-Item -ItemType Directory -Force "$S\modelos" | Out-Null
if (-not (Test-Path "$S\modelos\ggml-large-v3-turbo.bin")) {
  Write-Host 'Baixando o modelo de transcrição (1,6 GB)...'
  $ProgressPreference = 'SilentlyContinue'   # sem isso o download fica muito lento no PowerShell
  Invoke-WebRequest 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin' -OutFile "$S\modelos\ggml-large-v3-turbo.bin"
}

Write-Host ''
Write-Host 'Pronto. A skill reels-estilo-jornal-windows está instalada.'
Write-Host 'Feche e abra o Claude Code para ele reconhecer a skill.'
