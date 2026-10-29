import os,tempfile,threading,time,unittest
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from PySide6.QtCore import QPoint,QSettings
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from seed_overlay import SeedOverlay,OverlayPreferences
from note_editor import png,render_note,NOTES

TEXT='Welcome to the practice lawn. Choose your plants, plan a formation, and enjoy your next Adventure!\n\n- The LawnLab team'

class OverlayTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance()or QApplication([])
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.preferences=OverlayPreferences(QSettings(str(Path(self.tmp.name)/'overlay.ini'),QSettings.Format.IniFormat))
  self.studio=SimpleNamespace(owner=SimpleNamespace(engine=SimpleNamespace(is_connected=True)))
  self.o=SeedOverlay(self.studio,self.preferences);self.o.deck=SimpleNamespace(active=True,page=0,pages=5,poll=lambda:True);self.o.hwnd=1
  def rect(hwnd,p):p._obj.right=800;p._obj.bottom=600;return 1
  def origin(hwnd,p):p._obj.x=100;p._obj.y=200;return 1
  self.o.user=SimpleNamespace(IsIconic=lambda _:False,GetClientRect=rect,ClientToScreen=origin,GetForegroundWindow=lambda:1,GetWindowThreadProcessId=lambda *a:None,UnhookWindowsHookEx=Mock())
 def test_busy_controller_does_not_wait_for_its_operation_lock(self):
  self.studio.owner.busy=True;self.o.deck.poll=Mock(side_effect=AssertionError('UI must not wait for worker'))
  self.o.sync();self.o.deck.poll.assert_not_called();self.assertIsNone(self.o.bounds);self.assertTrue(self.o.deck.active)
 def tearDown(self):self.o.stop();self.o.close();self.tmp.cleanup()
 def test_hidden_bar_retains_card_bounds_and_wheel_input(self):
  self.o.hook=123;self.o.set_bar_visible(False);self.o.sync()
  self.assertFalse(self.o.isVisible());self.assertIsNotNone(self.o.bounds);self.assertEqual(self.o.hook,123)
  self.assertEqual(self.o.wheel_direction(0x20A,-120,250,240,1),1)
  self.o.user.UnhookWindowsHookEx.assert_not_called()
 def test_wheel_never_intercepts_outside_cards_or_another_foreground_window(self):
  self.o.sync()
  for args in [(0x20A,120,250,500,1),(0x20A,120,250,240,2),(0x201,120,250,240,1),(0x20A,0,250,240,1)]:self.assertEqual(self.o.wheel_direction(*args),0)
 def test_drag_position_survives_sync_and_settings_reload(self):
  self.o.sync();self.o.logical_scale=1;self.o.begin_drag(QPoint(100,100));self.o.drag_to(QPoint(145,135));self.o.end_drag()
  self.assertEqual(self.preferences.position,(155,121));self.o.sync();self.assertEqual(self.preferences.position,(155,121))
  reloaded=OverlayPreferences(QSettings(str(Path(self.tmp.name)/'overlay.ini'),QSettings.Format.IniFormat));self.assertEqual(reloaded.position,(155,121))
 def test_position_is_clamped_to_the_game_and_show_does_not_stop_deck(self):
  self.o.set_position(-100,10000);self.assertEqual(self.preferences.position,(0,574))
  self.o.set_bar_visible(False);self.o.set_bar_visible(True);self.assertTrue(self.o.deck.active);self.assertTrue(self.o.isVisible())

class AtomicPermissionTests(unittest.TestCase):
 def test_access_denied_is_reported_after_one_attempt_and_preserves_original(self):
  from studio_storage import atomic_bytes
  with tempfile.TemporaryDirectory()as folder:
   target=Path(folder)/'note.png';target.write_bytes(b'original')
   with patch('studio_storage.os.open',side_effect=PermissionError('denied'))as open_file:
    with self.assertRaisesRegex(PermissionError,'administrator'):atomic_bytes(target,b'new')
   self.assertEqual(open_file.call_count,1);self.assertEqual(target.read_bytes(),b'original')
 def test_only_name_collisions_retry_with_a_finite_bound(self):
  from studio_storage import atomic_bytes
  with tempfile.TemporaryDirectory()as folder:
   with patch('studio_storage.os.open',side_effect=FileExistsError('collision'))as open_file:
    with self.assertRaisesRegex(FileExistsError,'8 attempts'):atomic_bytes(Path(folder)/'note.png',b'new')
   self.assertEqual(open_file.call_count,8)
 def test_administrator_restart_cancellation_keeps_the_current_window(self):
  import admin_restart
  shell=SimpleNamespace(IsUserAnAdmin=Mock(return_value=False),ShellExecuteW=Mock(return_value=5));owner=SimpleNamespace(busy=False,engine=SimpleNamespace(is_connected=False),close=Mock())
  with patch('ctypes.WinDLL',return_value=shell):
   with self.assertRaisesRegex(RuntimeError,'remains open'):admin_restart.restart(owner)
  owner.close.assert_not_called();self.assertEqual(shell.ShellExecuteW.call_args.args[1],'runas')
 def test_administrator_restart_requires_disconnection(self):
  import admin_restart
  owner=SimpleNamespace(busy=False,engine=SimpleNamespace(is_connected=True))
  with patch('ctypes.WinDLL')as win:
   with self.assertRaisesRegex(RuntimeError,'Disconnect'):admin_restart.restart(owner)
   win.assert_not_called()

