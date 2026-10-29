# Third-party components in portable downloads

LawnLab's own code is MIT-licensed; see LICENSE. Dependency licenses remain
separate. The portable app dynamically loads its Python and Qt libraries from
`_internal`. Retain that directory and the notices when redistributing it.

| Component | License / upstream source |
| --- | --- |
| CPython 3.14 | PSF license and bundled component notices; [source](https://github.com/python/cpython/tree/3.14) |
| PySide6 Essentials / Shiboken6 | LGPL-3.0 or applicable upstream alternative; [PySide source](https://code.qt.io/cgit/pyside/pyside-setup.git/) |
| Qt 6 libraries | Applicable LGPL/GPL/commercial terms and individual component notices; [Qt source and releases](https://download.qt.io/official_releases/qt/) |
| pymem | MIT; [source](https://github.com/srounet/Pymem) |
| pefile | MIT; [source](https://github.com/erocarrera/pefile) |
| PyInstaller bootloader | GPL with its distribution exception; [source and license](https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt) |

The release ZIPs include the available installed-package license files, Python's
license, and the LGPL/GPL license texts under `third-party-licenses/`. Dependency
versions are recorded there. The LGPL-covered libraries can be replaced in the
portable folder with compatible builds; this project imposes no additional
restriction on modifying those libraries or reverse engineering for debugging
such modifications. Source is available through the upstream links above.

Microsoft runtime DLLs and Windows system components retain their own terms.
Their inclusion does not place them under LawnLab's MIT license.

Optional upstream mod/companion projects listed in LawnLab's catalog are not
included in these downloads. Plants vs. Zombies game executables, assets, audio
libraries and personal save data are also not included.
