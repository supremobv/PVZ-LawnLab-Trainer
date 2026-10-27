$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}
& $python -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $python render_preview.py
if ($LASTEXITCODE -ne 0) { throw 'Asset rendering failed.' }
& $python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Interface checks failed.' }
& $python -m PyInstaller --noconfirm --distpath release --workpath build-release lawnlab-portable.spec
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
Copy-Item -LiteralPath README.md -Destination 'release\LawnLab\README.md' -Force
Write-Host 'Built release\LawnLab\LawnLab.exe. Keep the _internal folder beside the executable.'
