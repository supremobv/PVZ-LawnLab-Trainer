# LawnLab 5.9 — movable seed bar and note fixes

## Move or hide the seed-page bar

Open **Lawn Studio → Seeds & shots**. Start a scrolling deck as before.

- Drag the **middle page label** in the game to move the bar. The arrow buttons still turn pages.
- Alternatively, change **Bar position X / Y** in Studio. Coordinates use the game's 800×600 reference space and follow its window when it moves or resizes.
- **Reset bar position** returns it to X 110, Y 86.
- Untick **Show in-game page bar** to hide the entire bar. The native mouse-wheel hook stays active: focus PVZ, point at its seed cards, and turn your mouse wheel. No buttons need to be visible.
- Tick the option again to show the bar. Position and visibility are saved locally between LawnLab sessions.

Wheel events outside the seed cards, in other foreground applications, or while the game is minimized pass through normally. Place or cancel a held plant before turning pages. Hiding the bar does not stop the deck; **Stop / restore cards**, Reset all or disconnection still stop it normally. Windowed/borderless mode is required for the visible bar.

## Full note preview

The Help and credits invitation previews now reserve the full scaled image height. The old label could collapse to 80 pixels and show only the middle of a note. Your line breaks and signature remain part of the full preview. Long text still auto-fits; text that cannot fit is rejected rather than silently truncated.

Font measurement and painting now run on the application's UI thread. Apply sends only the completed PNG bytes to its file worker. Notes and font selections are saved locally, including across an administrator restart.

## Applying notes under Program Files

Windows normally protects the GOTY installation under `C:\Program Files (x86)`. Close both games before applying or restoring resources.

1. Preview the note and check the complete text.
2. Click **Apply this note (game closed)**.
3. If Windows denies the write, the operation now stops promptly and reports the reason. Disconnect the trainer and click **Restart LawnLab as administrator (Windows prompt)** in the same tab.
4. Approve Windows' UAC prompt, then apply the saved draft in the restarted copy. Canceling UAC keeps the original window open. No game modification is automatically applied by the restart.
5. Restart the game after a successful application to reload its images. Use the resource restoration list to undo the note. Restore an existing note edit before replacing the same resource again.

The hang came from `tempfile.mkstemp` retrying access-denied errors on Windows because directory writability checks can be misleading. The replacement retries only actual temporary-name collisions, with an eight-attempt limit. Access denied returns immediately and leaves original resources intact. Failed writes no longer try to rewrite already-identical originals during rollback.

The previous interrupted operation had an `installing` journal record, but both target files were verified to match their original checksums. That unchanged record was cleared; its backups were retained. Automatic recovery clears only interrupted records whose complete resource set is still original. It never silently discards partial changes or outside edits.

## Verification

- **180 automated tests passed**, including drag-position persistence, hidden-bar wheel routing, foreground/pointer restrictions, full-height multiline preview, worker completion/failure, GUI-thread font rendering, bounded temporary-file creation and administrator-restart cancellation.
- On the actual protected GOTY folder, the new access-denied path completed in approximately **0.04 seconds**, with no stale installation record and both original resources unchanged.
- Your example multiline Help note was rendered and inspected in the full-height preview. The complete text and signature are visible.
- Position and wheel behavior were tested at the UI/input-routing level. A new physical drag/wheel gesture in the running game has not been manually confirmed in this release.
- Administrator elevation requires the user's Windows approval. An elevated write to the actual Program Files installation was not performed during these checks. Resource install/restore paths remain covered with writable temporary fixtures.

The existing 50 main controls and game addresses are unchanged. Matching 5.9 CT tables/catalogs are included; these overlay and note workflows remain in the GUI.


## 5.9.1 — dedicated original-note restoration

Each note editor now has its own **Restore original Help note / credits note (game closed)** button. **Restore both original notes** restores both. Select the correct edition/game folder and close both games first. Program Files restoration requires the same administrator permission as applying a note. Restart PVZ afterward. The preview shows the restored original image; your custom text and font drafts are retained.

Restoration copies the checksummed images saved before your LawnLab edit, rather than recreating the wording or font. If no LawnLab backup exists, files stay unchanged and the status explains that there is no known edit to restore. External file changes or damaged backups stop restoration. Classic stores both notes in one archive: restore the newer note first, or use Restore both to handle note order automatically. A newer unrelated Classic resource mod must be restored first.

Five added tests verify independent GOTY restoration, exact Classic archive restoration, no-backup behavior, damaged-backup refusal and preservation of outside edits. The full suite has 185 tests.
