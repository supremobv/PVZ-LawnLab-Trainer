# PVZ TRAINER PRO

```
╔═══════════════════════════════════════════════════════════════╗
║  ██████╗ ██╗   ██╗███████╗    ████████╗██████╗  █████╗ ██╗   ║
║  ██╔══██╗██║   ██║╚══███╔╝    ╚══██╔══╝██╔══██╗██╔══██╗██║   ║
║  ██████╔╝██║   ██║  ███╔╝        ██║   ██████╔╝███████║██║   ║
║  ██╔═══╝ ╚██╗ ██╔╝ ███╔╝         ██║   ██╔══██╗██╔══██║██║   ║
║  ██║      ╚████╔╝ ███████╗       ██║   ██║  ██║██║  ██║██║   ║
║  ╚═╝       ╚═══╝  ╚══════╝       ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝   ║
╚═══════════════════════════════════════════════════════════════╝
```

> **A powerful memory trainer for Plants vs. Zombies (GOTY Edition)**

![Version](https://img.shields.io/badge/Version-3.0-00ff88?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.x-00ccff?style=for-the-badge&logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows-aa55ff?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-ffcc00?style=for-the-badge)

---

## Features

### Sun Cheats
| Cheat | Description |
|-------|-------------|
| Infinite Sun (9999) | Automatically set sun to 9999 |
| Collect +1000 Sun | Each sun pickup gives +1000 sun |
| Auto Collect Suns | Automatically collect falling suns |
| Free Planting | Plant without spending sun |
| Planting Gives Sun | Earn +2000 sun when planting |
| Lock Sun Amount | Lock sun to a custom amount |

### Plant Cheats
| Cheat | Description |
|-------|-------------|
| No Cooldown | Instant seed packet recharge |
| Plant Anywhere | Ignore placement restrictions |
| Plant Changer | Replace plants with any other plant |
| Invincible Plants | Plants can't be damaged |
| Bullet Changer | Change projectile types |
| Rapid Fire | Plants shoot without delay |
| Fast Shoot | Reduce shooting delay |

### Zombie Cheats
| Cheat | Description |
|-------|-------------|
| One Hit Kill | Zombies die instantly |
| Invincible Zombies | Zombies can't be killed |
| Freeze Zombies | Stop zombie movement |
| Stop Spawning | Pause zombie waves |
| Force Zombie Row | Spawn zombies in specific row |
| Kill All Zombies | Instantly kill all zombies on field |
| Spawn All Zombies | Spawn the entire wave at once |

### Game Options
| Cheat | Description |
|-------|-------------|
| Run in Background | Game continues when minimized |
| Remove Fog | Clear fog in night levels |
| See Vase Contents | See inside vases in Vasebreaker |
| Game Speed Control | Adjust game speed (0.2x to 10x) |

### Advanced Cheats
| Cheat | Description |
|-------|-------------|
| Mushrooms Stay Awake | Mushrooms don't sleep during day |
| Lock Butter | Kernel-pult always throws butter |
| No Crater | Doom-shroom leaves no crater |
| No Ice Trail | Zomboni doesn't leave ice |
| No Jack Explosion | Jack-in-Box won't explode |
| Unlock Sun Limit | Remove 9990 sun cap |
| Fast Conveyor Belt | Speed up conveyor belt |
| Lock Shovel | Keep shovel selected after use |
| Restore Mowers | Reset all lawn mowers |
| Instant Win | Complete level immediately |
| Clear All Plants | Remove all plants from field |

---

## Installation

### Requirements
- Windows 10/11
- Python 3.8 or higher
- Plants vs. Zombies (GOTY Edition recommended)

### Setup

1. **Clone or download this repository**
   ```bash
   git clone https://github.com/supremopkv/pvz-trainer.git
   cd pvz-trainer
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the trainer**
   ```bash
   python pvz_trainer.py
   ```

---

## Usage

1. **Launch Plants vs. Zombies** first
2. **Run the trainer** - it will auto-detect the game
3. **Enable cheats** by clicking the toggles
4. **Enjoy!**

### Status Indicator
- `[ OFFLINE ]` - Game not detected
- `[ ONLINE :: TRAINER READY ]` - Connected and ready
- `[ ACTIVE :: CHEAT NAME ]` - Cheat is enabled

---

## Screenshots

```
┌─────────────────────────────────────────────┐
│         PVZ TRAINER PRO  [v3.0]             │
│   [ PLANTS VS. ZOMBIES MEMORY TRAINER ]     │
├─────────────────────────────────────────────┤
│  [ CHEATS ]  [ ABOUT ]                      │
├─────────────────────────────────────────────┤
│  ▌ SUN CHEATS                               │
│  • Infinite Sun (9999)                      │
│  • Collect +1000 Sun on Pickup              │
│  • Auto Collect Falling Suns                │
├─────────────────────────────────────────────┤
│  ▌ PLANT CHEATS                             │
│  • No Cooldown (Instant Recharge)           │
│  • Plant Anywhere                           │
│  • Invincible Plants                        │
├─────────────────────────────────────────────┤
│  [ ONLINE :: TRAINER READY ]    by supremo  │
└─────────────────────────────────────────────┘
```

---

## Color Theme

The trainer features a modern **gaming-inspired dark theme**:

| Element | Color | Hex |
|---------|-------|-----|
| Background | Deep Black | `#0d0d0d` |
| Accent (Main) | Neon Green | `#00ff88` |
| Sun Cheats | Gold | `#ffcc00` |
| Plant Cheats | Bright Green | `#00ff44` |
| Zombie Cheats | Red | `#ff3333` |
| Advanced | Purple | `#aa55ff` |
| Info | Cyan | `#00ccff` |

---

## Supported Game Versions

| Version | Status |
|---------|--------|
| GOTY 1.2.0.1073 EN | Fully Supported |
| GOTY 1.2.0.1096 EN | Fully Supported |
| PVZ 1.0.0.1051 EN | Supported |
| PVZ 1.2.0.1065 EN | Supported |

---

## Technical Details

- **Language:** Python 3
- **GUI Framework:** Tkinter
- **Memory Access:** pymem library
- **Architecture:** x86 (32-bit)

### How It Works
The trainer reads and writes to the game's memory using the `pymem` library. It patches specific memory addresses to enable various cheats:

- **Infinite Sun:** Patches the sun counter memory address
- **No Cooldown:** NOPs the cooldown check instruction
- **One Hit Kill:** Modifies zombie health calculation
- **And more...**

---

## Disclaimer

This trainer is for **educational and personal use only**. Use at your own risk. The author is not responsible for any issues that may arise from using this software.

- For single-player use only
- Do not use in any competitive or online context
- Backup your save files before using

---

## Credits

```
╔════════════════════════════════════════╗
║      Developed by: supremopkv          ║
║      Version: 3.0                      ║
║      Built with: Python + Tkinter      ║
╚════════════════════════════════════════╝
```

### Special Thanks
- Plants vs. Zombies community
- Cheat Engine community for reverse engineering knowledge

### Reference & Inspiration
This trainer was developed with guidance from:

- **[PvZ Toolkit](https://github.com/lmintlcx/pvztoolkit)** by [@lmintlcx](https://github.com/lmintlcx)
  - An excellent C++ based PvZ trainer that provided invaluable reference for memory addresses and game mechanics
  - Many of the cheat implementations in this trainer were inspired by their work

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <b>[ HAPPY GAMING! ]</b>
</p>
