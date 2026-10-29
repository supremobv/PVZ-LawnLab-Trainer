"""Cross-build code semantics, version boundaries and generated artifact coverage."""
import json,struct,unittest
from pathlib import Path
import capstone
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
import game_layout,classic_game_layout
import verified_engine,classic_verified_engine
from generate_classic import generate,ROOT
from classic_studio_engine import StudioGame,ARRAYS
from classic_profile_tools import ProfileTools,PROFILE_FIELDS
from test_studio import Memory,Native
from types import SimpleNamespace

class CodeSemantics(unittest.TestCase):
 def vm(self):
  vm=Uc(UC_ARCH_X86,UC_MODE_32)
  for a in(0x100000,0x300000,0x400000):vm.mem_map(a,0x10000)
  vm.reg_write(UC_X86_REG_ESP,0x308000);vm.reg_write(UC_X86_REG_EFLAGS,0x247)
  return vm
 def test_purchase_guards_preserve_counts_tree_and_flags_on_both_builds(self):
  for layout in(game_layout,classic_game_layout):
   for name,off,cap in [('shop_seed_cap',0x23C if layout is game_layout else 0x214,4),('shop_mower_cap',0x20C if layout is game_layout else 0x1E4,2),('shop_tree_preserve',0x11C if layout is game_layout else 0xF4,1)]:
    for initial in(0,cap-1,cap,1280543585):
     vm=self.vm();vm.reg_write(UC_X86_REG_EAX,0x400000);vm.reg_write(UC_X86_REG_EDX,0x400000);vm.reg_write(UC_X86_REG_ESI,1)
     vm.mem_write(0x400000+off,struct.pack('<I',initial));code=layout.shop_purchase_code(name,0x100000,0x101000,bytes.fromhex(layout.SHOP_CAP_ORIGINAL[name]));vm.mem_write(0x100000,code)
     vm.emu_start(0x100000,0x101000,count=100)
     self.assertEqual(vm.reg_read(UC_X86_REG_EIP),0x101000)
     expected=(initial if initial else 1)if name=='shop_tree_preserve'else initial+1 if initial<cap else initial
     self.assertEqual(struct.unpack('<I',vm.mem_read(0x400000+off,4))[0],expected,(layout.__name__,name,initial))
     flags=0x247
     if name!='shop_tree_preserve'and initial<cap:
      reference=self.vm();reference.reg_write(UC_X86_REG_EAX,0x400000);reference.reg_write(UC_X86_REG_ESI,1);reference.mem_write(0x400000+off,struct.pack('<I',initial));original=bytes.fromhex(layout.SHOP_CAP_ORIGINAL[name]);reference.mem_write(0x100000,original);reference.emu_start(0x100000,0x100000+len(original));flags=reference.reg_read(UC_X86_REG_EFLAGS)
     self.assertEqual(vm.reg_read(UC_X86_REG_EFLAGS),flags)
 def test_rapid_fire_uses_matching_projectile_count_and_native_tail(self):
  for layout,end,off in[(game_layout,0x46286F,0xF0),(classic_game_layout,0x45EF3D,0xD8)]:
   code=layout.rapid_direct_code(0x100000,end);ops=list(capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32).disasm(code,0x100000))
   self.assertIn(hex(off),ops[1].op_str);self.assertEqual(ops[-1].op_str,'0x462bcb'if layout is game_layout else'0x45f272')
 def test_one_hit_positive_damage_calls_correct_body_damage_abi(self):
  for layout,target,body,reg,stack in[(game_layout,0x5421C1,0x541CA0,UC_X86_REG_EDI,[2000000,0xAB]),(classic_game_layout,0x5317FF,0x5312D0,UC_X86_REG_ESI,[0x400000,2000000,0xAB])]:
   vm=self.vm();vm.mem_map(0x500000,0x50000);vm.reg_write(reg,0x400000);vm.reg_write(UC_X86_REG_EBP,1);vm.reg_write(UC_X86_REG_EBX,0xAB)
   vm.mem_write(0x100000,layout.one_hit_code(0x100000,target));captured=[]
   def reached(uc,address,size,data):
    if address==body:
     esp=uc.reg_read(UC_X86_REG_ESP);captured.extend(struct.unpack('<'+'I'*len(stack),uc.mem_read(esp+4,len(stack)*4)));uc.emu_stop()
   vm.hook_add(UC_HOOK_CODE,reached);vm.emu_start(0x100000,0x110000,count=100);self.assertEqual(captured,stack)
 def test_hook_and_guard_spans_end_on_whole_instructions(self):
  decoder=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
  for engine,layout in[(verified_engine,game_layout),(classic_verified_engine,classic_game_layout)]:
   for name,(rva,size)in(engine.HOOKS|layout.SHOP_CAP_HOOKS).items():
    old=bytes.fromhex((engine.HOOK_ORIGINAL|layout.SHOP_CAP_ORIGINAL)[name]);self.assertEqual(len(old),size);self.assertEqual(sum(i.size for i in decoder.disasm(old,rva)),size)
   rva,old=layout.SHOOT_GUARD;code=layout.shooting_guard_code(0x100000,0x400000+rva+len(bytes.fromhex(old)));ops=list(decoder.disasm(code,0x100000))
   self.assertEqual(int(ops[-1].op_str,16),0x400000+rva+len(bytes.fromhex(old)));popfd=next(i.address for i in ops if i.mnemonic=='popfd');self.assertEqual([int(i.op_str,16)for i in ops if i.mnemonic in('jg','jle')],[popfd,popfd])

