import hashlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import startup_options as options
from test_verified_engine import fixture

class RememberedLimbo(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.file=Path(self.tmp.name)/'startup.json';self.mock=patch('startup_options.state_file',return_value=self.file);self.mock.start()
 def tearDown(self):self.mock.stop();self.tmp.cleanup()
 def test_preferences_are_separate_for_each_edition(self):
  options.save('goty',True);self.assertTrue(options.remembered('goty'));self.assertFalse(options.remembered('classic'))
  options.save('classic',True);options.save('goty',False);self.assertTrue(options.remembered('classic'));self.assertFalse(options.remembered('goty'))
 def test_remembered_limbo_survives_reset_but_explicit_disable_clears_preference(self):
  e,r,backend,m=fixture();rva,old,new=options.LIMBO['goty'];e.set_limbo_remembered(True)
  self.assertTrue(options.remembered('goty'));self.assertEqual(m.read_bytes(e.base_address+rva,3),new)
  e.reset_all();self.assertTrue(e.limbo_page_active);self.assertEqual(m.read_bytes(e.base_address+rva,3),new)
  e.toggle_limbo_page(False);self.assertFalse(options.remembered('goty'));self.assertFalse(e._remembered_limbo);self.assertEqual(m.read_bytes(e.base_address+rva,3),old)
 def test_attach_adopts_only_the_known_live_patch_without_rewriting_it(self):
  e,r,b,m=fixture();options.save('goty',True);rva,old,new=options.LIMBO['goty'];m.write_bytes(e.base_address+rva,new,3);before=len(b.writes)
  options.attach(r);self.assertTrue(e.limbo_page_active);self.assertTrue(e._remembered_limbo);self.assertIn('limbo_page',r.manager.active);self.assertEqual(len(b.writes),before)
 def test_unknown_limbo_code_is_refused(self):
  e,r,b,m=fixture();rva,old,new=options.LIMBO['goty'];m.write_bytes(e.base_address+rva,b'\xcc'*3,3)
  with self.assertRaisesRegex(RuntimeError,'Unexpected'):options.attach(r)
 def test_classic_normalization_preserves_unknown_changes_for_full_hash_rejection(self):
  rva,old,new=options.LIMBO['classic'];original=bytearray(0x30000);original[rva:rva+3]=old;live=bytearray(original);live[rva:rva+3]=new
  self.assertEqual(options.normalize_classic(bytes(live)),bytes(original));live[0x1000]=0xcc
  self.assertNotEqual(hashlib.sha256(options.normalize_classic(bytes(live))).digest(),hashlib.sha256(original).digest())
 def test_non_boolean_preferences_are_rejected(self):
  for value in (1,'yes',None):
   with self.assertRaises(ValueError):options.save('goty',value)

