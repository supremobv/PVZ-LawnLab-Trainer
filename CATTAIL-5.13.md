# LawnLab 5.13 — Cattail without Lily Pad

1. Connect LawnLab to the supported GOTY or Classic game.
2. Under **Plants**, enable **Cattail without Lily Pad**. It also enables **Direct upgrade planting**, because Cattail is an upgrade card.
3. Choose Cattail from your seed bank/scrolling deck, then click a clear land or pool cell. No Lily Pad is required there. You can also select Cattail (ID 43) in Lawn Studio's placement tools.
4. The plant uses the game's normal homing-spike targeting. It still needs a target before firing. No target or paused game means no shots.

Normal sun cost, recharge and occupied-cell checks still apply. This does not unlock an unowned seed packet. Roof cells still need a Flower Pot unless **No Lily Pad / Flower Pot needed** is enabled. Graves/craters and other game-specific restrictions are preserved; use Remove all graves when needed. Other aquatic plants retain their terrain restrictions.

Turning off Cattail without Lily Pad restores its normal terrain restriction for future planting; it does not remove Cattails already placed. Direct upgrade planting remains on. Turning off Direct upgrade planting automatically turns off this Cattail option, so the UI cannot claim that unsupported upgrade placement is enabled.

Live bulk placement skips automatic Lily Pads specifically for Cattail while this control is enabled. Studio's runtime formation validator also accepts Cattail on pool cells without a Lily Pad. Saved-plan editing keeps its ordinary strict support validation; include Lily Pads in reusable pool plans where the plan editor requires them.

## Verification

GOTY live checks confirmed the native placement reason changes from needs-upgrade to allowed on land, the native constructor produces Cattail ID 43, occupied cells remain rejected, and the planted Cattail emits homing spike projectiles (type 8). Turning off Direct upgrade planting disables the dependent option. Temporary test controls and created entities were cleaned up. Classic's separate instruction location and original bytes were verified; this release did not include a new Classic live firing test.

Automated checks cover dependencies, restoration, Studio placement, aquatic restrictions and selective pool support. Both CTs and address catalogs are regenerated for the 5.13 companion.
