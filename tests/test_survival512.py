import unittest,struct,tempfile,os
from pathlib import Path
from unittest.mock import Mock,patch
from types import SimpleNamespace
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_EBP
import test_extensions57
from test_verified_engine import fixture
import extra_controls

class SurvivalRegression(unittest.TestCase):
 def test_native_repick_block_reproduces_old_null_button_and_valid_cards_preserve_it(self):
  # GOTY instructions +8EAF0..+8EB0D, the repick cooldown-copy block.
  code=bytes.fromhex('8b48348bd1c1e2042bd18d8c95bc0000008a504988512c8b4024894130')
  for seed in [-1,0,40,47]:
   u=Uc(UC_ARCH_X86,UC_MODE_32)
   for a in (0x100000,0x200000,0x300000):u.mem_map(a,0x10000)
   u.mem_write(0x100000,code);u.mem_write(0x200034,struct.pack('<i',seed));u.mem_write(0x3000b0,struct.pack('<I',0x12345678))
   u.reg_write(UC_X86_REG_EAX,0x200000);u.reg_write(UC_X86_REG_EBP,0x300000);u.emu_start(0x100000,0x100000+len(code))
   self.assertEqual(struct.unpack('<I',u.mem_read(0x3000b0,4))[0],0 if seed==-1 else 0x12345678)
 def test_partial_pages_and_single_card_decks_never_write_negative_types(self):
  f=test_extensions57.SeedPageTests();f.setUp()
  for cards in [[0],[0,1,2],list(range(47))]:
   d=f.deck;d.start(cards)
   for page in range(d.pages):
    d.show(page);types=[c['type']for c in f.g.seed_bank()];self.assertEqual(len(types),len(set(types)));self.assertTrue(all(0<=t<48 for t in types))
   d.stop()
 def test_repick_lifecycle_does_not_restore_over_the_native_chooser(self):
  f=test_extensions57.SeedPageTests();f.setUp();f.deck.start([0,1,2]);f.f.m.put(f.f.app+0x91c,2);before=dict(f.f.m.bytes)
  self.assertFalse(f.deck.poll());f.deck.stop();self.assertEqual(f.f.m.bytes,before)
 def test_invalid_initial_seed_bank_refused(self):
  f=test_extensions57.SeedPageTests();f.setUp();f.f.m.put(0x90005c,-1)
  with self.assertRaisesRegex(ValueError,'invalid seed'):f.deck.start([0,1,2])

class Graves(unittest.TestCase):
 def setUp(self):
  self.e,self.r,self.n,self.m=fixture();self.g=self.r.game;self.data=0x900000
  self.m.put(0x200134,self.data);self.m.put(0x200138,3)
  a,h=extra_controls.GRID_ITEMS['goty'][1:];self.r.image[a:a+8]=bytes.fromhex(h);self.r.native_action=Mock()
  for i,kind in enumerate([1,2,3]):
   p=self.data+i*0xec;self.m.put(p+4,0x200000);self.m.put(p+8,kind);self.m.put(p+0xe8,0x10000+i)
 def test_only_graves_use_native_cleanup(self):
  self.assertEqual(extra_controls.remove_graves(self.r),1);self.r.native_action.assert_called_once_with([(0x502b0,'esi',self.data,[])])
 def test_foreign_grave_or_invalid_bound_refuses_all_calls(self):
  self.m.put(self.data+4,0x500000)
  with self.assertRaises(RuntimeError):extra_controls.remove_graves(self.r)
  self.r.native_action.assert_not_called()
  self.m.put(0x200138,5000)
  with self.assertRaises(RuntimeError):extra_controls.remove_graves(self.r)
 def test_dead_and_free_slots_are_preserved(self):
  self.m.put(self.data+0x20,1,'<B');self.assertEqual(extra_controls.remove_graves(self.r),0);self.r.native_action.assert_not_called()

class SaveGuide(unittest.TestCase):
 def test_overview_reports_each_save_independently_without_writes(self):
  import edition_saves as s
  with tempfile.TemporaryDirectory()as directory,patch.dict(os.environ,PROGRAMDATA=directory):
   for kind,stage in [('legacy',10),('goty',12),('classic',14)]:
    folder=s.parent()/'PlantsVsZombies/userdata'if kind=='legacy'else s.save_root(kind)/'userdata';folder.mkdir(parents=True);(folder/'user1.dat').write_bytes(struct.pack('<ii',12,stage))
   before={str(p):p.read_bytes()for p in Path(directory).rglob('*')if p.is_file()};info=s.progress_overview()
   self.assertEqual([r['stage']for r in info['rows']],[10,12,14]);self.assertEqual(before,{str(p):p.read_bytes()for p in Path(directory).rglob('*')if p.is_file()})
 def test_closing_studio_hides_without_reset_or_stopping_overlay(self):
  from studio_ui import LawnStudio
  w=SimpleNamespace(hide=Mock(),owner=SimpleNamespace(engine=Mock()),session=Mock());ev=Mock();LawnStudio.closeEvent(w,ev)
  w.hide.assert_called_once();ev.ignore.assert_called_once();w.session.reset.assert_not_called()
