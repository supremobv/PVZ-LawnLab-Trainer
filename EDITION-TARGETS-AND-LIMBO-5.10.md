# LawnLab 5.10 â€” correct edition targets and remembered Limbo

## Help and credits in Classic

The earlier installation records showed both notes applied to GOTY, with no Classic note installation. Classic's original note images were still in its archive. Applying to GOTY does not modify Classic's separate files.

The editor now follows the edition when LawnLab connects to a game and remembers the target between sessions. A **Verified target** line distinguishes GOTY loose images from Classic's `main.pak`. A selector/folder mismatch refuses the operation. Successful application reports the exact edition and folder.

To edit Classic:

1. Select **Classic** in Mods, notes & launch and verify its folder is `<your Classic game folder>` on this computer.
2. Close both PVZ games. Preview the note, then Apply.
3. Restart Classic through its edition game shortcut. Note images are cached by the running game.

Classic replaces the image payloads inside `main.pak`, rather than creating ineffective loose overrides. Original archives are backed up. Both current custom GOTY note images were installed into Classic's archive, their dimensions and payloads verified, and **the user confirmed both custom notes display in Classic**. Use Restore both original notes to restore Classic's layered archive in the correct order. GOTY's custom notes remain installed separately.

## Limbo: session toggle versus remembered setting

Limbo's visibility is controlled by game code; there is no native player-profile unlock field for it. The earlier toggle changed only the running process. Its disappearance after restarting was not a failure to save player progress.

Studio â†’ **Mods, notes & launch** now has separate **Remember Limbo for GOTY / Classic launches** checkboxes. These preferences are stored in `%LOCALAPPDATA%\LawnLab\startup-options.json`, separately from player data. Both were enabled on this computer for the requested behavior.

Use the LawnLab edition game shortcuts. The launcher selects the edition's isolated save directory, applies the remembered Limbo patch and exits. The normal game continues with **no LawnLab trainer window or monitoring service required**. Reopen Minigames if its page was already open before changing visibility.

Reset all and normal trainer disconnection preserve remembered Limbo. Explicitly turning off the Limbo control clears that edition's remembered preference; unchecking its launch checkbox also disables it for an attached matching game. Preferences for the other edition are unchanged.

**Directly opening an original game EXE bypasses LawnLab's startup preferences and save-folder selection.** The matching normal GOTY desktop shortcut is routed through the save-aware helper, with its original shortcut backed up. The separate Classic shortcut uses the same helper. This does not patch the executable on disk or make a nonexistent native save field appear.

## Save consistency

Classic and GOTY retain separate native userdata folders to prevent Classic from removing GOTY-only achievement fields. Ordinary game shortcuts that go through the helper use the same folders as LawnLab's launch buttons. Progress is intentionally independent between editions; it is not silently merged or overwritten.

- GOTY: `C:\ProgramData\PopCap Games\PlantsVsZomGOTY\userdata`
- Classic: `C:\ProgramData\PopCap Games\PlantsVsZomCLSC\userdata`

The original legacy shared folder remains a separate copy. Starting an original EXE directly still uses that legacy folder until LawnLab attaches at Main Menu. Use the updated shortcuts consistently to avoid seeing different progress.

## Validation

- The user confirmed both notes and Limbo in Classic while LawnLab was closed.
- Classic was reattached with the known launch patch active; Reset preserved the remembered option and the correct save root.
- After closing Classic and relaunching GOTY, all **20 earned achievements remained present**, the GOTY save root was correct and Limbo remained enabled.
- Classic fingerprinting normalizes only the exact known three-byte Limbo change, then verifies the full `.text` hash. Other unknown code changes still fail verification.
- Automated tests cover edition targeting, mismatch refusal, per-edition preferences, reset persistence, explicit disable, adoption of the known patch and rejection of unknown changes.

The current build has 193 automated tests. Live reports are `validation/classic-notes510.json`, `validation/startup510-classic.json` and `validation/startup510-goty.json`.
