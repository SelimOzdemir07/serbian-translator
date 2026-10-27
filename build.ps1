# Builds dist\SerbianTranslator.exe and puts a shortcut to it on the Desktop.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

& .venv\Scripts\python -m pytest -q
if ($LASTEXITCODE -ne 0) { Write-Error "Tests failed - not building." }

& .venv\Scripts\pyinstaller --noconfirm --onefile --windowed --name SerbianTranslator --add-data "ui;ui" app.py
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller failed." }

$exe = Join-Path $PSScriptRoot "dist\SerbianTranslator.exe"
$lnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "SerbianTranslator.lnk"
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
$shortcut.TargetPath = $exe
$shortcut.WorkingDirectory = Split-Path $exe
$shortcut.Save()
Write-Host "Built $exe and created $lnk"
