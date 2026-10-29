# LawnLab 5.6 — control stability audit

Current compatibility and usage: [GOTY + Classic, Snail, Limbo, coin units, Tree height and Endless records](CLASSIC-AND-PROFILE-5.6.md). Both builds have their own CT/catalog; Classic has no native GOTY achievements.


The 5.3 interface routes all 43 main-window controls through `verified_engine.py`. `trainer_engine.py` remains historical source; its old toggle implementations are not used by LawnLab. Use the rebuilt `release/LawnLab/LawnLab.exe`, not an older copy or the legacy Python entry point.

**Version 5.2 corrects gameplay defects that the earlier ownership checks missed.** The pace field is App + `4B4`, seed recharge is at module + `91E55`, the common zombie-initialization lane hook is at module + `132A12`, and wave advancement requires a countdown of 1. Full causes, the **82-test suite**, actual firing/defence/economy results and a 24-control unpaused trial are in [GAMEPLAY-FIXES-5.2.md](GAMEPLAY-FIXES-5.2.md).

## Defects corrected

The screenshot alone cannot identify the exact failing instruction's owner. The source review nevertheless found concrete memory-corruption risks:

* Infinite sunshine and bigger pickups both owned the instruction at `0x41E6E0`. Disabling either could restore the other's patch or release code still referenced by a jump.
* Free planting and planting bonus overlapped at `0x41E844–0x41E84B`. Free planting now owns only the two-byte subtraction; the bonus owns the following six-byte store.
* Old sun loops wrote at LawnApp + `0x5578`. Sun belongs to Board + `0x5578`; the former can overwrite unrelated memory. Sunshine locks now use the checked Board pointer and install no code hook.
* Heuristic auto-collection could walk unrelated entity memory. It is replaced with the verified auto-collection branch.
* Repeated enables could allocate additional caves/workers, and cleanup could free code despite an unsuccessful restoration. Hooks now reuse bounded allocations retained until the game exits; a single joined worker owns continuous data updates.
* Plant replacement could overwrite the column as well as the type. It now substitutes the plant-factory type argument only, bounded to regular plant IDs 0–47.

## Shared rules

Attachment requires the fingerprinted GOTY executable: SHA-256 `1ff5a2dcf009b453b8866783a68e8d04bd0d066abda3f8196d75a677366b2dff`, image size `0x415000`. Both historical process names remain detectable, but a matching filename alone does not establish compatibility.

Code changes have expected-byte preflight, explicit ownership and rollback. Identical immunity patches can have multiple owners and restore only after the last owner releases them. Conflicting spans are refused before writes. Repeated enabling is idempotent. Parameters live outside immutable hook instructions. Code installation/restoration briefly suspends the process and checks WOW64 thread instruction pointers so a thread cannot resume inside a replaced span. Operations serialize with Studio through one shared lock.

If recovery itself fails, the game is kept paused and a restart is required. A native-call timeout also blocks further edits instead of freeing executing code. Logs stay local in `%LOCALAPPDATA%\LawnLab\logs\controls.jsonl`.

Mutually exclusive controls automatically release the previous mode: infinite sun/sun lock; invincible/fragile plants; Zombotany protection/fragile plants; one-hit/invincible zombies; rapid fire/firing delay. The UI, backend and profile validator use these rules. Explicit Studio plant placement refuses Plant changer; custom zombie spawning refuses Choose a lane.

## Review coverage

| Controls | Implementation reviewed / operating limits |
| --- | --- |
| Infinite sunshine; Sun limit | Validated Board field, one worker, no overlapping sun hook. |
| Free planting; Bigger sun pickups; Planting bonus | Separate instruction spans and preserved registers/flags; compatible together. |
| Auto collect; Uncap sunshine | Exact-build instruction patches; no guessed entity traversal. |
| Coin balance | Checked profile pointer and balance field. Persistent currency edit; reset stops the lock without restoring money already spent/earned. |
| Instant recharge; Plant anywhere | Exact-build recharge and placement checks. Studio placement still validates terrain/layers. |
| Invincible plants; Fragile plants; Zombotany protection | Explicit shared-byte ownership and incompatible-mode checks. |
| Plant changer | Type argument only; regular IDs 0–47; Studio placement conflict refused. |
| Rapid fire; Firing delay | Mutually exclusive; delay bounded to 1–255. A second guarded hook lets current firing animations finish, so short intervals do not suppress actual shots. |
| Projectile changer | Factory type argument, immutable hook with separate bounded parameter. Studio effects share the same control. Visual type selection does not guarantee every special impact on every target. |
| One-hit knockout; Invincible zombies | Exact-build body/helmet/shield damage paths with incompatible-mode checks. |
| Freeze the horde; Pause spawning | Exact-build movement/countdown paths. Advancing the wave refuses paused spawning. |
| Choose a lane | Common initializer row argument bounded to 0–5 and current lawn; guarded for preview, boss and terrain incompatibility. Does not relocate existing zombies. |
| Zombie preview | Seed-selection screen only; boss excluded. Does not rewrite live-wave masks during combat. |
| Play in background; Clear the fog; See inside vases | Verified update/render branches; scene-specific effects require the corresponding scene. Background mode does not dismiss an explicit pause menu. |
| Daytime mushrooms; Always butter; No craters; No ice trails; Quiet jack-in-the-box | Exact-build branches; relevant plant/zombie types must be present for an observable effect. |
| Faster conveyor; Keep the shovel | Exact-build conveyor/shovel paths; conveyor effect needs a conveyor stage. |
| Game pace | Checked frame-duration field; original duration journaled and restored. |
| Restore lawn mowers | Bounded mower array and verified delete/rebuild routines; temporary initialization patches restored. |
| Clear the horde | Bounded GOTY zombie entities and death phase. |
| Spawn the wave | Sets the natural countdown to 1, handles huge waves and waits for observed wave advancement; preserves the stage's composition. |
| Clear all plants | Verified native plant-deletion routine; does not zero or repurpose entity slots. |
| Finish this level | Verified board-completion routine. Changes progress; not used in the disposable-lawn stability trial. |
| All Lawn Studio tools | Stale lawn/entity IDs, strict documents, bounded queues, backup/restore guards, profile conflicts and native-call cleanup covered by the Studio suite. See [the Studio guide](LAWN-STUDIO.md) for mode and persistent-edit limits. |

