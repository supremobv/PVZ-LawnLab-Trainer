"""Edition launchers, independent note editors and credited mod management."""
from pathlib import Path
from PySide6.QtCore import Qt,QUrl,QSettings
from PySide6.QtGui import QDesktopServices,QPixmap,QImage
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QLineEdit,QComboBox,QTextEdit,QFontComboBox,QFileDialog,QTableWidgetItem,QDialog,QFormLayout,QDialogButtonBox,QCheckBox
from edition_saves import settings,remember_executable,launch,prepare,save_root
import resource_mods as resources
from companion_mods import CATALOG,install_a11y,launch_a11y,installed_a11y

def remember_connected_edition(engine):
 label=getattr(engine,'build_label','')
 if isinstance(label,str)and label.startswith(('Classic','GOTY')):QSettings('LawnLab','NoteEditor').setValue('target_edition','Classic'if label.startswith('Classic')else'GOTY')

class ExtensionsPanel(QWidget):
 def __init__(self,studio):
  super().__init__();self.studio=studio
  from studio_ui import row,combo,table
  box=QVBoxLayout(self);self.paths={};self.note_settings=QSettings('LawnLab','NoteEditor')
  f=studio.group(box,'GOTY and Classic — separate saves and launchers')
  note=QLabel('<b>Why Adventure can show a different level</b><br>1. Starting an <b>original game EXE</b> directly loads the old, shared save folder. That can show an earlier level.<br>2. These launch buttons, the updated desktop shortcuts, or <b>Play GOTY/Classic - current progress</b> inside each game folder load that edition’s separate save.<br>3. The launcher selects the save folder and exits. <b>You do not need to keep LawnLab or Lawn Studio open.</b><br>4. Connecting LawnLab to an original-EXE session at Main Menu switches to the edition save, which explains the apparent level jump. This does not merge progress.<br>5. GOTY and Classic keep independent progress. Playing one does not advance the other. This prevents Classic from erasing GOTY-only achievements.<br>6. For the same progress every time, always use the same edition launcher. Finish/quit normally so PVZ saves. Do not copy Classic saves over GOTY saves. Use Save backups before restoring or moving progress.');note.setWordWrap(True);f.addRow(note)
  self.progress_status=QLabel('Read progress locations to compare saved stages with the current running game. No save files are changed.');self.progress_status.setWordWrap(True);f.addRow(self.progress_status)
  self.progress_table=table(['Launch / save set','Saved Adventure stage','Save folder']);f.addRow(self.progress_table)
  f.addRow(studio.button('Read save locations and Adventure progress (read-only)',self.read_progress))
  for kind,title in [('goty','GOTY'),('classic','Classic')]:
   edit=QLineEdit(settings().get('executables',{}).get(kind,''));self.paths[kind]=edit
   f.addRow(title+' executable',row(edit,studio.button('Browse',lambda k=kind:self.choose_game(k))))
   f.addRow(row(studio.button('Launch '+title+' with separate saves',lambda k=kind:self.launch_game(k)),QLabel(str(save_root(kind)/'userdata'))))
  f.addRow(studio.button('Prepare / back up separate edition saves',self.prepare_saves))
  import startup_options
  self.remember_limbo={}
  for kind,title in [('goty','GOTY'),('classic','Classic')]:
   check=QCheckBox('Remember Limbo for '+title+' launches (trainer window not required)');check.setChecked(startup_options.remembered(kind));check.toggled.connect(lambda value,k=kind:self.save_limbo(k,value));self.remember_limbo[kind]=check;f.addRow(check)
  label=QLabel('Remembered Limbo is an installation preference, not a native save field. Use the LawnLab game shortcuts so the launch helper applies it and selects the same edition save folder, then exits. Directly starting an original EXE bypasses this.');label.setWordWrap(True);f.addRow(label)
  f=studio.group(box,'Game folder for note/resource edits — close both games before Apply')
  self.kind=combo(['GOTY','Classic']);self.game_folder=QLineEdit();remember_connected_edition(studio.owner.engine);self.kind.setCurrentText(str(self.note_settings.value('target_edition','GOTY')));self.kind.currentIndexChanged.connect(self.select_folder);self.select_folder()
  f.addRow('Target edition',self.kind);f.addRow('Target game folder',row(self.game_folder,studio.button('Browse folder',self.choose_folder)))
  self.target_status=QLabel('');self.target_status.setWordWrap(True);f.addRow(self.target_status);self.game_folder.textChanged.connect(self.check_target);self.check_target()
  notice=QLabel('Windows protects game folders under Program Files. If Apply reports access denied, disconnect LawnLab and use the administrator restart button. Note drafts and fonts are saved locally.');notice.setWordWrap(True);f.addRow(notice)
  f.addRow(studio.button('Restart LawnLab as administrator (Windows prompt)',self.restart_admin))
  self.note_edits={};self.note_fonts={};self.note_previews={}
  for kind,title in [('help','Help note text'),('credits','Credits invitation note text')]:
   f=studio.group(box,title+' — separate editor')
   text=QTextEdit();text.setPlaceholderText('Enter your custom '+title.lower()+'. Line breaks are supported.');text.setMaximumHeight(130);self.note_edits[kind]=text
   font=QFontComboBox();font.setCurrentText(str(self.note_settings.value(kind+'/font','Segoe Print')));self.note_fonts[kind]=font;text.setPlainText(str(self.note_settings.value(kind+'/text','')));f.addRow(text);f.addRow('Font',font)
   text.textChanged.connect(lambda k=kind:self.note_settings.setValue(k+'/text',self.note_edits[k].toPlainText()))
   font.currentTextChanged.connect(lambda value,k=kind:self.note_settings.setValue(k+'/font',value))
   preview=QLabel('Preview appears here.');preview.setMinimumHeight(80);preview.setWordWrap(False);preview.setAlignment(Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignLeft);self.note_previews[kind]=preview
   f.addRow(row(studio.button('Preview this note',lambda k=kind:self.preview_note(k)),studio.button('Apply this note (game closed)',lambda k=kind:self.apply_note(k))));f.addRow(preview)
   f.addRow(studio.button('Restore original '+('Help note'if kind=='help'else'credits note')+' (game closed)',lambda k=kind:self.restore_notes((k,))))
  f.addRow(studio.button('Restore both original notes (game closed)',lambda:self.restore_notes(('help','credits'))))
  note=QLabel('These replace the two handwritten invitation-note images shown in Help and before Roll Credits. They do not replace the original developer credit roll. Original files are backed up; use Restore below to undo each note. Restart the game to reload its images.');note.setWordWrap(True);box.addWidget(note)
  f=studio.group(box,'Open-source mod catalog — author, license and compatibility')
  self.catalog=table(['Mod','Author','License','Compatibility']);self.catalog.setRowCount(len(CATALOG))
  for i,d in enumerate(CATALOG):
   for j,value in enumerate((d['name'],d['author'],d['license'],'GOTY companion'if d['kind']=='companion'else'Standalone game; not a stock resource pack')):self.catalog.setItem(i,j,QTableWidgetItem(value))
  self.catalog.setCurrentCell(0,0);self.catalog.itemSelectionChanged.connect(self.describe);f.addRow(self.catalog)
  self.mod_description=QLabel();self.mod_description.setTextFormat(Qt.TextFormat.PlainText);self.mod_description.setWordWrap(True);f.addRow(self.mod_description);self.describe()
  f.addRow(row(studio.button('Open original project / credits',self.open_project),studio.button('Install reviewed PvZA11y release',self.install_companion),studio.button('Launch PvZA11y (trainer disconnected)',self.launch_companion)))
  f=studio.group(box,'Resource packs for stock GOTY / Classic')
  note=QLabel('Import a ZIP with lawnlab-mod.json, LICENSE.txt and resources/. The manifest must name its author, source, license, description and supported editions. Image/audio/text packs are supported. DLLs, scripts, patched game executables and mods for Fusion/.NET/Portable are not installed into the stock game. See the mod-pack guide for the exact format.');note.setWordWrap(True);f.addRow(note)
  self.pack_list=QComboBox();self.pack_info=QLabel();self.pack_info.setTextFormat(Qt.TextFormat.PlainText);self.pack_info.setWordWrap(True);self.pack_list.currentIndexChanged.connect(self.describe_pack)
  f.addRow(row(self.pack_list,studio.button('Import resource ZIP',self.import_pack),studio.button('Import loose resource folder',self.import_folder)));f.addRow(self.pack_info);f.addRow(studio.button('Apply selected pack to target edition',self.apply_pack))
  f=studio.group(box,'Restore installed resources and custom notes')
  self.active=table(['Installed edit / pack','Author','Game folder']);f.addRow(self.active)
  f.addRow(row(studio.button('Refresh pack lists',self.refresh),studio.button('Restore selected edit / pack',self.restore_selected)));self.refresh()
 def read_progress(self):
  from edition_saves import progress_overview
  def done(data):
   from studio_ui import fill
   rows=[dict(title=r['title'],stage=(f"{(r['stage']-1)//10+1}-{(r['stage']-1)%10+1} (stage {r['stage']})"if r['stage']is not None and 1<=r['stage']<=50 else'Not available'),folder=r['folder'])for r in data['rows']]
   fill(self.progress_table,rows,['title','stage','folder'])
   self.progress_status.setText(('Connected '+str(data['edition']).upper()+' | Live stage '+str(data['active_stage'])+' | Active root: '+str(data['active_root']))if data['active_root']else'No game connected. The table shows profile 1 on disk. Connect to read the active player and live save root. Saved-file stages can lag unsaved battle progress.')
  self.studio.run(lambda:progress_overview(self.studio.owner.engine),done)
 def choose_game(self,kind):
  value,_=QFileDialog.getOpenFileName(self,'Choose installed '+kind+' game',self.paths[kind].text(),'Game executable (*.exe)')
  if value:self.paths[kind].setText(value);remember_executable(kind,value);self.select_folder()
 def restart_admin(self):
  try:
   from admin_restart import restart
   self.note_settings.sync();restart(self.studio.owner)
  except Exception as error:self.studio.status.setText(str(error))
 def select_folder(self):
  kind='goty'if self.kind.currentIndex()==0 else'classic';value=self.paths[kind].text()
  self.note_settings.setValue('target_edition',self.kind.currentText())
  self.game_folder.setText(str(Path(value).parent)if value else'')
 def follow_connected_game(self):
  remember_connected_edition(self.studio.owner.engine);self.kind.setCurrentText(str(self.note_settings.value('target_edition','GOTY')));self.select_folder()
 def check_target(self):
  try:
   actual=resources.game_edition(self.game_folder.text());expected='goty'if self.kind.currentIndex()==0 else'classic'
   self.target_status.setText(('Verified target: '+actual.upper()+' — '+('main.pak archive resources'if actual=='classic'else'loose resource images'))if actual==expected else'Target mismatch: this folder contains '+actual.upper()+'. Select the matching edition or folder.')
  except Exception as error:self.target_status.setText('Target not verified: '+str(error))
 def target(self):
  root=self.game_folder.text();actual=resources.game_edition(root);expected='goty'if self.kind.currentIndex()==0 else'classic'
  if actual!=expected:raise ValueError('The selected folder is '+actual.upper()+', but the edition selector is '+expected.upper()+'. Nothing was changed.')
  return root
 def save_limbo(self,kind,value):
  import startup_options
  if self.studio.owner.busy:
   self.remember_limbo[kind].blockSignals(True);self.remember_limbo[kind].setChecked(startup_options.remembered(kind));self.remember_limbo[kind].blockSignals(False);return
  def operation():
   engine=self.studio.owner.engine
   if engine.is_connected and startup_options.kind(engine)==kind:engine.set_limbo_remembered(value)
   else:startup_options.save(kind,value)
   return 'Limbo launch preference saved for '+kind.upper()+'. Use the edition game shortcut; the trainer window can stay closed.'
  self.studio.run(operation)
 def choose_folder(self):
  path=QFileDialog.getExistingDirectory(self,'Choose game resource folder',self.game_folder.text())
  if path:self.game_folder.setText(path)
 def prepare_saves(self):
  def op():
   if resources.running():raise RuntimeError('Close both games before copying the initial edition save folders.')
   return prepare()
  self.studio.run(op,lambda value:self.studio.status.setText('Separate saves ready. Backup: '+value['backup']))
 def launch_game(self,kind):
  if self.studio.owner.engine.is_connected:self.studio.status.setText('Disconnect the trainer and close both games before using the launcher.');return
  path=self.paths[kind].text();remember_executable(kind,path)
  self.studio.status.setText('Launching '+kind+'. Click through the game title/loading screen if needed.')
  self.studio.run(lambda:launch(kind,path),lambda result:self.studio.status.setText('Game is using separate saves: '+result))
 def preview_note(self,kind):
  from note_editor import render_note
  if self.studio.owner.busy:return
  root=self.game_folder.text();text=self.note_edits[kind].toPlainText();font=self.note_fonts[kind].currentText()
  try:
   self.target()
   blobs,points=render_note(root,kind,text,font);self.show_note_preview(kind,blobs);self.studio.status.setText(f'Full note preview · {points} pt · not applied yet.')
  except Exception as error:self.studio.status.setText('Note preview: '+str(error))
 def show_note_preview(self,kind,blobs):
  from note_editor import NOTES
  image=QImage.fromData(blobs[NOTES[kind][0]]);image.invertPixels();pixmap=QPixmap.fromImage(image).scaledToWidth(430,Qt.TransformationMode.SmoothTransformation)
  preview=self.note_previews[kind];preview.setPixmap(pixmap);preview.setFixedSize(pixmap.size())
 def apply_note(self,kind):
  from note_editor import render_note,install_note
  if self.studio.owner.busy:return
  root=self.game_folder.text();text=self.note_edits[kind].toPlainText();font=self.note_fonts[kind].currentText()
  try:
   self.target()
   if resources.running():raise RuntimeError('Close both PVZ games before applying a note.')
   # Font metrics and text painting belong on the GUI thread. The worker only
   # installs immutable PNG bytes; it never enters Qt's GUI font engine.
   blobs,points=render_note(root,kind,text,font);self.show_note_preview(kind,blobs)
  except Exception as error:self.studio.status.setText('Note was not applied: '+str(error));return
  def install():
   resources.recover_unmodified_installations();return install_note(root,kind,blobs)
  self.studio.run(install,lambda _:self.after_install(root))
  if self.studio.owner.busy:self.studio.status.setText('Applying rendered note files and saving restore backups…')
 def restore_notes(self,kinds):
  from note_editor import restore_notes
  root=self.game_folder.text()
  def done(result):
   self.refresh()
   for kind,blobs in result['previews'].items():self.show_note_preview(kind,blobs)
   self.studio.status.setText(result['message'])
  self.studio.run(lambda:restore_notes(root,kinds),done)
 def describe(self):
  i=self.catalog.currentRow()
  if i>=0:self.mod_description.setText(CATALOG[i]['description']+' Source: '+CATALOG[i]['source'])
 def open_project(self):
  i=self.catalog.currentRow()
  if i>=0:QDesktopServices.openUrl(QUrl(CATALOG[i]['source']))
 def install_companion(self):self.studio.run(install_a11y,lambda d:self.studio.status.setText('Installed '+d['name']+' '+d['release']+' from its official project. Nothing was launched.'))
 def launch_companion(self):
  if self.studio.owner.engine.is_connected:self.studio.status.setText('Disconnect LawnLab before launching the companion. Restart PVZ before reconnecting.');return
  self.studio.run(launch_a11y,self.studio.status.setText)
 def import_pack(self):
  path,_=QFileDialog.getOpenFileName(self,'Import credited resource pack','','LawnLab resource ZIP (*.zip)')
  if path:self.studio.run(lambda:resources.import_pack(path),lambda _:self.refresh())
 def import_folder(self):
  path=QFileDialog.getExistingDirectory(self,'Choose a resource mod folder')
  if not path:return
  dialog=QDialog(self);dialog.setWindowTitle('Credit the resource mod author');form=QFormLayout(dialog);fields={}
  for key,title in [('name','Mod name'),('author','Original author'),('source','Original project URL'),('license','License name'),('description','Description')]:
   edit=QLineEdit();fields[key]=edit;form.addRow(title,edit)
  editions=QComboBox();editions.addItems(['GOTY only','Classic only','GOTY and Classic']);form.addRow('Author-declared compatibility',editions)
  license_text=QTextEdit();license_text.setPlaceholderText('Paste the author’s redistribution license for these resource files.');form.addRow('License text',license_text)
  for n in('LICENSE.txt','LICENSE','LICENSE.md'):
   p=Path(path)/n
   if p.is_file()and p.stat().st_size<100000:license_text.setPlainText(p.read_text(encoding='utf-8',errors='replace'));break
  note=QLabel('Only image/audio/text resources are imported. Game executables, DLLs and scripts are ignored; this cannot convert a standalone game mod into a stock-game resource mod.');note.setWordWrap(True);form.addRow(note)
  buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
  if dialog.exec()!=QDialog.DialogCode.Accepted:return
  metadata={k:v.text().strip()for k,v in fields.items()};metadata['editions']=[['goty'],['classic'],['goty','classic']][editions.currentIndex()];text=license_text.toPlainText()
  if not text.strip():self.studio.status.setText('Include the original author’s license text before importing.');return
  self.studio.run(lambda:resources.import_folder(path,metadata,text),lambda _:self.refresh())
 def refresh(self):
  self.pack_list.clear()
  for d in resources.packs():self.pack_list.addItem(d['name']+' — '+d['author'],d['id'])
  records=resources.installed();self.active.setRowCount(len(records))
  for i,(code,d)in enumerate(records.items()):
   for j,value in enumerate((d['metadata']['name'],d['metadata']['author'],d['game'])):
    item=QTableWidgetItem(value);item.setData(Qt.ItemDataRole.UserRole,code);self.active.setItem(i,j,item)
  self.describe_pack()
 def describe_pack(self):
  code=self.pack_list.currentData();d=next((d for d in resources.packs()if d['id']==code),None)
  self.pack_info.setText((d['description']+'\nAuthor: '+d['author']+' · License: '+d['license']+'\nSource: '+d['source']+' · Editions: '+', '.join(d['editions']))if d else'No resource pack imported.')
 def apply_pack(self):
  code=self.pack_list.currentData();root=self.game_folder.text()
  if not code:self.studio.status.setText('Import and select a resource pack first.');return
  self.studio.run(lambda:resources.apply_pack(root,code),lambda _:self.after_install(root))
 def after_install(self,root=None):
  self.refresh();target=root or self.game_folder.text();edition=resources.game_edition(target).upper();self.studio.status.setText('Applied to '+edition+' at '+str(target)+'. Original resources were backed up. Restart this edition to load the changes.')
 def restore_selected(self):
  item=self.active.item(self.active.currentRow(),0)
  if not item:self.studio.status.setText('Select an installed edit to restore.');return
  code=item.data(Qt.ItemDataRole.UserRole);self.studio.run(lambda:resources.restore(code),lambda _:self.after_restore())
 def after_restore(self):self.refresh();self.studio.status.setText('Original resources restored. Relaunch the game to refresh cached images.')
