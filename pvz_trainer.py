import pymem
import pymem.process
import tkinter as tk
from tkinter import messagebox, ttk
import threading
import time
import struct
import ctypes

# Plant names list (ID 0-52)
PLANT_NAMES = [
    "0 - Peashooter",
    "1 - Sunflower",
    "2 - Cherry Bomb",
    "3 - Wall-nut",
    "4 - Potato Mine",
    "5 - Snow Pea",
    "6 - Chomper",
    "7 - Repeater",
    "8 - Puff-shroom",
    "9 - Sun-shroom",
    "10 - Fume-shroom",
    "11 - Grave Buster",
    "12 - Hypno-shroom",
    "13 - Scaredy-shroom",
    "14 - Ice-shroom",
    "15 - Doom-shroom",
    "16 - Lily Pad",
    "17 - Squash",
    "18 - Threepeater",
    "19 - Tangle Kelp",
    "20 - Jalapeno",
    "21 - Spikeweed",
    "22 - Torchwood",
    "23 - Tall-nut",
    "24 - Sea-shroom",
    "25 - Plantern",
    "26 - Cactus",
    "27 - Blover",
    "28 - Split Pea",
    "29 - Starfruit",
    "30 - Pumpkin",
    "31 - Magnet-shroom",
    "32 - Cabbage-pult",
    "33 - Flower Pot",
    "34 - Kernel-pult",
    "35 - Coffee Bean",
    "36 - Garlic",
    "37 - Umbrella Leaf",
    "38 - Marigold",
    "39 - Melon-pult",
    "40 - Gatling Pea",
    "41 - Twin Sunflower",
    "42 - Gloom-shroom",
    "43 - Cattail",
    "44 - Winter Melon",
    "45 - Gold Magnet",
    "46 - Spikerock",
    "47 - Cob Cannon",
    "48 - Imitater",
    "49 - Explode-o-nut",
    "50 - Giant Wall-nut",
    "51 - Sprout",
    "52 - Left Peashooter",
]

# Row names for zombie spawning
ROW_NAMES = [
    "Row 1 (Top)",
    "Row 2",
    "Row 3 (Middle)",
    "Row 4",
    "Row 5 (Bottom)",
]


