# LawnLab 5.6 — Classic support and profile corrections

## Supported copies

LawnLab automatically selects a verified runtime:

| Build | Identity | Backend |
| --- | --- | --- |
| GOTY 1.2.0.1073 English x86 | Image `0x415000`; disk SHA256 `1ff5a2dcf009b453b8866783a68e8d04bd0d066abda3f8196d75a677366b2dff` | `verified_engine.py`, `studio_engine.py` |
| Classic 1.0.0.1051 English x86 | Image `0x394000`; mapped `.text` SHA256 `a53b1b79f1e79f974397640c7e026af9131417bfdd2c0b8b3136615ca440fd7e` | `classic_verified_engine.py`, `classic_studio_engine.py` |

The installed Classic copy starts through `PlantsVsZombies.exe`, but its game runs as **popcapgame1.exe**. LawnLab ignores the launcher. Open one supported game, choose Auto detect, and Connect. Close/disconnect the other trainer first. Other versions/languages remain refused until independently verified.

The 46 main controls and applicable Studio tools route through the selected build's own addresses. Classic has **no native GOTY achievement flags**; the achievement editor reports that limitation and refuses writes. Ordinary plant/state/terrain restrictions still apply in both versions. A scene-specific control needs the relevant scene or entity.

Classic differs in more than addresses: its zombie stride is `0x15C` rather than GOTY's `0x168`, its profile lacks the 40 achievement bytes, and several native functions use different registers/stack arguments. The port has separate signatures, hooks, data fields and loop gates. `generate_classic.py` shares reviewed logic through explicit context-specific maps; it does not guess offsets at runtime.

## Restock all sold-out items

Enable **Sun & economy → Shop restock** and buy normally. Owned gardens, tools, cleaners, capped upgrades, Snail and Tree may be purchased again at normal prices. Rebuying an owned permanent unlock does not create another garden or extra seed slots. Locked/coming-soon requirements still apply.

Purchase guards retain **ten seed slots**, **two mower upgrades** and the Tree's existing positive height. Full gardens still reject extra Marigolds. Supplies have a bounded count. Reset all restores stock rules; purchases already completed remain saved.

## Snail awake and fast

Enable **Lawn & world → Snail awake & fast**, then enter Zen Garden. You must own Stinky first (buy him or repeat his shop purchase). This makes the game's awake and chocolate-speed predicates true. Normal waking/boost animation transitions still take a moment. It does not create a second snail or consume chocolate. Disable the control to restore the game's normal timing rules.

## Find the wheelbarrow

The **Wheelbarrow is a one-plant carrier**, not another garden screen. Buy it from Dave or enable **Player data → Wheelbarrow owned** from Main Menu. In Zen Garden select the wheelbarrow toolbar icon, pick up a plant, switch to the desired garden with the yellow arrow, then place it. Studio also supports moving a selected saved plant into/out of the carrier from Main Menu. The profile inspected during testing already owned it.

## Hidden Limbo page

Enable **Lawn & world → Limbo hidden page**, then reopen the Minigames chooser. The hidden page becomes available while the patch is enabled. Hidden scenarios are experimental game content: they retain their original game behavior and may require particular conditions. This is separate from the ordinary Minigames-unlocked profile field. Reset all restores the hidden-page rule.

## Coins, Tree height and endless records

In **Lawn Studio → Player data**, Read first, tick the fields you intend to edit, return to **PVZ Main Menu**, then Apply. Each saved edit creates a backup.

* Both coin editors now use **stored units of $10**. `999999` means **$9,999,990**. The preview shows dollars; the accepted unit range is 0–99,999,999. Values above the original 99,999-unit ceiling enable **Extended coin bank** automatically. Keep that control enabled while earning/spending above the original ceiling; disabling it restores the game's ordinary cap, so a later transaction can clamp an oversized balance. Coin lock is separate and must be off when editing saved coins.
* **Tree of Wisdom height** uses the Tree record (`Profile+11C` GOTY, `Profile+F4` Classic), not the neighbouring record. It accepts 0–2,000,000,000 feet. Both inspected profiles read **1,280,543,585**, matching the game. Editing height is separate from owning the Tree.
* **Longest streak — Vasebreaker Endless** and **Longest streak — I, Zombie Endless** edit the best displayed records. **Best flags — Survival Endless** has Day, Night, Pool, Fog and Roof fields. Pool is the standard visible Endless tile; the others are hidden variants. These fields accept 0–1,000,000 and change best records, not the currently running wave. The inspected profile had Puzzle streaks of 2457 and Pool Survival best flags of 4.

## Cheat Engine companion

Use `LawnLab-GOTY-1.2.0.1073.CT` for GOTY or `LawnLab-Classic-1.0.0.1051.CT` for Classic. Both require the **5.6 LawnLab.exe** companion and use the same safe backend as the GUI. Attach CE to the actual game PID; the helper validates that exact PID and fingerprint. Disconnect the GUI before starting the CT controller. The Classic launcher PID is not supported.

Each CT contains all main controls plus read-only build-specific references. `LawnLab-addresses.json` and `LawnLab-Classic-addresses.json` inventory fields, hooks, originals, native signatures and source context. The Classic inventory lists integer literals with context because flags, opcodes and bounds are not all addresses. Full saved-data workflows remain in the GUI for backups and validation.

## Measured checks and limits

* **132 offline tests**: both-build purchase-guard execution in x86 emulation, native damage ABI, complete hook boundaries, animation-guard branches, Classic zombie identity/stride, achievement refusal, generated-source/catalog checks, and existing combination/recovery/UI tests.
* Classic: native plant placement, Conehead spawning, inspector edits/restoration, immediate lane move, projectile damage restoration, seed-bank writes, all toggle installation/restoration, a 30-second compatible-control trial with an advancing game clock, and one-hit positive damage through Conehead armour. All tracked code spans restored afterward.
* Both builds: actual native sold-out routine checked on 13 previously sold-out items; all became available with restock and returned to native rules afterward. Native snail predicates returned awake/boosted. A 999999-unit balance was verified and temporary profile bytes were restored and saved. GOTY also passed the full-garden guard, large named-profile/Tree/endless edits and a restored achievement toggle.
* Classic's Garden-to-Adventure native transition passed. The local profile readings and native conventions were verified; this does not mean every plant, hidden mode, terrain or scene-specific effect was visually exercised. Snail predicate/stock tests measure native state; every shop confirmation and the snail's full collection animation were not manually exercised.

Machine-readable results are in `validation/classic56-initial.json`, `validation/classic56-gameplay.json`, `validation/classic56-shop-profile.json` and `validation/goty56-shop-profile.json`. Earlier 5.5/5.4 results remain historical. Temporary validation edits were restored; created test-lawn entities are disposable battle changes.


