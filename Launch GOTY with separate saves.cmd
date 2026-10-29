@echo off
cd /d "%~dp0"
if exist "LawnLab.exe" (
 start "" "LawnLab.exe" --launch-edition goty
) else (
 start "" "%~dp0release\LawnLab\LawnLab.exe" --launch-edition goty
)