## Historical 5.1 ownership validation — 29 October 2026

**60 offline tests pass.** Coverage includes every main-window method routing to the verified runtime, every toggle's restoration, 600 randomized changes, 12 shuffled economy enable/disable sequences, repeated enables, shared immunity ownership, instruction boundaries/return jumps, partial writes, failed restoration, external patch conflicts, parameter rollback, worker shutdown and WOW64 context layout. The existing Studio/interface checks are included in this total.

On a fresh disposable lawn in the installed fingerprinted game:

* All 53 selected static patch records matched the executable before use.
* 32 controls enabled/disabled individually without runtime errors; background running was enabled separately.
* Twelve compatible controls remained enabled for a 90-second wall-clock trial: infinite sunshine, free planting, bigger pickups, planting bonus, auto collect, instant recharge, invincible plants, Zombotany protection, background running, uncap sunshine, faster conveyor and coin lock. Coin lock used the pre-test balance. The game remained accessible; its lawn clock advanced from 43 to 248, so this is not 90 seconds of continuous combat simulation.
* Reset restored every owned control code span, stopped the worker and restored the captured sun/balance. Six hook allocations were deliberately retained rather than freed while game threads could reference them.

These checks verify memory ownership and cleanup; they do not visually confirm every plant/projectile effect or every combination across all stages. Zombie preview's seed-selection refresh, stage completion/launch, persistent garden edits, alternate-scene effects and full formation rebuilding still need their individual gameplay checks. The earlier timed chilling-projectile visual test was missed. No crash-free guarantee is implied.

## Running the corrected build

The current combined suite has **82 tests**, including ten CT adapter/artifact checks. The CT reuses this runtime and acquires a per-game ownership lease so the CT helper and GUI cannot control the same process simultaneously. It requires a matching 5.2 companion handshake. See [CHEAT-ENGINE.md](CHEAT-ENGINE.md) for the CT address inventory and packaged-helper live checks.

Close old LawnLab copies and start a fresh PVZ process after a crash or use of an older trainer. Open `Launch LawnLab.cmd` or the rebuilt portable executable, then connect. Keep its `_internal` folder beside it. Reset all releases trainer-owned patches; it cannot undo damage, entity creation/deletion or persistent progress changes already made by one-time actions. Do not combine another memory editor's patches with this runtime.

## Version 5.3 additions

The common damage entry applies lethal body damage only after a positive incoming hit; equipment no longer consumes a separate first hit. Rapid fire combines a bounded 5-tick action timer with a supported-shooter firing hook and a 700-projectile headroom limit. Coin collection filters live silver/gold/diamond objects and invokes the native collector under the shared operation lock. Immediate row moves validate generation IDs, live state and terrain, then update row, native Y and render order together. Bulk plans preflight support layers, duplicate limits and a 250-plant cap before creating anything. Creation failures report partial progress; native actions are not transactional undo operations. See [the current usage guide](LAWN-STUDIO-GUIDE.md).

## Version 5.4 verification

The main-window controls now include Sunflower drops. The AddCoin hook checks both the production return site and Sunflower/Twin Sunflower type, then chooses native sun/silver/gold/diamond with the appropriate motion. Other sources are untouched. Coin generation IDs are at +D0, not +D4; the previous offset silently excluded real coins.

PreNewGame changes the mode before MakeNewBoard destroys the previous board. Launching Garden while an Adventure board still existed caused Garden LeaveGarden to dereference a null garden-board pointer (fatal +1F89C). The launcher now disposes the old board under its old mode and performs widget/loading calls through a retained one-shot request on the game loop. Entry and return passed live checks; the main-loop bytes restored normally. Paused dialogs and unsupported intro/result states are refused.

See [validation/gameplay-5.4.json](validation/gameplay-5.4.json) for actual results and remaining limits.

## Version 5.5 saved-data tools

Garden/Tree modes and other non-battle scenes are excluded from the lawn-only continuous worker. Named saved-data updates prevalidate the whole request, verify written bytes, use one native save per batch and roll memory back on ordinary save failures. A pending native timeout retains its request and requires recovery. User identity and saved-plant stamps reject stale selections; add/move operations require Main Menu and never compact the collection. Aquarium type and all destination-capacity checks run before mutation. Each UI persistent operation creates a save backup. Code Reset cannot undo saved changes. See [PROFILE-AND-GARDENS.md](PROFILE-AND-GARDENS.md).

