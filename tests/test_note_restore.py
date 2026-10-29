"""Original Help/credits restoration uses exact backups, not recreated text."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtGui import QImage
from note_editor import NOTES,png,install_note,restore_notes
import resource_mods as mods

class OriginalNotes(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.game=self.base/'game';self.game.mkdir();self.edition='goty'
  self.patches=[patch('resource_mods.library',return_value=self.base/'mods'),patch('resource_mods.running',return_value=False),patch('resource_mods.game_edition',side_effect=lambda root:self.edition)]
  for p in self.patches:p.start()
  self.original={}
  for i,name in enumerate(n for pair in NOTES.values()for n in pair):
   image=QImage(80,60,QImage.Format.Format_RGB32);image.fill(0xff101010+i);data=png(image);self.original[name]=data
   path=self.game/name;path.parent.mkdir(exist_ok=True);path.write_bytes(data)
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()
 def custom(self,kind):
  image=QImage(80,60,QImage.Format.Format_RGB32);image.fill(0xffdddddd)
  return {name:png(image)for name in NOTES[kind]}
 def test_help_and_credits_restore_independently_to_exact_original_bytes(self):
  install_note(self.game,'help',self.custom('help'));install_note(self.game,'credits',self.custom('credits'))
  result=restore_notes(self.game,('help',));self.assertEqual(result['restored'],1)
  for name in NOTES['help']:self.assertEqual((self.game/name).read_bytes(),self.original[name])
  for name in NOTES['credits']:self.assertEqual((self.game/name).read_bytes(),self.custom('credits')[name])
  restore_notes(self.game,('credits',))
  for name,data in self.original.items():self.assertEqual((self.game/name).read_bytes(),data)
  self.assertFalse(mods.installed())
 def test_classic_both_restores_notes_in_reverse_order_and_preserves_original_archive(self):
  from pak_resources import encode
  self.edition='classic';pak=self.game/'main.pak';original=encode([(name,data,b'\0'*8)for name,data in self.original.items()]);pak.write_bytes(original)
  install_note(self.game,'help',self.custom('help'));install_note(self.game,'credits',self.custom('credits'));before=pak.read_bytes()
  with self.assertRaisesRegex(RuntimeError,'Restore both'):restore_notes(self.game,('help',))
  self.assertEqual(pak.read_bytes(),before)
  result=restore_notes(self.game,('help','credits'));self.assertEqual(result['restored'],2);self.assertEqual(pak.read_bytes(),original)
  for kind in NOTES:
   for name in NOTES[kind]:self.assertEqual(result['previews'][kind][name],self.original[name])
 def test_no_known_note_backup_never_overwrites_any_resources(self):
  result=restore_notes(self.game,('help','credits'));self.assertEqual(result['restored'],0);self.assertIn('left unchanged',result['message'])
  for name,data in self.original.items():self.assertEqual((self.game/name).read_bytes(),data)
 def test_corrupt_original_backup_refuses_before_restoring_either_note(self):
  first=install_note(self.game,'help',self.custom('help'));install_note(self.game,'credits',self.custom('credits'))
  backup=mods.library()/'backups'/first/NOTES['help'][0];backup.write_bytes(b'corrupted')
  with self.assertRaisesRegex(RuntimeError,'checksum'):restore_notes(self.game,('help','credits'))
  for kind in NOTES:
   for name,data in self.custom(kind).items():self.assertEqual((self.game/name).read_bytes(),data)
 def test_outside_edits_are_preserved(self):
  install_note(self.game,'help',self.custom('help'));p=self.game/NOTES['help'][0];p.write_bytes(b'external')
  with self.assertRaisesRegex(RuntimeError,'outside LawnLab'):restore_notes(self.game,('help',))
  self.assertEqual(p.read_bytes(),b'external');self.assertTrue(mods.installed())
