"""Bounded-memory editor and persistent-storage tests; no real game access."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import copy,json,struct,tempfile,unittest
from pathlib import Path
from contextlib import contextmanager
from trainer_engine import PvZTrainer
from studio_engine import StudioGame,ARRAYS,SIGNATURES
from studio_models import formation,wave_plan,SpawnSchedule
from studio_storage import Documents,SaveBackups,safe_name
from studio_ui import LawnStudio,parse_hotkey

class Memory:
    def __init__(self):self.bytes={}
    def read_bytes(self,a,n):return bytes(self.bytes.get(a+i,0)for i in range(n))
    def write_bytes(self,a,data,n):
        for i,v in enumerate(data[:n]):self.bytes[a+i]=v
    def put(self,a,value,fmt='<i'):self.write_bytes(a,struct.pack(fmt,value),struct.calcsize(fmt))

class Native:
    def __init__(self):self.calls=[]
    @contextmanager
    def frozen(self):yield
    def execute(self,build):self.calls.append(build(0x40000000,0x4000f000));return 0
    execute_main=execute
    def write_code(self,*args):raise AssertionError('Unexpected native patch')

class EditorTests(unittest.TestCase):
    def setUp(self):
        self.e=PvZTrainer();self.e.base_address=0x400000;self.e.is_connected=True;self.e.pm=self.m=Memory();self.native=Native()
        self.g=StudioGame(self.e,verify=lambda:None,native=self.native);self.app=0x100000;self.b=0x200000;self.user=0x500000
        self.m.put(0x729670,self.app);self.m.put(self.app+0x868,self.b);self.m.put(self.app+0x94c,self.user);self.m.put(self.app+0x91c,3)
        self.m.put(self.b+0x5578,50);self.m.put(self.b+0x557c,20)
        self.addresses={}
        for i,(kind,(off,stride,dead,ident))in enumerate(ARRAYS.items()):
            address=0x600000+i*0x100000;self.addresses[kind]=address;self.m.put(self.b+off,address);self.m.put(self.b+off+4,1)
            self.m.put(address+ident,0x10000+i);self.m.put(address+0x40,100);self.m.put(address+0x44,300)
            if kind=='zombie':self.m.put(address+0xc8,270);self.m.put(address+0xcc,270)
        self.m.put(self.b+0x15c,0x900000);self.m.put(0x900024,2)
        self.m.put(0x90005c,0);self.m.put(0x9000ac,1)
        self.m.put(self.user+0x378,1);self.m.put(self.user+0x380,1);self.m.put(self.user+0x3ac,3)
        for rva,s in SIGNATURES.items():self.m.write_bytes(0x400000+rva,bytes.fromhex(s),len(bytes.fromhex(s)))
        for i in range(14):self.m.put(0x71e900+i*12,i);self.m.put(0x71e908+i*12,20)
    def test_entity_enumeration_and_dead_free_slots(self):
        self.assertEqual(len(self.g.entities('plant')),1)
        p=self.addresses['plant'];self.m.put(p+0x141,1,'<B');self.assertEqual(self.g.entities('plant'),[])
        self.m.put(p+0x141,0,'<B');self.m.put(p+0x148,7);self.assertEqual(self.g.entities('plant'),[])
    def test_corrupt_array_bound_is_rejected(self):
        self.m.put(self.b+0xc8,5000)
        with self.assertRaisesRegex(RuntimeError,'bound'):self.g.entities('plant')
    def test_entity_edits_restore_by_id(self):
        self.g.edit_entity('plant',0x10000,{'health':200,'attack_interval':75})
        self.assertEqual(self.g.read(self.addresses['plant']+0x40),200)
        self.g.reset();self.assertEqual(self.g.read(self.addresses['plant']+0x40),100)
    def test_stale_slot_is_not_restored(self):
        self.g.edit_entity('plant',0x10000,{'health':200});self.m.put(self.addresses['plant']+0x148,0x20000)
        self.g.reset();self.assertEqual(self.g.read(self.addresses['plant']+0x40),200)
    def test_reused_lawn_pointer_invalidates_selection_and_queue(self):
        self.m.put(self.b+0x5580,100);old=self.g.lawn_token();self.m.put(self.b+0x5580,1)
        with self.assertRaisesRegex(RuntimeError,'earlier lawn'):self.g.edit_entity('plant',0x10000,{'health':120},old)
    def test_invalid_entity_changes_make_no_writes(self):
        before=dict(self.m.bytes)
        for values in ({'health':1000},{'unknown':4},{'health':True}):
            with self.assertRaises(ValueError):self.g.edit_entity('plant',0x10000,values)
        with self.assertRaises(ValueError):self.g.edit_entity('zombie',0x10001,{'speed':float('nan')})
        self.assertEqual(before,self.m.bytes)
    def test_shield_health_never_writes_the_shield_type_enum(self):
        z=self.addresses['zombie'];self.m.put(z+0xd8,1);self.m.put(z+0xdc,100);self.m.put(z+0xe0,200)
        self.g.edit_entity('zombie',0x10001,{'shield':150})
        self.assertEqual(self.g.read(z+0xd8),1);self.assertEqual(self.g.read(z+0xdc),150)
        self.g.reset();self.assertEqual(self.g.read(z+0xdc),100)
    def test_equipment_edits_require_corresponding_equipment(self):
        with self.assertRaisesRegex(ValueError,'no corresponding'):self.g.edit_entity('zombie',0x10001,{'armour':200,'max_armour':200})
    def test_seed_duplicates_require_opt_in(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.g.set_seed(2,0)
        self.g.set_seed(2,0,allow_duplicates=True);self.assertEqual(self.g.seed_bank()[1]['type'],0)
    def test_imitation_seed_has_target(self):
        self.g.set_seed(2,5,imitater=True);self.assertEqual(self.g.seed_bank()[1]['type'],48);self.assertEqual(self.g.seed_bank()[1]['imitater'],5)
    def test_upcoming_wave_is_padded_and_past_wave_blocked(self):
        self.g.set_wave(2,[0,2,4]);self.assertEqual(self.g.read(self.b+0x6cc+200+12),-1)
        self.m.put(self.b+0x5594,2)
        with self.assertRaises(ValueError):self.g.set_wave(2,[0])
    def test_shared_damage_resets(self):
        self.g.set_projectile_damage(0,99);self.assertEqual(self.g.read(0x71e908),99)
        self.g.reset();self.assertEqual(self.g.read(0x71e908),20)
    def test_profile_garden_validation_and_native_save_payload(self):
        self.g.garden_edit(0,'water');self.assertGreater(self.g.read(self.user+0x398,'time'),0);self.assertEqual(len(self.native.calls),1)
        self.assertEqual(self.g.garden()[0]['fed'],1)
        with self.assertRaisesRegex(ValueError,'Water this plant'):self.g.garden_edit(0,'fertilize')
        self.m.put(self.user+0x3A8,3);self.g.garden_edit(0,'fertilize')
        self.assertEqual((self.g.garden()[0]['age'],self.g.garden()[0]['fed']),(1,0))
        self.m.put(self.user+0x378,201)
        with self.assertRaises(RuntimeError):self.g.garden()
    def test_level_launch_is_bounded_and_builds_native_call(self):
        with self.assertRaises(ValueError):self.g.launch_level(51)
        self.g.launch_level(10);self.assertEqual(self.g.read(self.user+0x4c),10);self.assertTrue(self.native.calls)
    def test_native_signature_mismatch_rejects_before_level_write(self):
        self.m.put(0x452820,0,'<B')
        with self.assertRaises(RuntimeError):self.g.launch_level(5)
        self.assertEqual(self.g.read(self.user+0x4c),0)
    def test_dashboard_counts(self):
        data=self.g.telemetry();self.assertEqual((data['sun'],data['plants'],data['zombies']),(50,1,1))
        self.m.put(self.app+0x918,43);self.m.put(self.b+0x5564,7);self.assertIn('Zen Garden',self.g.telemetry()['status'])

class SchemaTests(unittest.TestCase):
    def test_formation_layer_sort_and_overlap_validation(self):
        value={'version':1,'scene':2,'plants':[dict(type=0,row=3,col=1,imitater=False),dict(type=16,row=3,col=1,imitater=False)]}
        self.assertEqual(formation(value)['plants'][0]['type'],16)
        value['plants'].append(dict(type=1,row=3,col=1,imitater=False))
        with self.assertRaisesRegex(ValueError,'overlap'):formation(value)
    def test_wave_limits_and_unsupported_boss(self):
        item=dict(type=0,row=1,quantity=5,interval_ms=100,delay_ms=0)
        self.assertEqual(len(wave_plan({'version':1,'entries':[item]})['entries']),1)
        for key,value in [('type',25),('quantity',101),('row',7),('interval_ms',0)]:
            bad=dict(item,**{key:value})
            with self.assertRaises(ValueError):wave_plan({'version':1,'entries':[bad]})
    def test_schedule_timing_bound_and_board_cancellation(self):
        clock=[0];s=SpawnSchedule(lambda:clock[0]);plan={'version':1,'entries':[dict(type=0,row=1,quantity=10,interval_ms=100,delay_ms=0)]}
        s.start(plan,(1,1),5);calls=[];self.assertEqual(s.tick((1,1),lambda *x:calls.append(x)),1)
        clock[0]=5;self.assertEqual(s.tick((1,1),lambda *x:calls.append(x)),4)
        s.tick((1,2),lambda *x:calls.append(x));self.assertFalse(s.queue);self.assertEqual(len(calls),5)
    def test_schedule_failure_cancels_remaining_actions(self):
        s=SpawnSchedule(lambda:0);s.start({'version':1,'entries':[dict(type=0,row=1,quantity=2,interval_ms=100,delay_ms=0)]},1,5)
        def fail(*args):raise RuntimeError('spawn failed')
        with self.assertRaises(RuntimeError):s.tick(1,fail)
        self.assertFalse(s.queue)
    def test_hotkey_parser_rejects_scripts_windows_key_and_sequences(self):
        self.assertEqual(parse_hotkey('Ctrl+Alt+F6'),(0x75,{'Ctrl','Alt'}))
        for text in ['Win+F6','Ctrl+A','F13','F6, F7','exec()','Ctrl+Ctrl+F6','Alt+F4']:
            with self.assertRaises(ValueError):parse_hotkey(text)

class NativeSafetyTests(unittest.TestCase):
    def setUp(self):
        from studio_native import NativeCalls
        from unittest.mock import Mock
        from types import SimpleNamespace
        fixture=EditorTests();fixture.setUp();self.g=fixture.g;self.m=fixture.m
        self.native=object.__new__(NativeCalls);self.native.game=self.g;self.native.pm=self.m;self.native.handle=1;self.native.depth=0;self.native.poisoned=False
        self.native.write_code=lambda a,data:self.m.write_bytes(a,data,len(data))
        self.k=SimpleNamespace(VirtualAllocEx=Mock(return_value=0x40000000),VirtualFreeEx=Mock(),CreateRemoteThread=Mock(return_value=2),WaitForSingleObject=Mock(return_value=0),CloseHandle=Mock())
        self.native.k=self.k;self.m.write_bytes(0x5d6c6d,b'\xeb\xc8',2)
    def test_body_failure_restores_update_gate(self):
        with self.assertRaisesRegex(RuntimeError,'test failure'):
            with self.native.frozen():
                self.assertEqual(self.m.read_bytes(0x5d6c6d,2),b'\xeb\xfe');raise RuntimeError('test failure')
        self.assertEqual(self.m.read_bytes(0x5d6c6d,2),b'\xeb\xc8')
    def test_failed_thread_creation_releases_allocation_and_update_gate(self):
        self.k.CreateRemoteThread.return_value=0
        with self.assertRaises(OSError):self.native.execute(lambda a,r:b'')
        self.k.VirtualFreeEx.assert_called_once();self.assertEqual(self.m.read_bytes(0x5d6c6d,2),b'\xeb\xc8')
    def test_timeout_never_frees_executing_memory_or_resumes_updates(self):
        self.k.WaitForSingleObject.return_value=0x102
        with self.assertRaisesRegex(RuntimeError,'timed out'):self.native.execute(lambda a,r:b'')
        self.k.VirtualFreeEx.assert_not_called();self.assertTrue(self.native.poisoned)
        self.assertEqual(self.m.read_bytes(0x5d6c6d,2),b'\xeb\xfe')

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.folder=Path(self.tmp.name);self.source=self.folder/'userdata';self.source.mkdir();(self.source/'users.dat').write_bytes(b'users');(self.source/'user1.dat').write_bytes(b'profile')
        self.b=SaveBackups(self.source,self.folder/'backups')
    def tearDown(self):self.tmp.cleanup()
    def test_snapshot_restore_and_recovery(self):
        name=self.b.create();(self.source/'user1.dat').write_bytes(b'changed');(self.source/'game1_0.dat').write_bytes(b'newrun')
        recovery=self.b.restore(name)
        self.assertEqual((self.source/'user1.dat').read_bytes(),b'profile');self.assertFalse((self.source/'game1_0.dat').exists());self.assertIn('game1_0.dat',self.b.validate(recovery))
    def test_checksum_corruption_prevents_all_restore_writes(self):
        name=self.b.create();(self.b.root/name/'user1.dat').write_bytes(b'corrupted');before=(self.source/'user1.dat').read_bytes()
        with self.assertRaisesRegex(ValueError,'checksum'):self.b.restore(name)
        self.assertEqual((self.source/'user1.dat').read_bytes(),before)
    def test_running_game_blocks_restore(self):
        name=self.b.create();self.b.running=lambda:True
        with self.assertRaisesRegex(RuntimeError,'Close PVZ'):self.b.restore(name)
    def test_manifest_path_traversal_is_rejected(self):
        name=self.b.create();p=self.b.root/name/'manifest.json';value=json.loads(p.read_text());value['files']['../escape.dat']='0'*64;p.write_text(json.dumps(value))
        with self.assertRaises(ValueError):self.b.validate(name)
    def test_document_names_are_local_and_roundtrip_json(self):
        docs=Documents(self.folder/'documents');docs.save('profiles','Test',{'version':1});self.assertEqual(docs.load('profiles','Test'),{'version':1})
        for name in ('../escape','CON','C:\\escape','NUL',''):
            with self.assertRaises(ValueError):safe_name(name)
    def test_non_save_files_are_never_removed(self):
        (self.source/'notes.txt').write_text('keep');name=self.b.create();self.b.restore(name);self.assertTrue((self.source/'notes.txt').exists())

class StudioUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance()or QApplication([])
    def setUp(self):
        from test_interface import FakeEngine
        from lawnlab import LawnLab
        self.tmp=tempfile.TemporaryDirectory();self.owner=LawnLab(FakeEngine());self.owner.timer.stop();self.studio=LawnStudio(self.owner,documents=Documents(self.tmp.name),backups=SaveBackups(root=Path(self.tmp.name)/'backups'))
    def tearDown(self):self.studio.close();self.owner.close();self.tmp.cleanup()
    def test_all_seven_workspaces_and_default_hotkeys_are_off(self):
        self.assertEqual(self.studio.tabs.count(),9);self.assertFalse(self.studio.hotkeys_enabled.isChecked());self.assertFalse(self.studio.activate_profile.isChecked())
    def test_profile_values_unknown_actions_and_conflicts_are_validated(self):
        value=self.studio.settings();self.studio.validate_settings(value)
        bad=copy.deepcopy(value);bad['controls']['exec']={'enabled':True,'value':None}
        with self.assertRaises(ValueError):self.studio.validate_settings(bad)
        bad=copy.deepcopy(value);bad['controls']['toggle_infinite_sun']['enabled']=True;bad['controls']['toggle_sun_lock']['enabled']=True
        with self.assertRaises(ValueError):self.studio.validate_settings(bad)
    def test_equivalent_hotkey_modifier_orders_are_duplicates(self):
        value=self.studio.settings();value['hotkeys']['Sun lock']='Ctrl+Alt+F6';value['hotkeys']['Instant recharge']='Alt+Ctrl+F6'
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.studio.validate_settings(value)
    def test_hotkeys_require_game_focus_and_only_trigger_on_press_edge(self):
        from studio_ui import GameHotkeys
        from types import SimpleNamespace
        from unittest.mock import Mock
        self.owner.engine.is_connected=True;self.owner.engine.pm=SimpleNamespace(process_id=12)
        self.studio.hotkeys_enabled.setChecked(True);self.studio.hotkey_action=Mock()
        user=Mock();user.GetForegroundWindow.return_value=123
        foreground=[12];pressed={0x75}
        def pid(hwnd,value):value._obj.value=foreground[0]
        user.GetWindowThreadProcessId.side_effect=pid;user.GetAsyncKeyState.side_effect=lambda k:0x8000 if k in pressed else 0
        keys=GameHotkeys(self.studio);keys.user=user;keys.poll();keys.poll()
        self.studio.hotkey_action.assert_called_once_with('Sun lock')
        pressed.clear();keys.poll();foreground[0]=99;pressed.add(0x75);keys.poll();self.assertEqual(self.studio.hotkey_action.call_count,1)
        self.owner.engine.is_connected=False

