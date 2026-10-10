# Builds collector\dist\EdgeHealthColetor.exe (single file, no console, no Python needed).
# Run from any folder:  powershell -ExecutionPolicy Bypass -File collector\windows\build.ps1
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$collector = Split-Path $here -Parent
$venv = Join-Path $collector '.venv-build'
if (-not (Test-Path "$venv\Scripts\python.exe")) { python -m venv $venv }
& "$venv\Scripts\python.exe" -m pip install -q -r "$here\requirements-build.txt"
& "$venv\Scripts\python.exe" "$here\make_icon.py" "$collector\build\icone.ico"
& "$venv\Scripts\pyinstaller.exe" --noconfirm --clean --onefile --windowed --name EdgeHealthColetor `
    --icon "$collector\build\icone.ico" --add-data "$collector\build\icone.ico;." --paths $collector --collect-data certifi `
    --distpath "$collector\dist" --workpath "$collector\build" --specpath "$collector\build" `
    "$here\edgehealth_windows.py"
$exe = Join-Path $collector 'dist\EdgeHealthColetor.exe'
$hash = (Get-FileHash $exe -Algorithm SHA256).Hash
"$hash  EdgeHealthColetor.exe" | Set-Content -Encoding ascii (Join-Path $collector 'dist\EdgeHealthColetor.exe.sha256')
Write-Host "Pronto: $exe ($([math]::Round((Get-Item $exe).Length / 1MB, 1)) MB)  SHA-256 $hash"
