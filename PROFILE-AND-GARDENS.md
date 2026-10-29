# LawnLab 5.6 — saved plants, shop stock and player data

Current compatibility and usage: [GOTY + Classic, Snail, Limbo, coin units, Tree height and Endless records](CLASSIC-AND-PROFILE-5.6.md). Both builds have their own CT/catalog; Classic has no native GOTY achievements.


## What “selected saved plant slot” means

A saved slot is one record in the active player’s collection, across all gardens. Slot **0 is the first plant**, slot 1 is the second, and so on. It is not a plant-type ID, a garden number, or a square in the game. Selling a plant can change later slot numbers.

Connect LawnLab, open **Stages & Zen Garden**, press **Read saved garden collection**, then click a named row. The selected-plant line shows its name, garden and saved slot. The slot box is read-only; use the table to choose. Single-plant edits check the saved record’s identity fields and ask you to re-read if the collection changed.

The table contains all saved plants, even while you are looking at the Mushroom garden, Aquarium or Tree. An empty table before reading does not mean the saved collection is empty.

## Batch garden care

Choose **All saved plants** or a named garden, choose an action and press **Apply this action to the selected group**. Confirm the persistent change; LawnLab creates a save backup first and saves the batch once.

| Action | Result |
| --- | --- |
| Water all | Sets watering time and advances the water-feed count toward its requirement. |
| Fertilize eligible young plants | Advances one growth stage for watered, non-mature plants; reports skipped plants. |
| Fulfill current needs | Clears the current need and sets its fulfilled timestamp; does not raise growth. |
| Set growth stage for all | Explicitly selects Sprout, Small, Medium or Mature for the chosen group. |
| Give chocolate to all | Sets the chocolate timestamp for the chosen group. |

Trainer care does not consume supplies. The list refreshes after successful actions. Re-enter the garden to refresh visuals; the game may assign a new need later according to its own rules.

## Add plants to empty gardens

1. Return to **PVZ Main Menu**. Do not add or move saved plants while the garden is displayed.
2. Choose a destination, named plant, quantity and starting growth in **Add plants to an empty garden**.
3. Press **Add saved plants**, confirm and then re-enter the destination garden.

Existing plants are preserved. The whole request checks space before creating any record. The destination must be owned; buy it in the shop or edit its ownership in Player data.

| Destination | Capacity | Placement rules |
| --- | --- | --- |
| Main garden | 32 | 8 columns × 4 rows. |
| Mushroom garden | 8 | Uses the game’s eight special garden positions. |
| Aquarium | 8 | Lily Pad, Tangle Kelp, Sea-shroom or Cattail only. |
| Wheelbarrow | 1 | A carrier, not a separate garden screen. Use its toolbar icon to pick up a plant, switch gardens, then place it. Unlock via the shop or Player data. |

To move a plant, read and select it in the table, return to Main Menu, choose the destination and press **Move selected saved plant here**. Moving preserves its saved slot and does not delete other records. The total profile bound remains 200 records.

## Buy sold-out shop items again

Enable **Shop restock** in the main window’s Sun & economy category, or use its buttons in Studio. Open the shop and buy normally. Normal prices and purchase confirmations remain.

The override permits repeat supplies, daily Marigolds and owned tools/gardens/upgrades, including Snail and Tree. Buying an owned permanent tool again generally adds no extra benefit. Purchase guards retain ten seed slots, two mower upgrades and the Tree's existing positive height. Full gardens still refuse more Marigolds. Supply counts have a generous bounded ceiling. Locked/coming-soon items still need normal progression unlocks.

Turn off Shop restock or use Reset all to restore normal stock checks. Purchases already made remain saved.

## Edit player data

Open **Player data**, press **Read active player data and achievements**, and check the player name and ID. Tick only the named fields you want to change, then **Apply checked player-data changes** from PVZ Main Menu. Unchecked fields remain unchanged. Each Apply creates a backup. Changing active players requires a fresh read.

Editable values include coin units (×$10; 999999 means $9,999,990), Adventure stage/completions, future battle seed slots (6–10), corrected Tree height, named Puzzle/Survival Endless best records, mode unlocks and garden ownership. Large balances automatically enable Extended coin bank; keep it enabled for transactions above the normal cap. Turn off Coin balance lock before editing saved coins. Changes to future stage/seed settings do not rewrite an already-running battle. Locking a garden does not delete its plants. Name/ID and Zombatar data are preserved.

## Edit local GOTY achievements

Read the player first, then check or uncheck the 20 named achievement rows. **Check all** and **Uncheck all** only change the draft. **Apply changed achievement checkboxes** performs the saved edit from Main Menu after a backup.

Newly earned flags are marked as already shown to avoid a burst of popups. Clearing an achievement does not undo the progress that earned it; PVZ can award it again when its conditions remain met. These are the local GOTY flags, not Steam-account achievements.

## Verification and recovery

The live trial edited and restored profile values, toggled an achievement on/off, added Mushroom/Aquarium records, performed bulk care, moved a plant into the Wheelbarrow, and checked the actual game stock routine. Temporary profile bytes were restored and saved through PVZ’s own routine. Garden reads and background controls passed in a live Zen Garden session after the unsupported-scene fix. See **validation/profile-5.5.json** for measured results and limits.

Backups contain on-disk saves. To restore one, close PVZ first and use Save backups. Reset all restores active code modifications; it does not undo purchases, garden growth, added plants or saved player-data edits.

Layout reference: [reconstructed GOTY PlayerInfo](https://github.com/Patoke/re-plants-vs-zombies/blob/main/Lawn/System/PlayerInfo.h), [store logic](https://github.com/Patoke/re-plants-vs-zombies/blob/main/Lawn/Widget/StoreScreen.cpp), [achievement definitions](https://github.com/Patoke/re-plants-vs-zombies/blob/main/Lawn/Widget/AchievementsWidget.h). Actual offsets and instruction bytes were checked against the fingerprinted local executable.

