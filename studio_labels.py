"""Player-facing names, units and contextual instructions."""
from trainer_engine import PLANT_NAMES
from studio_models import ZOMBIES
HELMETS=['None','Traffic cone','Bucket','Football helmet','Digger hard hat','Giga-gargantuar red eyes','Headband','Bobsled helmet','Wall-nut head','Tall-nut head']
SHIELDS=['None','Screen door','Newspaper','Ladder']
GARDENS=['Main garden','Mushroom garden','Wheelbarrow (one-plant carrier)','Aquarium']
GROWTH=['Sprout (0)','Small (1)','Medium (2)','Mature (3)']
NEEDS=['No special need','Water','Fertilizer','Bug spray','Music / phonograph']
PRODUCERS={1,9,38,41}
SHOOTERS={0,5,7,8,10,13,18,28,31,32,34,39,40,42,43,44}
def named(values,index):return values[index]if type(index)is int and 0<=index<len(values)else f'Unknown ({index})'
def plant_name(index):
    text=named(PLANT_NAMES,index)
    return text.split(' - ',1)[-1]+f' (ID {index})'
def zombie_name(index):return ('Basic zombie'if index==0 else named(ZOMBIES,index))+f' (ID {index})'
def equipment(values,index):return named(values,index)+f' (ID {index})'
FIELD_LABELS={'health':'Current health (HP)','max_health':'Maximum health (HP)','attack_timer':'Ticks until next action','attack_interval':'Base action interval (ticks)',
 'armour':'Helmet durability (HP)','max_armour':'Maximum helmet durability (HP)','shield':'Held shield durability (HP)','max_shield':'Maximum shield durability (HP)',
 'speed':'Walking speed (pixels/tick)','chilled':'Slow / chill duration (ticks)','buttered':'Butter stun duration (ticks)','frozen':'Hard-freeze duration (ticks)'}
FIELD_HELP={'health':'Remaining body health. Cannot exceed Maximum health. To increase the limit, tick Maximum health and set it first.',
 'max_health':'The health ceiling for this one live plant or zombie.',
 'attack_timer':'A countdown: 0 means attempt the next action now. It is not damage or shots per second.',
 'attack_interval':'Base time between actions. 100 ticks is about one second at normal game pace. Global Rapid fire or Firing delay overrides shooter timing.',
 'armour':'Durability of the equipped cone, bucket or other head protection. It is not an equipment-type ID.',
 'max_armour':'Maximum durability of the existing helmet. This editor does not add a helmet to a bare-headed zombie.',
 'shield':'Durability of an existing screen door, newspaper or ladder. Body health and helmet health are separate.',
 'max_shield':'Maximum durability of the existing held shield. Spawn an equipped zombie to get a different shield type.',
 'speed':'0 stops horizontal movement; a normal walking zombie is often near 0.3. Range: 0–5 pixels per game tick. Special movement states can override this.',
 'chilled':'0 clears slowing. Positive values count down during play; 100 ticks ≈ 1 second at normal pace.',
 'buttered':'0 clears butter stun. Positive values stop the target for that many game ticks.',
 'frozen':'0 clears hard freezing. This is a timed status, not the global Freeze the horde control.'}
GUIDES={
 'player':('Edit one active local profile', 'Read first. Tick named progress fields or change the 20 achievement checkboxes, then Apply from PVZ Main Menu. Each Apply creates a backup. Unticked fields and player identity are preserved. Loading a trainer settings profile is separate from editing game progress.'),
 'lawn':('Build a lawn or spawn a saved setup', '1. Choose rectangle, whole lawn or an exact total quantity. Pick a plant and a rectangle: rows run top to bottom; columns run left to right. A 1×1 rectangle places one cell. Copies lets ordinary plants share a cell when stacking is enabled.<br>2. Open the visual planner, choose a brush and click cells. Right-click erases. Plan terrain only describes the saved layout; it does not change PVZ. Save the plan and build it later on a matching lawn. Capture current lawn saves plants already placed.<br>3. Zombie setups are named groups of types, lanes and spawn timings. Save a single group here, or mix types in Zombie waves. Created entities are not removed by Reset all.'),
 'entities':('Inspect one live plant or zombie', '1. Choose Plants or Zombies and refresh. “Type” means the species, for example Conehead (ID 2). The instance number identifies one live object.<br>2. Select a row, tick only the properties you want to change, then Apply checked changes. Greyed-out controls do not apply to that object.<br>3. HP is remaining durability, not an equipment ID. Raise the matching maximum first to allow a larger HP value. 100 ticks ≈ 1 second at normal pace.'),
 'waves':('Create a repeatable zombie test', 'A practice setup is a spawn schedule, not a game wave number. Each row is one group: type, lane, quantity, gap between zombies and delay before that group starts. Example: 5 Basic zombies in lane 1, 1,000 ms apart, delay 0 = one per second immediately.<br>Save the setup to reuse it. Run starts all groups on one shared clock; groups can overlap. Pause normal spawning in the main window for an isolated test. The separate Upcoming game wave section changes a future built-in wave, without spawning it now.'),
 'seeds':('Choose seed packets and future projectile behavior', 'Seed slot 1 is the leftmost card at the top of the game. Read the seed bank, choose a present slot and a named plant, then Apply. This changes the card, not plants already on the lawn. Duplicate testing permits the same plant in several slots.<br>Projectile effects change future shots from firing plants. They do not create a shooter. Shared damage affects every matching projectile type, including zombie weapons. One-hit knockout and Invincible zombies can override damage results.'),
 'garden':('Stages replace a battle; garden edits change saved progress', 'Adventure numbers 1–50 map to 1-1 through 5-10. Choosing another mode ignores the Adventure stage field. Launch replaces the current battle and may replace that mode’s saved run; an on-disk backup is created first.<br>For Zen Garden, read the profile and select a named plant. Garden slot is its position in your saved collection, not its plant-type ID. Water, fertilizer and growth are persistent changes. Mature plants do not need fertilizer; watering must meet the feeding requirement before growth advances.'),
 'backups':('Protect your progress', 'Create a backup before persistent experiments. A running-game backup contains files already saved on disk, not unsaved live memory. To restore, close PVZ, select a snapshot and Restore. A recovery backup is created first; only recognized PVZ save files are replaced.'),
 'profiles':('Save controls separately from game progress', 'A settings profile remembers trainer switches, numeric values and shortcuts. It is not a plant layout, zombie setup or game-save backup. Loading leaves controls off unless Activate saved controls is selected. One-time actions never auto-run. Hotkeys remain off until you enable them and work only while PVZ has focus.')}
EFFECT_HELP={0:'Normal pea: standard direct impact; it does not slow or stun.',1:'Snow pea: slows a hit zombie. This is chill, not an Ice-shroom hard freeze.',3:'Melon: native splash behavior around its impact.',5:'Winter melon: native splash and slowing; it does not hard-freeze.',6:'Fire pea: the game’s fire impact behavior. It is not a Cherry Bomb or a new explosion system.',12:'Butter: stuns the target for the game’s normal butter duration.'}
