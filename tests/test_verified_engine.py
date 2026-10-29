"""Patch combinations and failure recovery; no live process is accessed."""
import random,struct,threading,unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock
from unittest.mock import patch
from test_studio import Memory
from verified_engine import PvZTrainer,VerifiedRuntime,GROUPS,HOOKS,HOOK_ORIGINAL,CONTINUOUS,NAMES,CONFLICTS
from game_layout import FRAME_DURATION,SEED_RECHARGE,FREE_PLANTING,WAVE_COUNTDOWN,HUGE_WAVE_COUNTDOWN,SHOOT_GUARD,shooting_guard_code,SHOP_STOCK_EXTRA,SHOP_CAP_HOOKS,SHOP_CAP_ORIGINAL,BANK_PATCHES,SNAIL_PATCHES
from verified_patches import PATCHES
from patch_manager import PatchManager
import extra_controls
from studio_engine import StudioGame

class Backend:
    def __init__(self,pm):
        self.pm=pm;self.handle=1;self.level=0;self.allocations=[];self.fail_once=None;self.fail_always=set();self.writes=[]
        self.k=SimpleNamespace(VirtualAllocEx=lambda *args:self.allocate())
    def allocate(self):
        a=0x20000000+len(self.allocations)*4096;self.allocations.append(a);return a
    @contextmanager
    def suspended(self,regions=()):
        self.level+=1
        try:yield
        finally:self.level-=1
    frozen=suspended
    def write_code(self,a,data):
        assert self.level>0
        self.writes.append((a,bytes(data)))
        if a==self.fail_once:self.fail_once=None;self.pm.write_bytes(a,data[:1],1);raise OSError('partial write')
        if a in self.fail_always:raise OSError('persistent write failure')
        self.pm.write_bytes(a,data,len(data))

def fixture():
    e=PvZTrainer();e.base_address=0x400000;e.pm=Memory();e.is_connected=True;e.log=lambda *args:None;e._start_worker=lambda:None
    m=e.pm;backend=Backend(m);r=object.__new__(VerifiedRuntime);r.engine=e;r.base=e.base_address;r.native=backend
    r.image=bytearray(0x415000);r.caves={};r.initialized=set();r.frame_original=None;r.preview_original=None
    for values in PATCHES.values():
        for offset,original,desired in values:r.image[offset:offset+len(bytes.fromhex(original))]=bytes.fromhex(original)
    hooks=HOOK_ORIGINAL
    for name,(offset,size)in HOOKS.items():r.image[offset:offset+size]=bytes.fromhex(hooks[name])
    r.image[0x1e844:0x1e846]=bytes.fromhex('2bf3');r.image[0x684e4:0x684ea]=bytes.fromhex('0f8598feffff')
    # Sparse fake process memory contains original code only at patch sites.
    for values in PATCHES.values():
        for offset,original,desired in values:m.write_bytes(0x400000+offset,bytes.fromhex(original),len(bytes.fromhex(original)))
    for name,(offset,size)in HOOKS.items():m.write_bytes(0x400000+offset,bytes(r.image[offset:offset+size]),size)
    m.write_bytes(0x41e844,bytes.fromhex('2bf3'),2);m.write_bytes(0x4684e4,bytes.fromhex('0f8598feffff'),6)
    rva,old,new=SEED_RECHARGE;r.image[rva:rva+2]=bytes.fromhex(old);m.write_bytes(0x400000+rva,bytes.fromhex(old),2)
    rva,old=SHOOT_GUARD;r.image[rva:rva+6]=bytes.fromhex(old);m.write_bytes(0x400000+rva,bytes.fromhex(old),6)
    for rva,old,new in FREE_PLANTING:r.image[rva:rva+len(bytes.fromhex(old))]=bytes.fromhex(old);m.write_bytes(0x400000+rva,bytes.fromhex(old),len(bytes.fromhex(old)))
    rva,old,new=SHOP_STOCK_EXTRA;r.image[rva:rva+len(bytes.fromhex(old))]=bytes.fromhex(old);m.write_bytes(0x400000+rva,bytes.fromhex(old),len(bytes.fromhex(old)))
    for rva,old,new in BANK_PATCHES+SNAIL_PATCHES:
        data=bytes.fromhex(old);r.image[rva:rva+len(data)]=data;m.write_bytes(0x400000+rva,data,len(data))
    for name,(rva,size)in SHOP_CAP_HOOKS.items():
        data=bytes.fromhex(SHOP_CAP_ORIGINAL[name]);r.image[rva:rva+size]=data;m.write_bytes(0x400000+rva,data,size)
    for spans in extra_controls.PATCHES['goty'].values():
        for rva,old,new in spans:
            data=bytes.fromhex(old);r.image[rva:rva+len(data)]=data;m.write_bytes(0x400000+rva,data,len(data))
    rva=extra_controls.PLANT_HOOK['goty'];data=extra_controls.PLANT_ORIGINAL;r.image[rva:rva+len(data)]=data;m.write_bytes(0x400000+rva,data,len(data))
    m.put(0x729670,0x100000);m.put(0x100868,0x200000);m.put(0x10094c,0x300000);m.put(0x10091c,3);m.put(0x100000+FRAME_DURATION,10);m.put(0x100514,0x12345678)
    m.put(0x200000+0x5578,50);m.put(0x105578,123456)
    m.put(0x2000c4,0x500000);m.put(0x2000a8,0x510000);m.put(0x2000fc,0x520000)
    for row in range(5):m.put(0x200000+0x5f0+row*4,1)
    r.game=StudioGame(e,verify=lambda:None,native=backend);r.manager=PatchManager(m,backend);r.zombie_sizes=extra_controls.ZombieSizes(r.game);e.runtime=r
    return e,r,backend,m

