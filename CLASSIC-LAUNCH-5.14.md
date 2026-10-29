# LawnLab 5.14 — Classic launch and bass.dll

Classic's bass.dll exists in its game folder. The packaged trainer inherited PyInstaller's SetDllDirectory search override into the legacy wrapper and extracted game. A nonempty DLL-directory override excludes the current game directory from ordinary DLL lookup, so the extracted executable could fail to load its audio library despite the file being present.

The game launcher now clears that override only while spawning the external game, then restores LawnLab's previous DLL directory even if spawning fails. Both existing Classic launch paths (space-free legacy argv and ShellExecute fallback) retain their game-folder working directory. No game DLL or executable is replaced or downloaded.

The separate-save root is still selected early, but launch success is reported only after Main Menu is reached and Classic has loaded bass.dll. Click through the title screen if the launcher remains Working. Dismiss any old bass.dll error and close that game before retrying. The trainer GUI need not remain open after a successful launch.

Reference: [PyInstaller external-program launch guidance](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#launching-external-programs-from-the-frozen-application).

Use the updated in-app launch button or existing save-aware desktop/game-folder shortcuts. Original EXEs still use the old shared save folder. User progress and note/resource backups are not modified by the DLL-search fix.
