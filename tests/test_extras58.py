"""Native scale semantics, per-entity ownership and local Almanac boundaries."""
import math,struct,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from types import SimpleNamespace
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import *
import capstone
from extra_controls import PATCHES,PLANT_ORIGINAL,plant_scale_code,percent,ZombieSizes
from test_verified_engine import fixture

class NativeScale(unittest.TestCase):
 def run_scale(self,kind='goty',ui=3,mode=0,matching=True):
  u=Uc(UC_ARCH_X86,UC_MODE_32)
  for address in (0x100000,0x200000,0x300000,0x400000,0x800000):u.mem_map(address,0x10000)
  p=lambda value:struct.pack('<I',value)
  u.mem_write(0x300000,p(0x200000));u.mem_write(0x300004,p(0x500000))
  ui_off,mode_off,board_off=(0x7fc,0x7f8,0x768)if kind=='classic'else(0x91c,0x918,0x868)
  for off,value in [(ui_off,ui),(mode_off,mode),(board_off,0x500000 if matching else 0x600000)]:u.mem_write(0x200000+off,p(value))
  u.mem_write(0x107000,struct.pack('<f',2));u.mem_write(0x105000,struct.pack('<f',-1.5));u.mem_write(0x80f01c,struct.pack('<f',.75))
  u.reg_write(UC_X86_REG_EAX,0xcafebabe);u.reg_write(UC_X86_REG_EBX,0x300000);u.reg_write(UC_X86_REG_EBP,0x400000);u.reg_write(UC_X86_REG_ESP,0x80f000);u.reg_write(UC_X86_REG_EFLAGS,0x246)
  code=b'\xd9\x05'+p(0x105000)+plant_scale_code(0x107000,0x100006,0x101800,kind)
  u.mem_write(0x100000,code);u.emu_start(0x100000,0x101800,count=200)
  self.assertEqual(u.reg_read(UC_X86_REG_EAX),0xcafebabe);self.assertEqual(u.reg_read(UC_X86_REG_ESP),0x80f000)
  self.assertEqual(u.reg_read(UC_X86_REG_EFLAGS),0x246)
  self.assertEqual((u.reg_read(UC_X86_REG_FPSW)>>11)&7,0)
  return [struct.unpack('<f',u.mem_read(0x400000+off,4))[0]for off in (0x24,0x34)]
 def test_scale_multiplies_both_axes_without_changing_flags_or_stack(self):
  for kind in ('goty','classic'):self.assertEqual(self.run_scale(kind),[-3,1.5])
 def test_scale_leaves_almanac_gardens_previews_and_foreign_boards_unchanged(self):
  for args in [dict(ui=1),dict(ui=2),dict(mode=43),dict(mode=50),dict(matching=False)]:self.assertEqual(self.run_scale(**args),[-1.5,.75])
 def test_patch_spans_cover_complete_instructions(self):
  md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
  for kind,groups in PATCHES.items():
   for spans in groups.values():
    for offset,old,new in spans:
     self.assertEqual(len(bytes.fromhex(old)),len(bytes.fromhex(new)))
     self.assertEqual(sum(i.size for i in md.disasm(bytes.fromhex(old),offset)),len(bytes.fromhex(old)))
  self.assertEqual(sum(i.size for i in md.disasm(PLANT_ORIGINAL,0)),len(PLANT_ORIGINAL))
 def test_classic_almanac_shown_predicate_pops_its_stack_argument(self):
  code=bytes.fromhex(PATCHES['classic']['almanac_reveal'][2][2]);ops=list(capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32).disasm(code,0))
  self.assertEqual((ops[1].mnemonic,ops[1].op_str),('ret','4'))
 def test_size_limits_reject_bool_float_nan_and_unbounded_values(self):
  for value in [True,1.5,float('nan'),24,301,-1]:
   with self.assertRaises(ValueError):percent(value)
  for value in (25,100,300):self.assertEqual(percent(value),value)

class ZombieOwnership(unittest.TestCase):
 def setUp(self):
  self.e,self.r,self.b,self.m=fixture();self.g=self.r.game;self.s=ZombieSizes(self.g)
  self.m.put(0x2000ac,1);self.address=0x510000;self.m.put(self.address+0x164,0x10000);self.m.put(self.address+0x11c,.5,'<f')
 def size(self):return self.g.read(self.address+0x11c,'float')
 def test_native_small_zombie_scale_is_relative_and_does_not_compound(self):
  self.s.apply(200);self.assertEqual(self.size(),1)
  self.s.apply(200);self.assertEqual(self.size(),1)
  self.s.apply(50);self.assertEqual(self.size(),.25)
  self.s.restore();self.assertEqual(self.size(),.5)
 def test_recycled_slot_never_receives_an_old_zombie_scale(self):
  self.s.apply(200);self.m.put(self.address+0x164,0x20000);self.m.put(self.address+0x11c,.75,'<f');self.s.restore();self.assertEqual(self.size(),.75)
 def test_external_size_change_is_preserved_on_restore(self):
  self.s.apply(200);self.m.put(self.address+0x11c,.8,'<f');self.s.restore();self.assertAlmostEqual(self.size(),.8)
 def test_invalid_native_size_makes_no_partial_updates(self):
  self.m.put(self.address+0x11c,float('nan'),'<f')
  with self.assertRaises(RuntimeError):self.s.apply(200)
  self.assertTrue(math.isnan(self.size()))
 def test_menu_cleanup_does_not_write_to_the_previous_lawn(self):
  self.s.apply(200);self.m.put(0x10091c,1);self.s.restore();self.assertEqual(self.size(),1);self.assertFalse(self.s.saved)

class LauncherQuoting(unittest.TestCase):
 def test_classic_keeps_verified_application_but_avoids_quoted_wrapper_argv(self):
  from edition_saves import _start_game as start_game
  def short_name(source,buffer,size):buffer.value=r'C:\GAMES\PLANTS~1\PLANTS~1.EXE';return len(buffer.value)
  kernel=SimpleNamespace(GetShortPathNameW=Mock(side_effect=short_name));path=Path(r'C:\Games\Plants Vs Zombies\PlantsVsZombies.exe')
  with patch('ctypes.WinDLL',return_value=kernel),patch('subprocess.Popen')as launch:
   start_game('classic',path)
   args=launch.call_args
   self.assertNotIn('"',args.args[0]);self.assertNotIn(' ',args.args[0]);self.assertEqual(args.kwargs['executable'],str(path));self.assertEqual(args.kwargs['cwd'],str(path.parent))
 def test_without_short_names_classic_uses_normal_windows_shell_launch(self):
  from edition_saves import _start_game as start_game
  kernel=SimpleNamespace(GetShortPathNameW=Mock(return_value=0));shell=SimpleNamespace(ShellExecuteW=Mock(return_value=33))
  with patch('ctypes.WinDLL',side_effect=[kernel,shell]),patch('subprocess.Popen')as launch:
   start_game('classic',Path(r'C:\Games\Plants Vs Zombies\PlantsVsZombies.exe'));launch.assert_not_called();shell.ShellExecuteW.assert_called_once()
