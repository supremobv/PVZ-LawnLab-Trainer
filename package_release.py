"""Create and verify edition-specific portable ZIPs from a built LawnLab folder."""
import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION = '5.14'
EDITIONS = {
    'Classic': ('1.0.0.1051', 'LawnLab-Classic-1.0.0.1051.CT', 'LawnLab-Classic-addresses.json', 'PlantsVsZomCLSC'),
    'GOTY': ('1.2.0.1073', 'LawnLab-GOTY-1.2.0.1073.CT', 'LawnLab-addresses.json', 'PlantsVsZomGOTY'),
}


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def package(bundle, output, notices):
    exe = bundle / 'LawnLab.exe'
    if not exe.is_file() or not (bundle / '_internal/python314.dll').is_file():
        raise RuntimeError('Build the complete portable app first; executable or runtime is missing.')
    if not notices.is_dir() or not list(notices.rglob('*')):
        raise RuntimeError('Supply a directory containing dependency licenses and notices.')
    output.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    docs = [ROOT / name for name in tracked if name and (name.endswith('.md') or name == 'LICENSE' or name.startswith('assets/'))]
    runtime = [p for p in (bundle / '_internal').rglob('*') if p.is_file()]
    source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    results = []
    for edition, (game_version, table, catalog, save_folder) in EDITIONS.items():
        name = f'LawnLab-{VERSION}-{edition}-Windows-x64'
        target = output / f'{name}.zip'
        files = {'LawnLab.exe': exe}
        files.update({p.relative_to(bundle).as_posix(): p for p in runtime})
        files.update({p.relative_to(ROOT).as_posix(): p for p in docs})
        files.update({p.relative_to(notices).as_posix(): p for p in notices.rglob('*') if p.is_file()})
        for filename in (table, catalog, f'Launch {edition} with separate saves.cmd'):
            files[filename] = ROOT / filename
        guide = f'''# LawnLab {VERSION} — {edition} quick start

For the supported English x86 Plants vs. Zombies {edition} {game_version} build.
The trainer itself requires 64-bit Windows 10/11. Python and Cheat Engine are
not required for the main app. This download includes no game or game saves.

1. Extract this entire ZIP to a writable folder before running anything.
2. Keep `_internal` beside `LawnLab.exe`; do not copy the EXE alone.
3. Open `LawnLab.exe`. Go to Lawn Studio > Mods, notes & launch.
4. Choose the original {edition} game-folder EXE, prepare/back up the separate
   edition saves, then select Launch {edition} with separate saves.
5. Click through the game title screen to Main Menu. The helper exits after
   launch succeeds; the trainer window need not remain open for save isolation.
6. Connect LawnLab and start a disposable lawn before experimenting.

After configuring the path, `Launch {edition} with separate saves.cmd` provides
the same save-aware game launch. For ordinary trainer controls open LawnLab.exe.

Separate saves: `%PROGRAMDATA%\\PopCap Games\\{save_folder}\\userdata`.
Launching an original game EXE directly uses the old shared save directory and
can show different progress. Do not mix launch methods unintentionally.
Read README.md and the in-app Save progress guide before restoring/importing saves.

Optional Cheat Engine: open `{table}` and follow CHEAT-ENGINE.md. Select this
package's LawnLab.exe as the companion when asked. Disconnect the GUI before
starting the CT helper. Attach to the actual game process, not a launcher wrapper.

This edition download includes a focused CT/catalog, but LawnLab.exe still
contains both verified edition backends. Other releases/languages/modded game
executables need separate compatibility verification.

Project: https://github.com/supremobv/PVZ-LawnLab-Trainer
Developer: Primo (@supremobv / @supremopkv). Project code: MIT; dependency licenses
and source links are in THIRD-PARTY-NOTICES.md and third-party-licenses/.
'''
        manifest = dict(version=VERSION, edition=edition, game_version=game_version,
                        source_commit=source_commit, executable_sha256=sha256(exe),
                        table_sha256=sha256(ROOT / table), catalog_sha256=sha256(ROOT / catalog),
                        includes_game=False, includes_personal_saves=False)
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for relative, path in sorted(files.items()):
                archive.write(path, f'{name}/{relative}')
            archive.writestr(f'{name}/START-HERE.md', guide)
            archive.writestr(f'{name}/PACKAGE-INFO.json', json.dumps(manifest, indent=2) + '\n')
        with zipfile.ZipFile(target) as archive:
            broken = archive.testzip()
            if broken:
                raise RuntimeError(f'ZIP integrity failed: {broken}')
            entries = archive.namelist()
            assert f'{name}/{table}' in entries and f'{name}/LICENSE' in entries
            assert not any('/userdata/' in p or '/research/' in p or 'preview-note-text' in p for p in entries)
            assert hashlib.sha256(archive.read(f'{name}/LawnLab.exe')).hexdigest() == manifest['executable_sha256']
            assert len([p for p in entries if p.endswith('.CT')]) == 1
        results.append(dict(file=target.name, size=target.stat().st_size, sha256=sha256(target), entries=len(entries)))
    (output / 'SHA256SUMS.txt').write_text(''.join(f"{r['sha256']}  {r['file']}\n" for r in results), encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=ROOT / 'release/LawnLab')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/github-v5.14')
    parser.add_argument('--notices', type=Path, required=True)
    args = parser.parse_args()
    package(args.bundle.resolve(), args.output.resolve(), args.notices.resolve())
