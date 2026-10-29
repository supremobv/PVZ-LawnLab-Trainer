import io,json,os,struct,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import test_studio
from seed_pages import SeedDeck
import resource_mods as mods

class SeedPageTests(unittest.TestCase):
 def setUp(self):
  self.f=test_studio.EditorTests();self.f.setUp();self.g=self.f.g;self.g.engine.build_label='GOTY 1.2.0.1073';self.deck=SeedDeck(self.g)
  self.f.m.put(self.f.b+0x150,0xA00000)
  self.f.m.put(0x900000+0x28+0x48,1);self.f.m.put(0x900000+0x78+0x48,1)
 def test_pages_use_only_existing_slots_and_restore_native_cards(self):
  original=[c['type']for c in self.g.seed_bank()];self.assertEqual(self.deck.start(list(range(8))),4)
  self.deck.step(1);self.assertEqual([c['type']for c in self.g.seed_bank()],[2,3]);self.assertEqual(self.g.read(0x900024),2)
  self.deck.stop();self.assertEqual([c['type']for c in self.g.seed_bank()],original)
 def test_hidden_cooldowns_advance_with_game_ticks_not_wall_time(self):
  self.deck.start(list(range(4)));self.f.m.put(0x900000+0x28+0x24,10);self.f.m.put(0x900000+0x28+0x28,100);self.f.m.put(0x900000+0x28+0x48,0,'<B');self.f.m.put(0x900000+0x28+0x49,1,'<B')
  self.deck.step(1);self.f.m.put(self.f.b+0x5580,50);self.deck.step(1);self.assertEqual(self.deck.read_packet(0)['elapsed'],60);self.assertEqual(self.deck.read_packet(0)['active'],0)
  self.deck.step(1);self.f.m.put(self.f.b+0x5580,150);self.deck.step(1);self.assertEqual(self.deck.read_packet(0)['active'],1)
 def test_held_seed_refuses_a_page_change_without_writes(self):
  self.deck.start(list(range(4)));self.f.m.put(0xA00030,1);before=dict(self.f.m.bytes)
  with self.assertRaisesRegex(RuntimeError,'held'):self.deck.step(1)
  self.assertEqual(self.f.m.bytes,before)
 def test_external_seed_edit_is_not_overwritten_on_stop(self):
  self.deck.start(list(range(4)));self.f.m.put(0x90005C,7);self.deck.stop();self.assertEqual(self.g.read(0x90005C),7)
 def test_last_page_has_only_valid_native_seed_types(self):
  self.deck.start([0,1,2]);self.deck.step(1);self.assertEqual([c['type']for c in self.g.seed_bank()],[2,0]);self.assertEqual(self.deck.read_packet(1)['active'],1)
 def test_normal_seed_editor_and_reset_respect_deck_ownership(self):
  self.deck.start([0,1,2]);
  with self.assertRaisesRegex(RuntimeError,'scrolling'):self.g.set_seed(1,4)
  self.g.reset();self.assertFalse(self.deck.active)
 def test_duplicates_and_special_modes_are_refused(self):
  with self.assertRaises(ValueError):self.deck.start([0,0])
  self.f.m.put(self.f.app+0x918,16)
  with self.assertRaisesRegex(ValueError,'normal Adventure'):self.deck.start([0,1])

class ResourceTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.env=patch.dict(os.environ,LOCALAPPDATA=str(self.root/'local'));self.env.start();self.game=self.root/'game';self.game.mkdir();self.running=patch('resource_mods.running',return_value=False);self.running.start();self.edition=patch('resource_mods.game_edition',return_value='goty');self.edition.start()
 def tearDown(self):self.edition.stop();self.running.stop();self.env.stop();self.temp.cleanup()
 def pack(self,extra=None,editions=None):
  p=self.root/'pack.zip';info=dict(version=1,name='Test resource',author='Test author',source='https://example.org/mod',license='MIT',description='Test',editions=editions or['goty'],files=['properties/test.txt'])
  with zipfile.ZipFile(p,'w')as z:
   z.writestr('lawnlab-mod.json',json.dumps(info));z.writestr('LICENSE.txt','MIT test license');z.writestr('resources/properties/test.txt','new text')
   if extra:z.writestr(extra,'payload')
  return p
 def test_credited_pack_install_and_restore_preserve_original(self):
  p=self.game/'properties/test.txt';p.parent.mkdir();p.write_text('old text');code=mods.import_pack(self.pack());key=mods.apply_pack(self.game,code);self.assertEqual(p.read_text(),'new text');self.assertEqual(mods.installed()[key]['metadata']['author'],'Test author');mods.restore(key);self.assertEqual(p.read_text(),'old text')
 def test_new_override_is_removed_on_restore(self):
  code=mods.import_pack(self.pack());key=mods.apply_pack(self.game,code);mods.restore(key);self.assertFalse((self.game/'properties/test.txt').exists())
 def test_loose_resource_import_keeps_author_and_skips_executable(self):
  source=self.root/'incoming';(source/'properties').mkdir(parents=True);(source/'properties/example.txt').write_text('custom');(source/'mod.dll').write_bytes(b'not a resource')
  metadata=dict(name='Loose pack',author='Original creator',source='https://example.org/original',license='MIT',description='Resource pack',editions=['goty'])
  code=mods.import_folder(source,metadata,'MIT permission text');info=next(x for x in mods.packs()if x['id']==code);self.assertEqual(info['author'],'Original creator');self.assertEqual(info['files'],['properties/example.txt'])
 def test_executables_and_traversal_are_not_resource_packs(self):
  for extra in('resources/payload.dll','../outside.txt','C:/outside.txt'):
   with self.assertRaises(ValueError):mods.import_pack(self.pack(extra))
  for name in('../x.png','images/../../x.png','C:/x.png','images/link.dll','properties/partner.xml'):
   with self.assertRaises(ValueError):mods.relative(name)
 def test_wrong_edition_and_running_game_refuse_changes(self):
  code=mods.import_pack(self.pack(editions=['classic']))
  with self.assertRaisesRegex(ValueError,'compatibility'):mods.apply_pack(self.game,code)
  with patch('resource_mods.running',return_value=True):
   with self.assertRaisesRegex(RuntimeError,'Close both'):mods.apply_files(self.game,{'properties/x.txt':b'x'},dict(name='x',author='a'))
 def test_conflicting_pack_and_external_edits_are_preserved(self):
  code=mods.import_pack(self.pack());key=mods.apply_pack(self.game,code)
  with self.assertRaisesRegex(ValueError,'owns'):mods.apply_pack(self.game,code)
  p=self.game/'properties/test.txt';p.write_text('external edit')
  with self.assertRaisesRegex(RuntimeError,'outside LawnLab'):mods.restore(key)
  self.assertEqual(p.read_text(),'external edit')
 def test_write_failure_rolls_back_and_removes_install_journal(self):
  p=self.game/'properties/test.txt';p.parent.mkdir();p.write_bytes(b'original');real=mods.atomic_bytes
  def fail(path,data):
   if Path(path)==p and data==b'new':raise OSError('disk failure')
   return real(path,data)
  with patch('resource_mods.atomic_bytes',side_effect=fail):
   with self.assertRaises(OSError):mods.apply_files(self.game,{'properties/test.txt':b'new'},dict(name='x',author='a'))
  self.assertEqual(p.read_bytes(),b'original');self.assertFalse(mods.installed())
 def test_xml_external_entities_are_refused(self):
  with self.assertRaises(ValueError):mods.validate_content('properties/x.xml',b'<!DOCTYPE x [<!ENTITY y SYSTEM "file:///x">]><x/>')
  with self.assertRaises(ValueError):mods.validate_content('properties/x.xml',b'<Resources><Image path="//remote/x"/></Resources>')
 def test_restore_failure_reinstates_the_installed_pack(self):
  p=self.game/'properties/test.txt';p.parent.mkdir();p.write_bytes(b'old');key=mods.apply_files(self.game,{'properties/test.txt':b'new'},dict(name='x',author='a'));real=mods.atomic_bytes
  def fail(path,data):
   if Path(path)==p and data==b'old':raise OSError('restore failure')
   return real(path,data)
  with patch('resource_mods.atomic_bytes',side_effect=fail):
   with self.assertRaises(OSError):mods.restore(key)
  self.assertEqual(p.read_bytes(),b'new');self.assertIn(key,mods.installed())
 def test_note_editors_render_separate_masks_without_changing_game_files(self):
  from PySide6.QtWidgets import QApplication
  from PySide6.QtGui import QImage
  from PySide6.QtCore import Qt
  from note_editor import render_note,png
  app=QApplication.instance()or QApplication([]);image=QImage(529,359,QImage.Format.Format_RGB32);image.fill(Qt.GlobalColor.black)
  names=['ZombieNoteHelp.png','Credits_ZombieNote.png'];(self.game/'images').mkdir()
  for name in names:(self.game/'images'/name).write_bytes(png(image))
  before=(self.game/'images'/names[0]).read_bytes();help_files,_=render_note(self.game,'help','Custom help');credit_files,_=render_note(self.game,'credits','Custom invitation')
  self.assertNotEqual(set(help_files),set(credit_files));self.assertEqual((self.game/'images'/names[0]).read_bytes(),before)
  with self.assertRaises(ValueError):render_note(self.game,'help','  ')
 def test_classic_pak_layers_apply_and_restore_in_reverse_order(self):
  from pak_resources import encode,decode
  original=encode([('properties/a.txt',b'base a',b'\0'*8),('properties/b.txt',b'base b',b'\0'*8)]);p=self.game/'main.pak';p.write_bytes(original)
  with patch('resource_mods.game_edition',return_value='classic'):
   first=mods.apply_files(self.game,{'properties/a.txt':b'mod a'},dict(name='a',author='a'));second=mods.apply_files(self.game,{'properties/b.txt':b'mod b'},dict(name='b',author='b'))
   self.assertEqual(mods.read_resource(self.game,'properties/a.txt'),b'mod a');self.assertEqual(mods.read_resource(self.game,'properties/b.txt'),b'mod b')
   with self.assertRaisesRegex(RuntimeError,'newer Classic'):mods.restore(first)
   mods.restore(second);self.assertEqual(mods.read_resource(self.game,'properties/b.txt'),b'base b');mods.restore(first)
  self.assertEqual(p.read_bytes(),original)
 def test_pak_index_bounds_and_identity_roundtrip(self):
  from pak_resources import encode,decode
  blob=encode([('images/x.png',b'abc',b'12345678')]);self.assertEqual(encode(decode(blob)),blob)
  with self.assertRaises(ValueError):decode(blob[:-1])