class BuildBoundaries(unittest.TestCase):
 def test_version_router_exposes_shutdown_for_gui_disconnect(self):
  from unittest.mock import Mock
  from trainer_backend import PvZTrainer
  engine=PvZTrainer();engine._backend.shutdown=Mock();self.assertTrue(type(engine).safe_runtime_enabled);self.assertTrue(hasattr(type(engine),'shutdown'));engine.shutdown();engine._backend.shutdown.assert_called_once()
 def test_classic_studio_reuses_own_fingerprint_when_controls_already_patch_text(self):
  from unittest.mock import patch
  pm=Memory();engine=SimpleNamespace(pm=pm,is_connected=True,base_address=0x400000);engine.runtime=SimpleNamespace(game=SimpleNamespace(_checked=pm),image=b'original fingerprinted image')
  game=StudioGame(engine)
  with patch('runtime_image.classic_guard',side_effect=AssertionError('Do not hash our own live patches')):self.assertTrue(game.guard())
  self.assertIs(game._classic_image,engine.runtime.image)
 def test_classic_generated_sources_are_current(self):
  for name,value in generate().items():self.assertEqual((ROOT/name).read_text(encoding='utf-8'),value,name)
 def test_classic_entity_identity_uses_its_own_stride(self):
  m=Memory();engine=SimpleNamespace(pm=m,is_connected=True,base_address=0x400000);g=StudioGame(engine,verify=lambda:None,native=Native())
  m.put(0x6A9EC0,0x100000);m.put(0x1007FC,3);m.put(0x100768,0x200000);m.put(0x200090,0x600000);m.put(0x200094,2)
  for i in range(2):
   a=0x600000+i*0x15C;m.put(a+0x158,0x10000+i);m.put(a+0x24,2);m.put(a+0xC8,270)
  self.assertEqual([z['id']for z in g.entities('zombie')],[0x10000,0x10001]);self.assertEqual(ARRAYS['zombie'],(0x90,0x15C,0xEC,0x158))
 def test_classic_does_not_offer_nonexistent_native_achievements(self):
  self.assertFalse(ProfileTools.HAS_ACHIEVEMENTS)
  with self.assertRaisesRegex(ValueError,'no native'):ProfileTools(None).achievements({0:True})
 def test_tree_and_endless_records_are_distinct_on_each_build(self):
  from profile_tools import PROFILE_FIELDS as goty
  for key in goty:self.assertEqual(goty[key][1]-PROFILE_FIELDS[key][1],0x28)
  self.assertEqual(goty['tree_height'][1],0x11C);self.assertEqual(PROFILE_FIELDS['tree_height'][1],0xF4)
  self.assertEqual([goty[k][1]for k in('best_vasebreaker','best_izombie','best_survival_pool')],[0x144,0x16C,0x88])
 def test_classic_cheat_table_and_inventory_are_current(self):
  import generate_ct,xml.etree.ElementTree as ET
  data=generate_ct.build_classic();self.assertEqual((ROOT/'LawnLab-Classic-1.0.0.1051.CT').read_bytes(),data);tree=ET.fromstring(data);ids=[e.text for e in tree.iter('ID')];self.assertEqual(len(ids),len(set(ids)))
  self.assertEqual(json.loads((ROOT/'LawnLab-Classic-addresses.json').read_text()),json.loads(json.dumps(generate_ct.classic_inventory())))
