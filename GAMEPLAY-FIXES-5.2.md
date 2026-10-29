# LawnLab 5.2 — gameplay corrections and evidence

Version 5.1's patch-ownership tests were not sufficient gameplay validation. They proved that selected bytes could be installed and restored, but missed incorrect field arithmetic, a wrong feature mapping, an intercepted path that natural waves did not use, and a countdown edge case. The executable fingerprint was correct; several operations performed on that executable were not.

## Reported failures corrected

| Failure | Root cause | 5.2 correction | Observed game-side result |
| --- | --- | --- | --- |
| Pace caused a crash | App + `0x514` is a pointer. The crashing `0x5DA49B` instruction dereferences that pointer; writing the selected pace there could replace it with `5`. | The correct frame-duration field is App + `0x4B4` (`0x454 + 0x60`). Native update gating uses this same constant. | All six settings produced about 20, 50, 100, 199, 502 and 998 lawn updates/second. The protected pointer stayed unchanged and reset restored 10 ms/frame. |
| Instant recharge did nothing to seeds | The old mapping patched a plant action/production path called `reload_instantly` in the reference, not seed-packet recharge. | Patch the seed packet's actual refresh comparison at module + `0x91E55`, original `7E 14`, to `90 90`. | A genuinely cooling packet remained inactive without the patch, then became active and stopped refreshing after enabling it. |
| Lane selection missed normal waves | The old hook intercepted the custom challenge factory. Other factories and inlined natural-wave paths bypassed it. | Override the row argument at the common zombie initializer, module + `0x132A12`, before both row and vertical position are initialized. | Five consecutive natural waves produced three zombies each, all in their selected rows 1–5. |
| Spawn the wave did nothing | The timer was set to zero, but the update decrements it before testing for zero. It became negative. | Set the next countdown to **1**; handle an active huge-wave countdown too. Reject paused, completed and unsupported challenge states. Wait for actual wave advancement; a timeout reports failure and restores a pending timer where applicable. | The natural wave index increased and new zombies appeared in every lane test. |

Lane values now cover 0–5 (rows 1–6), and a selected row must exist on the current lawn. The initialization hook skips preview objects, boss zombies and incompatible water/land combinations. Existing zombies are not teleported.

## Other corrections found during the audit

* **Rapid fire / firing delay:** the old rapid-fire branch was in shooting animation logic. Extremely short intervals could also continually restart an animation before it emitted a projectile. Both modes now share a launch-timer hook plus a guard that lets the current animation finish. A Peashooter emitted **2 projectiles normally, 9 with rapid fire and 8 with delay 2**, in three-second samples. Very small delays therefore request the fastest complete attack animation, not an interrupted animation every tick.
* **Free planting:** stopping the subtraction alone still left affordability checks. Three separate, non-overlapping patches now allow seed affordability and spending at zero sun while preserving the planting-bonus store. A zero-sun spending request succeeded without deduction; the combined bonus added 2,000 sun.
* **Daytime mushrooms:** enabling the static patch now also invokes the verified wake routine on existing sleeping plants. A previously asleep Puff-shroom changed to awake.
* **Repeated mower restoration:** the array's storage bound can exceed six even with only five live mowers. Restoration now checks bounded storage separately from live generation-tagged records, then runs the game's delete queue before constructing replacements. Six consecutive restores on a paused lawn each produced five live mowers with a stable storage bound of ten.
* **Pace reset:** the verified GUI/profile paths preserve the engine's original-duration journal instead of applying another pace write after reset.
* **Projectile wording:** Winter Melon splash is labeled as a slow effect; it is not advertised as an Ice-shroom-style hard freeze.
* **CT synchronization:** the table and companion executable require a matching `5.2` handshake. An older 5.1 executable cannot silently serve the new CT controls. The generated address catalog includes the corrected fields, hook site and animation guard.

## Live gameplay checks