class SaveIsolationTests(unittest.TestCase):
 def test_startup_player_list_is_edition_specific_and_legacy_list_is_restored(self):
  import edition_saves as saves
  with tempfile.TemporaryDirectory()as folder,patch.dict(os.environ,PROGRAMDATA=folder,LOCALAPPDATA=folder):
   shared=saves.parent()/'PlantsVsZombies/userdata/users.dat';target=saves.save_root('goty')/'userdata/users.dat';shared.parent.mkdir(parents=True);target.parent.mkdir(parents=True);shared.write_bytes(b'legacy users');target.write_bytes(b'goty users')
   with saves.LaunchSummary('goty'):
    self.assertEqual(shared.read_bytes(),b'goty users');shared.write_bytes(b'new goty sequence')
   self.assertEqual(shared.read_bytes(),b'legacy users');self.assertEqual(target.read_bytes(),b'new goty sequence')
 def test_paths_preserve_original_native_string_length(self):
  from edition_saves import BUILDS
  self.assertTrue(all(len(v['product'])==len('PlantsVsZombies')for v in BUILDS.values()))
 def test_goty_native_interleaved_achievement_save_is_verified(self):
  import edition_saves as saves
  with tempfile.TemporaryDirectory()as folder:
   root=Path(folder);(root/'userdata').mkdir();data=bytearray(860);struct.pack_into('<i',data,0,12);struct.pack_into('<i',data,816,0);data[820+6]=data[820+7]=1;(root/'userdata/user1.dat').write_bytes(data)
   game=SimpleNamespace(read=lambda *a:1,user=lambda:0x1000);engine=SimpleNamespace(build_label='GOTY 1.2.0.1073',runtime=SimpleNamespace(game=game))
   with patch('edition_saves.root_info',return_value=(0,str(root))):
    self.assertTrue(saves.verify_achievements(engine,{3:True}))
    with self.assertRaisesRegex(RuntimeError,'did not persist'):saves.verify_achievements(engine,{4:True})
 def test_classic_truncated_save_is_refused_as_goty(self):
  import edition_saves as saves
  with tempfile.TemporaryDirectory()as folder:
   root=Path(folder);(root/'userdata').mkdir();data=bytearray(820);struct.pack_into('<i',data,0,12);(root/'userdata/user1.dat').write_bytes(data)
   game=SimpleNamespace(read=lambda *a:1,user=lambda:0x1000);engine=SimpleNamespace(build_label='GOTY 1.2.0.1073',runtime=SimpleNamespace(game=game))
   with patch('edition_saves.root_info',return_value=(0,str(root))):
    with self.assertRaisesRegex(RuntimeError,'section is missing'):saves.verify_achievements(engine,{0:True})

