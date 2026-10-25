# Benchmark CPU vs GPU (OptiX/CUDA) — 3 frames 1280x720, 64 amostras. Escreve studio\out\bench.txt
param([string]$Blender = "")
$ErrorActionPreference = "Stop"; $root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Blender) { $Blender = (Get-ChildItem "C:\Program Files\Blender Foundation" -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | ForEach-Object { Join-Path $_.FullName "blender.exe" } | Where-Object { Test-Path $_ } | Select-Object -First 1) }
if (-not $Blender) { throw "Blender não encontrado (instale o 5.2 LTS de blender.org)." }
& $Blender --version | Select-Object -First 1
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv 2>$null
if (-not (Test-Path "$root\out\scene.json")) { python "$root\build_assets.py" }
$env:W="1280"; $env:H="720"; $env:SAMPLES="64"; $env:STILL_P="0.30,0.55,0.90"
$log = "$root\out\bench.txt"; "" | Out-File $log
foreach ($dev in "CPU","GPU") {
  $env:DEVICE = $dev; $t = Measure-Command { & $Blender -b -P "$root\render_blender.py" 2>&1 | Tee-Object -Variable outp | Out-Null }
  $per = ($outp | Select-String "render still_.* ([0-9.]+)s" | ForEach-Object { [double]$_.Matches[0].Groups[1].Value })
  $line = "$dev : total $([math]::Round($t.TotalSeconds,1)) s ; por frame: $($per -join ' / ') s"
  Write-Host $line; $line | Out-File $log -Append
}
Get-Content $log
