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
& $python generate_classic.py
if ($LASTEXITCODE -ne 0) { throw 'Classic backend generation failed.' }
& $python generate_ct.py
if ($LASTEXITCODE -ne 0) { throw 'Cheat table generation failed.' }
& $python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Interface checks failed.' }
& $python -m PyInstaller --noconfirm --distpath build-output --workpath build-release lawnlab-portable.spec
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
if (Get-Process LawnLab -ErrorAction SilentlyContinue) { throw 'Close LawnLab before replacing its portable files.' }
New-Item -ItemType Directory -Path 'release\LawnLab' -Force | Out-Null
Copy-Item -Path 'build-output\LawnLab\*' -Destination 'release\LawnLab' -Recurse -Force
Copy-Item -LiteralPath LICENSE,README.md,'CLASSIC-LAUNCH-5.14.md','CATTAIL-5.13.md','SURVIVAL-AND-SAVES-5.12.md','UPGRADE-AND-COB-5.11.md','EDITION-TARGETS-AND-LIMBO-5.10.md','OVERLAY-AND-NOTES-5.9.md','UPGRADES-ALMANAC-SIZES-5.8.md','EXTENSIONS-AND-SAVES-5.7.md','Launch GOTY with separate saves.cmd','Launch Classic with separate saves.cmd','LAWN-STUDIO.md','LAWN-STUDIO-GUIDE.md','PROFILE-AND-GARDENS.md','CLASSIC-AND-PROFILE-5.6.md','STABILITY.md','CHEAT-ENGINE.md','GAMEPLAY-FIXES-5.2.md','LawnLab-GOTY-1.2.0.1073.CT','LawnLab-Classic-1.0.0.1051.CT','LawnLab-addresses.json','LawnLab-Classic-addresses.json' -Destination 'release\LawnLab' -Force
Copy-Item -LiteralPath validation -Destination 'release\LawnLab' -Recurse -Force
New-Item -ItemType Directory -Path 'release\LawnLab\assets' -Force | Out-Null
Copy-Item -Path 'assets\*' -Destination 'release\LawnLab\assets' -Force
Write-Host 'Built release\LawnLab\LawnLab.exe. Keep the _internal folder beside the executable.'