class NoteUITests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance()or QApplication([])
 def setUp(self):
  from lawnlab import LawnLab
  from studio_ui import LawnStudio
  from studio_storage import Documents,SaveBackups
  from test_interface import FakeEngine
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.game=self.root/'game';(self.game/'images').mkdir(parents=True)
  image=QImage(529,323,QImage.Format.Format_RGB32);image.fill(0)
  for name in NOTES['help']:(self.game/name).write_bytes(png(image))
  self.settings_patch=patch('extension_ui.QSettings',return_value=QSettings(str(self.root/'notes.ini'),QSettings.Format.IniFormat));self.settings_patch.start();self.recovery_patch=patch('resource_mods.recover_unmodified_installations',return_value=[]);self.recovery_patch.start();self.edition_patch=patch('resource_mods.game_edition',return_value='goty');self.edition_patch.start()
  self.owner=LawnLab(FakeEngine());self.owner.timer.stop();self.studio=LawnStudio(self.owner,documents=Documents(self.root/'docs'),backups=SaveBackups(root=self.root/'backups'))
  self.panel=self.studio.extensions;self.panel.game_folder.setText(str(self.game));self.panel.note_edits['help'].setPlainText(TEXT);self.panel.note_fonts['help'].setCurrentText('Segoe Script')
 def tearDown(self):self.owner.pool.waitForDone(5000);self.app.processEvents();self.studio.close();self.owner.close();self.settings_patch.stop();self.recovery_patch.stop();self.edition_patch.stop();self.tmp.cleanup()
 def wait(self):
  deadline=time.monotonic()+5
  while self.owner.busy and time.monotonic()<deadline:self.app.processEvents();time.sleep(.005)
  self.app.processEvents();self.assertFalse(self.owner.busy,'Note job did not finish')
 def test_multiline_preview_reserves_the_complete_pixmap_height(self):
  with patch('note_editor.render_note',wraps=render_note)as render:
   self.panel.preview_note('help');self.assertEqual(render.call_args.args[3],'Segoe Script')
  preview=self.panel.note_previews['help'];self.assertFalse(preview.pixmap().isNull())
  self.assertGreater(preview.height(),80);self.assertEqual(preview.height(),preview.pixmap().height());self.assertEqual(preview.width(),preview.pixmap().width())
 def test_apply_renders_on_ui_thread_then_completes_file_worker(self):
  calls=[]
  def install(root,kind,files):calls.append((threading.current_thread().ident,set(files)));return 'test-id'
  ui_thread=threading.current_thread().ident
  with patch('resource_mods.running',return_value=False),patch('note_editor.install_note',side_effect=install),patch.object(self.panel,'after_install')as after:
   self.panel.apply_note('help');self.wait();after.assert_called_once()
  self.assertEqual(calls[0][1],set(NOTES['help']));self.assertNotEqual(calls[0][0],ui_thread);self.assertNotIn('Working',self.studio.status.text())
 def test_install_failure_unlocks_buttons_and_reports_the_error(self):
  with patch('resource_mods.running',return_value=False),patch('note_editor.install_note',side_effect=PermissionError('Test destination is read-only')):
   self.panel.apply_note('help');self.wait()
  self.assertIn('read-only',self.studio.status.text());self.assertTrue(all(b.isEnabled()for b in self.studio.buttons if b.text()=='Apply this note (game closed)'))
 def test_font_rendering_in_a_worker_fails_clearly_instead_of_hanging(self):
  errors=[]
  def worker():
   try:render_note(self.game,'help',TEXT)
   except Exception as error:errors.append(str(error))
  thread=threading.Thread(target=worker);thread.start();thread.join(2);self.assertFalse(thread.is_alive());self.assertIn('UI thread',errors[0])
 def test_running_game_refuses_apply_before_starting_any_worker(self):
  with patch('resource_mods.running',return_value=True),patch('note_editor.install_note')as install:
   self.panel.apply_note('help');install.assert_not_called();self.assertFalse(self.owner.busy);self.assertIn('Close both',self.studio.status.text())
 def test_note_target_follows_the_connected_classic_edition(self):
  classic=self.root/'classic';self.panel.paths['classic'].setText(str(classic/'PlantsVsZombies.exe'));self.owner.engine.build_label='Classic 1.0.0.1051'
  with patch('resource_mods.game_edition',return_value='classic'):
   self.panel.follow_connected_game();self.assertEqual(self.panel.kind.currentText(),'Classic');self.assertEqual(Path(self.panel.target()),classic);self.assertIn('main.pak',self.panel.target_status.text())
 def test_mismatched_edition_refuses_note_installation(self):
  self.panel.kind.setCurrentText('Classic');self.panel.game_folder.setText(str(self.game))
  with patch('note_editor.install_note')as install:
   self.panel.apply_note('help');install.assert_not_called();self.assertIn('Nothing was changed',self.studio.status.text())
