import unittest,struct
from unittest.mock import Mock
from pathlib import Path
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ESP
import extra_controls as x
from test_verified_engine import fixture

class UpgradePackets(unittest.TestCase):
 def test_packet_requirement_patch_returns_true_with_balanced_stack_in_both_builds(self):
  for kind in ('goty','classic'):
   rva,old,new=x.PATCHES[kind]['direct_upgrades'][-1]
   u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(0x100000,0x10000);u.mem_map(0x200000,0x10000)
   u.mem_write(0x100000,bytes.fromhex(new));u.mem_write(0x208000,struct.pack('<I',0x101000))
   for plant in range(40,48):
    u.reg_write(UC_X86_REG_ESP,0x208000);u.reg_write(UC_X86_REG_EAX,plant);u.emu_start(0x100000,0x101000,count=5)
    self.assertEqual(u.reg_read(UC_X86_REG_EAX)&255,1);self.assertEqual(u.reg_read(UC_X86_REG_ESP),0x208004)
 def test_both_cell_and_packet_checks_restore_together(self):
  e,r,b,m=fixture();spans=x.PATCHES['goty']['direct_upgrades']
  e.toggle_direct_upgrades(True)
  for a,old,new in spans:self.assertEqual(m.read_bytes(r.base+a,len(bytes.fromhex(new))),bytes.fromhex(new))
  e.toggle_direct_upgrades(False)
  for a,old,new in spans:self.assertEqual(m.read_bytes(r.base+a,len(bytes.fromhex(old))),bytes.fromhex(old))

class AutomaticCobs(unittest.TestCase):
 def setUp(self):
  self.e,self.r,self.n,self.m=fixture();self.g=self.r.game;p=0x500000;z=0x510000
  self.p=p;self.z=z
  for a,v in [(0x2000c8,1),(0x2000ac,1),(p+0x148,0x10000),(p+0x24,47),(p+0x40,300),(p+0x3c,37),(z+0x164,0x10000),(z+0xc8,200)]:self.m.put(a,v)
  self.m.put(z+0x2c,500,'<f');self.m.put(z+0x30,200,'<f')
  a,h=x.COB_FIRE['goty'];self.r.image[a:a+8]=bytes.fromhex(h)
  self.r.native_action=Mock()
 def test_ready_fires_native_at_hostile_target_without_mouse_input(self):
  self.assertEqual(x.auto_cob(self.r),1)
  self.r.native_action.assert_called_once_with([(0x6a810,'eax',self.p,[280,540])])
 def test_paused_or_projectile_saturation_blocks_firing_and_reload_writes(self):
  for a,v in [(0x20017c,1),(0x2000f0,700)]:
   self.m.put(a,v);self.assertEqual(x.auto_cob(self.r),0);self.r.native_action.assert_not_called();self.m.put(a,0)
 def test_reload_wait_skipped_but_loading_and_firing_are_not_interrupted(self):
  for state in (35,36,38):
   self.m.put(self.p+0x3c,state);self.m.put(self.p+0x54,3000)
   self.assertEqual(x.auto_cob(self.r),0);self.assertEqual(self.g.read(self.p+0x3c),state)
   self.assertEqual(self.g.read(self.p+0x54),0 if state==35 else 3000)
  self.r.native_action.assert_not_called()
 def test_friendly_dying_and_offscreen_zombies_are_not_targets(self):
  for field,value,fmt in [(0xb8,1,'<i'),(0x28,2,'<i'),(0x2c,900,'<f')]:
   old=self.m.read_bytes(self.z+field,4);self.m.put(self.z+field,value,fmt);self.assertEqual(x.auto_cob(self.r),0);self.m.write_bytes(self.z+field,old,4)
  self.r.native_action.assert_not_called()
 def test_unknown_native_fire_routine_refuses_to_call(self):
  self.r.image[0x6a810]=0
  with self.assertRaises(RuntimeError):x.auto_cob(self.r)
  self.r.native_action.assert_not_called()
 def test_controller_reset_disables_automatic_firing(self):
  self.e.toggle_auto_cob(True);self.assertTrue(self.e.auto_cob_active)
  self.e.reset_all();self.assertFalse(self.e.auto_cob_active)

