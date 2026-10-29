# LawnLab — Plants vs. Zombies Trainer

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Version](https://img.shields.io/badge/LawnLab-5.14-green)
![Platform](https://img.shields.io/badge/platform-Windows-blue)

<p align="center">
  <img src="assets/lawnlab.png" alt="LawnLab sunflower logo" width="112" />
</p>

<p align="center"><strong>A desktop toolkit for making the Plants vs. Zombies lawn your own.</strong></p>

LawnLab 5.14 includes **Lawn Studio** and **55 controls** for verified GOTY 1.2.0.1073 and Classic 1.0.0.1051. It adds awake/fast Stinky, the hidden Limbo page, an extended coin bank, named Endless best records and corrected Tree height. Shop restock now includes previously excluded owned/capped items, with purchase guards preserving structural limits and Tree height. Read the [5.6 guide and measured checks](CLASSIC-AND-PROFILE-5.6.md).

**5.14:** fixes the packaged launcher DLL-search inheritance that prevented Classic from loading its existing bass.dll. Launch success now waits for Main Menu and Classic audio-library loading. See [launcher notes](CLASSIC-LAUNCH-5.14.md).

**5.13:** adds Cattail without Lily Pad on clear land and pool cells, including Studio placement. It enables Direct upgrade planting and preserves occupied-cell and roof-support checks. See [the Cattail guide](CATTAIL-5.13.md).

**5.12:** repairs the scrolling deck’s Survival repick crash, keeps scrolling active when Studio is hidden, adds native grave cleanup, and adds a read-only in-app save/progress guide. See [the 5.12 guide](SURVIVAL-AND-SAVES-5.12.md).

**5.11:** fixes the seed-packet prerequisite check for direct upgrades and adds automatic Cob Cannon targeting, firing and shortened reloading. It also adds instantly armed new Potato Mines and ordinary-plant placement without Lily Pads / Flower Pots. Read [the usage and validation notes](UPGRADE-AND-COB-5.11.md).

**5.10:** note targets follow the connected edition, Classic note installation is verified, and per-edition Limbo launch preferences work without the trainer window. The edition launchers retain separate native saves and GOTY achievements. Read [the 5.10 guide](EDITION-TARGETS-AND-LIMBO-5.10.md).

**5.9.1:** dedicated Restore original Help note, Restore original credits note and Restore both original notes actions use verified pre-edit resources and retain custom drafts.

**Fixed in 5.9:** drag and hide the in-game seed-page bar while retaining mouse-wheel paging; full-height note previews; bounded resource writes with clear Windows permission errors and an administrator restart action. Read the [5.9 guide](OVERLAY-AND-NOTES-5.9.md).

**New in 5.8:** direct upgrade planting without prerequisite plants, reversible Almanac reveal, independent plant/zombie size percentages and corrected Classic wrapper launch quoting. See the [5.8 feature guide](UPGRADES-ALMANAC-SIZES-5.8.md).

**New in 5.7:** separate GOTY/Classic save launchers preserve GOTY achievements across edition switches; a scrollable 48-plant deck pages the in-game seed bank; independent Help/credits-note editors and a reversible resource-mod manager are in the new **Mods, notes & launch** tab. Read the [5.7 usage and compatibility guide](EXTENSIONS-AND-SAVES-5.7.md). Use the new edition launchers: original game shortcuts still use the legacy shared saves.

Studio provides plant placement, custom zombie spawning, formations, entity inspection/upgrades, wave and seed editors, projectile effects, stage selection, Zen Garden tools, save backups, profiles/hotkeys and a live dashboard. Read the [profile and garden guide](PROFILE-AND-GARDENS.md), [step-by-step Studio guide](LAWN-STUDIO-GUIDE.md) and [patch ownership and recovery](STABILITY.md). The legacy implementation is retained for historical reference.

**Developer and owner: Primo — [@supremobv](https://github.com/supremobv).** The earlier GitHub account, [@supremopkv](https://github.com/supremopkv), belongs to the **same developer**. References to either account describe the same project's author, not two separate developers or a third-party fork.

![LawnLab desktop interface](assets/preview.png)

## Lawn Studio — new in 5.0

Click **Open Lawn Studio** in the sidebar. Nine workspaces cover the requested feature areas. Memory editors select the exact GOTY or Classic backend; Classic has no native GOTY achievements, so that editor is unavailable there. Controls and hotkeys start off, persistent actions create backups, and save restoration requires PVZ closed.

![Lawn Studio workspace](assets/preview-studio.png)

Read **[LAWN-STUDIO.md](LAWN-STUDIO.md)** for tools, hotkeys, data locations and reset behavior. The suite has **221 passing offline tests**, plus live Classic gameplay and both-build native shop/profile checks. Coverage and visual limits are listed in **[CLASSIC-AND-PROFILE-5.6.md](CLASSIC-AND-PROFILE-5.6.md)**. Earlier gameplay reports remain historical.

Current checks: [Classic gameplay](validation/classic56-gameplay.json), [Classic shop/profile](validation/classic56-shop-profile.json), and [GOTY shop/profile](validation/goty56-shop-profile.json).

## Cheat Engine companion

Use **[GOTY CT](LawnLab-GOTY-1.2.0.1073.CT)** or **[Classic CT](LawnLab-Classic-1.0.0.1051.CT)** for all 55 main controls, parameters and read-only build-specific references. Both require the matching **5.14 LawnLab.exe** companion. Disconnect the GUI before starting the CT helper. See **[CHEAT-ENGINE.md](CHEAT-ENGINE.md)**, the **[GOTY catalog](LawnLab-addresses.json)** and **[Classic catalog](LawnLab-Classic-addresses.json)**. Builds regenerate and ship both tables/catalogs.

## Contents

- [Overview](#overview)
- [Requirements](#requirements)
- [Quick start from source](#quick-start-from-source)
- [Connecting to the game](#connecting-to-the-game)
- [Controls](#controls)
- [Session and reset behavior](#session-and-reset-behavior)
- [Building a portable Windows app](#building-a-portable-windows-app)
- [Tests and visual checks](#tests-and-visual-checks)
- [Compatibility and limitations](#compatibility-and-limitations)
- [Troubleshooting](#troubleshooting)
- [Project structure](#project-structure)
- [Contributing](#contributing)
- [Credits and license](#credits-and-license)

## Overview

- **55 controls** organized into sun/economy, plants, zombies, lawn/world, and level actions, plus an All controls view.
- Live text search across control names, descriptions, and categories.
- **Auto detect** checks `popcapgame1.exe` and `PlantsVsZombies.exe`; either can also be selected manually.
- Explicit connection, busy, and active-control indicators.
- Editors for sun, coins, plant and projectile types, lanes, firing delay, and game pace.
- Worker-thread execution keeps the interface responsive during engine operations.
- Failed toggles synchronize back to the state reported by the engine.
- Mutually exclusive modes avoid enabling conflicting sun, plant-health, and zombie-health settings together.
- Level-changing actions ask before they run.
- A separate legacy application remains available in `pvz_trainer.py`.

The trainer operates on the selected game's process memory. It does not install a kernel driver, change Windows security settings, or install modifications automatically. Session controls start off; an explicitly remembered Limbo preference is reapplied by the edition launcher.

## Requirements

| Component | Requirement |
| --- | --- |
| Operating system | Windows 10 or Windows 11, 64-bit |
| Python for source runs/builds | Python 3.10 or later; locally tested with Python 3.14.3 |
| Interface | PySide6 Essentials / Qt 6 |
| Memory access | pymem 1.14 or later, below 2.0 |
| Game | Fingerprinted x86 GOTY 1.2.0.1073 or Classic 1.0.0.1051; see CLASSIC-AND-PROFILE-5.6.md |
| Administrator rights | Not requested by default; game and trainer need compatible privilege levels |

A locally built portable application includes Python and Qt, so its users do not need a separate Python installation. **Compiled executables and local environments are excluded from the source repository.** Build the application using the instructions below.

## Quick start from source

Open PowerShell in the directory where you want the project:

```powershell
git clone https://github.com/supremobv/PVZ-LawnLab-Trainer.git
cd PVZ-LawnLab-Trainer
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe lawnlab.py
```

Once dependencies are installed, **Launch LawnLab.cmd** opens the app. The launcher prefers `release\LawnLab\LawnLab.exe` when a portable build exists; otherwise it uses `.venv\Scripts\pythonw.exe` to run the source without a console.

Virtual-environment activation is optional: the commands above invoke its interpreter directly.

### Legacy application

`pvz_trainer.py` is the original Tkinter application and has been retained unchanged. To open it using the same environment:

```powershell
.\.venv\Scripts\python.exe pvz_trainer.py
```

Its original documentation is preserved as `README-legacy.md`. Descriptions and compatibility claims in that archived document refer to the older implementation; use this README for the current application's verified behavior.

## Connecting to the game

1. Open Plants vs. Zombies.
2. Launch LawnLab.
3. Leave **Auto detect** selected, or choose the exact executable name manually.
4. Click **Connect to game**.
5. Check the status message for the executable that was attached.
6. Open a level before using controls that require a lawn, plants, or zombies.
7. Enable the controls you want. For a control with an editor, choose its value **before** enabling it.

Auto detect examines `popcapgame1.exe` and `PlantsVsZombies.exe`, ignoring case, and releases temporary inspection handles. Classic's launcher wrapper is skipped in favor of the actual runtime. Close other supported games if detection finds multiple candidates.

The interface starts disconnected. The current backend checks the executable fingerprint before allowing controls. A process name alone does not establish compatibility.

## Saves, achievements and launchers

**Use the same launch method consistently.** Opening an original game EXE directly and opening it through LawnLab can load different progress. The trainer window does not need to remain open after a successful edition launch.

| Launch method | Save directory |
| --- | --- |
| Original EXE / original launcher | `%PROGRAMDATA%\PopCap Games\PlantsVsZombies\userdata` |
| LawnLab GOTY launcher | `%PROGRAMDATA%\PopCap Games\PlantsVsZomGOTY\userdata` |
| LawnLab Classic launcher | `%PROGRAMDATA%\PopCap Games\PlantsVsZomCLSC\userdata` |

Classic can discard GOTY-only achievements when both editions write the legacy shared save. Separate saves prevent this conflict. In **Mods, notes & launch**, prepare/back up the edition saves, choose the original game-folder executable for each edition, and use **Launch GOTY/Classic with separate saves** thereafter. Click through the title screen: launch success waits for Main Menu and Classic audio-library loading. The helper then exits.

Source users can also run these commands after configuring executable paths in LawnLab:

```powershell
.\.venv\Scripts\python.exe lawnlab.py --launch-edition goty
.\.venv\Scripts\python.exe lawnlab.py --launch-edition classic
```

The accompanying edition `.cmd` launchers require a local portable build; use the Python commands above for source runs. **Save progress guide** in the sidebar shows the active root and read-only Adventure progress comparisons. Back up before importing/restoring saves; restoration requires both games closed. Progress is not automatically merged between the folders.

## Studio, scrolling cards and customization

| Workspace | Tools |
| --- | --- |
| Lawn builder | Named plants, cells/rectangles, supported stacking, visual lawn painting, saved formations and custom zombie spawning |
| Inspect & edit | Select one live plant/zombie instance; inspect and edit supported health, timing and status fields with bounded inputs |
| Zombie waves | Named groups with zombie types, lanes, quantities and spawn timing |
| Seeds & shots | Existing seed-packet edits, projectile effects and a paged deck of up to 48 plant types |
| Stages & Zen Garden | Supported stage launches, saved garden collection, bulk care, growth, compatible plant additions and movement |
| Player data | Selected progress fields, Endless records, ownership and GOTY achievement flags |
| Save backups / Settings | Backup/restore, trainer profiles and configurable shortcuts |
| Mods, notes & launch | Separate-save launchers, independent Help/credits invitation-note editors, original-resource restoration and compatible resource packs |

The scrolling deck keeps at most ten native slots visible. Scroll the mouse wheel **over the seed bank**, use the page buttons, or use configured shortcuts. Drag the page bar to reposition it, or hide it while retaining wheel paging. Finish/cancel a held seed before changing pages. Hidden-card recharge follows the game clock. Paging stops safely on lawn replacement or Survival repick: start the next battle and restart the deck. Closing Studio hides it; exiting the main controller stops scrolling.

The Help and credits **invitation-note** editors are separate; the actual credits roll is unchanged. Close both games, select the correct edition and folder, preview, then apply. Original-resource backups allow restoring either note or both while retaining custom drafts. Protected game folders may require the explicit administrator restart action. Resource edits persist until restored.

Resource imports require compatible packs with author/license metadata. Arbitrary engine mods are not interchangeable with resource packs for stock executables. The credited upstream catalog distinguishes optional companions from standalone engines; those projects are not bundled. See [extensions](EXTENSIONS-AND-SAVES-5.7.md), [overlay and notes](OVERLAY-AND-NOTES-5.9.md), and [edition targeting](EDITION-TARGETS-AND-LIMBO-5.10.md).

Local logs, settings, backup journals and resource-library files live beneath `%LOCALAPPDATA%\LawnLab`, with Qt interface preferences stored separately by Qt. Personal game saves and runtime state are excluded from this repository.

## Controls

Select a category in the sidebar or use search. Controls remain disabled until the trainer connects. Active controls are counted in the footer.

### Sun & economy

| Control | Behavior |
| --- | --- |
| Infinite sunshine | Maintain 9,999 sun |
| Free planting | Plant without spending sun |
| Auto collect | Collect falling sunshine automatically |
| Shop restock | Repeat sold-out supplies, daily Marigolds and most owned tools while preserving structural limits |
| Auto collect coins | Collect silver coins, gold coins and diamonds during battle; excludes gifts/rewards |
| Bigger sun pickups | Add 1,000 sun per pickup |
| Planting bonus | Add 2,000 sun when planting |
| Sun limit | Lock sun to a selected value from 0 to 9,999 |
| Uncap sunshine | Remove the original sun ceiling; the custom lock editor still retains its own 9,999 limit |
| Coin balance | 0–99,999,999 stored units (×$10); oversized values enable Extended coin bank |
| Extended coin bank | Raise the native transaction ceiling for this session |
| Snail awake & fast | Keep owned Stinky awake with the native chocolate-speed behavior |
| Limbo hidden page | Reveal the hidden Minigames page while enabled |

Infinite sunshine and Sun limit cannot stay enabled together.

### Plants

| Control | Behavior |
| --- | --- |
| Sunflower drops | Choose normal sun, silver coins, gold coins or diamonds from future Sunflower/Twin Sunflower production |
| Instant recharge | Remove seed-packet recharge time |
| Direct upgrade planting | Place purple upgrades such as Winter Melon without the prerequisite plant; normal cost and other placement checks remain |
| Cattail without Lily Pad | Enables direct upgrades and permits Cattail on clear land/pool cells; roof support remains separate |
| No Lily Pad / Flower Pot needed | Bypass ordinary-plant supports on pool water and roofs; special plant restrictions remain |
| Instant Potato Mines | Newly planted mines start armed; existing mines retain their arming progress |
| Automatic Cob Cannons | Automatically target hostile zombies and fire, shortening reloads while preserving launch animations |
| Plant size / Zombie size | Scale animations 25–300%; collision and damage do not scale |
| Plant anywhere | Relax placement restrictions |
| Invincible plants | Prevent plant damage |
| Plant changer | Select an alternate plant ID |
| Rapid fire | Fire supported shooters every 5 ticks; about 20 shots/second at normal pace |
| Firing delay | Configure the action interval from 1 to 255 ticks (maximum 2.55 seconds at normal pace); animation limits still apply |
| Projectile changer | Select a projectile type, IDs 0–12 |
| Zombotany protection | Protect plants against Zombotany projectiles |

Invincible plants and Fragile plants are mutually exclusive.

### Zombies

| Control | Behavior |
| --- | --- |
| One-hit knockout | Apply lethal body damage on the first positive hit, including helmet/shield zombies |
| Freeze the horde | Pause movement |
| Pause spawning | Stop additional spawning |
| Invincible zombies | Prevent zombie death |
| Move existing zombies | Move eligible live zombies immediately to a compatible row; preserves horizontal position |
| Choose a lane | Move eligible current zombies once and route future spawns to the selected valid row |
| Zombie preview | Show all zombie types in the level preview |

One-hit knockout and Invincible zombies cannot stay enabled together.

### Lawn & world

| Control | Behavior |
| --- | --- |
| Play in background | Keep the game running when another window has focus |
| Clear the fog | Reveal fog-covered areas |
| See inside vases | Reveal Vasebreaker contents |
| Reveal Almanac entries | View locked plant/zombie entries without changing saved discovery progress |
| Daytime mushrooms | Keep mushrooms awake during daytime |
| Always butter | Make Kernel-pult throw butter |
| No craters | Prevent Doom-shroom craters |
| No ice trails | Prevent Zomboni ice trails |
| Quiet jack-in-the-box | Prevent jack-in-the-box explosions |
| Faster conveyor | Speed up seed delivery |
| Keep the shovel | Keep the shovel selected after digging |
| Game pace | Apply 0.2×, 0.5×, 1×, 2×, 5×, or 10× speed |

### Level actions

| Control | Behavior |
| --- | --- |
| Restore lawn mowers | Restore the lawn's mowers |
| Clear the horde | Remove zombies from the current lawn |
| Spawn the wave | Advance the next Adventure/Survival wave and confirm its index increases; resume the game first |
| Clear all plants | Remove plants from the lawn |
| Remove all graves | Native cleanup of current gravestones; preserves vases, craters and ladders |
| Finish this level | Complete the current level |
| Fragile plants | Make plants die instantly when damaged |

Actions that clear plants/zombies, spawn waves, or finish a level ask for confirmation. These actions are not undone by Reset all.

## Session and reset behavior

- **Reset all** restores owned control patches, the original frame duration and applicable preview settings through the verified runtime.
- Shared instruction patches restore only after the final owner releases them. Failed restoration retains the ownership journal for recovery.
- **Disconnect** attempts a reset before releasing the process handle.
- Closing the **main LawnLab window** while connected attempts a reset. Wait for any in-flight operation to finish.
- Closing **Lawn Studio** only hides it. Tools and seed scrolling continue while the main controller remains connected; use Stop/restore, Reset all or Disconnect to stop them.
- When the game exits, LawnLab clears its session and requires a new connection.
- Changed balances, completed levels, removed entities, and other one-time gameplay changes are not reversed by reset.

Errors are surfaced in the status area and local control log. Failed writes are rolled back; if rollback itself fails, restart PVZ as instructed. Reset cannot repair arbitrary memory damage from an old trainer or another editor.

## Building a portable Windows app

Run this from the repository directory:

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

The execution-policy option applies to that PowerShell invocation; the build does not permanently change Windows execution policy.

The build script:

1. Creates `.venv` if it does not exist.
2. Installs `requirements-dev.txt`.
3. Renders interface previews and logo/icon assets.
4. Generates the Classic backend, both CT tables and address catalogs.
5. Runs offline tests and stops if they fail.
6. Packages the app with `lawnlab-portable.spec`.
7. Copies the README, MIT license, guides, CT tables, catalogs, validation reports and assets into the output folder.

Output:

```text
release/
└── LawnLab/
    ├── LawnLab.exe
    ├── README.md
    └── _internal/
```

Distribute the **whole LawnLab folder**, keeping `_internal` next to `LawnLab.exe`. Copying the executable by itself is insufficient. The build has no UPX packing and does not request elevation on application startup.

The specification bundles the compatible VC runtime shipped by Qt. It excludes an unrelated `icuuc.dll` that some development-tool PATHs can contribute: Qt uses the Windows ICU API, while other ICU builds can export incompatible, version-suffixed symbols. This only affects the application bundle; system DLLs are not replaced.

## Tests and visual checks

Install development dependencies for Capstone/Unicorn instruction-level regression tests. The suite runs offline without a game installation.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe render_preview.py
```

The original **eight offline tests** cover:

- Fallback from `popcapgame1.exe` to `PlantsVsZombies.exe`.
- Honoring an explicitly selected executable.
- Closing a handle after failed module lookup.
- Detecting a process without opening game memory.
- Offline controls, category navigation, search, and empty results.
- Rolling back a toggle when the engine rejects it.
- Resolving conflicting modes and covering the legacy reset gap.
- Restoring game speed during reset.

Process calls are mocked in connection tests, and interface tests use a fake engine. **These tests do not modify a running game or validate memory offsets.**

The expanded suite covers bounded entity edits, stale-lawn checks, seed/wave editors, profile/hotkey validation, checksum-based backup recovery, native-call rollback/timeout handling, patch ownership and randomized control combinations. Current test counts and live checks are documented in [STABILITY.md](STABILITY.md); Studio gameplay limits are documented in [LAWN-STUDIO.md](LAWN-STUDIO.md).

`render_preview.py` renders the actual Qt interface using the offscreen platform and writes:

- `assets/preview.png`
- `assets/preview-plants.png`
- `assets/lawnlab.png`
- `assets/lawnlab.ico`

The editable logo source is `assets/lawnlab.svg`.

![Plants category](assets/preview-plants.png)

## Compatibility and limitations

LawnLab 5.14 requires one of the two fingerprints documented in [the compatibility guide](CLASSIC-AND-PROFILE-5.6.md). It uses separate verified version maps. Other executable builds are refused. Native GOTY achievements do not exist in Classic.

An executable name alone is not a compatibility check. Different releases, language editions or modifications need separate verification. Scene-specific features still require the appropriate plant, zombie or stage even after connection.

Additional limitations:

- The game-memory implementation is intended for 32-bit PVZ; a 64-bit trainer package does not make it compatible with a different 64-bit game engine.
- Several features require an active level rather than the main menu.
- The lane selector supports six rows where present and moves eligible existing zombies immediately. Boss and incompatible aquatic/land/special-state combinations retain their original lanes.
- Busy operations run outside the GUI thread and serialize with Studio. The interface waits rather than claiming it has cancelled an in-flight game-memory operation.
- This repository does not include the game, its installer, game saves, or third-party trainer drivers.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Game not found | Open the game first, use Auto detect, or select the exact process shown in Task Manager |
| Access denied | Check the game and trainer privilege levels; do not disable Windows security to work around an error |
| Controls are disabled | Connect to the game first; controls also pause while an operation is busy |
| A toggle switches back off | The engine rejected it; verify an active level and a compatible game build |
| A value editor is disabled | Turn its control off, change the value, then enable it again |
| Reset could not finish | Follow the displayed error. Retry recoverable conflicts; restart PVZ if rollback or a native call failed. |
| Missing DLL after copying the app | Copy the whole portable folder, including `_internal` |
| Classic says “Can't find bass.dll” | Use 5.14 or later, select the original game-folder EXE and keep its existing bass.dll beside it; see [launcher guide](CLASSIC-LAUNCH-5.14.md) |
| Launcher stays Working at the title screen | Click through to Main Menu; launch confirmation waits for it |
| Adventure progress differs between launches | Original EXEs use legacy shared saves; edition launchers use separate saves. Use the same launch method consistently |
| Scrolling stops after Survival flags | Choose cards and begin the next battle, then restart the scrolling deck |
| QtCore DLL import failure | Rebuild using `build.ps1` and the checked-in specification, rather than a generic packager command |
| Python package import error | Install requirements using `.venv\Scripts\python.exe`, not an unrelated Python installation |
| Window displays stale connection state | The game-exit checker runs periodically; reconnect after restarting the game |

To report a bug, include your Windows version, Python version (for source runs), exact game version/language, executable name, affected control, and steps to reproduce. Do not include personal game saves or sensitive files unless needed and intentionally shared.

## Project structure

```text
PVZ-LawnLab-Trainer/
├── lawnlab.py                 # Qt interface, controls, and session handling
├── trainer_engine.py          # Historical routines + connection lookup
├── verified_engine.py         # Current exact-build control runtime
├── verified_patches.py        # Expected/replacement instruction records
├── patch_manager.py           # Ownership, conflicts and transactional restoration
├── pvz_trainer.py             # Untouched legacy Tkinter application
├── Launch LawnLab.cmd         # Portable-build/source launcher
├── build.ps1                  # Dependency, test, asset, and packaging workflow
├── lawnlab-portable.spec      # PyInstaller bundle configuration
├── render_preview.py          # Offline previews and icon generation
├── requirements.txt           # Runtime dependencies
├── requirements-dev.txt       # Runtime + packaging dependencies
├── assets/                    # Original logo, Windows icon, and UI previews
├── tests/
│   ├── test_connection.py     # Mocked process selection and cleanup
│   └── test_interface.py      # Qt interaction tests with a fake engine
├── README-legacy.md           # Archived original documentation
└── LICENSE
```

`.venv`, caches, build directories, generated portable folders, and logs are ignored by Git. Screenshots and logo assets are included so the README renders on GitHub.

## Contributing

1. Open an issue describing the problem or proposed improvement.
2. Keep interface changes separate from game-build/offset changes where practical.
3. Run the offline tests before submitting a pull request.
4. For memory-patch changes, document the exact game build and the validation performed. Passing mocked tests alone is insufficient evidence of compatibility.

## Credits and license

**PVZ Trainer / LawnLab is developed and owned by Primo.**

- Current GitHub account: [supremobv](https://github.com/supremobv)
- Earlier GitHub account: [supremopkv](https://github.com/supremopkv)
- Both accounts belong to the same developer.

The original project's acknowledgments are retained:

- [PvZ Toolkit](https://github.com/lmintlcx/pvztoolkit), by [lmintlcx](https://github.com/lmintlcx), was referenced for memory addresses, game mechanics, and implementation ideas.
- [PvZA11y](https://github.com/CG8516/PvZA11y), by CG8516 and contributors, is listed as an optional MIT-licensed accessibility companion. It runs separately and is not bundled.
- [Archipelago Randomizer](https://github.com/vicr123/PvZ-Stable-Decompile-AP) and [PvZ-Portable LuaJIT](https://github.com/hello-lisai/PvZ-Portable-LuaJIT) are credited catalog references for standalone projects, not resource packs for the supported stock games.
- Thanks to the Plants vs. Zombies and Cheat Engine communities.

Project code is provided under the [MIT License](LICENSE), consistent with the license stated in the original documentation. Third-party dependencies retain their respective licenses. Plants vs. Zombies and its associated names and assets belong to their respective owners; this is an independent community project.