class PvZTrainer:
    def __init__(self):
        self.pm = None
        self.process_name = "popcapgame1.exe"
        self.base_address = None
        self.is_connected = False

        # Cheat states
        self.infinite_sun_active = False
        self.no_cooldown_active = False
        self.one_hit_kill_active = False
        self.collect_1000_sun_active = False
        self.prevent_spend_active = False
        self.planting_adds_sun_active = False
        self.show_all_zombies_active = False
        self.auto_collect_active = False

        # Addresses (Verified from CE script)
        self.sun_pointer_offset = 0x192390
        self.sun_final_offset = 0x5578
        self.cooldown_address = 0x91E55
        self.body_kill_address = 0x13E08B
        self.armor_kill_address = 0x1419FA
        self.collect_sun_address = 0x1E6E0
        self.collect_mov_address = 0x1E6F7
        self.plant_sub_instr = 0x1E844
        self.plant_sub_address = 0x1E846

        # Zombie-related addresses
        self.zombie_health_offset = 0xC8
        self.zombie_max_health_offset = 0xCC
        self.zombie_armor1_offset = 0xD0

        # Original bytes for restoration
        self.original_cooldown_bytes = bytes([0x7E, 0x14])
        self.original_body_bytes = bytes([0x8B, 0xB0, 0xC8, 0x00, 0x00, 0x00])
        self.original_armor_bytes = bytes([0x89, 0x8D, 0xD0, 0x00, 0x00, 0x00])
        self.original_collect_bytes = bytes([0x01, 0x88, 0x78, 0x55, 0x00, 0x00])
        self.original_collect_mov_bytes = bytes([0xC7, 0x80, 0x78, 0x55, 0x00, 0x00, 0x06, 0x27, 0x00, 0x00])
        self.original_plant_sub_bytes = bytes([0x89, 0xB7, 0x78, 0x55, 0x00, 0x00])
        self.original_sub_bytes = bytes([0x2B, 0xF3])

        # Code caves for injection
        self.body_cave = None
        self.armor_cave = None
        self.collect_cave = None
        self.plant_sub_cave = None
        self.collect_add_cave = None
        self.collect_mov_cave = None
        self._prev_prevent_spend_state = False
        self.auto_collect_cave = None
        self.auto_collect_patch_addr = 0x342EE
        self.auto_collect_return_addr = 0x342FD
        self.original_auto_collect_bytes = bytes([0x80, 0x7B, 0x50, 0x00, 0x75, 0x09])
        # Run-in-background state / originals (patches JE instructions)
        self.run_in_background_active = False
        self.original_background_bytes1 = bytes([0x0F, 0x84, 0xAC, 0x00, 0x00, 0x00])
        self.original_background_bytes2 = bytes([0x74, 0x40])
        # Plant-anywhere (patch JE -> NOP at offset +0x127EF)
        self.plant_anywhere_active = False
        self.plant_anywhere_offset = 0x127EF
        self.original_plant_anywhere_bytes = bytes([0x0F, 0x84, 0x20, 0x09, 0x00, 0x00])
        self.plant_anywhere_cave = None
        # Move-zombie-row feature
        self.move_zombie_row_active = False
        # try both the observed address and the CE script address
        self.move_zombie_row_active = False
        self.move_zombie_row_offsets = [0x1940C, 0x1936E]
        self.original_move_zombie_bytes = {}
        self.move_zombie_row_caves = {}
        self.move_zombie_row_value = 0  # default row 0
        # Plant changer feature - patches the instruction that reads plant type from seed packet
        # This is a safer approach than patching function entry
        self.plant_changer_active = False
        self.plant_changer_value = 0  # default plant id 0
        self.plant_changer_cave = None
        self.original_plant_changer_bytes = None
        self.plant_changer_patch_addr = None  # Address where we patch
        self.plant_changer_imm_offset = None  # Offset in cave where imm32 is stored
        # Offset where plant type is loaded - this is where "mov esi, [eax+0x28]" or similar happens
        # Common offsets for different PvZ versions:
        self.plant_changer_offsets = [0x12D54, 0x12D50, 0x12D58]  # Try multiple known offsets

        # Bullet changer feature - patches write of bullet type at [ebp+5C]
        self.bullet_changer_active = False
        self.bullet_changer_value = 0
        self.bullet_changer_cave = None
        self.original_bullet_bytes = None
        self.bullet_patch_addr = None
        self.bullet_imm_offset = None

        # Rapid fire (bypass shoot gate) - NOP out JNE after cmp [edi+90],1
        self.rapid_fire_active = False
        self.rapid_fire_jne_addr = None
        self.original_rapid_fire_bytes = None

        # Fast shoot (lower delay written to [esi+58]) via code cave
        self.fast_shoot_active = False
        self.fast_shoot_delay = 2
        self.fast_shoot_cave = None
        self.fast_shoot_patch_addr = None
        self.original_fast_shoot_bytes = None
        self.fast_shoot_imm_offset = None

        # Money changer (set coins/gold) via code cave
        self.money_changer_active = False
        self.money_amount = 99999
        self.money_cave = None
        self.money_patch_addr = None
        self.original_money_bytes = None
        self.money_imm_offset = None

        # New features: Instant Plant Death / Invincible Plants
        self.instant_plant_death_active = False
        self.invincible_plants_active = False
        self.plant_damage_offset = 0x140680  # add dword ptr [esi+40], -4
        self.original_plant_damage_bytes = bytes([0x83, 0x46, 0x40, 0xFC])
        # For cave-based instant kill
        self.plant_instant_cave = None
        self.plant_instant_patch_addr = None
        self.original_plant_instant_bytes = None

        # Invincible Zombies patches
        self.invincible_zombies_active = False
        self.zombie_sub_offset = 0x141CDA      # 2B 6C 24 20 -> 03 6C 24 20
        self.zombie_je1_offset = 0x142223      # 74 08 -> EB 08
        self.zombie_je2_offset = 0x142214      # 74 02 -> 90 90
        self.original_zombie_sub_bytes = bytes([0x2B, 0x6C, 0x24, 0x20])
        self.original_zombie_je1_bytes = bytes([0x74, 0x08])
        self.original_zombie_je2_bytes = bytes([0x74, 0x02])

        # ZomBotany unhittable plants
        self.unhittable_plants_active = False
        self.zombotany_je_offset = 0x71686     # 74 75 -> EB 75
        self.original_zombotany_je_bytes = bytes([0x74, 0x75])

        # Sun apply patch (force sun to imm32 at tick site)
        self.sun_apply_cave = None
        self.sun_apply_patch_addr = None
        self.sun_apply_imm_offset = None
        self.original_sun_apply_bytes = None

        # Fallback sun patches (add/cmp sites)
        self.sun_add_cave = None
        self.sun_add_patch_addr = None
        self.sun_add_imm_offset = None
        self.original_sun_add_bytes = None

        self.sun_cmp_cave = None
        self.sun_cmp_patch_addr = None
        self.sun_cmp_imm_offset = None
        self.original_sun_cmp_bytes = None

        # Sun clamp imm patch at base+0x1E6F7 (C7 80 78 55 00 00 06 27 00 00)
        self.sun_clamp_addr = None
        self.original_sun_clamp_bytes = None

        # Sun lock (continuous writer) to enforce amount immediately
        self.sun_lock_active = False
        self.sun_lock_amount = 9999
        self._sun_lock_thread = None

        # ===== NEW FEATURES FROM PVZ TOOLKIT =====
        # Game Speed Control
        self.game_speed_active = False
        self.game_speed_value = 10  # Default 10ms per frame (normal speed)
        self.original_game_speed = 10

        # No Fog (clear fog in night levels)
        self.no_fog_active = False
        self.no_fog_offset = 0x1A5F88  # je -> nop nop (74 XX -> 90 90)
        self.original_no_fog_bytes = None

        # Stop Spawning (pause zombie waves) - multiple version support
        self.stop_spawning_active = False
        # Multiple offsets for different versions (je 0x74 -> jmp 0xEB)
        self.stop_spawning_offsets = [
            0x290DC,  # GOTY 1.2.0.1073 EN
            0x2A12C,  # GOTY 1.2.0.1096 EN
            0x1FE2F,  # Alternative
            0x21F1F,  # PVZ 1.0.0.1051 EN
            0x2663C,  # PVZ 1.2.0.1065 EN
        ]
        self.stop_spawning_offset = None  # Will be detected
        self.original_stop_spawning_bytes = None

        # Stop/Freeze Zombies (uses two patches) - multiple version support
        self.stop_zombies_active = False
        # Different versions have different addresses
        # Format: (offset, original_byte, patch_byte)
        self.stop_zombies_version_offsets = [
            # GOTY 1.2.0.1073 EN (confirmed working with stop_spawning 0x290DC)
            [(0x13B433, 0x64, 0x54), (0x13B43C, 0x44, 0x54)],
            # GOTY 1.2.0.1096 EN
            [(0x13C4BB, 0x64, 0x54), (0x13C4C4, 0x44, 0x54)],
            # PVZ 1.0.0.1051 EN
            [(0x12AB2B, 0x64, 0x54), (0x12AB34, 0x44, 0x54)],
            # PVZ 1.2.0.1065 EN
            [(0x12F24B, 0x64, 0x54), (0x12F254, 0x44, 0x54)],
        ]
        self.stop_zombies_offsets = None  # Will be detected
        self.original_stop_zombies_bytes = None

        # call_put_zombie offsets for different versions
        self.call_put_zombie_offsets = [
            0x2CC90,  # GOTY 1.2.0.1073 EN
            0x2DCE0,  # GOTY 1.2.0.1096 EN
            0x20DC0,  # PVZ 1.0.0.1051 EN
            0x2A151,  # PVZ 1.2.0.1065 EN
        ]

        # Lock Butter (Kernel-pult always throws butter)
        self.lock_butter_active = False
        self.lock_butter_offset = 0xE963C  # jne -> jmp
        self.original_lock_butter_bytes = None

        # Mushrooms Awake (don't fall asleep during day)
        self.mushrooms_awake_active = False
        self.mushrooms_awake_offset = 0x12DD5  # skip sleep check
        self.original_mushrooms_awake_bytes = None

        # No Crater (Doom-shroom doesn't leave craters)
        self.no_crater_active = False
        self.no_crater_offset = 0xE6F63  # skip crater creation
        self.original_no_crater_bytes = None

        # See Vase (see contents in Vasebreaker)
        self.see_vase_active = False
        self.see_vase_offset = 0x1B59E4  # force vase transparency
        self.original_see_vase_bytes = None

        # Zombie Not Explode (jack-in-box/jalapeno zombie)
        self.zombie_not_explode_active = False
        self.zombie_not_explode_offset = 0x142FD4
        self.original_zombie_not_explode_bytes = None

        # ===== ADDITIONAL FEATURES FROM PVZTOOLKIT =====
        # No Ice Trail (Zomboni doesn't leave ice)
        # GOTY 1.2.0.1073: {0x0053b0b0, {0xc3}, {0x51}} and {0x004222ea, {0xeb}, {0x75}}
        self.no_ice_trail_active = False
        self.no_ice_trail_offset1 = 0x13B0B0  # 0x53b0b0 - 0x400000
        self.no_ice_trail_offset2 = 0x222EA   # 0x4222ea - 0x400000  
        self.original_no_ice_trail_bytes1 = None
        self.original_no_ice_trail_bytes2 = None

        # Zombie Not Explode (Jack-in-the-Box won't explode)
        # GOTY 1.2.0.1073: {{0x0053718c, {0x81}, {0x8f}}, {0x00537c6d, {0x81}, {0x85}}}
        self.zombie_not_explode_offset1 = 0x13718C  # 0x53718c - 0x400000
        self.zombie_not_explode_offset2 = 0x137C6D  # 0x537c6d - 0x400000
        self.original_zombie_not_explode_bytes1 = None
        self.original_zombie_not_explode_bytes2 = None

        # Unlock Sun Limit (remove 9990 cap)
        # GOTY 1.2.0.1073: {0x0041e6f5, {0xeb}, {0x7e}}
        self.unlock_sun_limit_active = False
        self.unlock_sun_limit_offset = 0x1E6F5  # 0x41e6f5 - 0x400000
        self.original_unlock_sun_limit_bytes = None

        # Fast Belt (conveyor belt moves faster)
        # GOTY 1.2.0.1073: {{0x004257ff, {0x80}, {0x8f}}, {0x004948ae, {0x33}, {0x85}}}
        self.fast_belt_active = False
        self.fast_belt_offset1 = 0x257FF   # 0x4257ff - 0x400000
        self.fast_belt_offset2 = 0x948AE   # 0x4948ae - 0x400000
        self.original_fast_belt_bytes1 = None
        self.original_fast_belt_bytes2 = None

        # Lock Shovel (keep shovel selected after use)
        # GOTY 1.2.0.1073: {0x00414d53, {0x39}, {0x89}}
        self.lock_shovel_active = False
        self.lock_shovel_offset = 0x14D53  # 0x414d53 - 0x400000
        self.original_lock_shovel_bytes = None

        # Restore Lawn Mowers (reset all lawn mowers)
        self.lawn_mower_initialized = False

        # Instant Win (complete level immediately)
        self.instant_win_active = False

    def check_game_running(self):
        """Check if the game is running without attaching"""
        # Try pid lookup first (less intrusive), then fall back to opening process
        try:
            try:
                pid = pymem.process.pid_from_name(self.process_name)
                if pid and pid > 0:
                    return True
            except Exception:
                pass

            pm_temp = pymem.Pymem(self.process_name)
            pm_temp.close_process()
            return True
        except Exception:
            return False

    def attach_process(self):
        """Attach to the game process"""
        try:
            self.pm = pymem.Pymem(self.process_name)
            self.base_address = pymem.process.module_from_name(
                self.pm.process_handle,
                self.process_name
            ).lpBaseOfDll
            self.is_connected = True
            print(f"[Attach] {self.process_name} base_address={hex(self.base_address)}")
            return True
        except Exception as e:
            # log attach error for diagnostics
            print(f"[Attach] failed: {e}")
            self.is_connected = False
            return False

    def get_game_board(self):
        """Get the game board pointer for zombie spawning"""
        try:
            # Try multiple lawn offsets for different game versions
            lawn_offsets = [
                0x329670,  # GOTY 1.2.0.1073 EN
                0x2A9EC0,  # Some versions
                0x329688,  # Alternative GOTY offset
                0x191A28,  # Other versions
                0x192390,
                0x191A04,
            ]
            for game_offset in lawn_offsets:
                try:
                    game_ptr_addr = self.base_address + game_offset
                    game_ptr = struct.unpack('<I', self.pm.read_bytes(game_ptr_addr, 4))[0]

                    if game_ptr and 0x10000 < game_ptr < 0x7FFFFFFF:
                        # Try both board offsets
                        for board_offset in [0x868, 0x768]:
                            board_ptr_addr = game_ptr + board_offset
                            board_ptr = struct.unpack('<I', self.pm.read_bytes(board_ptr_addr, 4))[0]

                            if board_ptr and 0x10000 < board_ptr < 0x7FFFFFFF:
                                print(f"[GetBoard] Lawn: 0x{game_offset:X}, Board offset: 0x{board_offset:X}")
                                return game_ptr, board_ptr
                except:
                    continue
            return None, None
        except:
            return None, None

    def refresh_zombies_preview(self, game_ptr, board_ptr):
        """
        Refreshes the zombie preview (street view) by calling internal game functions.
        Based on PvZ Toolkit implementation.
        """
        # Offsets for GOTY 1.2.0.1073
        hack_addr = self.base_address + 0x3D363
        remove_addr = self.base_address + 0x108E0
        place_addr = self.base_address + 0x3D350
        cut_scene_offset = 0x174
        
        # 1. Apply patch (0x85 -> 0x80)
        try:
            original_byte = self.pm.read_bytes(hack_addr, 1)
            if original_byte != b'\x85':
                print(f"[RefreshPreview] Warning: Unexpected byte at hack_addr: {original_byte.hex()}. Expected 85.")
                # Try to find the correct offset if possible, or proceed with caution
                # For now, we proceed but log it.
            
            self.pm.write_bytes(hack_addr, b'\x80', 1)
        except Exception as e:
            print(f"[RefreshPreview] Failed to apply patch: {e}")
            return

        addr = None
        try:
            # 2. Prepare shellcode
            # We need to call:
            # remove_cutscene_zombies(board_ptr in EBX)
            # place_street_zombies(cut_scene_ptr pushed on stack)
            
            # Read cut_scene pointer
            cut_scene_ptr = self.pm.read_int(board_ptr + cut_scene_offset)
            
            shellcode = b''
            
            # MOV EBX, board_ptr
            shellcode += b'\xBB' + struct.pack('<I', board_ptr)
            
            # MOV EAX, remove_addr
            shellcode += b'\xB8' + struct.pack('<I', remove_addr)
            # CALL EAX
            shellcode += b'\xFF\xD0'
            
            # PUSH cut_scene_ptr
            shellcode += b'\x68' + struct.pack('<I', cut_scene_ptr)
            
            # MOV EAX, place_addr
            shellcode += b'\xB8' + struct.pack('<I', place_addr)
            # CALL EAX
            shellcode += b'\xFF\xD0'
            
            # RET
            shellcode += b'\xC3'
            
            # Execute shellcode
            addr = self.pm.allocate(len(shellcode))
            self.pm.write_bytes(addr, shellcode, len(shellcode))
            thread_handle = self.pm.start_thread(addr)
            
            # Wait for thread to finish (essential for the patch to work during execution)
            if thread_handle:
                ctypes.windll.kernel32.WaitForSingleObject(thread_handle, 0xFFFFFFFF)
                ctypes.windll.kernel32.CloseHandle(thread_handle)
            
            print("[RefreshPreview] Refreshed street view zombies")
            
        except Exception as e:
            print(f"[RefreshPreview] Error executing shellcode: {e}")
        finally:
            # 3. Restore patch
            try:
                self.pm.write_bytes(hack_addr, original_byte, 1)
            except:
                pass
            
            # Free memory
            if addr:
                try:
                    self.pm.free(addr)
                except:
                    pass

    def toggle_show_all_zombies(self, state):
        """
        Spawn all zombie types on the field using code injection.
        Calls the game's native PutZombie function.
        """
        if not self.pm:
            if not self.attach_process():
                return False

        try:
            game_ptr, board_ptr = self.get_game_board()
            if not board_ptr:
                messagebox.showwarning("Warning",
                    "Could not find game board!\n\n"
                    "Make sure you are IN A LEVEL (not main menu).")
                return False

            # GOTY 1.2.0.1073: spawn_type (33 bools) is at board + 0x54D4
            spawn_type_offset = 0x54D4

            if state:
                print(f"[ShowZombies] Game: 0x{game_ptr:X}, Board: 0x{board_ptr:X}")

                # Save original spawn_type if not already saved
                if not hasattr(self, 'original_spawn_type') or self.original_spawn_type is None:
                    try:
                        self.original_spawn_type = self.pm.read_bytes(board_ptr + spawn_type_offset, 33)
                    except:
                        self.original_spawn_type = None

                # 1. Enable ALL zombie types in spawn_type
                all_zombies = list(range(33)) # 0 to 32
                spawn_type = bytearray(33)
                for z in all_zombies:
                    spawn_type[z] = 1
                self.pm.write_bytes(board_ptr + spawn_type_offset, bytes(spawn_type), 33)
                print(f"[ShowZombies] Enabled all {len(all_zombies)} zombie types")

                # 2. Refresh the street view (cutscene)
                self.refresh_zombies_preview(game_ptr, board_ptr)

                self.show_all_zombies_active = True
                return True
            else:
                # Restore original spawn_type
                if hasattr(self, 'original_spawn_type') and self.original_spawn_type:
                    self.pm.write_bytes(board_ptr + spawn_type_offset, self.original_spawn_type, 33)
                    print("[ShowZombies] Restored original zombie types")
                    self.original_spawn_type = None
                
                # Refresh to show restored zombies
                self.refresh_zombies_preview(game_ptr, board_ptr)

                self.show_all_zombies_active = False
                return True

        except Exception as e:
            print(f"[ShowZombies] Error: {e}")
            messagebox.showerror("Error", f"Failed to spawn zombies: {str(e)}")
            return False

    def spawn_zombies_natural(self, board_ptr):
        """Spawn zombies using the game's natural spawn system - SAFE version"""
        try:
            # GOTY 1.2.0.1073 offsets
            # spawn_type = board + 0x54D4 (33 bools - which zombies are enabled)

            print("[SpawnNatural] Enabling zombie types for spawning...")

            # Only use basic zombie types that work on ALL levels (no pool/roof specific)
            basic_zombies = [
                0,   # Zombie (Normal)
                2,   # Conehead
                4,   # Buckethead
                5,   # Newspaper
                7,   # Football
                21,  # Ladder
                23,  # Gargantuar
            ]

            # Step 1: Enable zombie types in spawn_type (this is SAFE)
            spawn_type_offset = 0x54D4
            try:
                spawn_type = bytearray(33)
                for z in basic_zombies:
                    if 0 <= z < 33:
                        spawn_type[z] = 1
                self.pm.write_bytes(board_ptr + spawn_type_offset, bytes(spawn_type), 33)
                print(f"[SpawnNatural] Enabled {len(basic_zombies)} basic zombie types")
            except Exception as e:
                print(f"[SpawnNatural] spawn_type failed: {e}")
                return False

            # Note: NOT writing to spawn_list or timers as that causes crashes
            # The spawn_type change affects what zombies appear in upcoming waves

            print("[SpawnNatural] Zombie types configured!")
            print("[SpawnNatural] New zombie types will appear in the next wave.")
            print("[SpawnNatural] (Different/stronger zombies will now spawn)")
            return True

        except Exception as e:
            print(f"[SpawnNatural] Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def spawn_zombies_safe_inject(self, game_ptr, board_ptr):
        """Spawn zombies using safe code injection with game loop blocking"""
        try:
            import ctypes
            import time

            kernel32 = ctypes.windll.kernel32

            # GOTY 1.2.0.1073 EN addresses
            # block_main_loop: 0x005d6c6e -> offset 0x1D6C6E
            # Original: 0xC8, Hack: 0xFE (pauses game loop)
            block_loop_offset = 0x1D6C6E
            block_loop_addr = self.base_address + block_loop_offset

            # call_put_zombie: 0x0042bd60 -> offset 0x2BD60 (GOTY 1.2.0.1073)
            call_put_zombie = self.base_address + 0x2BD60

            # Find challenge pointer (board + 0x160)
            challenge_ptr = None
            for offset in [0x160, 0x148]:
                try:
                    ptr = self.pm.read_int(board_ptr + offset)
                    if ptr and 0x10000 < ptr < 0x7FFFFFFF:
                        challenge_ptr = ptr
                        break
                except:
                    continue

            if not challenge_ptr:
                challenge_ptr = board_ptr

            print(f"[SafeInject] Challenge: 0x{challenge_ptr:X}")

            # Get number of rows
            num_rows = 5
            for row_offset in [0x5F0, 0x5D8]:
                try:
                    # Check row count
                    for i in range(6):
                        row_type = self.pm.read_int(board_ptr + row_offset + i * 4)
                        if row_type == 0:  # No row
                            num_rows = i
                            break
                    if num_rows > 0:
                        break
                except:
                    pass

            print(f"[SafeInject] Rows: {num_rows}")

            # Zombie types to spawn
            zombie_types = [0, 2, 4, 7, 21, 23]  # Normal, Cone, Bucket, Football, Ladder, Gargantuar

            # Step 1: Block the game loop
            print("[SafeInject] Blocking game loop...")
            orig_byte = self.pm.read_bytes(block_loop_addr, 1)
            self.pm.write_bytes(block_loop_addr, bytes([0xFE]), 1)
            time.sleep(0.05)  # Wait for game to reach block point

            spawned = 0

            try:
                # Step 2: Allocate memory for shellcode
                code_addr = kernel32.VirtualAllocEx(
                    self.pm.process_handle,
                    None,
                    0x1000,
                    0x3000,  # MEM_COMMIT | MEM_RESERVE
                    0x40    # PAGE_EXECUTE_READWRITE
                )

                if not code_addr:
                    print("[SafeInject] Failed to allocate memory")
                    return 0

                print(f"[SafeInject] Code at 0x{code_addr:X}")

                # Step 3: Build shellcode for ALL zombies at once (safer)
                asm = bytearray()

                # NOTE: We intentionally do not use pushad/popad here.
                # Some PvZ internal calls expect a sane stack/register state;
                # also, if the callee ever doesn't clean args, popad would crash.

                for zombie_type in zombie_types:
                    for row in range(num_rows):
                        # Valid columns are 0..8 (9 columns total). Using 9 can corrupt memory.
                        col = 8  # Right side

                        # PutZombie expects:
                        # push col
                        # push type
                        # eax = row
                        # ecx = challenge_ptr (or board_ptr if challenge is null)
                        # call PutZombie

                        # push col
                        asm += bytes([0x68]) + struct.pack('<I', col)
                        # push zombie_type
                        asm += bytes([0x68]) + struct.pack('<I', zombie_type)
                        # mov eax, row
                        asm += bytes([0xB8]) + struct.pack('<I', row)

                        # Resolve board/challenge pointers inside the remote thread:
                        # edx = game_ptr
                        # edx = [edx + 0x868]  (board)
                        # ecx = [edx + 0x160]  (challenge)
                        # if ecx == 0: ecx = edx
                        asm += bytes([0xBA]) + struct.pack('<I', game_ptr)          # mov edx, imm32
                        asm += bytes([0x8B, 0x92]) + struct.pack('<I', 0x868)      # mov edx, [edx+0x868]
                        asm += bytes([0x8B, 0x8A]) + struct.pack('<I', 0x160)      # mov ecx, [edx+0x160]
                        asm += bytes([0x85, 0xC9])                                  # test ecx, ecx
                        asm += bytes([0x75, 0x02])                                  # jnz +2
                        asm += bytes([0x8B, 0xCA])                                  # mov ecx, edx
                        # call call_put_zombie (relative)
                        call_from = code_addr + len(asm) + 5
                        rel = call_put_zombie - call_from
                        asm += bytes([0xE8]) + struct.pack('<i', rel)
                        # Note: PutZombie is likely __thiscall or similar, callee cleans stack

                        spawned += 1

                # ret
                asm += bytes([0xC3])

                print(f"[SafeInject] Shellcode size: {len(asm)} bytes")

                # Write shellcode
                self.pm.write_bytes(code_addr, bytes(asm), len(asm))

                # Execute via remote thread (single call for all zombies)
                thread = kernel32.CreateRemoteThread(
                    self.pm.process_handle,
                    None, 0, code_addr, None, 0, None
                )

                if thread:
                    result = kernel32.WaitForSingleObject(thread, 5000)
                    kernel32.CloseHandle(thread)
                    if result == 0:
                        print(f"[SafeInject] Executed successfully")
                    else:
                        print(f"[SafeInject] Execution timeout or error")
                        spawned = 0

                # Free memory
                kernel32.VirtualFreeEx(self.pm.process_handle, code_addr, 0, 0x8000)

            finally:
                # Step 4: Restore game loop
                print("[SafeInject] Restoring game loop...")
                self.pm.write_bytes(block_loop_addr, orig_byte, 1)

            print(f"[SafeInject] Done! Spawned {spawned} zombies")
            return spawned

        except Exception as e:
            print(f"[SafeInject] Error: {e}")
            import traceback
            traceback.print_exc()
            # Make sure to restore game loop on error
            try:
                self.pm.write_bytes(block_loop_addr, bytes([0xC8]), 1)
            except:
                pass
            return 0

    def spawn_all_zombies_now(self):
        """
        Spawns one of EVERY zombie type on the lawn immediately.
        Uses safe injection method.
        """
        if not self.pm:
            if not self.attach_process():
                return False

        try:
            game_ptr, board_ptr = self.get_game_board()
            if not board_ptr:
                messagebox.showwarning("Warning", "Could not find game board! Enter a level first.")
                return False

            # Use spawn_zombies_safe_inject logic but with ALL types
            import ctypes
            import time
            kernel32 = ctypes.windll.kernel32

            # GOTY 1.2.0.1073 EN addresses:
            # call_put_zombie: 0x0042bd60 -> offset 0x2BD60
            # Calling convention (thiscall):
            #   push col
            #   push type
            #   mov eax, row
            #   ecx = challenge pointer (this)
            #   call put_zombie
            call_put_zombie = self.base_address + 0x2BD60
            
            # Static addresses
            lawn_static_addr = self.base_address + 0x329670

            # call_put_zombie: 0x0042bd60 -> offset 0x2BD60 (GOTY 1.2.0.1073)
            # 0x2CC90 is for GOTY 1.1.0.1056 ZH
            call_put_zombie = self.base_address + 0x2BD60

            # Find challenge pointer
            challenge_ptr = None
            for offset in [0x160, 0x148]:
                try:
                    ptr = self.pm.read_int(board_ptr + offset)
                    if ptr and 0x10000 < ptr < 0x7FFFFFFF:
                        challenge_ptr = ptr
                        break
                except:
                    continue
            if not challenge_ptr:
                challenge_ptr = board_ptr

            # Get number of rows
            num_rows = 5
            try:
                # Try to read row count from board + 0x5D8 (row_type array)
                # Actually, let's just assume 5 or 6 based on scene
                scene = self.pm.read_int(board_ptr + 0x554C)
                if scene == 2 or scene == 3: # Pool / Fog
                    num_rows = 6
            except:
                pass

            # Check GameUI to ensure we are in a level
            # GameUI offset: 0x7FC (GOTY 1.2.0.1073)
            # 2 = Playing, 3 = Playing (IZ?), 1 = Main Menu, 4 = Seed Selection?
            # 15 = Playing (Observed by user in GOTY 1.2.0.1073)
            try:
                game_ui = self.pm.read_int(game_ptr + 0x7FC)
                # Allow 2, 3, and 15 (User reported 15 while on lawn)
                if game_ui not in [2, 3, 15]:
                    print(f"[SpawnAllNow] GameUI is {game_ui} (not 2, 3, or 15). Aborting spawn.")
                    messagebox.showwarning("Warning", f"You must be IN A LEVEL to spawn zombies!\nCurrent UI State: {game_ui}")
                    return 0
            except:
                pass

            # Get allowed zombies for this level (spawn_type array)
            # This ensures we only spawn zombies that belong to the current level
            # GOTY 1.2.0.1073: spawn_type (33 bools) is at board + 0x54D4
            spawn_type_offset = 0x54D4
            try:
                allowed_bytes = self.pm.read_bytes(board_ptr + spawn_type_offset, 33)
                zombie_types = [i for i, val in enumerate(allowed_bytes) if val]
                print(f"[SpawnAllNow] Found {len(zombie_types)} allowed zombie types: {zombie_types}")
            except Exception as e:
                print(f"[SpawnAllNow] Failed to read allowed zombies: {e}")
                zombie_types = [0, 2, 4, 7] # Fallback to basic

            # Use the level's allowed zombies, but filter out only the truly crashy ones
            # Zombie IDs:
            # 0=Normal, 1=Flag, 2=Conehead, 3=Pole Vault, 4=Buckethead,
            # 5=Newspaper, 6=Screen Door, 7=Football, 8=Dancing, 9=Backup Dancer,
            # 10-12=Ducky Tube variants, 13=Zomboni, 14=Dolphin, 15=Snorkel,
            # 16=Jack-in-box, 17=Balloon, 18=Digger, 19=Pogo, 20=Yeti,
            # 21=Bungee, 22=Ladder, 23=Catapult, 24=Gargantuar, 25=Imp,
            # 26-31=ZomBotany, 32=Giga-gargantuar
            
            # Only these are known to crash or cause issues:
            always_unsafe = [
                25,  # Dr. Zomboss (only works in boss fight)
                32,  # Giga-gargantuar (can be unstable)
            ]
            
            try:
                scene = self.pm.read_int(board_ptr + 0x554C)
                print(f"[SpawnAllNow] Scene: {scene}")
            except:
                scene = 0
            
            # Filter out only the truly unsafe ones
            zombie_types = [z for z in zombie_types if z not in always_unsafe]
            print(f"[SpawnAllNow] Safe zombie types: {zombie_types}")

            if not zombie_types:
                print("[SpawnAllNow] No safe zombies available for this level!")
                messagebox.showinfo("Info", "No safe zombies can be spawned on this level.\n\nThis level only allows special zombie types that cannot be safely spawned.")
                return 0

            spawned = 0
            
            # Use SAFE approach: Write zombies directly to spawn_list memory
            # This triggers natural zombie spawning without calling game functions
            
            # spawn_list is at board + 0x6B4 - array of 2000 ints (zombie types to spawn)
            # We write zombie types there and the game will spawn them naturally
            spawn_list_offset = 0x6B4
            
            try:
                # Build spawn list - put our zombies at the start
                spawn_data = bytearray()
                for zombie_type in zombie_types:
                    # Add each zombie type multiple times across rows
                    for _ in range(num_rows):
                        spawn_data += struct.pack('<i', zombie_type)
                        spawned += 1
                
                # Fill rest with -1 (empty/no spawn)
                while len(spawn_data) < 2000 * 4:
                    spawn_data += struct.pack('<i', -1)
                
                # Write to spawn_list
                self.pm.write_bytes(board_ptr + spawn_list_offset, bytes(spawn_data[:2000*4]), 2000*4)
                print(f"[SpawnAllNow] Wrote {spawned} zombies to spawn_list")
                
                # Trigger immediate spawn by setting spawn countdown to 0
                # spawn_countdown is typically near spawn_list
                for countdown_offset in [0x6B0, 0x559C, 0x55A0]:
                    try:
                        self.pm.write_int(board_ptr + countdown_offset, 0)
                    except:
                        pass
                
            except Exception as e:
                print(f"[SpawnAllNow] Error writing spawn_list: {e}")
                return 0

            print(f"[SpawnAllNow] Spawned {spawned} zombies")
            return True

        except Exception as e:
            print(f"[SpawnAllNow] Error: {e}")
            return False

    def spawn_zombies_via_memory(self, game_ptr, board_ptr):
        """Spawn zombies by directly writing to zombie array memory (safe method)"""
        try:
            # GOTY zombie struct size is 0x168, older is 0x15C
            ZOMBIE_STRUCT_SIZE = 0x168

            # Read zombie array info
            zombie_array = None
            zombie_count_max = 0

            for zombie_offset, count_offset in [(0xA8, 0xAC), (0x90, 0x94)]:
                try:
                    arr = self.pm.read_int(board_ptr + zombie_offset)
                    cnt = self.pm.read_int(board_ptr + count_offset)
                    if arr and 0x10000 < arr < 0x7FFFFFFF and 0 < cnt < 1000:
                        zombie_array = arr
                        zombie_count_max = cnt
                        print(f"[SpawnMem] Zombie array at 0x{arr:X}, max: {cnt}")
                        break
                except:
                    continue

            if not zombie_array:
                print("[SpawnMem] Could not find zombie array")
                return 0

            # Get number of rows
            num_rows = 5
            for row_offset in [0x5C0, 0x5A8]:
                try:
                    rows = self.pm.read_int(board_ptr + row_offset)
                    if 1 <= rows <= 6:
                        num_rows = rows
                        break
                except:
                    pass

            # Zombie types to spawn
            zombie_types = [0, 2, 4, 7, 21, 23]  # Normal, Cone, Bucket, Football, Ladder, Gargantuar

            # Zombie health values
            health_map = {
                0: 270,    # Normal
                2: 640,    # Conehead
                4: 1370,   # Buckethead
                5: 500,    # Newspaper
                6: 1170,   # Screen Door
                7: 2000,   # Football
                8: 500,    # Dancing
                17: 1100,  # Digger
                18: 500,   # Pogo
                21: 850,   # Ladder
                23: 3000,  # Gargantuar
            }

            # Row Y positions
            row_y = {0: 50, 1: 150, 2: 250, 3: 350, 4: 450, 5: 550}

            spawned = 0

            # Find empty zombie slots and fill them
            for i in range(zombie_count_max):
                zombie_addr = zombie_array + i * ZOMBIE_STRUCT_SIZE

                try:
                    # Check if this slot is dead/empty (dead flag at +0xEC)
                    is_dead = self.pm.read_bool(zombie_addr + 0xEC)

                    if is_dead:
                        # This slot is available, spawn a zombie
                        row = spawned % num_rows
                        zombie_type = zombie_types[spawned % len(zombie_types)]
                        health = health_map.get(zombie_type, 270)

                        # Write zombie data
                        # +0x18: Zombie type
                        self.pm.write_int(zombie_addr + 0x18, zombie_type)

                        # +0x1C: Phase (0 = normal)
                        self.pm.write_int(zombie_addr + 0x1C, 0)

                        # +0x28: Row
                        self.pm.write_int(zombie_addr + 0x28, row)

                        # +0x2C: X position (float) - right side of screen
                        x_pos = 800.0 + (spawned // num_rows) * 50
                        self.pm.write_bytes(zombie_addr + 0x2C, struct.pack('<f', x_pos), 4)

                        # +0x30: Y position (float)
                        y_pos = float(row_y.get(row, 250))
                        self.pm.write_bytes(zombie_addr + 0x30, struct.pack('<f', y_pos), 4)

                        # +0xC8: Current health
                        self.pm.write_int(zombie_addr + 0xC8, health)

                        # +0xCC: Max health
                        self.pm.write_int(zombie_addr + 0xCC, health)

                        # +0xEC: Dead flag = False
                        self.pm.write_bool(zombie_addr + 0xEC, False)

                        # +0x28: Status (for walking)
                        self.pm.write_int(zombie_addr + 0x20, 0)

                        spawned += 1
                        print(f"[SpawnMem] Spawned zombie type {zombie_type} at row {row}")

                        if spawned >= len(zombie_types) * num_rows:
                            break

                except Exception as e:
                    continue

            print(f"[SpawnMem] Spawned {spawned} zombies")
            return spawned

        except Exception as e:
            print(f"[SpawnMem] Error: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def trigger_zombie_wave(self, board_ptr):
        """Spawn zombies by writing to spawn_list and triggering spawn"""
        try:
            # GOTY 1.2.0.1073 offsets:
            # spawn_type = board + 0x54EC (33 bools for which zombies can spawn)
            # spawn_list = board + 0x6CC (2000 ints for spawn queue)

            print("[SpawnZombies] Writing spawn configuration...")

            # Zombie types to spawn
            zombie_types = [
                0,   # Zombie (Normal)
                1,   # Flag Zombie
                2,   # Conehead
                3,   # Pole Vaulting
                4,   # Buckethead
                5,   # Newspaper
                6,   # Screen Door
                7,   # Football
                8,   # Dancing
                11,  # Snorkel
                12,  # Zomboni
                14,  # Dolphin Rider
                15,  # Jack-in-the-Box
                17,  # Digger
                18,  # Pogo
                20,  # Bungee
                21,  # Ladder
                22,  # Catapult
                23,  # Gargantuar
            ]

            # Step 1: Enable all zombie types in spawn_type array
            # spawn_type is at board + 0x54EC, 33 bytes (bools)
            # GOTY 1.2.0.1073: spawn_type (33 bools) is at board + 0x54D4
            spawn_type_offset = 0x54D4
            try:
                # Enable all zombie types (write 1 for each type we want)
                spawn_type_array = bytearray(33)
                for zt in zombie_types:
                    if 0 <= zt < 33:
                        spawn_type_array[zt] = 1
                self.pm.write_bytes(board_ptr + spawn_type_offset, bytes(spawn_type_array), 33)
                print(f"[SpawnZombies] Enabled {len(zombie_types)} zombie types")
            except Exception as e:
                print(f"[SpawnZombies] spawn_type write failed: {e}")

            # Step 2: Write zombies directly to spawn_list
            # spawn_list is at board + 0x6CC, 2000 ints
            spawn_list_offset = 0x6CC
            try:
                # Get number of rows
                num_rows = 5
                for row_offset in [0x5F0, 0x5D8]:
                    try:
                        # row_type array tells us how many rows
                        rows = self.pm.read_int(board_ptr + row_offset)
                        if 1 <= rows <= 6:
                            num_rows = rows
                            break
                    except:
                        pass

                # Create spawn list entries
                # Each entry is just the zombie type (int)
                spawn_entries = []
                for _ in range(5):  # Repeat to fill list
                    for zt in zombie_types:
                        spawn_entries.append(zt)

                # Limit to 200 entries
                spawn_entries = spawn_entries[:200]

                # Fill rest with -1 (empty)
                while len(spawn_entries) < 2000:
                    spawn_entries.append(-1)

                # Write spawn list
                spawn_data = struct.pack('<' + 'i' * 2000, *spawn_entries)
                self.pm.write_bytes(board_ptr + spawn_list_offset, spawn_data, len(spawn_data))
                print(f"[SpawnZombies] Wrote {len(zombie_types) * 5} zombies to spawn list")

            except Exception as e:
                print(f"[SpawnZombies] spawn_list write failed: {e}")

            # Step 3: Trigger immediate spawning by setting spawn countdown to 0
            # and setting the "spawn zombies" flag
            try:
                # Sun offset is at 0x5578, nearby offsets control spawning
                # Try various spawn-related offsets
                for offset in [0x54D4, 0x54BC, 0x5564, 0x556C]:
                    try:
                        self.pm.write_int(board_ptr + offset, 0)
                    except:
                        pass

                print("[SpawnZombies] Spawn triggered")

            except Exception as e:
                print(f"[SpawnZombies] Trigger failed: {e}")

            print("[SpawnZombies] Done! Zombies should spawn with next wave.")
            return True

        except Exception as e:
            print(f"[SpawnZombies] Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def spawn_zombies_direct_fallback(self, board_ptr):
        """Fallback method - calls trigger_zombie_wave"""
        return self.trigger_zombie_wave(board_ptr)

    def infinite_sun_loop(self):
        """Thread for infinite sun"""
        while self.infinite_sun_active:
            try:
                for ptr_offset in [0x191A28, 0x192390, 0x191A04]:
                    try:
                        pointer_addr = self.base_address + ptr_offset
                        game_ptr = struct.unpack('<I', self.pm.read_bytes(pointer_addr, 4))[0]
                        if game_ptr != 0 and game_ptr < 0x7FFFFFFF:
                            sun_addr = game_ptr + 0x5578
                            self.pm.write_bytes(sun_addr, struct.pack('<I', 9999), 4)
                            break
                    except:
                        continue
            except:
                pass
            time.sleep(0.02)

    def auto_collect_loop(self):
        """Thread to auto-collect falling suns by scanning object array."""
        # try several possible struct sizes/offsets and scan a larger window
        struct_sizes = [0x15C, 0x50, 0x80, 0xA0]
        type_offsets = [0x18, 0x10, 0x00, 0x38]
        active_offsets = [0x50, 0x38, 0x4C]
        worth_offsets = [0x64, 0x40, 0x6C]

        while self.auto_collect_active:
            try:
                game_ptr, board_ptr = self.get_game_board()
                if not board_ptr or not game_ptr:
                    time.sleep(0.12)
                    continue

                sun_addr = game_ptr + self.sun_final_offset

                # attempt to read an object/zombie array pointer; try multiple board offsets
                candidates = [0xA8, 0xA0, 0xB0]
                obj_array = None
                obj_count = 0
                for off in candidates:
                    try:
                        val = struct.unpack('<I', self.pm.read_bytes(board_ptr + off, 4))[0]
                        if val and val > 0x10000:
                            obj_array = val
                            break
                    except:
                        continue

                try:
                    obj_count = struct.unpack('<I', self.pm.read_bytes(board_ptr + 0x94, 4))[0]
                except:
                    obj_count = 0

                if not obj_array or obj_array < 0x10000:
                    time.sleep(0.08)
                    continue

                max_entries = max(256, obj_count if obj_count > 0 else 0)

                # scan entries using multiple heuristics
                for struct_size in struct_sizes:
                    if not self.auto_collect_active:
                        break
                    for i in range(max_entries):
                        try:
                            addr = obj_array + (i * struct_size)

                            # try read type at multiple offsets
                            obj_type = None
                            for to in type_offsets:
                                try:
                                    obj_type = struct.unpack('<I', self.pm.read_bytes(addr + to, 4))[0]
                                    break
                                except:
                                    obj_type = None
                            if obj_type != 3:
                                continue

                            # check active flag
                            active = 0
                            for ao in active_offsets:
                                try:
                                    active = struct.unpack('<B', self.pm.read_bytes(addr + ao, 1))[0]
                                    break
                                except:
                                    active = 0
                            if active == 0:
                                continue

                            # determine worth
                            worth = None
                            for wo in worth_offsets:
                                try:
                                    # prefer integer then float
                                    raw = self.pm.read_bytes(addr + wo, 4)
                                    iv = struct.unpack('<I', raw)[0]
                                    if 0 < iv < 10000:
                                        worth = iv
                                        break
                                    fv = struct.unpack('<f', raw)[0]
                                    if 0 < fv < 10000:
                                        worth = int(fv)
                                        break
                                except:
                                    continue
                            if worth is None:
                                worth = 25

                            # add to player's sun
                            try:
                                cur = struct.unpack('<I', self.pm.read_bytes(sun_addr, 4))[0]
                                new = min(9999, cur + worth)
                                self.pm.write_bytes(sun_addr, struct.pack('<I', new), 4)
                            except:
                                pass

                            # mark inactive
                            for ao in active_offsets:
                                try:
                                    self.pm.write_bytes(addr + ao, struct.pack('<B', 0), 1)
                                except:
                                    pass

                        except:
                            continue

                time.sleep(0.04)
            except:
                time.sleep(0.1)
                continue

    def set_sun_amount(self, amount):
        """Set player's sun using a reliable hook at the tick site.

        Installs a small code cave near the routine that frequently reads
        `mov ecx, [eax+0x5578]` so we can force-write `imm32` to
        `[eax+0x5578]` and then execute the original read.
        Subsequent calls just update the imm32.
        Falls back to direct write if the hook cannot be installed.
        """
        if not self.pm:
            if not self.attach_process():
                return False
        # Clamp
        try:
            v = int(amount)
        except:
            v = 9999
        if v < 0:
            v = 0
        if v > 9999:
            v = 9999

        try:
            # Install patch on first use
            if not self.sun_apply_cave or not self.sun_apply_patch_addr:
                # Preferred known site: base+0x1E6E6 should be '8B 88 78 55 00 00'
                addr = None
                try:
                    candidate = self.base_address + 0x1E6E6
                    b = self.pm.read_bytes(candidate, 6)
                    if b == b"\x8B\x88\x78\x55\x00\x00":
                        addr = candidate
                except:
                    addr = None
                if addr is None:
                    # Signature scan for mov ecx, [eax+0x5578]
                    sig = b"\x8B\x88\x78\x55\x00\x00"
                    found = self.scan_for_pattern(sig, None, start_offset=0x1000, scan_size=0x1600000)
                    if found is not None:
                        addr = self.base_address + found
                if addr is None:
                    print("[SunSet] read signature not found; trying add/cmp sites")
                    # Try add site at base+0x1E6E0: 01 88 78 55 00 00
                    add_addr = None
                    try:
                        cand = self.base_address + 0x1E6E0
                        b = self.pm.read_bytes(cand, 6)
                        if b == b"\x01\x88\x78\x55\x00\x00":
                            add_addr = cand
                    except:
                        add_addr = None
                    if add_addr is None:
                        add_sig = b"\x01\x88\x78\x55\x00\x00"
                        found_add = self.scan_for_pattern(add_sig, None, start_offset=0x1000, scan_size=0x1600000)
                        if found_add is not None:
                            add_addr = self.base_address + found_add
                    if add_addr is not None and not self.sun_add_cave:
                        try:
                            self.original_sun_add_bytes = self.pm.read_bytes(add_addr, 6)
                        except:
                            self.original_sun_add_bytes = None
                        cave = self.pm.allocate(64)
                        stub = bytearray([0xC7, 0x80, 0x78, 0x55, 0x00, 0x00])
                        self.sun_add_imm_offset = len(stub)
                        stub += struct.pack('<I', v)
                        # Keep flow: mov ecx,[eax+0x5578]
                        stub += bytearray([0x8B, 0x88, 0x78, 0x55, 0x00, 0x00])
                        stub += bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                        ret = add_addr + 6
                        rel = ret - (cave + len(stub))
                        struct.pack_into('<i', stub, len(stub) - 4, rel)
                        self.pm.write_bytes(cave, bytes(stub), len(stub))
                        jmp = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00, 0x90])
                        struct.pack_into('<i', jmp, 1, cave - (add_addr + 5))
                        self.pm.write_bytes(add_addr, bytes(jmp), len(jmp))
                        self.sun_add_cave = cave
                        self.sun_add_patch_addr = add_addr
                        print(f"[SunSet] Patched add {hex(add_addr)} -> cave {hex(cave)} (sun={v})")

                    # Try cmp site at base+0x1E701: 81 B8 78 55 00 00 40 1F 00 00
                    cmp_addr = None
                    try:
                        cand = self.base_address + 0x1E701
                        b = self.pm.read_bytes(cand, 10)
                        if b and b[:2] == b"\x81\xB8" and b[2:8] == b"\x78\x55\x00\x00\x40\x1F":
                            cmp_addr = cand
                    except:
                        cmp_addr = None
                    if cmp_addr is None:
                        cmp_sig = b"\x81\xB8\x78\x55\x00\x00"  # cmp [eax+0x5578], imm16/32
                        found_cmp = self.scan_for_pattern(cmp_sig, None, start_offset=0x1000, scan_size=0x1600000)
                        if found_cmp is not None:
                            cmp_addr = self.base_address + found_cmp
                    if cmp_addr is not None and not self.sun_cmp_cave:
                        try:
                            self.original_sun_cmp_bytes = self.pm.read_bytes(cmp_addr, 10)
                        except:
                            self.original_sun_cmp_bytes = None
                        cave = self.pm.allocate(64)
                        stub = bytearray([0xC7, 0x80, 0x78, 0x55, 0x00, 0x00])
                        self.sun_cmp_imm_offset = len(stub)
                        stub += struct.pack('<I', v)
                        # original: cmp [eax+0x5578], 0x1F40
                        stub += bytearray([0x81, 0xB8, 0x78, 0x55, 0x00, 0x00, 0x40, 0x1F, 0x00, 0x00])
                        stub += bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                        ret = cmp_addr + 10
                        rel = ret - (cave + len(stub))
                        struct.pack_into('<i', stub, len(stub) - 4, rel)
                        self.pm.write_bytes(cave, bytes(stub), len(stub))
                        jmp = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                        struct.pack_into('<i', jmp, 1, cave - (cmp_addr + 5))
                        patch = jmp + bytes([0x90] * (10 - len(jmp)))
                        self.pm.write_bytes(cmp_addr, bytes(patch), len(patch))
                        self.sun_cmp_cave = cave
                        self.sun_cmp_patch_addr = cmp_addr
                        print(f"[SunSet] Patched cmp {hex(cmp_addr)} -> cave {hex(cave)} (sun={v})")
                else:
                    # Save original bytes
                    try:
                        self.original_sun_apply_bytes = self.pm.read_bytes(addr, 6)
                    except:
                        self.original_sun_apply_bytes = None
                    # Build cave: mov [eax+0x5578], imm32; mov ecx,[eax+0x5578]; jmp back
                    cave = self.pm.allocate(64)
                    stub = bytearray([0xC7, 0x80, 0x78, 0x55, 0x00, 0x00])
                    self.sun_apply_imm_offset = len(stub)
                    stub += struct.pack('<I', v)
                    stub += bytearray([0x8B, 0x88, 0x78, 0x55, 0x00, 0x00])
                    stub += bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                    ret = addr + 6
                    rel = ret - (cave + len(stub))
                    struct.pack_into('<i', stub, len(stub) - 4, rel)
                    self.pm.write_bytes(cave, bytes(stub), len(stub))

                    # Patch original with jmp + NOP padding to 6 bytes
                    jmp = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00, 0x90])
                    struct.pack_into('<i', jmp, 1, cave - (addr + 5))
                    self.pm.write_bytes(addr, bytes(jmp), len(jmp))

                    self.sun_apply_cave = cave
                    self.sun_apply_patch_addr = addr
                    print(f"[SunSet] Patched {hex(addr)} -> cave {hex(cave)} (sun={v})")

            # If patch is active, update imm32 and return
            if self.sun_apply_cave and self.sun_apply_imm_offset is not None:
                try:
                    self.pm.write_bytes(self.sun_apply_cave + self.sun_apply_imm_offset, struct.pack('<I', v), 4)
                    print(f"[SunSet] Updated sun imm to {v}")
                    return True
                except Exception as e:
                    print(f"[SunSet] imm update failed: {e}")

            # Update imm for fallback add/cmp sites if present
            updated = False
            try:
                if self.sun_add_cave and self.sun_add_imm_offset is not None:
                    self.pm.write_bytes(self.sun_add_cave + self.sun_add_imm_offset, struct.pack('<I', v), 4)
                    print(f"[SunSet] Updated sun imm at add-site to {v}")
                    updated = True
                if self.sun_cmp_cave and self.sun_cmp_imm_offset is not None:
                    self.pm.write_bytes(self.sun_cmp_cave + self.sun_cmp_imm_offset, struct.pack('<I', v), 4)
                    print(f"[SunSet] Updated sun imm at cmp-site to {v}")
                    updated = True
            except Exception as e:
                print(f"[SunSet] fallback imm update failed: {e}")
            if updated:
                return True

            # Fallback: direct write via resolved game pointer
            game_ptr, board_ptr = self.get_game_board()
            if game_ptr:
                target_addr = game_ptr + self.sun_final_offset
                try:
                    self.pm.write_bytes(target_addr, struct.pack('<I', v), 4)
                    print(f"[SunSet] Wrote sun={v} at {hex(target_addr)} (fallback)")
                    return True
                except Exception as e:
                    print(f"[SunSet] direct write failed: {e}")
            print("[SunSet] Could not apply sun value")
            return False
        except Exception as e:
            print(f"[SunSet] Error: {e}")
            return False

    def set_sun_lock_amount(self, amount):
        try:
            v = int(amount)
        except:
            v = 9999
        if v < 0:
            v = 0
        if v > 9999:
            v = 9999
        self.sun_lock_amount = v
        # If clamp site known, update it too
        try:
            if self.sun_clamp_addr:
                self.pm.write_bytes(self.sun_clamp_addr + 6, struct.pack('<I', v), 4)
        except:
            pass
        return True

    def sun_lock_loop(self):
        """Continuously write sun amount to ensure immediate UI update."""
        while self.sun_lock_active:
            try:
                game_ptr, board_ptr = self.get_game_board()
                if game_ptr:
                    sun_addr = game_ptr + self.sun_final_offset
                    self.pm.write_bytes(sun_addr, struct.pack('<I', self.sun_lock_amount), 4)
                time.sleep(0.04)
            except Exception:
                time.sleep(0.1)
                continue

    def toggle_sun_lock(self, state):
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            self.sun_lock_active = state
            if state:
                if not self._sun_lock_thread or not self._sun_lock_thread.is_alive():
                    t = threading.Thread(target=self.sun_lock_loop, daemon=True)
                    t.start()
                    self._sun_lock_thread = t
                print(f"[SunLock] Enabled (amount={self.sun_lock_amount})")
            else:
                print("[SunLock] Disabled")
            return True
        except Exception as e:
            print(f"[SunLock] toggle error: {e}")
            return False

    def toggle_infinite_sun(self, state):
        """Toggle infinite sun cheat"""
        if not self.pm:
            if not self.attach_process():
                return False

        self.infinite_sun_active = state

        try:
            collect_addr = self.base_address + self.collect_sun_address
            collect_mov_addr = self.base_address + self.collect_mov_address

            if state:
                self._prev_prevent_spend_state = self.prevent_spend_active
                self.toggle_prevent_spend(True)

                self.collect_add_cave = self.pm.allocate(128)
                self.collect_mov_cave = self.pm.allocate(128)

                cave_code = bytearray([
                    0xC7, 0x80, 0x78, 0x55, 0x00, 0x00,
                    0x0F, 0x27, 0x00, 0x00,
                    0xE9, 0x00, 0x00, 0x00, 0x00
                ])

                return_addr_add = collect_addr + 6
                jmp_offset_add = return_addr_add - (self.collect_add_cave + len(cave_code))
                struct.pack_into('<i', cave_code, len(cave_code) - 4, jmp_offset_add)

                self.pm.write_bytes(self.collect_add_cave, bytes(cave_code), len(cave_code))
                jmp_to_cave = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00, 0x90])
                cave_offset = self.collect_add_cave - (collect_addr + 5)
                struct.pack_into('<i', jmp_to_cave, 1, cave_offset)
                self.pm.write_bytes(collect_addr, bytes(jmp_to_cave), 6)

                cave_code2 = bytearray(cave_code)
                return_addr_mov = collect_mov_addr + len(self.original_collect_mov_bytes)
                jmp_offset_mov = return_addr_mov - (self.collect_mov_cave + len(cave_code2))
                struct.pack_into('<i', cave_code2, len(cave_code2) - 4, jmp_offset_mov)
                self.pm.write_bytes(self.collect_mov_cave, bytes(cave_code2), len(cave_code2))

                mov_jmp = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                mov_cave_offset = self.collect_mov_cave - (collect_mov_addr + 5)
                struct.pack_into('<i', mov_jmp, 1, mov_cave_offset)
                mov_patch = mov_jmp + bytes([0x90] * (len(self.original_collect_mov_bytes) - len(mov_jmp)))
                self.pm.write_bytes(collect_mov_addr, bytes(mov_patch), len(mov_patch))

                thread = threading.Thread(target=self.infinite_sun_loop, daemon=True)
                thread.start()
            else:
                try:
                    self.pm.write_bytes(collect_addr, self.original_collect_bytes, len(self.original_collect_bytes))
                except:
                    pass
                try:
                    self.pm.write_bytes(collect_mov_addr, self.original_collect_mov_bytes, len(self.original_collect_mov_bytes))
                except:
                    pass
                for cave_attr in ('collect_add_cave', 'collect_mov_cave'):
                    cave = getattr(self, cave_attr, None)
                    if cave:
                        try:
                            self.pm.free(cave)
                        except:
                            pass
                        setattr(self, cave_attr, None)
                self.toggle_prevent_spend(self._prev_prevent_spend_state)
        except Exception as e:
            print(f"[Sun] toggle error: {e}")

        return True

    def toggle_auto_collect(self, state):
        """Toggle auto-collect using memory patch (CE script equivalent)."""
        if not self.pm:
            if not self.attach_process():
                return False

        addr = self.base_address + self.auto_collect_patch_addr
        ret_addr = self.base_address + self.auto_collect_return_addr

        try:
            if state:
                # allocate cave and write cmp + jmp back to original flow
                self.auto_collect_cave = self.pm.allocate(64)

                # build newmem: cmp byte ptr [ebx+50],00  (80 7B 50 00)
                cave = bytearray([0x80, 0x7B, 0x50, 0x00])

                # append jmp to ret_addr
                cave += bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])

                # compute rel for jmp in cave (next instr after jmp is cave_base + len(cave))
                cave_base = self.auto_collect_cave
                # address after jmp is cave_base + len(cave)
                addr_after_jmp = cave_base + len(cave)
                rel = ret_addr - addr_after_jmp
                struct.pack_into('<i', cave, 5, rel)

                # write cave
                self.pm.write_bytes(cave_base, bytes(cave), len(cave))

                # write jmp at original addr to cave (E9 rel32) and pad to original length
                jmp = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                rel_orig = cave_base - (addr + 5)
                struct.pack_into('<i', jmp, 1, rel_orig)
                patch = jmp + bytes([0x90] * (len(self.original_auto_collect_bytes) - len(jmp)))
                self.pm.write_bytes(addr, bytes(patch), len(patch))

                self.auto_collect_active = True
            else:
                # restore original bytes and free cave
                try:
                    self.pm.write_bytes(addr, self.original_auto_collect_bytes, len(self.original_auto_collect_bytes))
                except:
                    pass
                if self.auto_collect_cave:
                    try:
                        self.pm.free(self.auto_collect_cave)
                    except:
                        pass
                    self.auto_collect_cave = None
                self.auto_collect_active = False

            return True
        except Exception as e:
            print(f"[AutoCollect] toggle error: {e}")
            return False

    def toggle_no_cooldown(self, state):
        """Toggle no cooldown cheat"""
        if not self.pm:
            if not self.attach_process():
                return False

        try:
            addr = self.base_address + self.cooldown_address
            if state:
                self.pm.write_bytes(addr, bytes([0x90, 0x90]), 2)
            else:
                self.pm.write_bytes(addr, self.original_cooldown_bytes, 2)
            self.no_cooldown_active = state
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle cooldown: {str(e)}")
            return False

    def toggle_one_hit_kill(self, state):
        """Toggle one hit kill cheat"""
        if not self.pm:
            if not self.attach_process():
                return False

        try:
            body_addr = self.base_address + self.body_kill_address
            armor_addr = self.base_address + self.armor_kill_address

            if state:
                self.body_cave = self.pm.allocate(128)

                body_code = bytearray([
                    0xC7, 0x80, 0xC8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0x33, 0xF6,
                    0xE9, 0x00, 0x00, 0x00, 0x00
                ])

                return_addr = body_addr + 6
                jmp_offset = return_addr - (self.body_cave + len(body_code))
                struct.pack_into('<i', body_code, len(body_code) - 4, jmp_offset)

                self.pm.write_bytes(self.body_cave, bytes(body_code), len(body_code))

                jmp_to_cave = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00, 0x90])
                cave_offset = self.body_cave - (body_addr + 5)
                struct.pack_into('<i', jmp_to_cave, 1, cave_offset)
                self.pm.write_bytes(body_addr, bytes(jmp_to_cave), 6)

                self.armor_cave = self.pm.allocate(256)

                armor_code = bytearray([
                    0xC7, 0x85, 0xD0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0xC7, 0x85, 0xDC, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0xC7, 0x85, 0xE0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0xC7, 0x85, 0xE4, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0xC7, 0x85, 0xC8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0xE9, 0x00, 0x00, 0x00, 0x00
                ])

                armor_return = armor_addr + 6
                armor_jmp_offset = armor_return - (self.armor_cave + len(armor_code))
                struct.pack_into('<i', armor_code, len(armor_code) - 4, armor_jmp_offset)

                self.pm.write_bytes(self.armor_cave, bytes(armor_code), len(armor_code))

                armor_jmp = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00, 0x90])
                armor_cave_offset = self.armor_cave - (armor_addr + 5)
                struct.pack_into('<i', armor_jmp, 1, armor_cave_offset)
                self.pm.write_bytes(armor_addr, bytes(armor_jmp), 6)
            else:
                self.pm.write_bytes(body_addr, self.original_body_bytes, 6)
                self.pm.write_bytes(armor_addr, self.original_armor_bytes, 6)

                if self.body_cave:
                    self.pm.free(self.body_cave)
                    self.body_cave = None
                if self.armor_cave:
                    self.pm.free(self.armor_cave)
                    self.armor_cave = None

            self.one_hit_kill_active = state
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle one hit kill: {str(e)}")
            return False

    def toggle_instant_plant_death(self, state):
        """Plants die instantly by forcing health to 0 at damage site via cave."""
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            addr = self.base_address + self.plant_damage_offset
            if state:
                # Patch 6 bytes with JMP to cave, preserve original 6 for restore
                try:
                    self.original_plant_instant_bytes = self.pm.read_bytes(addr, 6)
                except:
                    self.original_plant_instant_bytes = None
                cave = self.pm.allocate(64)
                # mov dword ptr [esi+40], 0
                stub = bytearray([0xC7, 0x46, 0x40, 0x00, 0x00, 0x00, 0x00])
                # jmp back
                stub += bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                ret = addr + 6
                rel = ret - (cave + len(stub))
                struct.pack_into('<i', stub, len(stub) - 4, rel)
                self.pm.write_bytes(cave, bytes(stub), len(stub))

                # write jmp (pad to 6 bytes)
                jmp = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00, 0x90])
                struct.pack_into('<i', jmp, 1, cave - (addr + 5))
                self.pm.write_bytes(addr, bytes(jmp), len(jmp))

                self.plant_instant_cave = cave
                self.plant_instant_patch_addr = addr
                print(f"[InstantPlantDeath] Patched {hex(addr)} -> cave {hex(cave)}")
            else:
                if self.plant_instant_patch_addr and self.original_plant_instant_bytes:
                    try:
                        self.pm.write_bytes(self.plant_instant_patch_addr, self.original_plant_instant_bytes, len(self.original_plant_instant_bytes))
                        print(f"[InstantPlantDeath] Restored bytes at {hex(self.plant_instant_patch_addr)}")
                    except Exception as e:
                        print(f"[InstantPlantDeath] restore failed: {e}")
                if self.plant_instant_cave:
                    try:
                        self.pm.free(self.plant_instant_cave)
                    except:
                        pass
                    self.plant_instant_cave = None
                self.plant_instant_patch_addr = None
                self.original_plant_instant_bytes = None
            self.instant_plant_death_active = state
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle instant plant death: {str(e)}")
            return False

    def toggle_invincible_plants(self, state):
        """NOP the plant damage instruction so plants don't lose HP."""
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            addr = self.base_address + self.plant_damage_offset
            if state:
                # Save and NOP 4 bytes
                try:
                    self.original_plant_damage_bytes = self.pm.read_bytes(addr, 4)
                except:
                    pass
                self.pm.write_bytes(addr, bytes([0x90, 0x90, 0x90, 0x90]), 4)
                print(f"[InvinciblePlants] NOPed damage at {hex(addr)}")
            else:
                try:
                    self.pm.write_bytes(addr, self.original_plant_damage_bytes, 4)
                    print(f"[InvinciblePlants] Restored bytes at {hex(addr)}")
                except:
                    pass
            self.invincible_plants_active = state
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle invincible plants: {str(e)}")
            return False

    def toggle_invincible_zombies(self, state):
        """Patch damage and checks so zombies don't die/take damage."""
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            sub_addr = self.base_address + self.zombie_sub_offset
            je1_addr = self.base_address + self.zombie_je1_offset
            je2_addr = self.base_address + self.zombie_je2_offset
            if state:
                # Save originals
                try:
                    self.original_zombie_sub_bytes = self.pm.read_bytes(sub_addr, 4)
                    self.original_zombie_je1_bytes = self.pm.read_bytes(je1_addr, 2)
                    self.original_zombie_je2_bytes = self.pm.read_bytes(je2_addr, 2)
                except:
                    pass
                # sub -> add
                self.pm.write_bytes(sub_addr, bytes([0x03, 0x6C, 0x24, 0x20]), 4)
                # je -> jmp short (same offset)
                self.pm.write_bytes(je1_addr, bytes([0xEB, 0x08]), 2)
                # je -> nop nop
                self.pm.write_bytes(je2_addr, bytes([0x90, 0x90]), 2)
                print(f"[InvincibleZombies] Patched sub/add and JE sites")
            else:
                # restore
                try:
                    self.pm.write_bytes(sub_addr, self.original_zombie_sub_bytes, 4)
                except:
                    pass
                try:
                    self.pm.write_bytes(je1_addr, self.original_zombie_je1_bytes, 2)
                except:
                    pass
                try:
                    self.pm.write_bytes(je2_addr, self.original_zombie_je2_bytes, 2)
                except:
                    pass
                print(f"[InvincibleZombies] Restored originals")
            self.invincible_zombies_active = state
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle invincible zombies: {str(e)}")
            return False

    def toggle_unhittable_plants_zombotany(self, state):
        """Make plants unhittable in ZomBotany by forcing JE -> JMP."""
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            addr = self.base_address + self.zombotany_je_offset  # 0x71686
            target = self.base_address + 0x716FD                  # 0x716FD absolute target
            if state:
                # Save original 5 bytes, replace with near JMP (E9 rel32)
                try:
                    self.original_zombotany_je_bytes = self.pm.read_bytes(addr, 5)
                except:
                    self.original_zombotany_je_bytes = None
                rel = target - (addr + 5)
                jmp = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                struct.pack_into('<i', jmp, 1, rel)
                # Write JMP and pad with NOP if we want to ensure 5-byte overwrite only
                self.pm.write_bytes(addr, bytes(jmp), 5)
                print(f"[ZomBotany] Patched {hex(addr)} -> JMP {hex(target)} (rel={rel:+d})")
            else:
                # Restore original 5 bytes
                if self.original_zombotany_je_bytes:
                    try:
                        self.pm.write_bytes(addr, self.original_zombotany_je_bytes, 5)
                        print(f"[ZomBotany] Restored original bytes at {hex(addr)}")
                    except:
                        pass
            self.unhittable_plants_active = state
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle ZomBotany unhittable plants: {str(e)}")
            return False

    # ===== NEW FEATURES FROM PVZ TOOLKIT =====

    def set_game_speed(self, speed_ms):
        """Set game speed by changing frame duration (lower = faster)."""
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            v = int(speed_ms)
            if v < 1:
                v = 1
            if v > 100:
                v = 100
            self.game_speed_value = v
            # Frame duration offset for GOTY 1.2.0.1073:
            # lawn pointer at: base + 0x329670
            # frame_duration at: lawn + 0x4B4 (which is 0x454 + 0x60)
            base_ptr = self.pm.read_int(self.base_address + 0x329670)
            if base_ptr:
                frame_addr = base_ptr + 0x4B4
                self.pm.write_int(frame_addr, v)
                print(f"[GameSpeed] Set to {v}ms per frame at {hex(frame_addr)}")
                return True
            else:
                print("[GameSpeed] Could not read lawn pointer")
        except Exception as e:
            print(f"[GameSpeed] Error: {e}")
        return False

    def toggle_no_fog(self, state):
        """Remove fog in night/fog levels."""
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            # From PVZ Toolkit data.cpp for GOTY 1.2.0.1073:
            # {0x0041d17d, {0xd231}, {0xf23b}}, // no_fog
            # Address: base + 0x1D17D
            # Original: 0x3B 0xF2 (cmp esi, edx) - stored little-endian as f23b
            # Patched:  0x31 0xD2 (xor edx, edx) - stored little-endian as d231
            fog_addr = self.base_address + 0x1D17D
            
            if state:
                # Save original bytes
                try:
                    self.original_no_fog_bytes = self.pm.read_bytes(fog_addr, 2)
                    print(f"[NoFog] Original bytes at 0x{fog_addr:X}: {self.original_no_fog_bytes.hex()}")
                except:
                    pass
                # xor edx, edx (0x31 0xD2) - clears fog value
                self.pm.write_bytes(fog_addr, bytes([0x31, 0xD2]), 2)
            else:
                # Restore original: cmp esi, edx (0x3B 0xF2)
                if self.original_no_fog_bytes:
                    self.pm.write_bytes(fog_addr, self.original_no_fog_bytes, 2)
                else:
                    self.pm.write_bytes(fog_addr, bytes([0x3B, 0xF2]), 2)
            
            self.no_fog_active = state
            print(f"[NoFog] {'Enabled' if state else 'Disabled'}")
            return True
        except Exception as e:
            print(f"[NoFog] Error: {e}")
            return False

    def toggle_stop_spawning(self, state):
        """Pause zombie wave spawning."""
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            if state:
                # Try to find the correct offset by looking for 0x74 (je instruction)
                found_offset = None
                for offset in self.stop_spawning_offsets:
                    addr = self.base_address + offset
                    try:
                        current_byte = self.pm.read_bytes(addr, 1)
                        # Look for je (0x74) or already patched jmp (0xEB)
                        if current_byte[0] == 0x74 or current_byte[0] == 0xEB:
                            found_offset = offset
                            self.original_stop_spawning_bytes = current_byte
                            print(f"[StopSpawning] Found at offset 0x{offset:X}, byte: 0x{current_byte[0]:02X}")
                            break
                    except:
                        continue

                if found_offset is None:
                    print("[StopSpawning] Could not find valid offset")
                    return False

                self.stop_spawning_offset = found_offset
                addr = self.base_address + found_offset
                # Change je to jmp to skip spawning (0x74 -> 0xEB)
                self.pm.write_bytes(addr, bytes([0xEB]), 1)
                print(f"[StopSpawning] Enabled at 0x{addr:X}")
            else:
                if self.stop_spawning_offset and self.original_stop_spawning_bytes:
                    addr = self.base_address + self.stop_spawning_offset
                    self.pm.write_bytes(addr, self.original_stop_spawning_bytes, 1)
                    print(f"[StopSpawning] Disabled at 0x{addr:X}")

            self.stop_spawning_active = state
            return True
        except Exception as e:
            print(f"[StopSpawning] Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def toggle_stop_zombies(self, state):
        """Freeze zombies in place (stop movement)."""
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            if state:
                # Try to find the correct version by checking expected bytes
                found_offsets = None
                for version_offsets in self.stop_zombies_version_offsets:
                    all_match = True
                    for offset, orig_byte, patch_byte in version_offsets:
                        addr = self.base_address + offset
                        try:
                            current_byte = self.pm.read_bytes(addr, 1)[0]
                            # Check if byte matches expected original or already patched
                            if current_byte != orig_byte and current_byte != patch_byte:
                                all_match = False
                                break
                        except:
                            all_match = False
                            break

                    if all_match:
                        found_offsets = version_offsets
                        print(f"[StopZombies] Found matching version")
                        break

                if found_offsets is None:
                    print("[StopZombies] Could not find matching version, trying first set")
                    found_offsets = self.stop_zombies_version_offsets[0]

                self.stop_zombies_offsets = found_offsets

                # Save original bytes and apply patches
                self.original_stop_zombies_bytes = []
                for offset, orig_byte, patch_byte in found_offsets:
                    addr = self.base_address + offset
                    try:
                        orig = self.pm.read_bytes(addr, 1)
                        self.original_stop_zombies_bytes.append((addr, orig))
                        self.pm.write_bytes(addr, bytes([patch_byte]), 1)
                        print(f"[StopZombies] Patched 0x{addr:X}: 0x{orig[0]:02X} -> 0x{patch_byte:02X}")
                    except Exception as e:
                        print(f"[StopZombies] Failed to patch 0x{addr:X}: {e}")
            else:
                # Restore original bytes
                if self.original_stop_zombies_bytes:
                    for addr, orig in self.original_stop_zombies_bytes:
                        self.pm.write_bytes(addr, orig, 1)
                        print(f"[StopZombies] Restored 0x{addr:X}")

            self.stop_zombies_active = state
            print(f"[StopZombies] {'Enabled' if state else 'Disabled'}")
            return True
        except Exception as e:
            print(f"[StopZombies] Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def toggle_lock_butter(self, state):
        """Kernel-pult always throws butter instead of corn."""
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            # Offset 0x62b42: JNE instruction in butter decision code
            # This is the correct offset from pvztoolkit for GOTY 1.2.0.1073
            # Code: test eax, eax; jne +3Fh (skip butter creation if random check fails)
            # Original: 75 (JNE - conditional jump based on random butter check)
            # Patched:  70 (JO - Jump if Overflow, never triggers so always falls through to butter)
            addr = self.base_address + 0x62b42
            if state:
                try:
                    self.original_lock_butter_bytes = self.pm.read_bytes(addr, 1)
                    print(f"[LockButter] Original byte at {hex(addr)}: {self.original_lock_butter_bytes.hex()}")
                except:
                    pass
                # Change JNE (0x75) to JO (0x70) - never jumps, always butter
                self.pm.write_bytes(addr, bytes([0x70]), 1)
            else:
                if self.original_lock_butter_bytes:
                    self.pm.write_bytes(addr, self.original_lock_butter_bytes, 1)
                else:
                    # Original: 75 (JNE)
                    self.pm.write_bytes(addr, bytes([0x75]), 1)
            self.lock_butter_active = state
            print(f"[LockButter] {'Enabled' if state else 'Disabled'} at {hex(addr)}")
            return True
        except Exception as e:
            print(f"[LockButter] Error: {e}")
            return False

    def toggle_mushrooms_awake(self, state):
        """Mushrooms don't fall asleep during day."""
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            # pvztoolkit GOTY 1.2.0.1073: {0x004617c2, {0xeb}, {0x74}}
            # Address: 0x4617C2 = base (0x400000) + 0x617C2
            # Original: 0x74 (JE - jump if equal/zero)
            # Patched:  0xEB (JMP - unconditional jump)
            addr = self.base_address + 0x617C2
            if state:
                try:
                    self.original_mushrooms_awake_bytes = self.pm.read_bytes(addr, 1)
                    print(f"[MushroomsAwake] Original byte at {hex(addr)}: {self.original_mushrooms_awake_bytes.hex()}")
                except:
                    pass
                # Change JE to JMP
                self.pm.write_bytes(addr, bytes([0xEB]), 1)
            else:
                if self.original_mushrooms_awake_bytes:
                    self.pm.write_bytes(addr, self.original_mushrooms_awake_bytes, 1)
                else:
                    self.pm.write_bytes(addr, bytes([0x74]), 1)
            self.mushrooms_awake_active = state
            print(f"[MushroomsAwake] {'Enabled' if state else 'Disabled'} at {hex(addr)}")
            return True
        except Exception as e:
            print(f"[MushroomsAwake] Error: {e}")
            return False

    def toggle_no_crater(self, state):
        """Doom-shroom doesn't leave craters."""
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            # Offset 0x2057d: JNE instruction in crater creation code
            # This is the correct offset from pvztoolkit for GOTY 1.2.0.1073
            # Original: 75 (JNE - conditional jump to crater creation)
            # Patched:  70 (JO - Jump if Overflow, never triggers so crater is skipped)
            addr = self.base_address + 0x2057d
            if state:
                try:
                    self.original_no_crater_bytes = self.pm.read_bytes(addr, 1)
                except:
                    pass
                # Change JNE (0x75) to JO (0x70) - never jumps, no crater
                self.pm.write_bytes(addr, bytes([0x70]), 1)
            else:
                if self.original_no_crater_bytes:
                    self.pm.write_bytes(addr, self.original_no_crater_bytes, 1)
                else:
                    self.pm.write_bytes(addr, bytes([0x75]), 1)
            self.no_crater_active = state
            print(f"[NoCrater] {'Enabled' if state else 'Disabled'}")
            return True
        except Exception as e:
            print(f"[NoCrater] Error: {e}")
            return False

    def toggle_see_vase(self, state):
        """See contents of vases in Vasebreaker."""
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            # pvztoolkit GOTY 1.2.0.1073: {0x004518aa, {0x0033b866}, {0x047ec085}}
            # Address: 0x004518AA = base (0x400000) + 0x518AA
            # Original bytes (little-endian): 0x047ec085 -> 85 C0 7E 04
            # Patch bytes (little-endian): 0x0033b866 -> 66 B8 33 00
            # 
            # Original: test eax,eax; jle +4
            # Patched:  mov ax, 0x33 (sets vase to "show contents" state)
            #
            # IMPORTANT: You must EXIT and RE-ENTER the Vasebreaker level
            # after enabling this cheat for it to take effect on the vases!
            addr = self.base_address + 0x518AA
            if state:
                try:
                    self.original_see_vase_bytes = self.pm.read_bytes(addr, 4)
                    print(f"[SeeVase] Original bytes at {hex(addr)}: {self.original_see_vase_bytes.hex()}")
                except:
                    pass
                # Apply pvztoolkit patch: mov ax, 0x33
                self.pm.write_bytes(addr, bytes([0x66, 0xB8, 0x33, 0x00]), 4)
                print(f"[SeeVase] Patched to: 66b83300 (mov ax, 0x33)")
                print(f"[SeeVase] NOTE: Exit and re-enter Vasebreaker level for effect!")
            else:
                if self.original_see_vase_bytes:
                    self.pm.write_bytes(addr, self.original_see_vase_bytes, 4)
                else:
                    self.pm.write_bytes(addr, bytes([0x85, 0xC0, 0x7E, 0x04]), 4)
            self.see_vase_active = state
            print(f"[SeeVase] {'Enabled' if state else 'Disabled'} at {hex(addr)}")
            return True
        except Exception as e:
            print(f"[SeeVase] Error: {e}")
            return False

    def kill_all_zombies(self):
        """Kill all zombies currently on the field."""
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            # Try multiple lawn offsets for different game versions
            lawn_offsets = [
                0x329670,  # GOTY 1.2.0.1073 EN
                0x2A9EC0,  # Some versions
                0x329688,  # Alternative GOTY offset
                0x191A28,  # Other versions
            ]

            lawn_ptr = None
            for lawn_offset in lawn_offsets:
                try:
                    ptr = self.pm.read_int(self.base_address + lawn_offset)
                    if ptr and 0x10000 < ptr < 0x7FFFFFFF:
                        lawn_ptr = ptr
                        print(f"[KillAllZombies] Found lawn at offset 0x{lawn_offset:X} -> 0x{ptr:X}")
                        break
                except:
                    continue

            if not lawn_ptr:
                print("[KillAllZombies] Could not find lawn pointer")
                return False

            # Board offset: 0x868 for GOTY, 0x768 for older versions
            board_ptr = None
            for board_offset in [0x868, 0x768]:
                try:
                    ptr = self.pm.read_int(lawn_ptr + board_offset)
                    if ptr and 0x10000 < ptr < 0x7FFFFFFF:
                        board_ptr = ptr
                        print(f"[KillAllZombies] Found board at offset 0x{board_offset:X} -> 0x{ptr:X}")
                        break
                except:
                    continue

            if not board_ptr:
                print("[KillAllZombies] Could not find board pointer")
                return False

            # Zombie array: 0xA8 for GOTY, 0x90 for older
            zombie_array = None
            zombie_count_max = 0
            for zombie_offset, count_offset in [(0xA8, 0xAC), (0x90, 0x94)]:
                try:
                    arr = self.pm.read_int(board_ptr + zombie_offset)
                    cnt = self.pm.read_int(board_ptr + count_offset)
                    if arr and 0x10000 < arr < 0x7FFFFFFF and cnt > 0:
                        zombie_array = arr
                        zombie_count_max = cnt
                        print(f"[KillAllZombies] Zombie array at 0x{arr:X}, max count: {cnt}")
                        break
                except:
                    continue

            if not zombie_array:
                print("[KillAllZombies] Could not find zombie array")
                return False

            zombie_struct_size = 0x168  # GOTY version
            kills = 0
            for i in range(min(zombie_count_max, 1000)):  # Safety limit
                offset = zombie_array + i * zombie_struct_size
                # Check if zombie is alive (dead flag at +0xEC)
                try:
                    dead = self.pm.read_bool(offset + 0xEC)
                    if not dead:
                        # Set status to dying (3 = instant death)
                        self.pm.write_int(offset + 0x28, 3)
                        kills += 1
                except:
                    pass
            print(f"[KillAllZombies] Killed {kills} zombies")
            return kills
        except Exception as e:
            print(f"[KillAllZombies] Error: {e}")
            return False

    def clear_all_plants(self):
        """Remove all plants from the field."""
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            # GOTY 1.2.0.1073 lawn offset: 0x329670
            base_ptr = self.pm.read_int(self.base_address + 0x329670)
            if not base_ptr:
                return False
            # board offset for GOTY: 0x768 + 0x100 = 0x868
            board_ptr = self.pm.read_int(base_ptr + 0x868)
            if not board_ptr:
                return False
            # plant offset for GOTY: 0xac + 0x18 = 0xC4
            plant_array = self.pm.read_int(board_ptr + 0xC4)
            # plant_count_max for GOTY: 0xb0 + 0x18 = 0xC8
            plant_count_max = self.pm.read_int(board_ptr + 0xC8)
            
            plant_struct_size = 0x14C
            cleared = 0
            for i in range(plant_count_max):
                offset = plant_array + i * plant_struct_size
                try:
                    dead = self.pm.read_bool(offset + 0x141)
                    squished = self.pm.read_bool(offset + 0x142)
                    if not dead and not squished:
                        # Mark plant as dead
                        self.pm.write_bool(offset + 0x141, True)
                        cleared += 1
                except:
                    pass
            print(f"[ClearAllPlants] Cleared {cleared} plants")
            return cleared
        except Exception as e:
            print(f"[ClearAllPlants] Error: {e}")
            return False

    def toggle_collect_1000_sun(self, state):
        """Toggle collect +1000 sun"""
        if not self.pm:
            if not self.attach_process():
                return False

        try:
            addr = self.base_address + self.collect_sun_address

            if state:
                self.collect_cave = self.pm.allocate(64)

                body_code = bytearray([
                    0x81, 0x80, 0x78, 0x55, 0x00, 0x00,
                    0xE8, 0x03, 0x00, 0x00,
                    0xE9, 0x00, 0x00, 0x00, 0x00
                ])

                return_addr = addr + 6
                jmp_offset = return_addr - (self.collect_cave + len(body_code))
                struct.pack_into('<i', body_code, len(body_code) - 4, jmp_offset)

                self.pm.write_bytes(self.collect_cave, bytes(body_code), len(body_code))

                jmp_to_cave = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00, 0x90])
                cave_offset = self.collect_cave - (addr + 5)
                struct.pack_into('<i', jmp_to_cave, 1, cave_offset)
                self.pm.write_bytes(addr, bytes(jmp_to_cave), 6)
            else:
                self.pm.write_bytes(addr, self.original_collect_bytes, len(self.original_collect_bytes))

                if self.collect_cave:
                    try:
                        self.pm.free(self.collect_cave)
                    except:
                        pass
                    self.collect_cave = None

            self.collect_1000_sun_active = state
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle collect+1000 sun: {str(e)}")
            return False

    def toggle_prevent_spend(self, state):
        """Toggle prevention of sun subtraction when planting"""
        if not self.pm:
            if not self.attach_process():
                return False

        try:
            addr = self.base_address + self.plant_sub_address

            if state:
                nops = bytes([0x90] * 6)
                self.pm.write_bytes(addr, nops, len(nops))
            else:
                self.pm.write_bytes(addr, self.original_plant_sub_bytes, len(self.original_plant_sub_bytes))

            self.prevent_spend_active = state
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle prevent-spend: {str(e)}")
            return False

    def toggle_planting_adds_sun(self, state):
        """When planting, add sun instead of subtracting"""
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            addr = self.base_address + self.plant_sub_instr

            if state:
                self.plant_add_cave = self.pm.allocate(256)

                imm = struct.pack('<I', 2000)
                cave_code = bytearray([0x81, 0xC6]) + imm
                cave_code += bytearray([0x89, 0xB7, 0x78, 0x55, 0x00, 0x00])
                cave_code += bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])

                return_addr = addr + 8
                jmp_back = return_addr - (self.plant_add_cave + len(cave_code))
                struct.pack_into('<i', cave_code, len(cave_code) - 4, jmp_back)

                self.pm.write_bytes(self.plant_add_cave, bytes(cave_code), len(cave_code))

                jmp_to_cave = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00, 0x90, 0x90, 0x90])
                cave_offset = self.plant_add_cave - (addr + 5)
                struct.pack_into('<i', jmp_to_cave, 1, cave_offset)

                self.original_plant_patch_bytes = self.original_sub_bytes + self.original_plant_sub_bytes
                self.pm.write_bytes(addr, bytes(jmp_to_cave), len(jmp_to_cave))
            else:
                try:
                    self.pm.write_bytes(self.base_address + self.plant_sub_instr, self.original_plant_patch_bytes, len(self.original_plant_patch_bytes))
                except:
                    pass

                if getattr(self, 'plant_add_cave', None):
                    try:
                        self.pm.free(self.plant_add_cave)
                    except:
                        pass
                    self.plant_add_cave = None

            self.planting_adds_sun_active = state
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle planting-adds-sun: {str(e)}")
            return False

    def toggle_plant_anywhere(self, state):
        """Toggle planting anywhere using a code-cave that still blocks occupied tiles."""
        if not self.pm:
            if not self.attach_process():
                return False

        addr = self.base_address + self.plant_anywhere_offset
        original_jump_target = self.base_address + 0x13115
        try:
            if state:
                # Save original bytes, then write an unconditional JMP to the original JE target
                try:
                    self.original_plant_anywhere_bytes = self.pm.read_bytes(addr, 6)
                except:
                    pass

                # build JMP instruction: E9 <rel32> and pad with NOP to 6 bytes
                jmp = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00, 0x90])
                rel = original_jump_target - (addr + 5)
                struct.pack_into('<i', jmp, 1, rel)

                self.pm.write_bytes(addr, bytes(jmp), len(jmp))
            else:
                # restore original bytes
                try:
                    self.pm.write_bytes(addr, self.original_plant_anywhere_bytes, len(self.original_plant_anywhere_bytes))
                except:
                    pass

            self.plant_anywhere_active = state
            return True
        except Exception as e:
            print(f"[PlantAnywhere] toggle error: {e}")
            return False

    def set_move_zombie_row_value(self, row):
        try:
            r = int(row)
        except:
            return False
        if r < 0:
            r = 0
        if r > 4:
            r = 4
        self.move_zombie_row_value = r
        # If feature is active, update the imm32 in existing caves so change applies immediately
        if getattr(self, 'move_zombie_row_active', False):
            # imm32 in our stub is at offset 6 (mov 3 bytes + C7 modrm+disp = 3 bytes)
            imm_offset = 6
            for addr, cave in getattr(self, 'move_zombie_row_caves', {}).items():
                if cave:
                    try:
                        self.pm.write_bytes(cave + imm_offset, struct.pack('<I', self.move_zombie_row_value), 4)
                    except Exception as e:
                        try:
                            print(f"[MoveZombie] failed to update cave {hex(cave)}: {e}")
                        except:
                            pass
        return True

    def set_plant_changer_value(self, plant_id):
        try:
            v = int(plant_id)
        except:
            return False
        if v < 0:
            v = 0
        if v > 52:
            v = 52
        self.plant_changer_value = v
        # If active, update ALL imm32 values in the code cave
        if getattr(self, 'plant_changer_active', False) and getattr(self, 'plant_changer_cave', None):
            try:
                # Update all imm32 offsets (for [ebx+1C], [ebx+24], [ebx+28])
                imm_offsets = getattr(self, 'plant_changer_imm_offsets', None)
                if imm_offsets:
                    for offset in imm_offsets:
                        self.pm.write_bytes(
                            self.plant_changer_cave + offset,
                            struct.pack('<I', self.plant_changer_value),
                            4
                        )
                # Also check old single offset attributes for backward compatibility
                else:
                    imm_offset = getattr(self, 'plant_changer_imm_offset', None)
                    if imm_offset is not None:
                        self.pm.write_bytes(
                            self.plant_changer_cave + imm_offset,
                            struct.pack('<I', self.plant_changer_value),
                            4
                        )
                    imm_offset2 = getattr(self, 'plant_changer_imm_offset2', None)
                    if imm_offset2 is not None:
                        self.pm.write_bytes(
                            self.plant_changer_cave + imm_offset2,
                            struct.pack('<I', self.plant_changer_value),
                            4
                        )
                print(f"[PlantChanger] Updated plant value to {v} ({PLANT_NAMES[v] if v < len(PLANT_NAMES) else 'Unknown'})")
            except Exception as e:
                try:
                    print(f"[PlantChanger] failed to update plant value: {e}")
                except:
                    pass
        return True

    def set_bullet_changer_value(self, bullet_id):
        """Set desired bullet type (0-12). Updates imm32 if active."""
        try:
            v = int(bullet_id)
        except:
            return False
        if v < 0:
            v = 0
        if v > 12:
            v = 12
        self.bullet_changer_value = v
        if getattr(self, 'bullet_changer_active', False) and getattr(self, 'bullet_changer_cave', None):
            try:
                if self.bullet_imm_offset is not None:
                    self.pm.write_bytes(self.bullet_changer_cave + self.bullet_imm_offset, struct.pack('<I', self.bullet_changer_value), 4)
                print(f"[BulletChanger] Updated bullet value to {v}")
            except Exception as e:
                try:
                    print(f"[BulletChanger] failed to update bullet value: {e}")
                except:
                    pass
        return True

    def set_fast_shoot_delay(self, delay):
        """Set desired shoot delay ticks (0-255)."""
        try:
            v = int(delay)
        except:
            return False
        if v < 0:
            v = 0
        if v > 255:
            v = 255
        self.fast_shoot_delay = v
        if getattr(self, 'fast_shoot_active', False) and getattr(self, 'fast_shoot_cave', None):
            try:
                if self.fast_shoot_imm_offset is not None:
                    self.pm.write_bytes(self.fast_shoot_cave + self.fast_shoot_imm_offset, struct.pack('<I', self.fast_shoot_delay), 4)
                print(f"[FastShoot] Updated delay to {v}")
            except Exception as e:
                try:
                    print(f"[FastShoot] failed to update delay: {e}")
                except:
                    pass
        return True

    def set_money_amount(self, amount):
        """Set desired money amount (0-999999). Updates imm32 if active."""
        try:
            v = int(amount)
        except:
            return False
        if v < 0:
            v = 0
        if v > 9999999:
            v = 9999999
        self.money_amount = v
        if getattr(self, 'money_changer_active', False) and getattr(self, 'money_cave', None):
            try:
                if self.money_imm_offset is not None:
                    self.pm.write_bytes(self.money_cave + self.money_imm_offset, struct.pack('<I', self.money_amount), 4)
                print(f"[Money] Updated amount to {v}")
            except Exception as e:
                try:
                    print(f"[Money] failed to update amount: {e}")
                except:
                    pass
        return True

    def toggle_move_zombie_row(self, state):
        """Toggle forcing zombies into a chosen row by patching mov [eax+1C]."""
        if not self.pm:
            if not self.attach_process():
                return False
        addrs = [self.base_address + off for off in self.move_zombie_row_offsets]

        try:
            if state:
                orig_len = 9
                for addr in addrs:
                    try:
                        try:
                            ob = self.pm.read_bytes(addr, orig_len)
                        except:
                            ob = None
                        self.original_move_zombie_bytes[addr] = ob

                        cave = self.pm.allocate(256)
                        self.move_zombie_row_caves[addr] = cave

                        # build stub
                        if ob and len(ob) >= orig_len:
                            mov_instr = ob[0:3]
                            imul_instr = ob[3:orig_len]
                            orig_modrm = mov_instr[1]
                            disp = mov_instr[2]
                            rm = orig_modrm & 0x07

                            stub = bytearray()
                            stub += bytes(mov_instr)
                            c7_modrm = 0x40 | (rm & 0x07)
                            stub += bytearray([0xC7, c7_modrm, disp])
                            stub += struct.pack('<I', self.move_zombie_row_value)
                            stub += bytes(imul_instr)
                            stub += bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                        else:
                            stub = bytearray()
                            stub += bytearray([0x8B, 0x50, 0x1C])
                            stub += bytearray([0xC7, 0x40, 0x1C, 0x00, 0x00, 0x00, 0x00])
                            stub += bytearray([0x69, 0xD2, 0x10, 0x27, 0x00, 0x00])
                            stub += bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                            struct.pack_into('<I', stub, 3, self.move_zombie_row_value)

                        cave_base = cave
                        jmp_index = len(stub) - 4
                        addr_after_jmp = cave_base + jmp_index + 4
                        ret = addr + orig_len
                        rel = ret - addr_after_jmp
                        struct.pack_into('<i', stub, jmp_index, rel)

                        try:
                            print(f"[MoveZombie] addr={hex(addr)} orig_bytes={(ob.hex() if ob else None)} cave={hex(cave_base)} stub={stub.hex()}")
                        except:
                            pass

                        self.pm.write_bytes(cave_base, bytes(stub), len(stub))

                        jmp = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                        rel_to_cave = cave_base - (addr + 5)
                        struct.pack_into('<i', jmp, 1, rel_to_cave)
                        patch = jmp + bytes([0x90] * (orig_len - len(jmp)))
                        self.pm.write_bytes(addr, bytes(patch), len(patch))
                    except Exception as e:
                        print(f"[MoveZombie] patch addr {hex(addr)} failed: {e}")
            else:
                for addr in addrs:
                    try:
                        ob = self.original_move_zombie_bytes.get(addr, None)
                        if ob:
                            self.pm.write_bytes(addr, ob, len(ob))
                    except:
                        pass
                    cave = self.move_zombie_row_caves.get(addr, None)
                    if cave:
                        try:
                            self.pm.free(cave)
                        except:
                            pass
                        self.move_zombie_row_caves[addr] = None

            self.move_zombie_row_active = state
            return True
        except Exception as e:
            print(f"[MoveZombieRow] toggle error: {e}")
            return False

    def scan_for_pattern(self, pattern, mask=None, start_offset=0, scan_size=0x300000):
        """Scan memory for a byte pattern. Returns offset from base if found, None otherwise.

        pattern: bytes to search for
        mask: optional mask where 0x00 means wildcard, 0xFF means exact match
        """
        try:
            scan_start = self.base_address + start_offset
            chunk_size = 0x400000  # 4MB chunks to avoid cross-region reads
            total = 0
            while total < scan_size:
                size = min(chunk_size, scan_size - total)
                cur_addr = scan_start + total
                try:
                    data = self.pm.read_bytes(cur_addr, size)
                except Exception:
                    # Skip unreadable range
                    total += size
                    continue

                if mask is None:
                    idx = data.find(pattern)
                    if idx != -1:
                        return start_offset + total + idx
                else:
                    pattern_len = len(pattern)
                    for i in range(len(data) - pattern_len):
                        match = True
                        for j in range(pattern_len):
                            if mask[j] == 0xFF and data[i + j] != pattern[j]:
                                match = False
                                break
                        if match:
                            return start_offset + total + i
                total += size
            return None
        except Exception as e:
            print(f"[Scan] Error: {e}")
            return None

    def toggle_plant_changer(self, state):
        """Toggle plant changer by finding and patching the plant type read instruction.

        Scans for the instruction pattern that reads plant type from seed packet
        and replaces it with a mov instruction that loads our desired plant type.
        """
        if not self.pm:
            if not self.attach_process():
                return False

        try:
            if state:
                # Attempt 0 (CE-style): Patch the read of [esi+28] sequence 8B 46 28 8B FD
                # This matches Cheat Engine scripts that hook the plant type fetch and
                # overwrite the seed packet type just-in-time. It preserves EAX.
                ce_sig = bytes([0x8B, 0x46, 0x28, 0x8B, 0xFD])
                ce_found = None
                try:
                    ce_found = self.scan_for_pattern(
                        pattern=ce_sig,
                        mask=None,
                        start_offset=0x1000,
                        scan_size=0x1000000
                    )
                except Exception:
                    ce_found = None

                if ce_found is not None:
                    try:
                        addr0 = self.base_address + ce_found
                        # Save original 5 bytes (two instructions)
                        orig_len0 = 5
                        ob0 = self.pm.read_bytes(addr0, orig_len0)

                        cave0 = self.pm.allocate(128)
                        stub0 = bytearray()
                        # Replicate original and preserve EAX
                        stub0 += bytearray([0x8B, 0x46, 0x28])     # mov eax, [esi+28]
                        stub0 += bytearray([0x50])                 # push eax
                        # mov dword ptr [esi+28], imm32
                        stub0 += bytearray([0xC7, 0x46, 0x28])
                        imm_off = len(stub0)
                        stub0 += struct.pack('<I', self.plant_changer_value)
                        stub0 += bytearray([0x58])                 # pop eax
                        stub0 += bytearray([0x8B, 0xFD])           # mov edi, ebp
                        # jmp back
                        stub0 += bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                        ret0 = addr0 + orig_len0
                        rel0 = ret0 - (cave0 + len(stub0))
                        struct.pack_into('<i', stub0, len(stub0) - 4, rel0)

                        # Write cave
                        self.pm.write_bytes(cave0, bytes(stub0), len(stub0))

                        # Patch original with JMP (5 bytes)
                        jmp0 = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                        struct.pack_into('<i', jmp0, 1, cave0 - (addr0 + 5))
                        self.pm.write_bytes(addr0, bytes(jmp0), len(jmp0))

                        # Track for updates/restoration
                        self.original_plant_changer_bytes = ob0
                        self.plant_changer_patch_addr = addr0
                        self.plant_changer_cave = cave0
                        self.plant_changer_imm_offsets = [imm_off]
                        print(f"[PlantChanger] CE-style patch at {hex(addr0)} -> cave {hex(cave0)} (imm at +{imm_off})")
                        # Mark as patched and skip other attempts
                        self.plant_changer_active = True
                        return True
                    except Exception as e:
                        print(f"[PlantChanger] CE-style patch failed: {e}")
                        # Fall through to next attempts

                # Safer default approach: use the seed-bank monitor thread to overwrite plant types
                # This avoids in-place code patching which has been causing crashes.
                # Before starting the thread, restore any previous patch if present.
                try:
                    if getattr(self, 'plant_changer_patch_addr', None) and self.plant_changer_patch_addr != "thread":
                        if self.original_plant_changer_bytes:
                            try:
                                self.pm.write_bytes(self.plant_changer_patch_addr, self.original_plant_changer_bytes, len(self.original_plant_changer_bytes))
                                print(f"[PlantChanger] Restored previous patch at {hex(self.plant_changer_patch_addr)} before starting thread")
                            except Exception:
                                pass
                        if getattr(self, 'plant_changer_cave', None):
                            try:
                                self.pm.free(self.plant_changer_cave)
                            except:
                                pass
                            self.plant_changer_cave = None

                except Exception:
                    pass

                # Attempt 1: Patch at 0x61570 where plant type is WRITTEN to the plant object.
                # We'll write our value to BOTH behavior and visual type fields to keep
                # animations/collision in sync for "fake" plants.
                # [ebx+24] = behavior type
                # [ebx+28] = visual/animation type
                # Also override ESI before it's used elsewhere
                patched = False
                target_offset = 0x61570
                addr = self.base_address + target_offset

                try:
                    # Read 9 bytes (both instructions we'll replace)
                    orig_len = 9
                    ob = self.pm.read_bytes(addr, orig_len)
                    print(f"[PlantChanger] Original bytes at {hex(addr)}: {ob.hex()}")

                    # Verify signature: 89 73 24 (mov [ebx+24], esi)
                    if ob[:3] != b"\x89\x73\x24":
                        print(f"[PlantChanger] Signature mismatch: expected 897324, got {ob[:3].hex()}")
                    else:
                        print("[PlantChanger] Confirmed: mov [ebx+24],esi found!")

                        cave = self.pm.allocate(128)

                        # Build stub - write to [ebx+24] (behavior) and [ebx+28] (visual)
                        stub = bytearray()

                        # 1. Override ESI with our plant value
                        stub += bytes([0xBE])  # mov esi, imm32
                        self.plant_changer_imm_offsets = [len(stub)]
                        stub += struct.pack('<I', self.plant_changer_value)

                        # 2a. Write to behavior field
                        stub += bytes([0x89, 0x73, 0x24])  # mov [ebx+24], esi
                        # 2b. Write to visual/animation field
                        stub += bytes([0x89, 0x73, 0x28])  # mov [ebx+28], esi

                        # DO NOT write to other offsets:
                        # [ebx+08] = row position
                        # [ebx+1C] = zombie targeting / planting validation
                        # [ebx+28] = plant-to-zombie collision

                        # 3. Preserve original second instruction: mov [ebx+0x138], edx
                        stub += bytes([0x89, 0x93, 0x38, 0x01, 0x00, 0x00])

                        # 7. Jump back
                        stub += bytes([0xE9, 0x00, 0x00, 0x00, 0x00])
                        return_addr = addr + orig_len  # 0x461579
                        jmp_rel = return_addr - (cave + len(stub))
                        struct.pack_into('<i', stub, len(stub) - 4, jmp_rel)

                        # Write cave
                        self.pm.write_bytes(cave, bytes(stub), len(stub))
                        print(f"[PlantChanger] Cave at {hex(cave)}: {stub.hex()}")

                        # Write JMP + NOPs (9 bytes total)
                        jmp_to_cave = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                        jmp_offset = cave - (addr + 5)
                        struct.pack_into('<i', jmp_to_cave, 1, jmp_offset)
                        jmp_to_cave += bytes([0x90] * 4)

                        # Save original and apply patch
                        self.original_plant_changer_bytes = ob
                        self.plant_changer_patch_addr = addr
                        self.plant_changer_cave = cave

                        self.pm.write_bytes(addr, bytes(jmp_to_cave), 9)
                        print(f"[PlantChanger] SUCCESS! Patched {hex(addr)} -> cave {hex(cave)}")
                        print(f"[PlantChanger] Writes to [ebx+24] (behavior) and [ebx+28] (visual)")
                        patched = True

                except Exception as e:
                    print(f"[PlantChanger] Patch failed: {e}")
                    import traceback
                    traceback.print_exc()

                # Attempt 2: Early init patch only if the fallback didn't match your build
                if not patched:
                    early_found = None
                    try:
                        # Wildcard search for 'mov esi, [eax+disp]' pattern: 8B 70 ??
                        early_found = self.scan_for_pattern(
                            pattern=bytes([0x8B, 0x70, 0x00]),
                            mask=bytes([0xFF, 0xFF, 0x00]),
                            start_offset=0x10000,
                            scan_size=0x800000
                        )
                    except Exception:
                        early_found = None

                    if early_found is not None:
                        try:
                            addr2 = self.base_address + early_found
                            orig_len2 = 6
                            ob2 = self.pm.read_bytes(addr2, orig_len2)
                            # displacement used by the found instruction
                            try:
                                disp = self.pm.read_bytes(addr2 + 2, 1)[0]
                            except:
                                disp = 0x28

                            cave2 = self.pm.allocate(128)
                            stub2 = bytearray()
                            # Write desired type into the seed packet memory: [eax+disp] = imm32
                            stub2 += bytearray([0xC7, 0x40, disp])
                            imm_offset1 = len(stub2)
                            stub2 += struct.pack('<I', self.plant_changer_value)
                            # Set esi to the same value: mov esi, imm32
                            stub2 += bytearray([0xBE])
                            imm_offset2 = len(stub2)
                            stub2 += struct.pack('<I', self.plant_changer_value)
                            # Jump back after the original bytes we replaced
                            stub2 += bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                            ret2 = addr2 + orig_len2
                            rel2 = ret2 - (cave2 + len(stub2))
                            struct.pack_into('<i', stub2, len(stub2) - 4, rel2)

                            self.pm.write_bytes(cave2, bytes(stub2), len(stub2))
                            jmp2 = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                            struct.pack_into('<i', jmp2, 1, cave2 - (addr2 + 5))
                            patch2 = jmp2 + bytes([0x90] * (orig_len2 - len(jmp2)))
                            self.pm.write_bytes(addr2, bytes(patch2), len(patch2))

                            self.original_plant_changer_bytes = ob2
                            self.plant_changer_patch_addr = addr2
                            self.plant_changer_cave = cave2
                            self.plant_changer_imm_offsets = [imm_offset1, imm_offset2]
                            print(f"[PlantChanger] Early init patch applied at {hex(addr2)} with disp {hex(disp)} -> cave {hex(cave2)}")
                            patched = True
                        except Exception as e:
                            print(f"[PlantChanger] Early init patch failed: {e}")

                if not patched:
                    # Start the seed bank monitor thread (safe method)
                    print("[PlantChanger] Starting safe seed-bank monitor thread")
                    self._plant_changer_thread_active = True
                    self.plant_changer_patch_addr = "thread"

                    # change-detection monitor: write immediately after game writes plant type
                    if not hasattr(self, '_plant_changer_prev_values'):
                        self._plant_changer_prev_values = {}

                    def plant_type_monitor():
                        while getattr(self, '_plant_changer_thread_active', False):
                            try:
                                game_ptr, board_ptr = self.get_game_board()
                                if not board_ptr:
                                    time.sleep(0.02)
                                    continue

                                # Robust approach: continuously set every seed slot's type
                                # so any slot plants the chosen type with full behavior.
                                seed_bank_ptr = None
                                for sbo in [0x144, 0x148, 0x140, 0x14C]:
                                    try:
                                        val = struct.unpack('<I', self.pm.read_bytes(board_ptr + sbo, 4))[0]
                                        if val and val > 0x10000:
                                            seed_bank_ptr = val
                                            break
                                    except:
                                        continue

                                if seed_bank_ptr and seed_bank_ptr > 0x10000:
                                    slot_sizes = [0x50, 0x58, 0x60, 0x70]
                                    for slot in range(12):
                                        for sz in slot_sizes:
                                            slot_addr = seed_bank_ptr + (slot * sz)
                                            # behavior type
                                            try:
                                                self.pm.write_bytes(slot_addr + 0x24, struct.pack('<I', self.plant_changer_value), 4)
                                            except:
                                                pass
                                            # visual/animation type
                                            try:
                                                self.pm.write_bytes(slot_addr + 0x28, struct.pack('<I', self.plant_changer_value), 4)
                                            except:
                                                pass

                            except Exception:
                                pass
                            # Keep interval small for responsiveness without overloading the process.
                            time.sleep(0.002)

                    thread = threading.Thread(target=plant_type_monitor, daemon=True)
                    thread.start()
                    print("[PlantChanger] Seed bank monitor change-detection thread started (safe mode)")

            else:
                # Stop thread if running
                self._plant_changer_thread_active = False

                # Restore original bytes (if not thread-based)
                if self.original_plant_changer_bytes and self.plant_changer_patch_addr:
                    if self.plant_changer_patch_addr != "thread":
                        try:
                            self.pm.write_bytes(
                                self.plant_changer_patch_addr,
                                self.original_plant_changer_bytes,
                                len(self.original_plant_changer_bytes)
                            )
                            print(f"[PlantChanger] Restored {len(self.original_plant_changer_bytes)} bytes at {hex(self.plant_changer_patch_addr)}")
                        except Exception as e:
                            print(f"[PlantChanger] Failed to restore: {e}")

                # Free code cave if used
                if self.plant_changer_cave:
                    try:
                        self.pm.free(self.plant_changer_cave)
                        print(f"[PlantChanger] Freed code cave")
                    except:
                        pass
                    self.plant_changer_cave = None

                self.plant_changer_patch_addr = None
                self.original_plant_changer_bytes = None
                print("[PlantChanger] Disabled")

            self.plant_changer_active = state
            return True
        except Exception as e:
            print(f"[PlantChanger] Toggle error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def toggle_run_in_background(self, state):
        """Toggle running while unfocused (patch JE -> NOP)."""
        if not self.pm:
            if not self.attach_process():
                return False

        # Offsets from module base (observed in CE trace)
        addr1 = self.base_address + 0x1D21BB  # 6-byte JE (0F 84 AC 00 00 00)
        addr2 = self.base_address + 0x1D21D9  # 2-byte JE (74 40)

        try:
            if state:
                # Save originals and write NOPs
                try:
                    self.original_background_bytes1 = self.pm.read_bytes(addr1, 6)
                except:
                    pass
                try:
                    self.original_background_bytes2 = self.pm.read_bytes(addr2, 2)
                except:
                    pass

                self.pm.write_bytes(addr1, bytes([0x90] * 6), 6)
                self.pm.write_bytes(addr2, bytes([0x90] * 2), 2)
            else:
                # Restore originals
                try:
                    self.pm.write_bytes(addr1, self.original_background_bytes1, len(self.original_background_bytes1))
                except:
                    pass
                try:
                    self.pm.write_bytes(addr2, self.original_background_bytes2, len(self.original_background_bytes2))
                except:
                    pass

            self.run_in_background_active = state
            return True
        except Exception as e:
            print(f"[Background] toggle error: {e}")
            return False

    def toggle_bullet_changer(self, state):
        """Toggle changing bullet type by patching the write to [ebp+5C].

        Hooks the instruction sequence '89 45 5C 8B C6' and replaces it with
        a cave that writes our imm32 bullet type to [ebp+5C], then restores
        the original 'mov eax, esi' before jumping back.
        """
        if not self.pm:
            if not self.attach_process():
                return False

        try:
            if state:
                # Try direct address first, then pattern scan
                patched = False
                candidates = [0x70E29]
                sig = b"\x89\x45\x5C\x8B\xC6"
                addr0 = None

                for off in candidates:
                    try:
                        a = self.base_address + off
                        ob = self.pm.read_bytes(a, 5)
                        if ob == sig:
                            addr0 = a
                            break
                    except:
                        continue

                if addr0 is None:
                    found = self.scan_for_pattern(sig, None, start_offset=0x1000, scan_size=0x1200000)
                    if found is not None:
                        addr0 = self.base_address + found

                if addr0 is None:
                    print("[BulletChanger] Signature not found")
                else:
                    try:
                        # Save original bytes
                        self.original_bullet_bytes = self.pm.read_bytes(addr0, 5)

                        # Build cave: C7 45 5C imm32 ; 8B C6 ; E9 rel32
                        cave = self.pm.allocate(64)
                        stub = bytearray([0xC7, 0x45, 0x5C])
                        self.bullet_imm_offset = len(stub)
                        stub += struct.pack('<I', self.bullet_changer_value)
                        stub += bytearray([0x8B, 0xC6])
                        stub += bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                        ret = addr0 + 5
                        rel = ret - (cave + len(stub))
                        struct.pack_into('<i', stub, len(stub) - 4, rel)

                        self.pm.write_bytes(cave, bytes(stub), len(stub))

                        # Patch: JMP cave
                        jmp = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                        struct.pack_into('<i', jmp, 1, cave - (addr0 + 5))
                        self.pm.write_bytes(addr0, bytes(jmp), len(jmp))

                        self.bullet_changer_cave = cave
                        self.bullet_patch_addr = addr0
                        print(f"[BulletChanger] Patched {hex(addr0)} -> cave {hex(cave)} (imm at +{self.bullet_imm_offset})")
                        patched = True
                    except Exception as e:
                        print(f"[BulletChanger] Patch failed: {e}")

                if not patched:
                    return False
            else:
                # restore
                try:
                    if self.bullet_patch_addr and self.original_bullet_bytes:
                        self.pm.write_bytes(self.bullet_patch_addr, self.original_bullet_bytes, len(self.original_bullet_bytes))
                        print(f"[BulletChanger] Restored 5 bytes at {hex(self.bullet_patch_addr)}")
                except Exception as e:
                    print(f"[BulletChanger] restore failed: {e}")
                if self.bullet_changer_cave:
                    try:
                        self.pm.free(self.bullet_changer_cave)
                    except:
                        pass
                    self.bullet_changer_cave = None
                self.bullet_patch_addr = None
                self.original_bullet_bytes = None

            self.bullet_changer_active = state
            return True
        except Exception as e:
            print(f"[BulletChanger] toggle error: {e}")
            return False

    def toggle_rapid_fire(self, state):
        """Bypass the shoot gate by NOPing the conditional JNE following 'cmp dword ptr [edi+90], 01'."""
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            if state:
                sig = b"\x83\xBF\x90\x00\x00\x00\x01"  # cmp dword ptr [edi+90],01
                found = self.scan_for_pattern(sig, None, start_offset=0x1000, scan_size=0x1400000)
                if found is None:
                    print("[RapidFire] cmp signature not found")
                    return False
                cmp_addr = self.base_address + found
                jne_addr = cmp_addr + 7  # JNE starts right after cmp (length 6)
                try:
                    self.original_rapid_fire_bytes = self.pm.read_bytes(jne_addr, 6)
                except:
                    self.original_rapid_fire_bytes = None
                # Write NOPs to disable branch
                self.pm.write_bytes(jne_addr, bytes([0x90] * 6), 6)
                self.rapid_fire_jne_addr = jne_addr
                print(f"[RapidFire] NOPed JNE at {hex(jne_addr)}")
            else:
                if self.rapid_fire_jne_addr and self.original_rapid_fire_bytes:
                    try:
                        self.pm.write_bytes(self.rapid_fire_jne_addr, self.original_rapid_fire_bytes, len(self.original_rapid_fire_bytes))
                        print(f"[RapidFire] Restored JNE at {hex(self.rapid_fire_jne_addr)}")
                    except Exception as e:
                        print(f"[RapidFire] restore failed: {e}")
                self.rapid_fire_jne_addr = None
                self.original_rapid_fire_bytes = None
            self.rapid_fire_active = state
            return True
        except Exception as e:
            print(f"[RapidFire] toggle error: {e}")
            return False

    def toggle_fast_shoot(self, state):
        """Lower shoot delay by writing imm32 to [esi+58] via cave and preserving cmp eax,12."""
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            if state:
                addr = self.base_address + 0x6322C
                # We patch 6 bytes (mov [esi+58], ecx; cmp eax,12)
                try:
                    self.original_fast_shoot_bytes = self.pm.read_bytes(addr, 6)
                except:
                    self.original_fast_shoot_bytes = None

                cave = self.pm.allocate(64)
                stub = bytearray([0xC7, 0x46, 0x58])  # mov dword ptr [esi+58], imm32
                self.fast_shoot_imm_offset = len(stub)
                stub += struct.pack('<I', self.fast_shoot_delay)
                stub += bytearray([0x83, 0xF8, 0x12])  # cmp eax,12
                stub += bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                ret = addr + 6
                rel = ret - (cave + len(stub))
                struct.pack_into('<i', stub, len(stub) - 4, rel)
                self.pm.write_bytes(cave, bytes(stub), len(stub))

                jmp = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00, 0x90])  # pad to 6 bytes
                struct.pack_into('<i', jmp, 1, cave - (addr + 5))
                self.pm.write_bytes(addr, bytes(jmp), len(jmp))

                self.fast_shoot_cave = cave
                self.fast_shoot_patch_addr = addr
                print(f"[FastShoot] Patched {hex(addr)} -> cave {hex(cave)} (delay={self.fast_shoot_delay})")
            else:
                if self.fast_shoot_patch_addr and self.original_fast_shoot_bytes:
                    try:
                        self.pm.write_bytes(self.fast_shoot_patch_addr, self.original_fast_shoot_bytes, len(self.original_fast_shoot_bytes))
                        print(f"[FastShoot] Restored bytes at {hex(self.fast_shoot_patch_addr)}")
                    except Exception as e:
                        print(f"[FastShoot] restore failed: {e}")
                if self.fast_shoot_cave:
                    try:
                        self.pm.free(self.fast_shoot_cave)
                    except:
                        pass
                    self.fast_shoot_cave = None
                self.fast_shoot_patch_addr = None
                self.original_fast_shoot_bytes = None
            self.fast_shoot_active = state
            return True
        except Exception as e:
            print(f"[FastShoot] toggle error: {e}")
            return False

    def toggle_money_changer(self, state):
        """Set coins by hooking 'mov eax,[ecx+50]; cmp eax,imm'.

        Replaces the sequence at the read/compare site with a cave that writes
        our desired amount to `[ecx+50]`, performs the original `mov` and `cmp`,
        then returns. Works across versions via signature scan.
        """
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            if state:
                # Preferred known address first, then signature scan
                addr = None
                candidates = [0x976AD]
                seq_len = 8  # 8B 41 50 3D 9F 86 01 00
                for off in candidates:
                    try:
                        a = self.base_address + off
                        b = self.pm.read_bytes(a, seq_len)
                        if b and len(b) >= 8 and b[:3] == b"\x8B\x41\x50":
                            addr = a
                            break
                    except:
                        continue
                if addr is None:
                    sig = b"\x8B\x41\x50\x3D\x9F\x86\x01\x00"
                    found = self.scan_for_pattern(sig, None, start_offset=0x1000, scan_size=0x1600000)
                    if found is not None:
                        addr = self.base_address + found
                if addr is None:
                    print("[Money] signature not found")
                    return False

                try:
                    self.original_money_bytes = self.pm.read_bytes(addr, seq_len)
                except:
                    self.original_money_bytes = None

                cave = self.pm.allocate(64)
                stub = bytearray()
                # mov dword ptr [ecx+50], imm32
                stub += bytearray([0xC7, 0x41, 0x50])
                self.money_imm_offset = len(stub)
                stub += struct.pack('<I', self.money_amount)
                # original: mov eax, [ecx+50]
                stub += bytearray([0x8B, 0x41, 0x50])
                # original: cmp eax, 0001869F
                stub += bytearray([0x3D, 0x9F, 0x86, 0x01, 0x00])
                # jmp back
                stub += bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                ret = addr + seq_len
                rel = ret - (cave + len(stub))
                struct.pack_into('<i', stub, len(stub) - 4, rel)
                self.pm.write_bytes(cave, bytes(stub), len(stub))

                # patch: E9 rel32 + NOPs (pad to seq_len)
                jmp = bytearray([0xE9, 0x00, 0x00, 0x00, 0x00])
                struct.pack_into('<i', jmp, 1, cave - (addr + 5))
                patch = jmp + bytes([0x90] * (seq_len - len(jmp)))
                self.pm.write_bytes(addr, bytes(patch), len(patch))

                self.money_cave = cave
                self.money_patch_addr = addr
                print(f"[Money] Patched {hex(addr)} -> cave {hex(cave)} (amount={self.money_amount})")
            else:
                if self.money_patch_addr and self.original_money_bytes:
                    try:
                        self.pm.write_bytes(self.money_patch_addr, self.original_money_bytes, len(self.original_money_bytes))
                        print(f"[Money] Restored bytes at {hex(self.money_patch_addr)}")
                    except Exception as e:
                        print(f"[Money] restore failed: {e}")
                if self.money_cave:
                    try:
                        self.pm.free(self.money_cave)
                    except:
                        pass
                    self.money_cave = None
                self.money_patch_addr = None
                self.original_money_bytes = None
            self.money_changer_active = state
            return True
        except Exception as e:
            print(f"[Money] toggle error: {e}")
            return False

    # ===== NEW PVZTOOLKIT FEATURES =====

    def toggle_no_ice_trail(self, state):
        """Toggle no ice trail (Zomboni won't leave ice).
        GOTY 1.2.0.1073: {0x0053b0b0, {0xc3}, {0x51}} and {0x004222ea, {0xeb}, {0x75}}
        Also clears ice_trail_cd array when enabled.
        """
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            addr1 = self.base_address + self.no_ice_trail_offset1  # 0x13B0B0
            addr2 = self.base_address + self.no_ice_trail_offset2  # 0x222EA

            if state:
                # Save original bytes
                try:
                    self.original_no_ice_trail_bytes1 = self.pm.read_bytes(addr1, 1)
                    self.original_no_ice_trail_bytes2 = self.pm.read_bytes(addr2, 1)
                except:
                    pass
                # Patch: addr1: 0x51 -> 0xC3 (ret instead of push ecx)
                # Patch: addr2: 0x75 -> 0xEB (JNE -> JMP)
                self.pm.write_bytes(addr1, bytes([0xC3]), 1)
                self.pm.write_bytes(addr2, bytes([0xEB]), 1)
                
                # Clear existing ice trails (like pvztoolkit does)
                try:
                    lawn_ptr = self.pm.read_int(self.base_address + 0x329670)
                    if lawn_ptr:
                        board_ptr = self.pm.read_int(lawn_ptr + 0x868)
                        if board_ptr:
                            # ice_trail_cd offset for GOTY: 0x624 + 0x18 = 0x63C
                            ice_trail_cd_offset = 0x63C
                            # Clear ice trail cooldown for all 6 rows (6 ints = 24 bytes)
                            for i in range(6):
                                self.pm.write_int(board_ptr + ice_trail_cd_offset + i * 4, 0)
                            print(f"[NoIceTrail] Cleared existing ice trails")
                except:
                    pass
                    
                print(f"[NoIceTrail] Enabled at {hex(addr1)} and {hex(addr2)}")
            else:
                # Restore original bytes
                if self.original_no_ice_trail_bytes1:
                    self.pm.write_bytes(addr1, self.original_no_ice_trail_bytes1, 1)
                else:
                    self.pm.write_bytes(addr1, bytes([0x51]), 1)
                if self.original_no_ice_trail_bytes2:
                    self.pm.write_bytes(addr2, self.original_no_ice_trail_bytes2, 1)
                else:
                    self.pm.write_bytes(addr2, bytes([0x75]), 1)
                print(f"[NoIceTrail] Disabled")

            self.no_ice_trail_active = state
            return True
        except Exception as e:
            print(f"[NoIceTrail] Error: {e}")
            return False

    def toggle_zombie_not_explode(self, state):
        """Toggle zombie not explode (Jack-in-the-Box won't explode).
        GOTY 1.2.0.1073: {{0x0053718c, {0x81}, {0x8f}}, {0x00537c6d, {0x81}, {0x85}}}
        """
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            addr1 = self.base_address + self.zombie_not_explode_offset1  # 0x13718C
            addr2 = self.base_address + self.zombie_not_explode_offset2  # 0x137C6D

            if state:
                # Save original bytes
                try:
                    self.original_zombie_not_explode_bytes1 = self.pm.read_bytes(addr1, 1)
                    self.original_zombie_not_explode_bytes2 = self.pm.read_bytes(addr2, 1)
                except:
                    pass
                # Patch: addr1: 0x8F -> 0x81 (change condition)
                # Patch: addr2: 0x85 -> 0x81 (change condition)
                self.pm.write_bytes(addr1, bytes([0x81]), 1)
                self.pm.write_bytes(addr2, bytes([0x81]), 1)
                print(f"[ZombieNotExplode] Enabled at {hex(addr1)} and {hex(addr2)}")
            else:
                # Restore original bytes
                if self.original_zombie_not_explode_bytes1:
                    self.pm.write_bytes(addr1, self.original_zombie_not_explode_bytes1, 1)
                else:
                    self.pm.write_bytes(addr1, bytes([0x8F]), 1)
                if self.original_zombie_not_explode_bytes2:
                    self.pm.write_bytes(addr2, self.original_zombie_not_explode_bytes2, 1)
                else:
                    self.pm.write_bytes(addr2, bytes([0x85]), 1)
                print(f"[ZombieNotExplode] Disabled")

            self.zombie_not_explode_active = state
            return True
        except Exception as e:
            print(f"[ZombieNotExplode] Error: {e}")
            return False

    def toggle_unlock_sun_limit(self, state):
        """Toggle unlock sun limit (remove 9990 cap).
        GOTY 1.2.0.1073: {0x0041e6f5, {0xeb}, {0x7e}}
        """
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            addr = self.base_address + self.unlock_sun_limit_offset  # 0x1E6F5

            if state:
                # Save original byte
                try:
                    self.original_unlock_sun_limit_bytes = self.pm.read_bytes(addr, 1)
                except:
                    pass
                # Patch: 0x7E (JLE) -> 0xEB (JMP) - always jump, bypassing limit check
                self.pm.write_bytes(addr, bytes([0xEB]), 1)
                print(f"[UnlockSunLimit] Enabled at {hex(addr)}")
            else:
                # Restore original byte
                if self.original_unlock_sun_limit_bytes:
                    self.pm.write_bytes(addr, self.original_unlock_sun_limit_bytes, 1)
                else:
                    self.pm.write_bytes(addr, bytes([0x7E]), 1)
                print(f"[UnlockSunLimit] Disabled")

            self.unlock_sun_limit_active = state
            return True
        except Exception as e:
            print(f"[UnlockSunLimit] Error: {e}")
            return False

    def toggle_fast_belt(self, state):
        """Toggle fast conveyor belt.
        GOTY 1.2.0.1073: {{0x004257ff, {0x80}, {0x8f}}, {0x004948ae, {0x33}, {0x85}}}
        """
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            addr1 = self.base_address + self.fast_belt_offset1  # 0x257FF
            addr2 = self.base_address + self.fast_belt_offset2  # 0x948AE

            if state:
                # Save original bytes
                try:
                    self.original_fast_belt_bytes1 = self.pm.read_bytes(addr1, 1)
                    self.original_fast_belt_bytes2 = self.pm.read_bytes(addr2, 1)
                except:
                    pass
                # Patch: addr1: 0x8F -> 0x80 (change jump condition)
                # Patch: addr2: 0x85 -> 0x33 (xor eax,eax instead of test)
                self.pm.write_bytes(addr1, bytes([0x80]), 1)
                self.pm.write_bytes(addr2, bytes([0x33]), 1)
                print(f"[FastBelt] Enabled at {hex(addr1)} and {hex(addr2)}")
            else:
                # Restore original bytes
                if self.original_fast_belt_bytes1:
                    self.pm.write_bytes(addr1, self.original_fast_belt_bytes1, 1)
                else:
                    self.pm.write_bytes(addr1, bytes([0x8F]), 1)
                if self.original_fast_belt_bytes2:
                    self.pm.write_bytes(addr2, self.original_fast_belt_bytes2, 1)
                else:
                    self.pm.write_bytes(addr2, bytes([0x85]), 1)
                print(f"[FastBelt] Disabled")

            self.fast_belt_active = state
            return True
        except Exception as e:
            print(f"[FastBelt] Error: {e}")
            return False

    def toggle_lock_shovel(self, state):
        """Toggle lock shovel (keep shovel selected after use).
        GOTY 1.2.0.1073: {0x00414d53, {0x39}, {0x89}}
        """
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            addr = self.base_address + self.lock_shovel_offset  # 0x14D53

            if state:
                # Save original byte
                try:
                    self.original_lock_shovel_bytes = self.pm.read_bytes(addr, 1)
                except:
                    pass
                # Patch: 0x89 (MOV) -> 0x39 (CMP) - compare instead of move, keeping shovel selected
                self.pm.write_bytes(addr, bytes([0x39]), 1)
                print(f"[LockShovel] Enabled at {hex(addr)}")
            else:
                # Restore original byte
                if self.original_lock_shovel_bytes:
                    self.pm.write_bytes(addr, self.original_lock_shovel_bytes, 1)
                else:
                    self.pm.write_bytes(addr, bytes([0x89]), 1)
                print(f"[LockShovel] Disabled")

            self.lock_shovel_active = state
            return True
        except Exception as e:
            print(f"[LockShovel] Error: {e}")
            return False

    def restore_lawn_mowers(self):
        """Restore all lawn mowers using ASM code injection to call game function.
        GOTY 1.2.0.1073 offsets from pvztoolkit:
        - block_main_loop: 0x00551a90 + 6 = 0x551A96 (patch 0xC8 -> 0xC9 to block)
        - init_lawn_mowers: 0x0040e5b4 + 3 = 0x40E5B7 (patch 0x00 -> 0x01)
        - lawn_mower_initialize: 0x0045b8d0 + 2 = 0x45B8D2 (patch dword)
        - call_delete_lawn_mower: 0x0045c5d0
        - call_restore_lawn_mower: 0x0040e510
        - lawn_mower offset: 0x118 (from board)
        - lawn_mower_dead offset: 0x30 (in struct)
        - lawn_mower_count_max offset: 0x11C (from board)
        - lawn_mower_struct_size: 0x48
        """
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            import struct
            import ctypes
            import time

            # Get lawn and board pointers
            lawn_ptr = self.pm.read_int(self.base_address + 0x329670)
            if not lawn_ptr:
                print("[RestoreLawnMowers] Could not find lawn pointer")
                return False

            board_ptr = self.pm.read_int(lawn_ptr + 0x868)
            if not board_ptr:
                print("[RestoreLawnMowers] Could not find board pointer")
                return False

            # GOTY 1.2.0.1073 addresses
            block_main_loop_addr = self.base_address + 0x151A96    # 0x551A96
            init_lawn_mowers_addr = self.base_address + 0xE5B7     # 0x40E5B7
            lawn_mower_initialize_addr = self.base_address + 0x5B8D2  # 0x45B8D2
            call_delete_lawn_mower = self.base_address + 0x5C5D0   # 0x45C5D0
            call_restore_lawn_mower = self.base_address + 0xE510   # 0x40E510

            # Static addresses for dynamic pointer reading in ASM
            lawn_static_addr = self.base_address + 0x329670
            board_offset = 0x868

            # Lawn mower structure offsets
            lawn_mower_offset = 0x118      # board + 0x118
            lawn_mower_dead_offset = 0x30  # within lawn mower struct
            lawn_mower_count_max_offset = 0x11C  # board + 0x11C
            lawn_mower_struct_size = 0x48

            # Step 1: Block the game's main loop (CRITICAL for safe injection)
            print("[RestoreLawnMowers] Step 1: Blocking game main loop...")
            orig_block_main_loop = self.pm.read_bytes(block_main_loop_addr, 1)
            self.pm.write_bytes(block_main_loop_addr, bytes([0xC9]), 1)  # Block
            time.sleep(0.05)  # Wait for game to pause

            try:
                # Step 2: Enable the two critical hacks
                print("[RestoreLawnMowers] Step 2: Enabling memory patches...")

                orig_init_lawn_mowers = self.pm.read_bytes(init_lawn_mowers_addr, 1)
                orig_lawn_mower_initialize = self.pm.read_bytes(lawn_mower_initialize_addr, 4)

                self.pm.write_bytes(init_lawn_mowers_addr, bytes([0x01]), 1)
                self.pm.write_bytes(lawn_mower_initialize_addr, struct.pack('<I', 0x006FE1E4), 4)

                print(f"[RestoreLawnMowers] Patches applied")

                try:
                    # Step 3: Get lawn mower array info
                    lawn_mower_array = self.pm.read_int(board_ptr + lawn_mower_offset)
                    lawn_mower_count_max = self.pm.read_int(board_ptr + lawn_mower_count_max_offset)

                    print(f"[RestoreLawnMowers] Step 3: Lawn mower array at {hex(lawn_mower_array)}, count_max={lawn_mower_count_max}")

                    code_addr = self.pm.allocate(512)
                    if not code_addr:
                        print("[RestoreLawnMowers] Failed to allocate memory")
                        return False

                    try:
                        asm_code = bytearray()

                        # Delete existing non-dead lawn mowers
                        for i in range(lawn_mower_count_max):
                            mower_addr = lawn_mower_array + (lawn_mower_struct_size * i)
                            try:
                                is_dead = self.pm.read_bytes(mower_addr + lawn_mower_dead_offset, 1)[0]
                                if not is_dead:
                                    # mov eax, mower_addr
                                    asm_code.append(0xB8)
                                    asm_code.extend(struct.pack('<I', mower_addr))
                                    # call call_delete_lawn_mower
                                    call_offset = call_delete_lawn_mower - (code_addr + len(asm_code) + 5)
                                    asm_code.append(0xE8)
                                    asm_code.extend(struct.pack('<i', call_offset))
                                    print(f"[RestoreLawnMowers] Will delete mower at {hex(mower_addr)}")
                            except:
                                pass

                        # Call restore_lawn_mower with dynamically read board pointer
                        # mov eax, [lawn_static_addr] - read lawn pointer
                        asm_code.append(0xA1)  # mov eax, [imm32]
                        asm_code.extend(struct.pack('<I', lawn_static_addr))

                        # mov eax, [eax + board_offset] - read board pointer
                        asm_code.extend([0x8B, 0x80])  # mov eax, [eax + imm32]
                        asm_code.extend(struct.pack('<I', board_offset))

                        # push eax - push board pointer
                        asm_code.append(0x50)

                        # call call_restore_lawn_mower
                        call_offset = call_restore_lawn_mower - (code_addr + len(asm_code) + 5)
                        asm_code.append(0xE8)
                        asm_code.extend(struct.pack('<i', call_offset))

                        # ret (no stack cleanup needed - we're returning immediately)
                        asm_code.append(0xC3)

                        # Write the code
                        self.pm.write_bytes(code_addr, bytes(asm_code), len(asm_code))
                        print(f"[RestoreLawnMowers] Step 4: Executing ASM code at {hex(code_addr)}, length={len(asm_code)}")

                        # Execute using CreateRemoteThread
                        kernel32 = ctypes.windll.kernel32
                        PROCESS_ALL_ACCESS = 0x1F0FFF
                        INFINITE = 0xFFFFFFFF

                        process_handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, self.pm.process_id)
                        if process_handle:
                            thread_handle = kernel32.CreateRemoteThread(
                                process_handle, None, 0, code_addr, None, 0, None
                            )
                            if thread_handle:
                                kernel32.WaitForSingleObject(thread_handle, INFINITE)
                                kernel32.CloseHandle(thread_handle)
                                print("[RestoreLawnMowers] Lawn mowers restored!")
                            else:
                                print("[RestoreLawnMowers] Failed to create remote thread")
                            kernel32.CloseHandle(process_handle)
                        else:
                            print("[RestoreLawnMowers] Failed to open process")

                    finally:
                        try:
                            self.pm.free(code_addr)
                        except:
                            pass

                finally:
                    # Restore memory patches
                    print("[RestoreLawnMowers] Restoring memory patches...")
                    self.pm.write_bytes(init_lawn_mowers_addr, orig_init_lawn_mowers, 1)
                    self.pm.write_bytes(lawn_mower_initialize_addr, orig_lawn_mower_initialize, 4)

            finally:
                # Unblock the game's main loop
                print("[RestoreLawnMowers] Unblocking game main loop...")
                self.pm.write_bytes(block_main_loop_addr, bytes([0xC8]), 1)  # Unblock

            return True
        except Exception as e:
            print(f"[RestoreLawnMowers] Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def instant_win(self):
        """Trigger instant win using ASM code injection to call game function.
        GOTY 1.2.0.1073: call_fade_out_level = 0x0040ecd0
        """
        if not self.pm:
            if not self.attach_process():
                return False
        try:
            # Get lawn and board pointers
            lawn_ptr = self.pm.read_int(self.base_address + 0x329670)
            if not lawn_ptr:
                print("[InstantWin] Could not find lawn pointer")
                return False
            
            board_ptr = self.pm.read_int(lawn_ptr + 0x868)
            if not board_ptr:
                print("[InstantWin] Could not find board pointer")
                return False

            # Address of call_fade_out_level function
            call_fade_out_level = self.base_address + 0xECD0  # 0x40ECD0 - 0x400000
            
            # Allocate memory for our code
            code_addr = self.pm.allocate(256)
            if not code_addr:
                print("[InstantWin] Failed to allocate memory")
                return False
            
            try:
                # Build ASM code to call FadeOutLevel
                # void __thiscall Board::FadeOutLevel(Board* this)
                # The function takes board pointer in ecx (thiscall convention)
                # 
                # mov ecx, board_ptr
                # call call_fade_out_level
                # ret
                
                import struct
                asm_code = bytearray()
                
                # mov ecx, board_ptr (B9 + dword)
                asm_code.append(0xB9)
                asm_code.extend(struct.pack('<I', board_ptr))
                
                # call call_fade_out_level (E8 + relative offset)
                # relative offset = target - (current_address + 5)
                call_offset = call_fade_out_level - (code_addr + len(asm_code) + 5)
                asm_code.append(0xE8)
                asm_code.extend(struct.pack('<i', call_offset))  # signed 32-bit
                
                # ret (C3)
                asm_code.append(0xC3)
                
                # Write the code
                self.pm.write_bytes(code_addr, bytes(asm_code), len(asm_code))
                
                # Execute the code using CreateRemoteThread
                import ctypes
                kernel32 = ctypes.windll.kernel32
                
                # Get process handle
                PROCESS_ALL_ACCESS = 0x1F0FFF
                process_handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, self.pm.process_id)
                
                if process_handle:
                    # Create remote thread
                    thread_handle = kernel32.CreateRemoteThread(
                        process_handle,
                        None,
                        0,
                        code_addr,
                        None,
                        0,
                        None
                    )
                    
                    if thread_handle:
                        # Wait for thread to complete
                        kernel32.WaitForSingleObject(thread_handle, 1000)
                        kernel32.CloseHandle(thread_handle)
                        print("[InstantWin] Level win triggered!")
                    else:
                        print("[InstantWin] Failed to create remote thread")
                    
                    kernel32.CloseHandle(process_handle)
                else:
                    print("[InstantWin] Failed to open process")
                    
            finally:
                # Free allocated memory
                try:
                    self.pm.free(code_addr)
                except:
                    pass
            
            return True
        except Exception as e:
            print(f"[InstantWin] Error: {e}")
            return False

    def reset_all(self):
        """Disable all cheats and restore all original bytes."""
        if not self.pm:
            return False

        print("[ResetAll] Disabling all cheats and restoring original bytes...")

        # Disable infinite sun
        if self.infinite_sun_active:
            self.toggle_infinite_sun(False)

        # Disable no cooldown
        if self.no_cooldown_active:
            self.toggle_no_cooldown(False)

        # Disable one hit kill
        if self.one_hit_kill_active:
            self.toggle_one_hit_kill(False)

        # Disable collect 1000 sun
        if self.collect_1000_sun_active:
            self.toggle_collect_1000_sun(False)

        # Disable prevent spend
        if self.prevent_spend_active:
            self.toggle_prevent_spend(False)

        # Disable planting adds sun
        if self.planting_adds_sun_active:
            self.toggle_planting_adds_sun(False)

        # Disable auto collect
        if self.auto_collect_active:
            self.toggle_auto_collect(False)

        # Disable run in background
        if self.run_in_background_active:
            self.toggle_run_in_background(False)

        # Disable plant anywhere
        if getattr(self, 'plant_anywhere_active', False):
            self.toggle_plant_anywhere(False)

        # Disable move zombie row
        if getattr(self, 'move_zombie_row_active', False):
            self.toggle_move_zombie_row(False)

        # Disable plant changer
        if getattr(self, 'plant_changer_active', False):
            self.toggle_plant_changer(False)

        # Disable bullet changer
        if getattr(self, 'bullet_changer_active', False):
            self.toggle_bullet_changer(False)

        # Disable rapid fire
        if getattr(self, 'rapid_fire_active', False):
            self.toggle_rapid_fire(False)

        # Disable fast shoot
        if getattr(self, 'fast_shoot_active', False):
            self.toggle_fast_shoot(False)

        # Disable money changer
        if getattr(self, 'money_changer_active', False):
            self.toggle_money_changer(False)

        # Disable combat feature patches
        if getattr(self, 'instant_plant_death_active', False):
            self.toggle_instant_plant_death(False)
        if getattr(self, 'invincible_plants_active', False):
            self.toggle_invincible_plants(False)
        if getattr(self, 'invincible_zombies_active', False):
            self.toggle_invincible_zombies(False)
        if getattr(self, 'unhittable_plants_active', False):
            self.toggle_unhittable_plants_zombotany(False)

        # Disable new PVZ Toolkit features
        if getattr(self, 'no_fog_active', False):
            self.toggle_no_fog(False)
        if getattr(self, 'stop_spawning_active', False):
            self.toggle_stop_spawning(False)
        if getattr(self, 'stop_zombies_active', False):
            self.toggle_stop_zombies(False)
        if getattr(self, 'lock_butter_active', False):
            self.toggle_lock_butter(False)
        if getattr(self, 'mushrooms_awake_active', False):
            self.toggle_mushrooms_awake(False)
        if getattr(self, 'no_crater_active', False):
            self.toggle_no_crater(False)
        if getattr(self, 'see_vase_active', False):
            self.toggle_see_vase(False)

        # Disable new PVZTOOLKIT features
        if getattr(self, 'no_ice_trail_active', False):
            self.toggle_no_ice_trail(False)
        if getattr(self, 'zombie_not_explode_active', False):
            self.toggle_zombie_not_explode(False)
        if getattr(self, 'unlock_sun_limit_active', False):
            self.toggle_unlock_sun_limit(False)
        if getattr(self, 'fast_belt_active', False):
            self.toggle_fast_belt(False)
        if getattr(self, 'lock_shovel_active', False):
            self.toggle_lock_shovel(False)

        # Disable sun lock
        if getattr(self, 'sun_lock_active', False):
            self.toggle_sun_lock(False)

        # Restore sun apply patch (if installed)
        if self.sun_apply_patch_addr and self.original_sun_apply_bytes:
            try:
                self.pm.write_bytes(self.sun_apply_patch_addr, self.original_sun_apply_bytes, len(self.original_sun_apply_bytes))
                print(f"[SunSet] Restored bytes at {hex(self.sun_apply_patch_addr)}")
            except Exception as e:
                print(f"[SunSet] restore failed: {e}")
        if self.sun_apply_cave:
            try:
                self.pm.free(self.sun_apply_cave)
            except:
                pass
            self.sun_apply_cave = None
        self.sun_apply_patch_addr = None
        self.original_sun_apply_bytes = None
        self.sun_apply_imm_offset = None

        # Restore sun apply/add/cmp patches
        if self.sun_apply_patch_addr and self.original_sun_apply_bytes:
            try:
                self.pm.write_bytes(self.sun_apply_patch_addr, self.original_sun_apply_bytes, len(self.original_sun_apply_bytes))
                print(f"[SunSet] Restored bytes at {hex(self.sun_apply_patch_addr)}")
            except Exception as e:
                print(f"[SunSet] restore failed: {e}")
        if self.sun_apply_cave:
            try:
                self.pm.free(self.sun_apply_cave)
            except:
                pass
            self.sun_apply_cave = None
        self.sun_apply_patch_addr = None
        self.original_sun_apply_bytes = None
        self.sun_apply_imm_offset = None

        if self.sun_add_patch_addr and self.original_sun_add_bytes:
            try:
                self.pm.write_bytes(self.sun_add_patch_addr, self.original_sun_add_bytes, len(self.original_sun_add_bytes))
                print(f"[SunSet] Restored add-site bytes at {hex(self.sun_add_patch_addr)}")
            except Exception as e:
                print(f"[SunSet] add-site restore failed: {e}")
        if self.sun_add_cave:
            try:
                self.pm.free(self.sun_add_cave)
            except:
                pass
            self.sun_add_cave = None
        self.sun_add_patch_addr = None
        self.original_sun_add_bytes = None
        self.sun_add_imm_offset = None

        if self.sun_cmp_patch_addr and self.original_sun_cmp_bytes:
            try:
                self.pm.write_bytes(self.sun_cmp_patch_addr, self.original_sun_cmp_bytes, len(self.original_sun_cmp_bytes))
                print(f"[SunSet] Restored cmp-site bytes at {hex(self.sun_cmp_patch_addr)}")
            except Exception as e:
                print(f"[SunSet] cmp-site restore failed: {e}")
        if self.sun_cmp_cave:
            try:
                self.pm.free(self.sun_cmp_cave)
            except:
                pass
            self.sun_cmp_cave = None
        self.sun_cmp_patch_addr = None
        self.original_sun_cmp_bytes = None
        self.sun_cmp_imm_offset = None

        print("[ResetAll] All cheats disabled and original bytes restored.")
        return True


class TrainerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PVZ TRAINER PRO - supremopkv")
        self.root.geometry("540x820")
        self.root.resizable(False, False)

        # Gaming/Trainer Dark Theme Colors - Inspired by gaming aesthetics
        self.bg_color = "#0d0d0d"           # Deep black background
        self.bg_secondary = "#1a1a1a"        # Card background
        self.bg_tertiary = "#141414"         # Input fields
        self.bg_highlight = "#252525"        # Hover states
        self.fg_color = "#f0f0f0"            # Primary text
        self.fg_secondary = "#888888"        # Secondary text
        self.fg_disabled = "#444444"         # Disabled text

        # Neon accent colors for gaming feel
        self.accent_color = "#00ff88"        # Main accent - neon green
        self.accent_sun = "#ffcc00"          # Sun yellow/gold
        self.accent_plant = "#00ff44"        # Bright plant green
        self.accent_zombie = "#ff3333"       # Zombie red
        self.accent_purple = "#aa55ff"       # Purple for advanced
        self.accent_cyan = "#00ccff"         # Cyan for highlights
        self.warning_color = "#ff8800"       # Warning orange
        self.border_color = "#333333"        # Border color

        # Glow colors for active states
        self.glow_green = "#00ff88"
        self.glow_red = "#ff4444"
        self.glow_gold = "#ffcc00"

        self.root.configure(bg=self.bg_color)

        # Configure ttk styles for comboboxes with gaming look
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TCombobox',
            fieldbackground=self.bg_tertiary,
            background=self.bg_highlight,
            foreground=self.accent_cyan,
            arrowcolor=self.accent_color,
            bordercolor=self.accent_color,
            lightcolor=self.bg_secondary,
            darkcolor=self.bg_secondary,
            selectbackground=self.accent_color,
            selectforeground=self.bg_color,
            padding=5
        )
        self.style.map('TCombobox',
            fieldbackground=[('readonly', self.bg_tertiary), ('focus', self.bg_highlight)],
            selectbackground=[('readonly', self.accent_color)],
            selectforeground=[('readonly', self.bg_color)],
            bordercolor=[('focus', self.accent_color), ('active', self.accent_color)]
        )
        # Custom scrollbar style
        self.style.configure('Vertical.TScrollbar',
            background=self.bg_secondary,
            troughcolor=self.bg_tertiary,
            arrowcolor=self.accent_color
        )

        self.trainer = PvZTrainer()
        self.is_connected = False
        self.all_toggles = []  # Store all toggle checkbuttons
        self.current_page = "main"  # Track current page

        self.create_widgets()
        self.start_connection_checker()

    def create_section_frame(self, parent, title, accent_color, icon=""):
        """Create a styled section frame with title - Gaming trainer style"""
        # Outer container with padding
        outer = tk.Frame(parent, bg=self.bg_color)

        # Inner frame with neon border effect
        frame = tk.Frame(outer, bg=self.bg_secondary, highlightbackground=accent_color,
                        highlightthickness=1, padx=18, pady=14)
        frame.pack(fill="x", padx=3, pady=3)

        # Title bar with gaming style
        title_frame = tk.Frame(frame, bg=self.bg_secondary)
        title_frame.pack(anchor="w", fill="x", pady=(0, 12))

        # Left accent bar (gaming style indicator)
        accent_bar = tk.Frame(title_frame, bg=accent_color, width=4, height=20)
        accent_bar.pack(side="left", padx=(0, 10))
        accent_bar.pack_propagate(False)

        # Icon if provided
        if icon:
            icon_label = tk.Label(title_frame, text=icon, font=("Segoe UI", 12),
                                bg=self.bg_secondary, fg=accent_color)
            icon_label.pack(side="left", padx=(0, 8))

        # Title with uppercase gaming font style
        title_label = tk.Label(title_frame, text=title.upper(), font=("Segoe UI", 11, "bold"),
                              bg=self.bg_secondary, fg=accent_color)
        title_label.pack(side="left")

        # Decorative line after title
        line_frame = tk.Frame(title_frame, bg=self.bg_highlight, height=1)
        line_frame.pack(side="left", fill="x", expand=True, padx=(15, 0), pady=10)

        return frame, outer

    def create_toggle(self, parent, text, variable, command, accent_color):
        """Create a styled toggle checkbox - Gaming trainer style"""
        # Container for the toggle row with hover effect area
        row_frame = tk.Frame(parent, bg=self.bg_secondary)
        row_frame.pack(anchor="w", fill="x", pady=3)

        # Status indicator (small dot that glows when active)
        status_dot = tk.Label(row_frame, text="\u2022", font=("Segoe UI", 14),
                             bg=self.bg_secondary, fg=self.fg_disabled)
        status_dot.pack(side="left", padx=(0, 6))

        check = tk.Checkbutton(
            row_frame,
            text=text,
            variable=variable,
            command=lambda: self._on_toggle_click(check, status_dot, variable, command, accent_color),
            font=("Consolas", 10),  # Gaming/monospace font
            bg=self.bg_secondary,
            fg=self.fg_color,
            disabledforeground=self.fg_disabled,
            selectcolor=self.bg_tertiary,
            activebackground=self.bg_highlight,
            activeforeground=accent_color,
            highlightthickness=0,
            bd=0,
            padx=3,
            cursor="hand2",
            state="disabled"  # Start disabled
        )
        check.pack(side="left", anchor="w")

        # Store reference to status dot for updates
        check.status_dot = status_dot
        check.accent = accent_color

        self.all_toggles.append(check)
        return check

    def _on_toggle_click(self, check, status_dot, variable, command, accent_color):
        """Handle toggle click with visual feedback"""
        # Update status dot color based on state
        if variable.get():
            status_dot.config(fg=accent_color)
        else:
            status_dot.config(fg=self.fg_disabled)
        # Call original command
        command()

    def create_nav_button(self, parent, text, is_active, command):
        """Create a navigation button - Gaming tab style"""
        bg = self.accent_color if is_active else self.bg_tertiary
        fg = self.bg_color if is_active else self.fg_secondary

        btn = tk.Button(
            parent,
            text=text,
            font=("Consolas", 10, "bold"),
            bg=bg,
            fg=fg,
            activebackground=self.accent_color,
            activeforeground=self.bg_color,
            bd=0,
            padx=25,
            pady=10,
            cursor="hand2",
            command=command,
            relief="flat"
        )
        # Add hover effects
        def on_enter(e):
            if not is_active:
                btn.config(bg=self.bg_highlight)
        def on_leave(e):
            if not is_active:
                btn.config(bg=self.bg_tertiary)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    def show_main_page(self):
        """Switch to main trainer page"""
        if self.current_page == "main":
            return
        self.current_page = "main"
        self.credits_page.pack_forget()
        self.main_page.pack(fill="both", expand=True, padx=20, pady=5)
        self.update_nav_buttons()

    def show_credits_page(self):
        """Switch to credits page"""
        if self.current_page == "credits":
            return
        self.current_page = "credits"
        self.main_page.pack_forget()
        self.credits_page.pack(fill="both", expand=True, padx=20, pady=5)
        self.update_nav_buttons()

    def update_nav_buttons(self):
        """Update navigation button styles"""
        if self.current_page == "main":
            self.nav_main_btn.config(bg=self.accent_color, fg=self.bg_color)
            self.nav_credits_btn.config(bg=self.bg_tertiary, fg=self.fg_secondary)
        else:
            self.nav_main_btn.config(bg=self.bg_tertiary, fg=self.fg_secondary)
            self.nav_credits_btn.config(bg=self.accent_color, fg=self.bg_color)

    def create_widgets(self):
        # Header with gaming trainer style
        header_frame = tk.Frame(self.root, bg=self.bg_color)
        header_frame.pack(fill="x", pady=(12, 5))

        # Top accent line
        top_line = tk.Frame(header_frame, bg=self.accent_color, height=2)
        top_line.pack(fill="x", padx=20, pady=(0, 12))

        # Title container
        title_container = tk.Frame(header_frame, bg=self.bg_color)
        title_container.pack()

        # Main title with glow effect simulation
        title = tk.Label(
            title_container,
            text="PVZ TRAINER PRO",
            font=("Consolas", 28, "bold"),
            bg=self.bg_color,
            fg=self.accent_color
        )
        title.pack()

        # Version badge
        version_frame = tk.Frame(title_container, bg=self.accent_color, padx=8, pady=2)
        version_frame.pack(pady=(5, 0))
        version_label = tk.Label(
            version_frame,
            text="v3.0",
            font=("Consolas", 8, "bold"),
            bg=self.accent_color,
            fg=self.bg_color
        )
        version_label.pack()

        subtitle = tk.Label(
            header_frame,
            text="[ PLANTS VS. ZOMBIES MEMORY TRAINER ]",
            font=("Consolas", 9),
            bg=self.bg_color,
            fg=self.fg_secondary
        )
        subtitle.pack(pady=(8, 0))

        # Navigation bar with gaming style
        nav_frame = tk.Frame(self.root, bg=self.bg_color)
        nav_frame.pack(fill="x", padx=20, pady=(10, 8))

        # Left decorative bracket
        left_bracket = tk.Label(nav_frame, text="[", font=("Consolas", 14, "bold"),
                               bg=self.bg_color, fg=self.accent_color)
        left_bracket.pack(side="left", padx=(0, 5))

        self.nav_main_btn = self.create_nav_button(nav_frame, "CHEATS", True, self.show_main_page)
        self.nav_main_btn.pack(side="left", padx=(0, 5))

        self.nav_credits_btn = self.create_nav_button(nav_frame, "ABOUT", False, self.show_credits_page)
        self.nav_credits_btn.pack(side="left")

        # Right decorative bracket
        right_bracket = tk.Label(nav_frame, text="]", font=("Consolas", 14, "bold"),
                                bg=self.bg_color, fg=self.accent_color)
        right_bracket.pack(side="left", padx=(5, 0))

        # Warning banner (shown when game not detected) - Gaming style
        self.warning_frame = tk.Frame(self.root, bg="#1a0505", highlightbackground="#ff3333",
                                      highlightthickness=1, padx=15, pady=10)
        self.warning_frame.pack(fill="x", padx=20, pady=(0, 8))

        self.warning_icon = tk.Label(
            self.warning_frame,
            text="[!]",
            font=("Consolas", 12, "bold"),
            bg="#1a0505",
            fg="#ff3333"
        )
        self.warning_icon.pack(side="left", padx=(0, 12))

        self.warning_label = tk.Label(
            self.warning_frame,
            text="GAME NOT DETECTED - Launch Plants vs. Zombies to enable trainer",
            font=("Consolas", 9, "bold"),
            bg="#1a0505",
            fg="#ff6666",
            justify="left"
        )
        self.warning_label.pack(side="left")

        # Create scrollable main content area
        self.main_page = tk.Frame(self.root, bg=self.bg_color)
        self.main_page.pack(fill="both", expand=True, padx=20, pady=5)

        # Create canvas with scrollbar for main content - gaming style scrollbar
        self.canvas = tk.Canvas(self.main_page, bg=self.bg_color, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self.main_page, orient="vertical", command=self.canvas.yview,
                                      bg=self.bg_tertiary, troughcolor=self.bg_color,
                                      activebackground=self.accent_color, width=10)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.bg_color)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Make scrollable frame expand to canvas width
        def on_canvas_configure(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)

        self.canvas.bind("<Configure>", on_canvas_configure)

        # Bind mousewheel to scroll
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        self.canvas.bind_all("<MouseWheel>", on_mousewheel)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # SUN CHEATS SECTION
        sun_frame, sun_outer = self.create_section_frame(self.scrollable_frame, "SUN CHEATS", self.accent_sun, icon="\u2600")
        sun_outer.pack(fill="x", pady=4)

        self.sun_var = tk.BooleanVar()
        self.create_toggle(sun_frame, "Infinite Sun (9999)", self.sun_var,
                          self.toggle_sun, self.accent_sun)

        self.collect_var = tk.BooleanVar()
        self.create_toggle(sun_frame, "Collect +1000 Sun on Pickup", self.collect_var,
                          self.toggle_collect_sun, self.accent_sun)

        self.auto_collect_var = tk.BooleanVar()
        self.create_toggle(sun_frame, "Auto Collect Falling Suns", self.auto_collect_var,
                          self.toggle_auto_collect_ui, self.accent_sun)

        self.prevent_spend_var = tk.BooleanVar()
        self.create_toggle(sun_frame, "Free Planting (No Sun Cost)", self.prevent_spend_var,
                          self.toggle_prevent_spend_ui, self.accent_sun)

        self.plant_add_var = tk.BooleanVar()
        self.create_toggle(sun_frame, "Planting Gives +2000 Sun", self.plant_add_var,
                          self.toggle_plant_add_ui, self.accent_sun)

        # Sun Amount Setter - Gaming Style
        sun_set_frame = tk.Frame(sun_frame, bg=self.bg_secondary)
        sun_set_frame.pack(anchor="w", fill="x", pady=(4, 8), padx=(25, 10))
        tk.Label(sun_set_frame, text="Sun Amount >", font=("Consolas", 9),
                 bg=self.bg_secondary, fg=self.accent_sun).pack(side="left", padx=(0, 8))
        self.sun_amount_var = tk.StringVar(value="9999")
        self.sun_amount_entry = tk.Entry(
            sun_set_frame,
            textvariable=self.sun_amount_var,
            bg=self.bg_tertiary,
            fg=self.accent_cyan,
            insertbackground=self.accent_color,
            width=10,
            font=("Consolas", 10),
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.border_color,
            highlightcolor=self.accent_sun
        )
        self.sun_amount_entry.pack(side="left", pady=(2, 0))
        self.sun_amount_entry.bind("<Return>", self.on_sun_amount_apply)
        apply_btn = tk.Button(
            sun_set_frame,
            text="[SET]",
            command=self.on_sun_amount_apply,
            font=("Consolas", 9, "bold"),
            bg=self.accent_sun,
            fg="#000000",
            activebackground="#ffaa00",
            activeforeground="#000000",
            bd=0,
            padx=10,
            pady=3,
            cursor="hand2",
            relief="flat"
        )
        apply_btn.pack(side="left", padx=(10, 0), pady=(2, 0))

        # Lock Sun toggle (uses amount above)
        self.sun_lock_var = tk.BooleanVar()
        self.create_toggle(sun_frame, "Lock Sun to Amount", self.sun_lock_var,
                          self.toggle_sun_lock_ui, self.accent_sun)

        # PLANT CHEATS SECTION
        plant_frame, plant_outer = self.create_section_frame(self.scrollable_frame, "PLANT CHEATS", self.accent_plant, icon="\u2618")
        plant_outer.pack(fill="x", pady=4)

        self.cooldown_var = tk.BooleanVar()
        self.create_toggle(plant_frame, "No Cooldown (Instant Recharge)", self.cooldown_var,
                          self.toggle_cooldown, self.accent_plant)

        self.plant_anywhere_var = tk.BooleanVar()
        self.create_toggle(plant_frame, "Plant Anywhere (ignore placement checks)", self.plant_anywhere_var,
                  self.toggle_plant_anywhere_ui, self.accent_plant)

        # Plant Changer UI
        self.plant_changer_var = tk.BooleanVar()
        self.create_toggle(plant_frame, "Plant Changer", self.plant_changer_var,
              self.toggle_plant_changer_ui, self.accent_plant)

        # Instant Plant Death
        self.instant_plant_death_var = tk.BooleanVar()
        self.create_toggle(plant_frame, "Plants Die Instantly", self.instant_plant_death_var,
            self.toggle_instant_plant_death_ui, self.accent_plant)

        # Invincible Plants
        self.invincible_plants_var = tk.BooleanVar()
        self.create_toggle(plant_frame, "Invincible Plants", self.invincible_plants_var,
            self.toggle_invincible_plants_ui, self.accent_plant)

        # Plant selection dropdown
        pc_frame = tk.Frame(plant_frame, bg=self.bg_secondary)
        pc_frame.pack(anchor="w", fill="x", pady=(2, 6), padx=(25, 10))

        tk.Label(pc_frame, text="Replace with:", font=("Segoe UI", 9),
                bg=self.bg_secondary, fg=self.fg_secondary).pack(anchor="w")

        self.plant_changer_varval = tk.IntVar(value=0)
        self.plant_combo = ttk.Combobox(
            pc_frame,
            values=PLANT_NAMES,
            state="readonly",
            width=30,
            font=("Segoe UI", 9)
        )
        self.plant_combo.current(0)  # Default to Peashooter
        self.plant_combo.pack(anchor="w", pady=(2, 0))
        self.plant_combo.bind("<<ComboboxSelected>>", self.on_plant_combo_changed)

        # Bullet Changer UI
        self.bullet_changer_var = tk.BooleanVar()
        self.create_toggle(plant_frame, "Bullet Changer", self.bullet_changer_var,
              self.toggle_bullet_changer_ui, self.accent_plant)

        bc_frame = tk.Frame(plant_frame, bg=self.bg_secondary)
        bc_frame.pack(anchor="w", fill="x", pady=(2, 6), padx=(25, 10))

        tk.Label(bc_frame, text="Bullet type (0-12):", font=("Segoe UI", 9),
            bg=self.bg_secondary, fg=self.fg_secondary).pack(anchor="w")

        self.bullet_changer_varval = tk.IntVar(value=0)
        self.bullet_combo = ttk.Combobox(
            bc_frame,
            values=[f"{i} - Bullet {i}" for i in range(13)],
            state="readonly",
            width=20,
            font=("Segoe UI", 9)
        )
        self.bullet_combo.current(0)
        self.bullet_combo.pack(anchor="w", pady=(2, 0))
        self.bullet_combo.bind("<<ComboboxSelected>>", self.on_bullet_combo_changed)

        # Rapid Fire UI
        self.rapid_fire_var = tk.BooleanVar()
        self.create_toggle(plant_frame, "Rapid Fire (bypass check)", self.rapid_fire_var,
                self.toggle_rapid_fire_ui, self.accent_plant)

        # Fast Shoot UI
        self.fast_shoot_var = tk.BooleanVar()
        self.create_toggle(plant_frame, "Shoot Faster (lower delay)", self.fast_shoot_var,
                self.toggle_fast_shoot_ui, self.accent_plant)

        fs_frame = tk.Frame(plant_frame, bg=self.bg_secondary)
        fs_frame.pack(anchor="w", fill="x", pady=(2, 6), padx=(25, 10))
        tk.Label(fs_frame, text="Delay ticks (0-20):", font=("Segoe UI", 9),
            bg=self.bg_secondary, fg=self.fg_secondary).pack(anchor="w")
        self.fast_shoot_varval = tk.IntVar(value=2)
        self.fast_shoot_combo = ttk.Combobox(
            fs_frame,
            values=[str(i) for i in range(0, 21)],
            state="readonly",
            width=8,
            font=("Segoe UI", 9)
        )
        self.fast_shoot_combo.current(2)
        self.fast_shoot_combo.pack(anchor="w", pady=(2, 0))
        self.fast_shoot_combo.bind("<<ComboboxSelected>>", self.on_fast_shoot_combo_changed)

        # Money Changer UI
        self.money_changer_var = tk.BooleanVar()
        self.create_toggle(plant_frame, "Money Changer", self.money_changer_var,
                self.toggle_money_changer_ui, self.accent_plant)

        money_frame = tk.Frame(plant_frame, bg=self.bg_secondary)
        money_frame.pack(anchor="w", fill="x", pady=(4, 8), padx=(25, 10))
        tk.Label(money_frame, text="Money Amount >", font=("Consolas", 9),
            bg=self.bg_secondary, fg=self.accent_sun).pack(side="left", padx=(0, 8))
        self.money_amount_var = tk.StringVar(value="99999")
        self.money_entry = tk.Entry(money_frame, textvariable=self.money_amount_var,
            bg=self.bg_tertiary, fg=self.accent_cyan, insertbackground=self.accent_color,
            font=("Consolas", 10), relief="flat", width=12,
            highlightthickness=1, highlightbackground=self.border_color, highlightcolor=self.accent_sun)
        self.money_entry.pack(side="left", pady=(2, 0))
        self.money_entry.bind("<FocusOut>", self.on_money_amount_changed)

        # ZomBotany Unhittable Plants
        self.zombotany_unhittable_var = tk.BooleanVar()
        self.create_toggle(plant_frame, "ZomBotany: Unhittable Plants", self.zombotany_unhittable_var,
            self.toggle_zombotany_unhittable_ui, self.accent_plant)

        # ZOMBIE CHEATS SECTION
        zombie_frame, zombie_outer = self.create_section_frame(self.scrollable_frame, "ZOMBIE CHEATS", self.accent_zombie, icon="\u2620")
        zombie_outer.pack(fill="x", pady=4)

        self.kill_var = tk.BooleanVar()
        self.create_toggle(zombie_frame, "One Hit Kill (Instant Death)", self.kill_var,
                          self.toggle_kill, self.accent_zombie)

        # Invincible Zombies
        self.invincible_zombies_var = tk.BooleanVar()
        self.create_toggle(zombie_frame, "Invincible Zombies", self.invincible_zombies_var,
                  self.toggle_invincible_zombies_ui, self.accent_zombie)

        # Stop Zombies (Freeze)
        self.stop_zombies_var = tk.BooleanVar()
        self.create_toggle(zombie_frame, "Freeze Zombies (Stop Movement)", self.stop_zombies_var,
                  self.toggle_stop_zombies_ui, self.accent_zombie)

        # Stop Spawning
        self.stop_spawning_var = tk.BooleanVar()
        self.create_toggle(zombie_frame, "Stop Zombie Spawning", self.stop_spawning_var,
                  self.toggle_stop_spawning_ui, self.accent_zombie)

        self.show_zombies_var = tk.BooleanVar()
        self.create_toggle(zombie_frame, "Show All Zombies (Preview)", self.show_zombies_var,
                          self.toggle_show_zombies, self.accent_zombie)

        # Spawn All Zombies Now Button
        spawn_now_frame = tk.Frame(zombie_frame, bg=self.bg_secondary)
        spawn_now_frame.pack(anchor="w", fill="x", pady=(2, 4))
        
        self.spawn_now_btn = tk.Button(
            spawn_now_frame,
            text="[ SPAWN ALL ZOMBIES ]",
            font=("Consolas", 9, "bold"),
            bg=self.accent_purple,
            fg="#ffffff",
            activebackground="#9933ff",
            activeforeground="#ffffff",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.spawn_all_now_ui,
            relief="flat"
        )
        self.spawn_now_btn.pack(side="left", padx=20)

        # Kill All Zombies Button
        kill_all_frame = tk.Frame(zombie_frame, bg=self.bg_secondary)
        kill_all_frame.pack(anchor="w", fill="x", pady=(6, 4))

        self.kill_all_btn = tk.Button(
            kill_all_frame,
            text="[ KILL ALL ZOMBIES ]",
            font=("Consolas", 9, "bold"),
            bg=self.accent_zombie,
            fg="#ffffff",
            activebackground="#cc0000",
            activeforeground="#ffffff",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.kill_all_zombies_ui,
            state="disabled",
            relief="flat"
        )
        self.kill_all_btn.pack(side="left", padx=5)

        # Move Zombie Row controls
        self.move_zombie_var = tk.BooleanVar()
        self.create_toggle(zombie_frame, "Force Zombie Row", self.move_zombie_var,
                  self.toggle_move_zombie_ui, self.accent_zombie)

        # Row selection dropdown
        row_frame = tk.Frame(zombie_frame, bg=self.bg_secondary)
        row_frame.pack(anchor="w", fill="x", pady=(2, 6), padx=(25, 10))

        tk.Label(row_frame, text="Spawn zombies in:", font=("Segoe UI", 9),
                bg=self.bg_secondary, fg=self.fg_secondary).pack(anchor="w")

        self.zombie_row_var = tk.IntVar(value=0)
        self.row_combo = ttk.Combobox(
            row_frame,
            values=ROW_NAMES,
            state="readonly",
            width=20,
            font=("Segoe UI", 9)
        )
        self.row_combo.current(0)  # Default to Row 1
        self.row_combo.pack(anchor="w", pady=(2, 0))
        self.row_combo.bind("<<ComboboxSelected>>", self.on_row_combo_changed)

        # GAME SECTION
        game_frame, game_outer = self.create_section_frame(self.scrollable_frame, "GAME OPTIONS", self.accent_cyan, icon="\u2699")
        game_outer.pack(fill="x", pady=4)

        self.background_var = tk.BooleanVar()
        self.create_toggle(game_frame, "Run in Background (no pause on alt-tab)", self.background_var,
                          self.toggle_run_in_background_ui, self.accent_color)

        # No Fog
        self.no_fog_var = tk.BooleanVar()
        self.create_toggle(game_frame, "Remove Fog (Night/Fog Levels)", self.no_fog_var,
                          self.toggle_no_fog_ui, self.accent_color)

        # See Vase (Vasebreaker)
        self.see_vase_var = tk.BooleanVar()
        self.create_toggle(game_frame, "See Vase Contents (Vasebreaker)", self.see_vase_var,
                          self.toggle_see_vase_ui, self.accent_color)

        # Game Speed Control
        speed_frame = tk.Frame(game_frame, bg=self.bg_secondary)
        speed_frame.pack(anchor="w", fill="x", pady=(6, 4), padx=(5, 10))
        
        tk.Label(speed_frame, text="⚡ Game Speed:", font=("Segoe UI", 9, "bold"),
                bg=self.bg_secondary, fg=self.accent_color).pack(side="left")
        
        self.speed_var = tk.StringVar(value="10")
        self.speed_combo = ttk.Combobox(
            speed_frame,
            values=["1 (10x Fast)", "2 (5x Fast)", "5 (2x Fast)", "10 (Normal)", "20 (0.5x Slow)", "50 (0.2x Slow)"],
            state="readonly",
            width=14,
            font=("Segoe UI", 9)
        )
        self.speed_combo.current(3)  # Default to Normal
        self.speed_combo.pack(side="left", padx=(8, 0))
        self.speed_combo.bind("<<ComboboxSelected>>", self.on_speed_combo_changed)

        # ADVANCED CHEATS SECTION
        adv_frame, adv_outer = self.create_section_frame(self.scrollable_frame, "ADVANCED CHEATS", self.accent_purple, icon="\u269B")
        adv_outer.pack(fill="x", pady=4)

        # Mushrooms Awake
        self.mushrooms_awake_var = tk.BooleanVar()
        self.create_toggle(adv_frame, "Mushrooms Stay Awake (Day)", self.mushrooms_awake_var,
                          self.toggle_mushrooms_awake_ui, "#a855f7")

        # Lock Butter
        self.lock_butter_var = tk.BooleanVar()
        self.create_toggle(adv_frame, "Lock Butter (Kernel-pult)", self.lock_butter_var,
                          self.toggle_lock_butter_ui, "#a855f7")

        # No Crater
        self.no_crater_var = tk.BooleanVar()
        self.create_toggle(adv_frame, "No Crater (Doom-shroom)", self.no_crater_var,
                          self.toggle_no_crater_ui, "#a855f7")

        # ===== NEW PVZTOOLKIT FEATURES =====
        # No Ice Trail
        self.no_ice_trail_var = tk.BooleanVar()
        self.create_toggle(adv_frame, "No Ice Trail (Zomboni)", self.no_ice_trail_var,
                          self.toggle_no_ice_trail_ui, "#a855f7")

        # Zombie Not Explode
        self.zombie_not_explode_var = tk.BooleanVar()
        self.create_toggle(adv_frame, "No Explosion (Jack-in-Box)", self.zombie_not_explode_var,
                          self.toggle_zombie_not_explode_ui, "#a855f7")

        # Unlock Sun Limit
        self.unlock_sun_limit_var = tk.BooleanVar()
        self.create_toggle(adv_frame, "Unlock Sun Limit (No 9990 Cap)", self.unlock_sun_limit_var,
                          self.toggle_unlock_sun_limit_ui, "#a855f7")

        # Fast Belt
        self.fast_belt_var = tk.BooleanVar()
        self.create_toggle(adv_frame, "Fast Conveyor Belt", self.fast_belt_var,
                          self.toggle_fast_belt_ui, "#a855f7")

        # Lock Shovel
        self.lock_shovel_var = tk.BooleanVar()
        self.create_toggle(adv_frame, "Lock Shovel (Keep Selected)", self.lock_shovel_var,
                          self.toggle_lock_shovel_ui, "#a855f7")

        # Action Buttons Frame
        new_action_frame = tk.Frame(adv_frame, bg=self.bg_secondary)
        new_action_frame.pack(anchor="w", fill="x", pady=(6, 4))

        # Restore Lawn Mowers Button
        self.restore_mowers_btn = tk.Button(
            new_action_frame,
            text="[ RESTORE MOWERS ]",
            font=("Consolas", 9, "bold"),
            bg=self.accent_plant,
            fg="#000000",
            activebackground="#00cc33",
            activeforeground="#000000",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.restore_mowers_ui,
            state="disabled",
            relief="flat"
        )
        self.restore_mowers_btn.pack(side="left", padx=5)

        # Instant Win Button
        self.instant_win_btn = tk.Button(
            new_action_frame,
            text="[ INSTANT WIN ]",
            font=("Consolas", 9, "bold"),
            bg=self.accent_sun,
            fg="#000000",
            activebackground="#ffaa00",
            activeforeground="#000000",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.instant_win_ui,
            state="disabled",
            relief="flat"
        )
        self.instant_win_btn.pack(side="left", padx=5)

        # Clear All Plants Button
        action_frame = tk.Frame(adv_frame, bg=self.bg_secondary)
        action_frame.pack(anchor="w", fill="x", pady=(6, 4))

        self.clear_plants_btn = tk.Button(
            action_frame,
            text="[ CLEAR ALL PLANTS ]",
            font=("Consolas", 9, "bold"),
            bg=self.warning_color,
            fg="#000000",
            activebackground="#ff6600",
            activeforeground="#000000",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.clear_all_plants_ui,
            state="disabled",
            relief="flat"
        )
        self.clear_plants_btn.pack(side="left", padx=5)

        # Reset All Button
        reset_frame = tk.Frame(game_frame, bg=self.bg_secondary)
        reset_frame.pack(anchor="w", fill="x", pady=(12, 4))

        self.reset_btn = tk.Button(
            reset_frame,
            text="[ RESET ALL CHEATS ]",
            font=("Consolas", 10, "bold"),
            bg=self.accent_zombie,
            fg="#ffffff",
            activebackground="#cc0000",
            activeforeground="#ffffff",
            bd=0,
            padx=16,
            pady=8,
            cursor="hand2",
            command=self.reset_all_ui,
            state="disabled",
            relief="flat"
        )
        self.reset_btn.pack(side="left", padx=5)

        reset_label = tk.Label(
            reset_frame,
            text="Disable all cheats & restore game",
            font=("Consolas", 9),
            bg=self.bg_secondary,
            fg=self.fg_secondary
        )
        reset_label.pack(side="left", padx=10)

        # CREDITS PAGE (hidden by default)
        self.credits_page = tk.Frame(self.root, bg=self.bg_color)
        self.create_credits_page()

        # STATUS BAR - Gaming style footer
        status_frame = tk.Frame(self.root, bg=self.bg_tertiary, height=55)
        status_frame.pack(fill="x", side="bottom")
        status_frame.pack_propagate(False)

        # Bottom accent line
        bottom_line = tk.Frame(status_frame, bg=self.accent_color, height=2)
        bottom_line.pack(fill="x", side="top")

        # Status container
        status_container = tk.Frame(status_frame, bg=self.bg_tertiary)
        status_container.pack(fill="both", expand=True)

        # Left bracket
        left_status = tk.Label(status_container, text="[", font=("Consolas", 16, "bold"),
                              bg=self.bg_tertiary, fg=self.accent_color)
        left_status.pack(side="left", padx=(20, 5), pady=10)

        # Connection indicator dot with pulsing effect
        self.connection_dot = tk.Label(
            status_container,
            text="\u25CF",
            font=("Consolas", 14),
            bg=self.bg_tertiary,
            fg="#ff3333"
        )
        self.connection_dot.pack(side="left", padx=(0, 8), pady=10)

        self.status_label = tk.Label(
            status_container,
            text="OFFLINE :: START GAME",
            font=("Consolas", 10, "bold"),
            bg=self.bg_tertiary,
            fg="#ff3333"
        )
        self.status_label.pack(side="left", pady=10)

        # Right bracket
        right_status = tk.Label(status_container, text="]", font=("Consolas", 16, "bold"),
                               bg=self.bg_tertiary, fg=self.accent_color)
        right_status.pack(side="left", padx=(5, 0), pady=10)

        # Author credit on right side
        author_label = tk.Label(status_container, text="by supremopkv", font=("Consolas", 9),
                               bg=self.bg_tertiary, fg=self.fg_secondary)
        author_label.pack(side="right", padx=(0, 20), pady=10)

        # Try to auto-connect if game is already running
        self.root.after(100, self.try_auto_connect)

    def try_auto_connect(self):
        """Try to connect to game automatically at startup"""
        if self.trainer.check_game_running():
            if self.trainer.attach_process():
                self.is_connected = True
                self.on_connected()

    def on_row_combo_changed(self, event=None):
        """Called when the row combobox selection changes; update trainer immediately."""
        try:
            # Get selected index from combobox
            row = self.row_combo.current()
            self.zombie_row_var.set(row)
            # Update trainer value
            self.trainer.set_move_zombie_row_value(row)
            if self.trainer.move_zombie_row_active:
                self.update_status(f"Force Zombie Row: {ROW_NAMES[row]}", True)
        except Exception:
            pass

    def create_credits_page(self):
        """Create the credits page content - Gaming style"""
        # Center container
        center_frame = tk.Frame(self.credits_page, bg=self.bg_color)
        center_frame.pack(expand=True, fill="both")

        # Credits card with border
        card = tk.Frame(center_frame, bg=self.bg_secondary, padx=50, pady=45,
                       highlightbackground=self.accent_color, highlightthickness=1)
        card.place(relx=0.5, rely=0.4, anchor="center")

        # Title with brackets
        title = tk.Label(
            card,
            text="[ ABOUT ]",
            font=("Consolas", 22, "bold"),
            bg=self.bg_secondary,
            fg=self.accent_color
        )
        title.pack(pady=(0, 20))

        # Decorative line
        divider = tk.Frame(card, bg=self.accent_color, height=2, width=180)
        divider.pack(pady=(0, 25))

        # Developer section
        dev_label = tk.Label(
            card,
            text=":: DEVELOPER ::",
            font=("Consolas", 10),
            bg=self.bg_secondary,
            fg=self.fg_secondary
        )
        dev_label.pack()

        dev_name = tk.Label(
            card,
            text="supremopkv",
            font=("Consolas", 26, "bold"),
            bg=self.bg_secondary,
            fg=self.accent_sun
        )
        dev_name.pack(pady=(8, 20))

        # Version badge
        version_frame = tk.Frame(card, bg=self.accent_color, padx=15, pady=4)
        version_frame.pack(pady=(0, 15))
        version_label = tk.Label(
            version_frame,
            text="VERSION 3.0",
            font=("Consolas", 10, "bold"),
            bg=self.accent_color,
            fg=self.bg_color
        )
        version_label.pack()

        game_label = tk.Label(
            card,
            text="Plants vs. Zombies Trainer",
            font=("Consolas", 10),
            bg=self.bg_secondary,
            fg=self.fg_color
        )
        game_label.pack()

        game_label2 = tk.Label(
            card,
            text="[ GOTY Edition Supported ]",
            font=("Consolas", 9),
            bg=self.bg_secondary,
            fg=self.fg_secondary
        )
        game_label2.pack(pady=(5, 0))

        # Divider
        divider2 = tk.Frame(card, bg=self.border_color, height=1, width=220)
        divider2.pack(pady=25)

        # Tech stack
        tech_label = tk.Label(
            card,
            text="Built with Python + Tkinter",
            font=("Consolas", 9),
            bg=self.bg_secondary,
            fg=self.fg_secondary
        )
        tech_label.pack()

        # Thanks message with accent
        thanks = tk.Label(
            card,
            text="> THANKS FOR USING <",
            font=("Consolas", 11, "bold"),
            bg=self.bg_secondary,
            fg=self.accent_color
        )
        thanks.pack(pady=(15, 0))

        # Fun gaming message
        gaming_msg = tk.Label(
            card,
            text="Happy Gaming!",
            font=("Consolas", 9),
            bg=self.bg_secondary,
            fg=self.accent_plant
        )
        gaming_msg.pack(pady=(8, 0))

    def start_connection_checker(self):
        """Start a background thread to check game connection"""
        def check_connection():
            while True:
                game_running = self.trainer.check_game_running()

                # Update UI from main thread
                self.root.after(0, lambda: self.update_connection_status(game_running))

                time.sleep(2)  # Check every 2 seconds

        thread = threading.Thread(target=check_connection, daemon=True)
        thread.start()

    def update_connection_status(self, is_running):
        """Update UI based on game connection status"""
        if is_running and not self.is_connected:
            # Game just started - try to connect
            if self.trainer.attach_process():
                self.is_connected = True
                self.on_connected()
        elif not is_running and self.is_connected:
            # Game closed
            self.is_connected = False
            self.trainer.is_connected = False
            self.trainer.pm = None
            self.on_disconnected()
        elif not is_running and not self.is_connected:
            # Still not running
            pass

    def manual_connect(self):
        """Manual connect button handler - attempts to attach and shows message on failure"""
        if self.trainer.attach_process():
            self.is_connected = True
            self.on_connected()
            messagebox.showinfo("Connected", "Attached to game successfully.")
        else:
            messagebox.showwarning("Connect Failed", "Could not attach to process. Check that the game is running and you have permissions.")

    def on_connected(self):
        """Called when game is connected"""
        # If widgets haven't been created yet, skip
        if not hasattr(self, 'status_label'):
            return

        # Hide warning with smooth transition
        try:
            self.warning_frame.pack_forget()
        except:
            pass

        # Enable all toggles
        for toggle in self.all_toggles:
            try:
                toggle.config(state="normal", cursor="hand2")
            except:
                pass

        # Enable reset button
        try:
            self.reset_btn.config(state="normal")
        except:
            pass

        # Enable action buttons
        for btn_name in ('kill_all_btn', 'clear_plants_btn', 'spawn_now_btn', 'restore_mowers_btn', 'instant_win_btn'):
            try:
                getattr(self, btn_name).config(state="normal")
            except:
                pass

        # Update status with gaming style
        try:
            self.status_label.config(
                text="ONLINE :: TRAINER READY",
                fg=self.accent_color,
                bg=self.bg_tertiary
            )
            self.connection_dot.config(fg=self.accent_color, bg=self.bg_tertiary)
        except:
            pass

    def on_disconnected(self):
        """Called when game is disconnected"""
        # If widgets haven't been created yet, skip
        if not hasattr(self, 'status_label'):
            return

        # Show warning - place it after the nav frame
        try:
            self.warning_frame.pack(fill="x", padx=20, pady=(0, 8), after=self.root.winfo_children()[1])
        except:
            pass

        # Disable all toggles and reset their state
        for toggle in self.all_toggles:
            try:
                toggle.config(state="disabled")
            except:
                pass

        # Disable reset button
        try:
            self.reset_btn.config(state="disabled")
        except:
            pass

        # Disable action buttons
        for btn_name in ('kill_all_btn', 'clear_plants_btn', 'spawn_now_btn', 'restore_mowers_btn', 'instant_win_btn'):
            try:
                getattr(self, btn_name).config(state="disabled")
            except:
                pass

        # Reset all variables (guard each in case not created)
        for var_name in ('sun_var','collect_var','prevent_spend_var','plant_add_var','auto_collect_var','sun_lock_var',
                         'cooldown_var','kill_var','show_zombies_var','background_var','plant_anywhere_var',
                         'move_zombie_var','plant_changer_var','bullet_changer_var','rapid_fire_var','fast_shoot_var',
                         'instant_plant_death_var','invincible_plants_var','invincible_zombies_var',
                         'zombotany_unhittable_var','stop_zombies_var','stop_spawning_var',
                         'no_fog_var','see_vase_var','mushrooms_awake_var','lock_butter_var','no_crater_var',
                         'no_ice_trail_var','zombie_not_explode_var','unlock_sun_limit_var','fast_belt_var','lock_shovel_var'):
            try:
                getattr(self, var_name).set(False)
            except:
                pass

        # Update status
        try:
            self.status_label.config(
                text="DISCONNECTED - Start the game",
                fg="#ef4444",
                bg=self.bg_tertiary
            )
            self.connection_dot.config(fg="#ef4444", bg=self.bg_tertiary)
        except:
            pass

    def toggle_sun(self):
        state = self.sun_var.get()
        if self.trainer.toggle_infinite_sun(state):
            self.update_status("Infinite Sun", state)

    def toggle_cooldown(self):
        state = self.cooldown_var.get()
        if self.trainer.toggle_no_cooldown(state):
            self.update_status("No Cooldown", state)

    def toggle_kill(self):
        state = self.kill_var.get()
        if self.trainer.toggle_one_hit_kill(state):
            self.update_status("One Hit Kill", state)

    def toggle_collect_sun(self):
        state = self.collect_var.get()
        if self.trainer.toggle_collect_1000_sun(state):
            self.update_status("Collect +1000 Sun", state)

    def toggle_auto_collect_ui(self):
        state = self.auto_collect_var.get()
        if self.trainer.toggle_auto_collect(state):
            self.update_status("Auto Collect Suns", state)

    def toggle_prevent_spend_ui(self):
        state = self.prevent_spend_var.get()
        if self.trainer.toggle_prevent_spend(state):
            self.update_status("Free Planting", state)

    def toggle_plant_add_ui(self):
        state = self.plant_add_var.get()
        if self.trainer.toggle_planting_adds_sun(state):
            self.update_status("Planting Adds Sun", state)

    def toggle_show_zombies(self):
        state = self.show_zombies_var.get()
        if self.trainer.toggle_show_all_zombies(state):
            self.update_status("Show All Zombies (Preview)", state)

    def spawn_all_now_ui(self):
        """Handler for Spawn All Zombies Now button"""
        if self.trainer.spawn_all_zombies_now():
            messagebox.showinfo("Success", "Spawned all zombie types on the lawn!")
        else:
            messagebox.showerror("Error", "Failed to spawn zombies. Make sure you are in a level.")

    def toggle_move_zombie_ui(self):
        state = self.move_zombie_var.get()
        # Get row from combobox
        row = self.row_combo.current()
        self.zombie_row_var.set(row)
        self.trainer.set_move_zombie_row_value(row)
        if self.trainer.toggle_move_zombie_row(state):
            if state:
                self.update_status(f"Force: {ROW_NAMES[row]}", True)
            else:
                self.update_status("Force Zombie Row", False)

    def toggle_run_in_background_ui(self):
        state = self.background_var.get()
        if self.trainer.toggle_run_in_background(state):
            self.update_status("Run in Background", state)

    def toggle_plant_anywhere_ui(self):
        state = self.plant_anywhere_var.get()
        if self.trainer.toggle_plant_anywhere(state):
            self.update_status("Plant Anywhere", state)

    def toggle_plant_changer_ui(self):
        state = self.plant_changer_var.get()
        # Get plant ID from combobox
        plant_id = self.plant_combo.current()
        self.plant_changer_varval.set(plant_id)
        self.trainer.set_plant_changer_value(plant_id)
        if self.trainer.toggle_plant_changer(state):
            if state:
                self.update_status(f"Plant: {PLANT_NAMES[plant_id]}", True)
            else:
                self.update_status("Plant Changer", False)

    def toggle_bullet_changer_ui(self):
        state = self.bullet_changer_var.get()
        bullet_id = self.bullet_combo.current()
        self.bullet_changer_varval.set(bullet_id)
        self.trainer.set_bullet_changer_value(bullet_id)
        if self.trainer.toggle_bullet_changer(state):
            if state:
                self.update_status(f"Bullet Type: {bullet_id}", True)
            else:
                self.update_status("Bullet Changer", False)

    def toggle_rapid_fire_ui(self):
        state = self.rapid_fire_var.get()
        if self.trainer.toggle_rapid_fire(state):
            self.update_status("Rapid Fire", state)

    def toggle_fast_shoot_ui(self):
        state = self.fast_shoot_var.get()
        delay = int(self.fast_shoot_combo.get()) if hasattr(self, 'fast_shoot_combo') else 2
        self.fast_shoot_varval.set(delay)
        self.trainer.set_fast_shoot_delay(delay)
        if self.trainer.toggle_fast_shoot(state):
            if state:
                self.update_status(f"Shoot Delay: {delay}", True)
            else:
                self.update_status("Shoot Faster", False)

    def toggle_money_changer_ui(self):
        state = self.money_changer_var.get()
        # Parse amount from entry
        try:
            amt = int(self.money_amount_var.get())
        except:
            amt = 99999
            self.money_amount_var.set(str(amt))
        self.trainer.set_money_amount(amt)
        if self.trainer.toggle_money_changer(state):
            if state:
                self.update_status(f"Money: {amt}", True)
            else:
                self.update_status("Money Changer", False)

    def on_plant_combo_changed(self, event=None):
        """Called when the plant combobox selection changes; update trainer immediately."""
        try:
            # Get selected index from combobox (index = plant ID)
            plant_id = self.plant_combo.current()
            self.plant_changer_varval.set(plant_id)
            # Update trainer value
            self.trainer.set_plant_changer_value(plant_id)
            if self.trainer.plant_changer_active:
                self.update_status(f"Plant: {PLANT_NAMES[plant_id]}", True)
        except Exception:
            pass

    def on_bullet_combo_changed(self, event=None):
        """Update bullet value immediately when selection changes."""
        try:
            bullet_id = self.bullet_combo.current()
            self.bullet_changer_varval.set(bullet_id)
            self.trainer.set_bullet_changer_value(bullet_id)
            if self.trainer.bullet_changer_active:
                self.update_status(f"Bullet Type: {bullet_id}", True)
        except Exception:
            pass

    def on_fast_shoot_combo_changed(self, event=None):
        try:
            delay = int(self.fast_shoot_combo.get())
            self.fast_shoot_varval.set(delay)
            self.trainer.set_fast_shoot_delay(delay)
            if self.trainer.fast_shoot_active:
                self.update_status(f"Shoot Delay: {delay}", True)
        except Exception:
            pass

    def on_money_amount_changed(self, event=None):
        try:
            amt = int(self.money_amount_var.get())
            self.trainer.set_money_amount(amt)
            if self.trainer.money_changer_active:
                self.update_status(f"Money: {amt}", True)
        except Exception:
            pass

    def on_sun_amount_apply(self, event=None):
        try:
            amt = int(self.sun_amount_var.get())
        except Exception:
            amt = 9999
            self.sun_amount_var.set(str(amt))
        # Update lock amount first so continuous writer uses it
        self.trainer.set_sun_lock_amount(amt)
        ok = self.trainer.set_sun_amount(amt)
        if ok:
            self.update_status(f"Sun: {amt}", True)
        else:
            messagebox.showerror("Error", "Failed to set sun amount.")

    def toggle_sun_lock_ui(self):
        state = self.sun_lock_var.get()
        try:
            amt = int(self.sun_amount_var.get())
        except Exception:
            amt = 9999
            self.sun_amount_var.set(str(amt))
        self.trainer.set_sun_lock_amount(amt)
        if self.trainer.toggle_sun_lock(state):
            if state:
                self.update_status(f"Sun Locked: {amt}", True)
            else:
                self.update_status("Sun Locked", False)

    def toggle_instant_plant_death_ui(self):
        state = self.instant_plant_death_var.get()
        if self.trainer.toggle_instant_plant_death(state):
            self.update_status("Plants Die Instantly", state)

    def toggle_invincible_plants_ui(self):
        state = self.invincible_plants_var.get()
        if self.trainer.toggle_invincible_plants(state):
            self.update_status("Invincible Plants", state)

    def toggle_invincible_zombies_ui(self):
        state = self.invincible_zombies_var.get()
        if self.trainer.toggle_invincible_zombies(state):
            self.update_status("Invincible Zombies", state)

    def toggle_zombotany_unhittable_ui(self):
        state = self.zombotany_unhittable_var.get()
        if self.trainer.toggle_unhittable_plants_zombotany(state):
            self.update_status("ZomBotany Unhittable Plants", state)

    def toggle_stop_zombies_ui(self):
        state = self.stop_zombies_var.get()
        if self.trainer.toggle_stop_zombies(state):
            self.update_status("Stop Zombies", state)

    def toggle_stop_spawning_ui(self):
        state = self.stop_spawning_var.get()
        if self.trainer.toggle_stop_spawning(state):
            self.update_status("Stop Spawning", state)

    def toggle_no_fog_ui(self):
        state = self.no_fog_var.get()
        if self.trainer.toggle_no_fog(state):
            self.update_status("No Fog", state)

    def toggle_see_vase_ui(self):
        state = self.see_vase_var.get()
        if self.trainer.toggle_see_vase(state):
            self.update_status("See Vase", state)

    def toggle_mushrooms_awake_ui(self):
        state = self.mushrooms_awake_var.get()
        if self.trainer.toggle_mushrooms_awake(state):
            self.update_status("Mushrooms Awake", state)

    def toggle_lock_butter_ui(self):
        state = self.lock_butter_var.get()
        if self.trainer.toggle_lock_butter(state):
            self.update_status("Lock Butter", state)

    def toggle_no_crater_ui(self):
        state = self.no_crater_var.get()
        if self.trainer.toggle_no_crater(state):
            self.update_status("No Crater", state)

    # ===== NEW PVZTOOLKIT UI HANDLERS =====
    def toggle_no_ice_trail_ui(self):
        state = self.no_ice_trail_var.get()
        if self.trainer.toggle_no_ice_trail(state):
            self.update_status("No Ice Trail", state)

    def toggle_zombie_not_explode_ui(self):
        state = self.zombie_not_explode_var.get()
        if self.trainer.toggle_zombie_not_explode(state):
            self.update_status("Zombie Not Explode", state)

    def toggle_unlock_sun_limit_ui(self):
        state = self.unlock_sun_limit_var.get()
        if self.trainer.toggle_unlock_sun_limit(state):
            self.update_status("Unlock Sun Limit", state)

    def toggle_fast_belt_ui(self):
        state = self.fast_belt_var.get()
        if self.trainer.toggle_fast_belt(state):
            self.update_status("Fast Belt", state)

    def toggle_lock_shovel_ui(self):
        state = self.lock_shovel_var.get()
        if self.trainer.toggle_lock_shovel(state):
            self.update_status("Lock Shovel", state)

    def restore_mowers_ui(self):
        count = self.trainer.restore_lawn_mowers()
        if count and count > 0:
            self.update_status(f"Restored {count} Lawn Mowers", True)
        else:
            messagebox.showerror("Error", "Failed to restore lawn mowers")

    def instant_win_ui(self):
        if self.trainer.instant_win():
            self.update_status("Instant Win!", True)
        else:
            messagebox.showerror("Error", "Failed to trigger instant win")

    def on_speed_combo_changed(self, event=None):
        try:
            speed_text = self.speed_combo.get()
            # Map combobox text to frame duration in ms
            # Default is 10ms per frame (1x speed)
            # Lower ms = faster game, Higher ms = slower game
            speed_map = {
                "1 (10x Fast)": 1,
                "2 (5x Fast)": 2,
                "5 (2x Fast)": 5,
                "10 (Normal)": 10,
                "20 (0.5x Slow)": 20,
                "50 (0.2x Slow)": 50
            }
            speed_ms = speed_map.get(speed_text, 10)
            if self.trainer.set_game_speed(speed_ms):
                self.update_status(f"Game Speed: {speed_text}", speed_ms != 10)
        except Exception as e:
            print(f"[SpeedCombo] Error: {e}")

    def kill_all_zombies_ui(self):
        count = self.trainer.kill_all_zombies()
        if count >= 0:
            self.update_status(f"Killed {count} Zombies", True)
        else:
            messagebox.showerror("Error", "Failed to kill zombies")

    def clear_all_plants_ui(self):
        count = self.trainer.clear_all_plants()
        if count >= 0:
            self.update_status(f"Cleared {count} Plants", True)
        else:
            messagebox.showerror("Error", "Failed to clear plants")

    def reset_all_ui(self):
        """Reset all cheats and restore original bytes."""
        if not self.is_connected:
            return

        # Call trainer's reset_all method
        self.trainer.reset_all()

        # Reset all UI toggle variables
        for var_name in ('sun_var', 'collect_var', 'prevent_spend_var', 'plant_add_var',
                         'auto_collect_var', 'cooldown_var', 'kill_var', 'show_zombies_var',
                         'background_var', 'plant_anywhere_var', 'move_zombie_var', 'plant_changer_var',
                         'bullet_changer_var','rapid_fire_var','fast_shoot_var','money_changer_var',
                         'instant_plant_death_var','invincible_plants_var','invincible_zombies_var',
                         'zombotany_unhittable_var','stop_zombies_var','stop_spawning_var',
                         'no_fog_var','see_vase_var','mushrooms_awake_var','lock_butter_var','no_crater_var',
                         'no_ice_trail_var','zombie_not_explode_var','unlock_sun_limit_var','fast_belt_var','lock_shovel_var'):
            try:
                getattr(self, var_name).set(False)
            except:
                pass

        # Reset speed combo to 1x
        try:
            self.speed_combo.current(3)  # 1x
        except:
            pass

        # Update status
        self.status_label.config(
            text="ALL CHEATS RESET",
            fg=self.accent_color
        )
        self.connection_dot.config(fg=self.accent_color)

    def update_status(self, cheat_name, state):
        """Update status bar with cheat state - Gaming style"""
        if state:
            self.status_label.config(
                text=f"ACTIVE :: {cheat_name.upper()}",
                fg=self.accent_color
            )
            self.connection_dot.config(fg=self.accent_color)
        else:
            self.status_label.config(
                text=f"DISABLED :: {cheat_name.upper()}",
                fg=self.accent_zombie
            )
            self.connection_dot.config(fg=self.accent_color)


if __name__ == "__main__":
    root = tk.Tk()
    app = TrainerGUI(root)
    root.mainloop()