class OwnershipTests(unittest.TestCase):
    def setUp(self):self.e,self.r,self.b,self.m=fixture()
    def test_every_gui_feature_routes_to_verified_override(self):
        from lawnlab import FEATURES
        for f in FEATURES:self.assertIn(f.method,PvZTrainer.__dict__,f.title)
    def test_all_toggles_cycle_and_restore(self):
        for name in sorted(NAMES):
            self.e._toggle(name,True);self.e._toggle(name,False)
        self.assertFalse(self.r.manager.active)
        for values in PATCHES.values():
            for offset,old,new in values:self.assertEqual(self.m.read_bytes(0x400000+offset,len(bytes.fromhex(old))),bytes.fromhex(old))
    def test_sun_writes_board_not_app_and_installs_no_sun_hook(self):
        before=self.m.read_bytes(0x41e6e0,6);self.e.toggle_infinite_sun(True)
        self.assertEqual(self.r.game.read(0x205578),9999);self.assertEqual(self.r.game.read(0x105578),123456)
        self.assertEqual(self.m.read_bytes(0x41e6e0,6),before);self.assertFalse(self.b.allocations)
    def test_economy_combination_no_overlapping_hooks_in_any_disable_order(self):
        names=['infinite_sun','collect_1000_sun','prevent_spend','planting_adds_sun','auto_collect','unlock_sun_limit','money_changer']
        for seed in range(12):
            rng=random.Random(seed);rng.shuffle(names)
            for n in names:self.e._toggle(n,True)
            self.assertEqual(len(self.r.manager.active),7)
            rng.shuffle(names)
            for n in names:self.e._toggle(n,False)
            self.assertFalse(self.r.manager.active)
    def test_repeated_enable_is_idempotent_and_caves_are_reused(self):
        for _ in range(40):
            self.e.toggle_bullet_changer(True);self.e.toggle_bullet_changer(True);self.e.toggle_bullet_changer(False)
        self.assertEqual(len(self.b.allocations),1);self.assertEqual(self.m.read_bytes(0x470e29,5),bytes.fromhex('89455c8bc6'))
    def test_parameter_update_changes_data_not_executing_code(self):
        self.e.toggle_bullet_changer(True);a=self.r.caves['bullet_changer'];before=self.m.read_bytes(a,64)
        self.e.set_bullet_changer_value(12)
        self.assertEqual(self.m.read_bytes(a,64),before);self.assertEqual(self.r.game.read(a+0x100),12)
    def test_shared_immunity_is_restored_only_after_last_owner(self):
        self.e.toggle_invincible_plants(True);self.e.toggle_unhittable_plants_zombotany(True)
        self.e.toggle_invincible_plants(False);self.assertEqual(self.m.read_bytes(0x47169b,3),b'\x90'*3)
        self.e.toggle_unhittable_plants_zombotany(False);self.assertEqual(self.m.read_bytes(0x47169b,3),bytes.fromhex('295040'))
    def test_partial_parameter_write_restores_value(self):
        self.e.toggle_bullet_changer(True);a=self.r.caves['bullet_changer']+0x100;old=self.m.read_bytes(a,4)
        self.b.fail_once=a
        with self.assertRaises(OSError):self.e.set_bullet_changer_value(12)
        self.assertEqual(self.m.read_bytes(a,4),old);self.assertTrue(self.e.last_error)
    def test_unrecoverable_parameter_write_marks_backend_unsafe(self):
        self.e.toggle_bullet_changer(True);a=self.r.caves['bullet_changer']+0x100;self.b.fail_always.add(a)
        with self.assertRaisesRegex(RuntimeError,'restart PVZ'):self.e.set_bullet_changer_value(12)
        self.assertTrue(self.b.poisoned);self.assertTrue(self.e.last_error)
    def test_conflicting_modes_auto_disable_at_backend(self):
        for group in CONFLICTS:
            a,b=sorted(group);self.e._toggle(a,True);self.e._toggle(b,True)
            self.assertFalse(getattr(self.e,a+'_active'));self.assertTrue(getattr(self.e,b+'_active'));self.e.reset_all()
    def test_random_feature_combinations_remain_consistent(self):
        rng=random.Random(42);names=sorted(NAMES)
        for _ in range(600):
            n=rng.choice(names);self.e._toggle(n,not getattr(self.e,n+'_active',False))
            self.assertEqual(set(self.r.manager.active),{n for n in NAMES if getattr(self.e,n+'_active',False)})
        self.e.reset_all();self.assertFalse(self.r.manager.active);self.assertLessEqual(len(self.b.allocations),len(HOOKS)+len(SHOP_CAP_HOOKS)+1)
    def test_mismatched_code_rejects_before_partial_multi_patch(self):
        specs=self.r.specs('invincible_plants');bad=specs[-1][0];self.m.write_bytes(bad,b'\xcc',1);first=specs[0]
        with self.assertRaises(RuntimeError):self.e.toggle_invincible_plants(True)
        self.assertEqual(self.m.read_bytes(first[0],len(first[1])),first[1]);self.assertFalse(self.e.invincible_plants_active)
    def test_partial_multi_patch_write_rolls_back(self):
        specs=self.r.specs('invincible_plants');self.b.fail_once=specs[2][0]
        with self.assertRaises(OSError):self.e.toggle_invincible_plants(True)
        for a,old,new in specs:self.assertEqual(self.m.read_bytes(a,len(old)),old)
        self.assertFalse(self.e.invincible_plants_active)
    def test_restore_failure_keeps_flags_and_journal_for_retry(self):
        self.e.toggle_auto_collect(True);a=self.r.manager.active['auto_collect'][0][0];self.b.fail_always.add(a)
        with self.assertRaises(OSError):self.e.toggle_auto_collect(False)
        self.assertTrue(self.e.auto_collect_active);self.assertIn('auto_collect',self.r.manager.active)
        self.b.fail_always.clear();self.e.reset_all();self.assertFalse(self.e.auto_collect_active)
    def test_external_conflict_never_overwritten_on_restore(self):
        self.e.toggle_auto_collect(True);a=self.r.manager.active['auto_collect'][0][0];self.m.write_bytes(a,b'\xcc',1)
        with self.assertRaises(RuntimeError):self.e.toggle_auto_collect(False)
        self.assertEqual(self.m.read_bytes(a,1),b'\xcc')
    def test_hooks_end_on_original_instruction_boundaries(self):
        import capstone
        decoder=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
        for name,(rva,size)in HOOKS.items():
            self.assertEqual(sum(x.size for x in decoder.disasm(bytes(self.r.image[rva:rva+size]),self.r.base+rva)),size)
            self.e._toggle(name,True);a=self.r.caves[name]
            code=next(data for address,data in self.b.writes if address==a);instructions=list(decoder.disasm(code,a))
            self.assertEqual(instructions[-1].mnemonic,'jmp');self.assertEqual(int(instructions[-1].op_str,16),0x462bcb if name=='rapid_fire'else self.r.base+rva+size)
            self.e._toggle(name,False)
    def test_single_worker_is_joined_before_handle_close(self):
        del self.e._start_worker
        self.e.toggle_infinite_sun(True);worker=self.e._safe_worker
        for _ in range(10):self.e.toggle_infinite_sun(True)
        self.assertIs(self.e._safe_worker,worker);self.e.shutdown();self.assertFalse(worker.is_alive())
    def test_wow64_context_layout_matches_target_abi(self):
        import ctypes
        from studio_native import Wow64Context,ThreadEntry
        self.assertEqual(ctypes.sizeof(Wow64Context),716);self.assertEqual(Wow64Context.eip.offset,184);self.assertEqual(ctypes.sizeof(ThreadEntry),28)
    def test_pace_never_changes_audio_pointer(self):
        for value in (1,2,5,10,20,50):
            self.e.set_game_speed(value);self.assertEqual(self.r.game.read(0x100000+FRAME_DURATION),value)
            self.assertEqual(self.m.read_bytes(0x100514,4),bytes.fromhex('78563412'))
        self.e.reset_all();self.assertEqual(self.r.game.read(0x100000+FRAME_DURATION),10)
    def test_recharge_targets_seed_packet_update(self):
        plant=self.m.read_bytes(0x464a0b,1);self.e.toggle_no_cooldown(True)
        self.assertEqual(self.m.read_bytes(0x491e55,2),b'\x90\x90');self.assertEqual(self.m.read_bytes(0x464a0b,1),plant)
        self.e.toggle_no_cooldown(False);self.assertEqual(self.m.read_bytes(0x491e55,2),b'\x7e\x14')
    def test_zero_sun_free_planting_owns_affordability_and_spending_checks(self):
        self.e.toggle_prevent_spend(True)
        self.assertEqual(len(self.r.manager.active['prevent_spend']),3)
        self.assertEqual(self.m.read_bytes(0x41e88f,3),b'\xb0\x01\x90')
        self.e.toggle_prevent_spend(False);self.assertEqual(self.m.read_bytes(0x41e88f,3),b'\x0f\x9e\xc0')
    def test_invalid_lane_has_no_writes_and_does_not_poison_session(self):
        self.e.set_move_zombie_row_value(5)
        with self.assertRaisesRegex(RuntimeError,'does not exist'):self.e.toggle_move_zombie_row(True)
        self.assertFalse(self.e.last_error);self.assertNotIn('move_zombie_row',self.r.manager.active)
    def test_wave_timeout_reports_failure_and_restores_pending_countdown(self):
        self.m.put(0x200000+0x557c,30);self.m.put(0x200000+WAVE_COUNTDOWN,1200)
        with patch('verified_engine.time.monotonic',side_effect=[0,3]):
            with self.assertRaisesRegex(RuntimeError,'did not advance'):self.e.spawn_all_zombies_now()
        self.assertEqual(self.r.game.read(0x200000+WAVE_COUNTDOWN),1200)
    def test_invalid_frame_duration_is_rejected_before_writes(self):
        self.m.put(0x100000+FRAME_DURATION,0)
        with self.assertRaisesRegex(RuntimeError,'Unexpected frame duration'):self.e.set_game_speed(5)
        self.assertEqual(self.r.game.read(0x100000+FRAME_DURATION),0);self.assertEqual(self.m.read_bytes(0x100514,4),bytes.fromhex('78563412'))
    def test_mower_restore_distinguishes_storage_bound_from_live_count(self):
        self.m.put(0x200118,0x600000);self.m.put(0x20011c,10)
        for index in range(5,10):
            self.m.put(0x600000+index*0x48+0x44,0x10000+index);self.m.put(0x600000+index*0x48+0x14,index-5)
        self.r.native_action=Mock();self.e.restore_lawn_mowers();actions=self.r.native_action.call_args.args[0]
        self.assertEqual(len(actions),7);self.assertEqual(actions[-2],(0x1e8a0,'esi',0x200000,[]))
        self.assertFalse(self.r.manager.active)
    def test_wave_countdown_is_one_not_zero_and_huge_wave_is_expired(self):
        self.m.put(0x200000+0x557c,30);self.m.put(0x200000+0x5594,3);self.m.put(0x200000+HUGE_WAVE_COUNTDOWN,750)
        with patch('verified_engine.time.sleep',side_effect=lambda _:self.m.put(0x200000+0x5594,4)):self.e.spawn_all_zombies_now()
        self.assertEqual(self.r.game.read(0x200000+WAVE_COUNTDOWN),1);self.assertEqual(self.r.game.read(0x200000+HUGE_WAVE_COUNTDOWN),1)
    def test_wave_rejects_paused_unsupported_finished_or_stopped_state(self):
        self.m.put(0x200000+0x557c,30)
        for address,value in [(0x200000+0x17c,1),(0x100918,20),(0x200000+0x5594,30)]:
            self.m.put(address,value)
            with self.assertRaises(RuntimeError):self.e.spawn_all_zombies_now()
            self.m.put(address,0)
        self.e.toggle_stop_spawning(True)
        with self.assertRaises(RuntimeError):self.e.spawn_all_zombies_now()
    def test_rapid_fire_uses_firing_timer_hook_with_one_tick(self):
        old=self.m.read_bytes(0x4684e4,6);self.e.toggle_rapid_fire(True)
        self.assertEqual(self.r.game.read(self.r.caves['fast_shoot']+0x100),5)
        self.assertEqual(self.m.read_bytes(0x4684e4,6),old)
        self.assertEqual(len(self.r.manager.active['rapid_fire']),3)
    def test_shooting_guard_branches_to_original_instructions(self):
        import capstone
        code=shooting_guard_code(0x20000200,0x463211);ops=list(capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32).disasm(code,0x20000200))
        destinations=[int(i.op_str,16)for i in ops if i.mnemonic in ('jle','jg')]
        popfd=next(i.address for i in ops if i.mnemonic=='popfd');self.assertEqual(destinations,[popfd,popfd])
    def test_lane_hook_uses_natural_factory_and_code_does_not_overlap_parameter(self):
        old=self.m.read_bytes(0x42cc90,7)
        self.e.toggle_move_zombie_row(True);address=self.r.caves['move_zombie_row']
        code=next(data for a,data in self.b.writes if a==address)
        self.assertLess(len(code),0x100);self.assertEqual(HOOKS['move_zombie_row'],(0x132a12,6))
        self.assertEqual(self.m.read_bytes(0x42cc90,7),old)

