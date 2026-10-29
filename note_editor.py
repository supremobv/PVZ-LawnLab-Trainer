"""Native note text is an alpha-mask image, not a LawnStrings entry."""
from PySide6.QtCore import Qt,QRect,QByteArray,QBuffer,QIODevice,QThread
from PySide6.QtGui import QImage,QPainter,QFont,QFontMetrics,QGuiApplication
from resource_mods import read_resource,apply_files

NOTES={'help':('images/ZombieNoteHelp.png','images/ZombieNoteHelpBlack.png'),
       'credits':('images/Credits_ZombieNote.png','images/Credits_ZombieNoteBlack.png')}
def png(image):
 data=QByteArray();buffer=QBuffer(data);buffer.open(QIODevice.OpenModeFlag.WriteOnly)
 if not image.save(buffer,'PNG'):raise RuntimeError('Could not encode note image.')
 return bytes(data)
def render_note(root,kind,text,family='Segoe Print'):
 app=QGuiApplication.instance()
 if app is None or QThread.currentThread()!=app.thread():raise RuntimeError('Render note text on the application UI thread before starting file installation.')
 if kind not in NOTES:raise ValueError('Choose the Help or credits invitation note.')
 if not isinstance(text,str)or not text.strip()or len(text)>2500:raise ValueError('Enter 1–2500 characters of note text.')
 template=QImage.fromData(read_resource(root,NOTES[kind][0]))
 if template.isNull():raise ValueError('The installed note image is invalid.')
 image=QImage(template.size(),QImage.Format.Format_RGB32);image.fill(Qt.GlobalColor.black);area=image.rect().adjusted(12,8,-12,-8)
 flags=Qt.TextFlag.TextWordWrap|Qt.AlignmentFlag.AlignCenter
 for points in range(40,9,-1):
  font=QFont(family,points);metrics=QFontMetrics(font);bounds=metrics.boundingRect(area,int(flags),text)
  if bounds.height()<=area.height()and bounds.width()<=area.width():break
 else:raise ValueError('This text cannot fit the note. Shorten it.')
 painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.TextAntialiasing);painter.setPen(Qt.GlobalColor.white);painter.setFont(font);painter.drawText(area,int(flags),text);painter.end()
 black=QImage(template.size(),QImage.Format.Format_RGB32);black.fill(Qt.GlobalColor.black)
 return {NOTES[kind][0]:png(image),NOTES[kind][1]:png(black)},points
def apply_note(root,kind,text,family='Segoe Print'):
 files,size=render_note(root,kind,text,family)
 return install_note(root,kind,files)

def install_note(root,kind,files):
 if kind not in NOTES or set(files)!=set(NOTES[kind]):raise ValueError('The rendered note files do not match the selected note.')
 return apply_files(root,files,dict(name=('Help note'if kind=='help'else'Credits invitation note'),author='Local user',license='Local custom text',source='LawnLab note editor',description='Custom note alpha mask; original developer credit roll is unchanged.'))

def restore_notes(root,kinds):
 """Restore the checksummed pre-edit resources, leaving note drafts untouched."""
 from pathlib import Path
 import resource_mods as resources
 kinds=tuple(kinds)
 if not kinds or len(set(kinds))!=len(kinds)or any(kind not in NOTES for kind in kinds):raise ValueError('Choose Help, credits, or both notes.')
 if resources.running():raise RuntimeError('Close both PVZ games before restoring original notes.')
 root=Path(root).resolve();resources.game_edition(root);resources.recover_unmodified_installations()
 journal=resources.installed();selected=[]
 for code,item in journal.items():
  if str(Path(item['game']).resolve()).casefold()!=str(root).casefold():continue
  if item.get('metadata',{}).get('source')!='LawnLab note editor':continue
  names=set(item.get('resource_names',[]))
  if any(names==set(NOTES[kind])for kind in kinds):selected.append(code)
 if not selected:return dict(restored=0,previews={},message='No LawnLab custom note edit to restore for this folder. Files and saved drafts were left unchanged.')
 # A Classic layer backs up the entire archive. Refuse before making changes
 # if a newer unrelated layer would be lost; restoring both notes handles
 # their order automatically without undoing other mods.
 chosen=set(selected);all_keys=list(journal)
 for code in selected:
  item=journal[code]
  if item['edition']=='classic':
   for later in all_keys[all_keys.index(code)+1:]:
    newer=journal[later]
    if str(Path(newer['game']).resolve()).casefold()==str(root).casefold()and newer['edition']=='classic'and later not in chosen:
     raise RuntimeError('Classic loads notes from one archive. Restore the newer note first, or choose Restore both original notes. If a newer resource mod is installed, restore that mod first.')
  for record in item['files']:
   if record['before']is not None:
    backup=resources.library()/'backups'/code/record['name']
    if not backup.is_file()or resources.digest(backup.read_bytes())!=record['before']:raise RuntimeError('Original note backup checksum differs. No notes were restored.')
 for code in reversed(selected):resources.restore(code)
 previews={kind:{name:resources.read_resource(root,name)for name in NOTES[kind]}for kind in kinds}
 return dict(restored=len(selected),previews=previews,message='Original note resources restored from verified backups. Restart PVZ to reload them. Your custom text drafts are still saved.')
