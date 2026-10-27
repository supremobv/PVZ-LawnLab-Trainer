# PyInstaller specification for a portable Windows folder.
from pathlib import Path

root = Path(SPECPATH)
qt = root / '.venv' / 'Lib' / 'site-packages' / 'PySide6'
a = Analysis(
    [str(root / 'lawnlab.py')], pathex=[str(root)],
    binaries=[(str(qt / name), '.') for name in ('VCRUNTIME140.dll', 'VCRUNTIME140_1.dll')],
    datas=[(str(root / 'assets' / 'lawnlab.svg'), 'assets')],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['tkinter'], noarchive=False,
)
# Qt links to Windows' unversioned ICU API. An unrelated Poppler installation
# on the build host PATH exports suffixed ICU symbols and must not be bundled.
a.binaries = [item for item in a.binaries if Path(item[0]).name.lower() != 'icuuc.dll']
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='LawnLab',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, icon=str(root / 'assets' / 'lawnlab.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='LawnLab')