class SunflowerDropTests(unittest.TestCase):
    def test_drop_parameter_updates_without_rewriting_hook_and_restores(self):
        e,r,b,m=fixture();e.set_sunflower_drop_value(3);e.toggle_sunflower_drop(True)
        cave=r.caves['sunflower_drop'];original_code=m.read_bytes(cave,240)
        self.assertEqual(r.game.read(cave+0x100),3)
        e.set_sunflower_drop_value(2);self.assertEqual(r.game.read(cave+0x100),2)
        self.assertEqual(m.read_bytes(cave,240),original_code)
        e.toggle_sunflower_drop(False);self.assertEqual(m.read_bytes(0x40f400,6),bytes.fromhex('558bec83e4f8'))
        with self.assertRaises(ValueError):e.set_sunflower_drop_value(4)

class GardenWorkerTests(unittest.TestCase):
    def test_special_gardens_never_receive_lawn_only_worker_writes(self):
        e,r,b,m=fixture();m.put(0x200000+0x5564,9)
        for mode in (43,50):
            m.put(0x100000+0x918,mode);e.toggle_infinite_sun(True);e.toggle_auto_coins(True);r.tick()
            self.assertEqual(r.game.read(0x200000+0x5578),50);self.assertFalse(e.last_error);e.reset_all()
