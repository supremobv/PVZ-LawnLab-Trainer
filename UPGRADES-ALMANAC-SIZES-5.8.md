# LawnLab 5.8 — upgrade plants, Almanac and sizes

These controls support the verified English GOTY 1.2.0.1073 and Classic 1.0.0.1051 executables. They start off and restore through their toggles, Reset all or normal trainer disconnection. The matching CT tables contain the same four new controls, two size parameters and edition-specific address references.

## Direct upgrade planting

Under **Plants**, enable **Direct upgrade planting**, then use the desired seed card in PVZ normally. Winter Melon no longer needs a Melon-pult first. The other purple upgrades—Gatling Pea, Twin Sunflower, Gloom-shroom, Cattail, Spikerock, Gold Magnet and Cob Cannon—also bypass the prerequisite plant check.

Normal sun prices and recharge still apply unless you separately enable Free planting or Instant recharge. Terrain restrictions remain: Cattail belongs in a pool row, roof plants need pots, and ordinary pool plants need lily pads. Cob Cannon still needs two compatible adjacent cells and cannot extend past the right edge. An occupied cell must still be a valid ordinary upgrade or an empty legal location; this control does not turn arbitrary occupied plants into upgrades.

This changes only the two native prerequisite branches, not the global easy-planting cheat flag. It does not buy/unlock seed packets in your save. Choose cards you own, use the seed editor, or use the scrolling deck. Lawn Studio already creates named upgrade plants directly; its placement validation now also allows Cattail directly in a pool cell without a prerequisite lily pad.

## Reveal Almanac entries

Under **Lawn & world**, enable **Reveal Almanac entries**, then close and reopen PVZ's Almanac. Locked plant cards become selectable, and zombie entries expose artwork and descriptions, including the Yeti instead of its silhouette and question marks.

This is a temporary viewing override confined to Almanac code. It does not mark Adventure complete, purchase plants, earn achievements or change which zombies may spawn. Turn it off and reopen the Almanac to restore ordinary locked-entry behavior. The supported native Almanac roster is retained; this does not create entries for unused or mod-only IDs.

## Plant and zombie size

Use **Plants → Plant size (%)** and **Zombies → Zombie size (%)**. Enter the percentage before enabling the switch. To change a value through the main menu, turn its switch off, set the new value and turn it back on.

| Percentage | Result |
| --- | --- |
| 25% | One quarter of native size |
| 50% | Half size |
| 100% | Native size |
| 200% | Double size |
| 300% | Triple size |

The controls affect current and newly created battle entities. Plants multiply their native animation scales; planting-grid occupancy and damage are unchanged. Almanac displays, seed-selection previews and Zen Garden are excluded. Plant shadows and independent particles may retain their original appearance.

Zombies use the game's native scale field. Each entity's original value is retained, so a naturally half-sized zombie remains proportionally smaller. Native zombie scaling can also affect animation offsets and some interactions; it is not a damage or immortality control. Repeated updates do not compound size. Turning the control off restores the original scale of surviving owned entities. Dead entities, recycled slots and old lawns are never restored through cached addresses. An unexpected scale written by another tool is preserved on disable.

Sizes are bounded to 25–300 percent. This limits extreme overlap and visual clipping; a large sprite can still cover neighboring cells. The game must be running for animation updates to become visible. These controls do not persist in saved progress.

## Classic launcher correction

This release fixes **Invalid command line parameter -changedir** from the old Classic wrapper. The wrapper mishandled the quoted program path and forwarded a stray quote into its child game's arguments. LawnLab now keeps the verified full executable as the Windows application name while passing its existing space-free Windows short path as the legacy command line. If no short name exists, it uses the normal Windows shell launch path.

Continue using the **LawnLab Classic - separate saves** and **LawnLab GOTY - separate saves** desktop shortcuts. These still point to the portable executable and therefore use the corrected launcher after updating. GOTY and Classic keep separate native userdata folders; see the [save and extensions guide](EXTENSIONS-AND-SAVES-5.7.md).

## Validation

- Both actual game builds accepted the seven land-upgrade types at an empty cell: native planting reason changed from 8 (needs prerequisite) to 0 (allowed). A Winter Melon was created directly on each disposable test lawn.
- Both actual builds changed plant body animation scales from 1× to 2× and restored them after disabling.
- With each battle clock moving, both actual builds changed zombie animation scales from 1× to 2×, accepted a subsequent half-size setting and restored each original size.
- Original bytes for all new patch spans and plant hook tails matched both verified executable images. Almanac patches installed and restored in both live processes. The fully revealed Almanac screen has not yet been manually confirmed visually.
- Automated checks exercise x87 stack balance, preservation of registers/flags, menu/garden/foreign-board exclusion, Classic's RET 4 calling convention, size limits, naturally small zombies, repeated updates, recycled IDs, external edits and launcher quoting. The complete suite has 167 tests.

Live reports are in `validation/extras58-live.json` and `validation/extras58-classic-live.json`. Disposable test plants/zombies are limited to those test lawns; original plant/zombie size settings were restored. No profile progress was edited for these feature checks.

Research reference: [Patoke/re-plants-vs-zombies](https://github.com/Patoke/re-plants-vs-zombies), particularly Board's planting validation, Plant's UpdateReanim and the Almanac predicates. LawnLab independently checks instructions against each supported original executable and uses separate version maps; source reconstruction alone is not treated as proof of a runtime address.
