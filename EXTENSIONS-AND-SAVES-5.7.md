# LawnLab 5.7 — saves, scrolling seeds, notes and mods

## Keep GOTY achievements when switching editions

Classic and GOTY previously wrote to the same PopCap userdata folder. Classic's profile format lacks GOTY's achievement fields and can remove them when saving. LawnLab now gives each verified edition its own native save directory:

| Edition | Save directory |
| --- | --- |
| GOTY | `C:\ProgramData\PopCap Games\PlantsVsZomGOTY\userdata` |
| Classic | `C:\ProgramData\PopCap Games\PlantsVsZomCLSC\userdata` |

Use **LawnLab GOTY — separate saves** or **LawnLab Classic — separate saves** on the desktop, the included CMD launchers, or Studio → **Mods, notes & launch**. Close both games before launching. Click through the game's title screen if the launcher is waiting. Each edition keeps its own subsequent progress and player list. Preparation backs up existing saves and does not overwrite an existing isolated collection.

**Original game shortcuts still use the old shared folder.** Connecting LawnLab at Main Menu redirects that running game to its isolated folder; connecting after starting a battle from an original shortcut is refused until you return to Main Menu. Reset all does not switch the running game's save folder back. The launcher changes the game's in-memory save-root string, not its executable file; no background service remains running.

The user's 20 earned GOTY achievements were restored. Native disk verification and reload passed, including GOTY → Classic save → GOTY restart. Achievement writes now verify the actual saved interleaved earned/shown bytes. A failed save is reported and rolled back. Classic has no native GOTY achievement editor.

## Scroll the in-game seed bank

1. Open a normal Adventure or Survival battle. Use windowed or borderless mode.
2. Connect LawnLab; open Studio → **Seeds & shots** → **Scrollable in-game seed bank**.
3. Tick named plants, or choose **Select all 48**. Drag entries to change their order.
4. Click **Start scrolling deck**. Move the mouse over PVZ's seed cards and scroll the wheel, click the overlay's arrows, or use Studio's Previous/Next buttons.
5. Place or cancel a held plant before turning the page. Click **Stop / restore cards** to restore the original deck.

PVZ retains its existing 1–10 physical slots. Pages expose up to 48 different plants without writing past that native allocation. Hidden cards retain their recharge progress using the game clock, so pausing PVZ also pauses cooldowns. Empty spaces on the final page are disabled. This does not unlock more physical slots, change plants already placed, or allow duplicate entries in the scrolling deck.

Conveyor/special Adventure levels and other special modes are excluded. Manual seed-slot edits are blocked while paging is active. Reset all, disconnect and lawn changes stop paging. If another tool changes the bank, LawnLab abandons restoration instead of overwriting unknown data; restart the lawn if needed. The overlay needs a visible game window and may require adjustment with unusual display scaling or exclusive fullscreen.

## Independent Help and credits invitation notes

Studio → **Mods, notes & launch** contains separate text boxes for the Help note and the zombie invitation shown before the credit roll. Choose the target edition and game folder, enter text and line breaks, pick a font, then Preview. Close **both** PVZ games before Apply; restart the selected edition afterward.

These handwritten notes are image masks, not editable LawnStrings entries. LawnLab renders a fitted mask over the original paper background. Text that cannot fit is refused. This changes the invitation note only; the original developer credit roll remains intact. Restore an applied note through the active resource edits list. Applying the same resource again requires restoring its current edit first.

## Resource mods with author credits

The same tab imports compatible resource ZIPs or a loose resource folder. Supply the original author, source URL, license identifier and license text. Credit alone is not redistribution permission: retain the author's license and obey its terms.

Resource packs accept validated images, sounds, music and properties under those directories. Executables, DLLs and scripts are not accepted as resource replacements. Compatibility means the exact supported stock GOTY/Classic build and matching resource paths; a standalone engine or executable mod is a different product.

For a ZIP, include `lawnlab-mod.json`, `LICENSE.txt`, optional `CREDITS.txt`, and files under `resources/`. Example manifest:

```json
{
  "version": 1,
  "name": "My lawn artwork",
  "author": "Original artist",
  "source": "https://example.com/original-project",
  "license": "MIT",
  "description": "A compatible replacement image",
  "editions": ["goty", "classic"],
  "files": ["images/MyReplacement.png"]
}
```

Use actual existing compatible resource paths. Import validates traversal, file sizes, images and XML resource paths. Applying requires both games closed, backs up original data, and records installed hashes. Conflicting replacements are refused. Restore preserves unexpected external changes and reports the conflict instead of erasing them.

GOTY uses loose resource backups. Classic loads bundled assets before loose overrides, so LawnLab transactionally rewrites `main.pak` and backs up the whole original archive. Multiple disjoint Classic edits can layer; **restore the newest Classic layer first**. The archive roundtrip preserves all original entry names, order and timestamps. Backups and installed records live under `%LOCALAPPDATA%\LawnLab\mods`.

## Reviewed open-source projects

| Project / author | License | Integration and compatibility |
| --- | --- | --- |
| [PvZA11y](https://github.com/CG8516/PvZA11y), CG8516 and contributors | MIT | Separate accessibility/controller companion for supported GOTY releases, including DVD 1.2.0.1073; not Classic. Optional reviewed beta.1.17.2 download, hash checked. Requires .NET 8 Desktop Runtime. |
| [Archipelago Randomizer](https://github.com/vicr123/PvZ-Stable-Decompile-AP), Victor Tran/vicr123, Bonzorio and contributors | MIT | Standalone recompiled game. Catalog/source link only; cannot be applied to stock PVZ as a resource pack. |
| [PvZ-Portable LuaJIT](https://github.com/hello-lisai/PvZ-Portable-LuaJIT), hello-lisai and contributors | LGPL-3.0-or-later | Standalone engine with Lua mod support. Catalog/source link only; scripts do not run inside stock GOTY/Classic through LawnLab. |

The catalog explains compatibility before installation. PvZA11y downloads into a separate AppData companion folder with its upstream license and recorded hashes; it is not bundled into LawnLab. Disconnect LawnLab before using it, then restart PVZ before reconnecting LawnLab. LawnLab refuses attachment while PvZA11y is running to prevent competing memory controllers. Original project licenses and authors remain authoritative.

## Validation and limits

- 155 automated tests passed, including seed ownership/cooldowns, save-tail verification, resource rollback/conflicts, path validation, note rendering and layered Classic PAK restoration.
- Live GOTY paging passed through five pages; native arrow signals changed the actual card types, the wheel hook installed, and the original ten cards restored. A physical mouse-wheel gesture has not yet been manually confirmed.
- All 20 achievements survived GOTY restart and a save through Classic in its isolated folder.
- Classic's real 2,413-entry archive decoded and re-encoded byte for byte. Resource application/restoration was tested in disposable fixtures; user-installed game resources were not changed during these checks.
- The packaged 5.7 CT helper passed 21 command round trips, synchronized conflicting toggles, refused a second controller and restored all tested patch bytes.
- Both new Studio panels were rendered and inspected. Custom note text has not yet been visually checked inside the game. The optional PvZA11y companion was downloaded and hash checked but not launched during validation.

The CT files remain companions for the 46 main controls. Their catalogs include the new save-root and seed-packet addresses; scrolling deck setup, note changes and mod management are GUI workflows. Use the matching 5.7 executable, keep its `_internal` directory beside it, and run only one trainer controller at a time.