class SupportPlacement(unittest.TestCase):
 def test_studio_uses_support_toggle_but_keeps_native_creation_and_cell_limits(self):
  for scene,row in [(2,3),(4,1)]:
   e,r,n,m=fixture();g=r.game;m.put(0x200000+0x5564,scene)
   with self.assertRaisesRegex(ValueError,'lily pad|flower pot'):g.place_plant(0,row,2)
   e.toggle_no_support(True);g._signature=Mock();n.execute=Mock(return_value=0x600000)
   g.entities=Mock(side_effect=[[],[dict(address=0x600000,type=0,row=row,col=2,id=0x10000,kind='plant')]])
   self.assertEqual(g.place_plant(0,row,2)['id'],0x10000);n.execute.assert_called_once()
   with self.assertRaises(ValueError):g.place_plant(0,row,10)
 def test_mine_and_support_patches_restore_original_bytes(self):
  e,r,n,m=fixture()
  for name in ('instant_mines','no_support'):
   e._toggle(name,True);e._toggle(name,False)
   for a,old,new in x.PATCHES['goty'][name]:self.assertEqual(m.read_bytes(r.base+a,len(bytes.fromhex(old))),bytes.fromhex(old))

 def test_support_free_live_formations_keep_cell_and_terrain_bounds(self):
  from studio_models import formation
  for scene,row in [(2,3),(4,1)]:
   v=dict(version=2,scene=scene,stack=False,plants=[dict(type=0,row=row,col=2,imitater=False)])
   with self.assertRaises(ValueError):formation(v)
   self.assertEqual(len(formation(v,require_support=False)['plants']),1)
   v['plants'][0]['col']=10
   with self.assertRaises(ValueError):formation(v,require_support=False)

class CattailLand(unittest.TestCase):
 def test_dependency_and_reverse_disable_restore_cattail_restriction(self):
  e,r,n,m=fixture();e.toggle_cattail_land(True)
  self.assertTrue(e.cattail_land_active);self.assertTrue(e.direct_upgrades_active);self.assertEqual(m.read_bytes(0x410e1f,2),bytes.fromhex('eb11'))
  e.toggle_direct_upgrades(False);self.assertFalse(e.cattail_land_active);self.assertFalse(e.direct_upgrades_active);self.assertEqual(m.read_bytes(0x410e1f,2),bytes.fromhex('7511'))
 def test_cattail_off_leaves_explicit_upgrade_control_on(self):
  e,r,n,m=fixture();e.toggle_cattail_land(True);e.toggle_cattail_land(False);self.assertTrue(e.direct_upgrades_active);e.reset_all();self.assertFalse(e.direct_upgrades_active)
 def test_studio_allows_cattail_on_land_without_allowing_other_aquatics(self):
  e,r,n,m=fixture();g=r.game
  with self.assertRaisesRegex(ValueError,'aquatic'):g.place_plant(43,1,2)
  e.toggle_cattail_land(True)
  for kind in (16,19,24):
   with self.assertRaisesRegex(ValueError,'aquatic'):g.place_plant(kind,1,2)
  g._signature=Mock();n.execute=Mock(return_value=0x600000);g.entities=Mock(side_effect=[[],[dict(address=0x600000,type=43,row=1,col=2,id=0x10000,kind='plant')]])
  self.assertEqual(g.place_plant(43,1,2)['type'],43)
 def test_live_pool_formations_waive_only_cattail_lily_support(self):
  from studio_models import formation
  v=dict(version=2,scene=2,stack=False,plants=[dict(type=43,row=3,col=2,imitater=False)])
  with self.assertRaises(ValueError):formation(v)
  self.assertEqual(formation(v,allow_cattail=True)['plants'][0]['type'],43)
  v['plants'][0]['type']=0
  with self.assertRaises(ValueError):formation(v,allow_cattail=True)
