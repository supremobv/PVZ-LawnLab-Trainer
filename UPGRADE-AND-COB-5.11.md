# LawnLab 5.11 — direct upgrades and automatic Cob Cannons

## Direct upgrade planting

Enable **Plants → Direct upgrade planting**, then select the upgrade seed card and click a valid lawn cell. Winter Melon no longer requires a Melon-pult anywhere on the lawn. The same applies to Gatling Pea, Twin Sunflower, Gloom-shroom, Cattail, Gold Magnet, Spikerock and Cob Cannon.

The earlier implementation changed cell validation but missed the separate seed-card prerequisite predicate. This release patches both, and restores the original instructions when disabled. This does not unlock unowned seed packets or remove their sun/recharge cost. Use Infinite sunshine / Free planting / Instant recharge separately if wanted.

Terrain and occupied-cell checks still apply. Cattail needs a pool row; water/roof plants still need their normal support where applicable. Cob Cannon occupies **two adjacent cells**, so leave both clear and do not use the last column. Gloom-shroom still follows the mushroom sleep rules unless Mushrooms awake is enabled.

## Automatic Cob Cannons

Enable **Plants → Automatic Cob Cannons** after placing a Cob Cannon. No cannon click or target click is required. The controller chooses the living hostile zombie closest to the house, aims at its current position, and invokes the game's native cannon firing routine when ready.

The long arming/reload countdown is skipped when an eligible target is present. Native charging and launch animations finish normally, so this is continuous automatic firing rather than a projectile every frame. GOTY's measured test produced four launches in 18 seconds. Moving targets can move before the projectile lands; automatic targeting is not a guaranteed hit.

Friendly/hypnotized, dying and off-screen zombies are skipped. The controller pauses during in-game pause, menus and Garden/Tree modes. A high projectile count blocks extra launches to preserve pool headroom. Multiple cannons may choose the same closest enemy. Disabled/reset controls stop future automatic launches; already launched shots continue, and elapsed/reduced reload time is not rewound.

**Rapid fire** and **Firing delay** remain standard-shooter controls. They do not replace the Cob Cannon control.

## Instant Potato Mines

Enable **Plants → Instant Potato Mines** before placing a mine. New mines initialize in the native armed state and armed animation, without the 15-second underground wait. Each still explodes only once. Existing mines retain their current arming progress. Disabling restores normal initialization for future mines; armed mines are not reset underground.

## No Lily Pad / Flower Pot needed

Enable **Plants → No Lily Pad / Flower Pot needed** to place ordinary plants directly on pool water or roof tiles, from seed packets or Lawn Studio. This changes only the water-support and roof-pot checks. Native cell bounds, occupied cells, sun/recharge, graves/craters and special aquatic or ground-only restrictions remain. It can be combined with Direct upgrade planting.

Disabling restores placement requirements for future placements. It does not delete plants you already placed without supports. Live bulk placement also honors the toggle and skips automatic supports. Saved-plan editing retains its terrain/support validation; include supports when saving a reusable pool/roof plan.

## Cheat Engine

Both generated 5.11 CTs include the new toggle and refreshed address catalogs. Use the matching 5.11 LawnLab.exe helper, with the GUI disconnected. No separate guessed CE implementation is used.

## Validation

Automated checks cover both editions' prerequisite returns and stack balance, patch restoration, cannon targeting, pause/projectile guards, native signature refusal, reload-state handling and reset. Live report files under validation record each edition's seed-packet results, reload restoration and automatic launches/damage.

## Adventure progress when starting from a game folder

The original Classic and GOTY EXEs use the same legacy save folder (currently stage 10). They cannot select LawnLab’s separate edition saves by themselves. Use **Play GOTY - current progress** or **Play Classic - current progress** shortcuts installed in the game folders, or the matching desktop shortcuts. The helper selects the edition save (stage 12 at validation), then exits; no LawnLab window needs to stay open. Original EXEs and existing shared saves are preserved. Classic/GOTY progress remains separate by design to protect GOTY achievements.