These checks observed actual game state on the authorized disposable Adventure lawn, using the fingerprinted GOTY executable. Window capture failed twice, so the evidence is **instrumented gameplay, not visual confirmation**. The captured results are in [validation/gameplay-5.2.json](validation/gameplay-5.2.json).

| Feature area | Observed behavior |
| --- | --- |
| Economy | Infinite sun, custom sun lock and coin lock changed their intended fields. A normal sun-add routine added 25, the bigger-pickup mode added 1,000, and free planting/bonus combinations produced the expected balances. The normal cap limited a test to 9,990; Uncap sunshine allowed 10,025. Test balances were restored. |
| Auto collect | A Sunflower produced sun during the game update and the bank rose by 25 without a mouse click. |
| Seed recharge | The packet's actual active/refreshing flags changed as described above. |
| Plant replacement | A Wall-nut factory request produced the selected Snow Pea and retained row 5, column 1. |
| Firing | Real projectile generation increased with rapid fire; delay 2 still emitted shots instead of starving animations. |
| Projectile behavior | Chilling projectiles raised a target's chill timer. Always-butter shots raised its butter/stun timer. |
| Damage and protection | An invincible zombie retained its health while hit; one-hit mode killed the target. An invincible plant retained health while a zombie was eating it; disabling protection let bites reduce health, and fragile mode killed it. Zombotany protection blocked actual Peashooter-zombie projectiles, and disabling it allowed damage. |
| Movement and spawning | Freeze stopped measured movement. Five naturally spawned groups used the chosen lanes. The next wave advanced rather than merely changing a timer. Pause spawning held a countdown at 1,000; disabling it let the timer decrease to 967. |
| Mushrooms | An existing sleeping mushroom woke after enabling the control. |
| Special entities | Quiet jack prevented a forced-due jack-in-the-box from entering its pop sequence; disabling it let it explode. No-ice suppressed a Zomboni's ice timer; disabling it let the timer rise. Doom-shroom left no crater with No craters enabled and did leave one when disabled. |
| Level cleanup | Mower restoration yielded five live mowers, including six repeated paused restores. Clear horde removed the zombies; clear plants removed the plants through the native deletion routine. |
| Pace | All six settings changed the measured update rate, without modifying the protected pointer or crashing the game. |

The combined-load test kept **24 compatible controls enabled for 30 seconds**, with **6,287 live lawn updates**. It also advanced waves, created plants, changed pace six times and toggled firing hooks while the game ran. Every owned code span restored afterward, including the additional shooting guard. No runtime errors were recorded, the pointer remained unchanged and frame duration returned to 10.

The 24-control test includes scene-specific patches installed on the day lawn. This proves coexistence and restoration there; it does **not** establish fog rendering, Vasebreaker visibility or conveyor timing in their actual modes.

## Coverage limits and operating rules

All 39 main-window controls were reviewed and route through the verified runtime. The **82-test offline suite** includes GUI wiring, profile validation, randomized toggle orders, overlaps, rollback, immutable parameters, code boundaries, adapter generation, wrong-helper rejection and the new gameplay regressions. Passing those tests does not certify every visual effect or every possible stage combination.

Fog rendering, Vasebreaker visibility, conveyor timing, shovel interaction, the placement cursor/preview restrictions, seed-selection zombie preview and level completion still require individual checks in their appropriate gameplay contexts. Persistent stage/garden actions and saved-layout rebuilding retain the limits in [LAWN-STUDIO.md](LAWN-STUDIO.md); this audit did not rewrite the user's saved progress to exercise every stage. These are explicit remaining checks, not reported as successful gameplay tests.

Reset cannot undo entities created/deleted, damage already dealt, a level already completed or other one-time effects. A save backup was made before the broader effects tests. Native-call timeout or failed rollback still requires restarting PVZ. Use a fresh process after a crash, and use the rebuilt portable app with its matching CT rather than an older executable copied elsewhere.
