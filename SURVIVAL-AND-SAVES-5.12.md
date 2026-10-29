# LawnLab 5.12 — Survival repick, graves and save progress

## Survival: Night (Hard) crash

The reported GOTY 1.2.0.1073 crash at 0044AF50 dereferences ESI, a UI button pointer. The old scrolling deck put seed type -1 into unused slots of its final page. The Survival repick constructor indexes its chosen-seed array directly by that type. Its native cooldown-copy instructions can therefore write before that array and clear a button pointer. This matches the reported ESI=0 crash after the next chooser is created.

The 5.12 deck never writes a negative type into a counted packet slot. A short last page wraps valid cards from the deck to fill the native bank; it does not increase the native slot count. An invalid initial bank is refused. On a round/lawn change, the deck stops without restoring stale card data over the new chooser. Choose seeds, start the next battle, then start the scrolling deck again.

The real GOTY repick copy block (+8EAF0..+8EB0D) was emulated to reproduce the previous null-button overwrite with -1. Valid plant IDs preserve the buttons. Live Survival: Night (Hard) checks used the final 48-card page (40..47,0,1) and completed two successive next-chooser transitions through the game's finish-stage path. All seven buttons remained valid and both choosers stayed running. These checks address this crash path, not every possible game crash.

Primary source cross-check: [SeedChooserScreen constructor](https://github.com/Patoke/re-plants-vs-zombies/blob/main/Lawn/Widget/SeedChooserScreen.cpp). Runtime addresses and bytes were independently checked against the installed executable.

## Scrolling with Studio hidden

Closing Lawn Studio now hides that tool window. The seed overlay, mouse-wheel input, hotkeys and active Studio session can continue while the main LawnLab controller remains connected. Reopen Studio through its main-window button. Use Stop / restore cards, Reset all, Disconnect, or exit the main controller to end the session. Closing the entire controller cannot leave wheel scrolling working independently.

## Remove all graves

Connect to a live battle, choose **Level actions → Remove all graves**, and run the action. It removes current gravestones through native GridItemDie, including animation cleanup. It does not alter plants, craters, ladders or vases. It does not change saved unlocks, award Grave Buster credit, or stop future graves from spawning. Already removed graves are not restored by Reset all. Re-run the action if more graves appear.

GOTY live check removed nine gravestones; a second action correctly removed zero. Classic uses a separately verified array offset and native routine; that new action has not received a Classic live-play check in this release.

## Which Adventure progress am I using?

Click **Save progress guide** in the main LawnLab sidebar. It opens the launch/save section and reads three save locations without changing files. The table displays saved Adventure stages and folders; a connected game also shows its live stage and active native save root. Disk progress can lag unsaved gameplay.

- Original game EXEs load `C:\ProgramData\PopCap Games\PlantsVsZombies\userdata` — the old shared progress.
- GOTY edition launchers load `C:\ProgramData\PopCap Games\PlantsVsZomGOTY\userdata`.
- Classic edition launchers load `C:\ProgramData\PopCap Games\PlantsVsZomCLSC\userdata`.

Always use the updated desktop shortcuts, in-app launch buttons, or **Play GOTY/Classic - current progress** shortcuts inside the game folders. The launcher selects the proper save folder and exits; the trainer window need not remain open. The original EXEs are unchanged and bypass this routing.

Connecting LawnLab at Main Menu can switch an original-EXE session to its edition save. This explains the apparent jump from stage 10 to stage 12; progress was in different files. It does not merge saves. GOTY and Classic advance independently, preserving GOTY-only achievements. Quit normally to save, back up before restore/import, and do not overwrite GOTY files with Classic files.

## Validation and CTs

Both CTs and catalogs are regenerated for the matching 5.12 companion. Validation covers the native invalid-index regression, safe final pages, round-change ownership, selective grave cleanup, read-only progress reports and Studio hide behavior. Live transition and grave reports are in validation/survival512-goty*.json. A complete save backup was created before the disposable Survival test.
