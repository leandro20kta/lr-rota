# Rota Cinema Studio — render local na RTX (Windows / PowerShell)
# Requisitos: Blender 5.2 LTS instalado (https://www.blender.org/download/), Python 3.11+ com "pip install pillow".
# Uso (na pasta do repositório):  powershell -ExecutionPolicy Bypass -File studio\render_local.ps1 -Mode clip -W 3840 -H 2160 -Samples 256 -Dur 5 -Fps 30
param(
  [string]$Mode = "stills",      # stills | clip
  [int]$W = 1920, [int]$H = 1080,
  [int]$Samples = 128,
  [double]$Dur = 5, [int]$Fps = 30,
  [string]$Blender = ""           # caminho do blender.exe; vazio = procura automática
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Blender) {
  $cands = Get-ChildItem "C:\Program Files\Blender Foundation" -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | ForEach-Object { Join-Path $_.FullName "blender.exe" }
  $Blender = ($cands | Where-Object { Test-Path $_ } | Select-Object -First 1)
  if (-not $Blender) { throw "Blender não encontrado. Instale o Blender 5.2 LTS de blender.org ou passe -Blender 'C:\...\blender.exe'." }
}
Write-Host "Blender: $Blender"
python "$root\build_assets.py"
$env:W = "$W"; $env:H = "$H"; $env:SAMPLES = "$Samples"; $env:DUR = "$Dur"; $env:FPS = "$Fps"; $env:DEVICE = "GPU"
if ($Mode -eq "stills") { $env:STILL_P = "0.30,0.55,0.90"; $env:FRAMES = "" } else { $env:STILL_P = ""; $env:FRAMES = "" }
& $Blender -b -P "$root\render_blender.py"
python "$root\overlay_frames.py"
if ($Mode -eq "clip") {
  $ff = (Get-Command ffmpeg -ErrorAction SilentlyContinue).Source
  if (-not $ff) { Write-Host "ffmpeg não encontrado: os frames estão em studio\out\frames (f####.ov.png). Instale ffmpeg (winget install ffmpeg) para gerar o MP4."; exit 0 }
  & $ff -y -framerate $Fps -i "$root\out\frames\f%04d.ov.png" -c:v libx264 -pix_fmt yuv420p -crf 16 -preset slow "$root\out\cinema_${W}x${H}.mp4"
  Write-Host "MP4: $root\out\cinema_${W}x${H}.mp4"
}
