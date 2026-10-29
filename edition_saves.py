"""Separate native save roots without changing either game executable.

The original MSVC string allocation stays owned by PVZ. Only equal-length,
validated path text changes; native LoadDetails then reloads the selected user.
"""
import json,os,struct,time,ctypes
from contextlib import contextmanager
from pathlib import Path
from studio_storage import SaveBackups,atomic_bytes,linked
from studio_native import push,call,mov,u32

BUILDS={
 'goty':dict(product='PlantsVsZomGOTY',root=0x3DB0C0,getter=0x1FF440,signature='558bec83ec2cc745fc0000000068c0b07d00',load=0x6D530,load_signature='558bec6aff6886596c00'),
 'classic':dict(product='PlantsVsZomCLSC',root=0x2A533C,getter=0x1AF590,signature='5133c06aff50c746180f000000894614683c536a00',load=0x69400,load_signature='558bec6aff68a6986400'),
}
def edition(engine):return'classic'if engine.build_label.startswith('Classic')else'goty'
def state_file():return Path(os.getenv('LOCALAPPDATA',Path.home()))/'LawnLab/edition-saves.json'
def settings():
 p=state_file()
 return json.loads(p.read_text(encoding='utf-8'))if p.exists()else{'enabled':False,'executables':{}}
def write_settings(value):atomic_bytes(state_file(),json.dumps(value,indent=2).encode())
def parent():return Path(os.getenv('PROGRAMDATA','C:/ProgramData'))/'PopCap Games'
def save_root(kind):return parent()/BUILDS[kind]['product']
def root_info(engine):
 g=engine.runtime.game;g.guard();config=BUILDS[edition(engine)];address=g.base+config['root']
 sig=bytes.fromhex(config['signature'])
 if engine.pm.read_bytes(g.base+config['getter'],len(sig))!=sig:raise RuntimeError('Save-root getter signature differs.')
 length=g.read(address+0x14,'uint');capacity=g.read(address+0x18,'uint')
 if not 0<=length<=240 or capacity<length:raise RuntimeError('Unexpected native save-root string.')
 buffer=address+4 if capacity<16 else g.pointer(address+4);raw=engine.pm.read_bytes(buffer,length+1)
 if raw[-1]!=0:raise RuntimeError('Save-root terminator differs.')
 return buffer,raw[:-1].decode('ascii')
def prepare():
 source=parent()/'PlantsVsZombies'/'userdata';backup=SaveBackups(source=source).create('before-edition-save-isolation')
 blobs={p.name:p.read_bytes()for p in SaveBackups(source=source).files()}
 created=[]
 for kind in BUILDS:
  dest=save_root(kind)/'userdata'
  if linked(dest)or linked(dest.parent):raise RuntimeError('Save isolation refuses linked folders.')
  if dest.exists():
   SaveBackups(source=dest).files();continue
  dest.mkdir(parents=True)
  for name,data in blobs.items():atomic_bytes(dest/name,data)
  created.append(kind)
 value=settings();value['enabled']=True;write_settings(value)
 return dict(backup=backup,created=created,roots={k:str(save_root(k)/'userdata')for k in BUILDS})
def activate(engine,reload=True,preload=False):
 """Called at Main Menu. The redirected root lasts until this game exits."""
 kind=edition(engine);g=engine.runtime.game;config=BUILDS[kind];buffer,current=root_info(engine)
 target=str(save_root(kind))+'\\';original=str(parent()/'PlantsVsZombies')+'\\'
 if current.casefold()==target.casefold():engine.save_source=save_root(kind)/'userdata';return target
 if current.casefold()!=original.casefold()and not(kind=='classic'and current==''):raise RuntimeError('Unexpected existing save root; no path changed.')
 if not settings().get('enabled'):raise RuntimeError('Prepare edition saves first.')
 ui=g.read(g.app()+(0x7FC if kind=='classic'else 0x91C))
 if preload and current and ui==0 and g.read(g.app()+(0x82C if kind=='classic'else 0x94C),'uint')==0:
  replacement=target.encode('ascii')
  if len(replacement)!=len(current.encode('ascii')):raise RuntimeError('Save-root length differs.')
  with g._native().suspended():engine.pm.write_bytes(buffer,replacement,len(replacement))
  engine.save_source=save_root(kind)/'userdata';return target
 if ui!=1:raise RuntimeError('Return to Main Menu to switch to isolated edition saves. Use the LawnLab game launcher next time.')
 SaveBackups(source=save_root(kind)/'userdata').files()
 replacement=target.encode('ascii');old=current.encode('ascii')
 if len(replacement)!=len(old):raise RuntimeError('The edition path must preserve the native string length.')
 signature=bytes.fromhex(config['load_signature'])
 if engine.pm.read_bytes(g.base+config['load'],len(signature))!=signature:raise RuntimeError('Profile-load signature differs.')
 engine.reset_all();u=g.user();identity=g.read(u+0x20,'uint')
 with g.lock,g.frozen():
  engine.pm.write_bytes(buffer,replacement,len(replacement))
  try:
   if reload:
    def build(origin,result):
     payload=push(u);return payload+call(origin+len(payload),g.base+config['load'])
    g._native().execute(build)
   if g.user()!=u or g.read(u+0x20,'uint')!=identity:raise RuntimeError('Active player changed during profile reload.')
   if root_info(engine)[1]!=target:raise RuntimeError('Save-root verification failed.')
  except Exception:
   if not g._native().poisoned:
    engine.pm.write_bytes(buffer,old,len(old))
   raise
 engine.save_source=save_root(kind)/'userdata';return target

def remember_executable(kind,path):
 value=settings();value.setdefault('executables',{})[kind]=str(Path(path).resolve());write_settings(value)

class LaunchSummary:
 """Present the edition's player list during early startup, then restore legacy.

 Some startup paths load users.dat before a current player exists. Stage only
 that small summary, never another edition's userN.dat/progress files.
 """
 def __init__(self,kind):
  self.shared=parent()/'PlantsVsZombies/userdata/users.dat';self.target=save_root(kind)/'userdata/users.dat'
  if linked(self.shared)or linked(self.target):raise RuntimeError('Linked player summaries are refused.')
  self.before=self.shared.read_bytes();self.staged=self.target.read_bytes()
  if max(len(self.before),len(self.staged))>1_000_000:raise RuntimeError('Unexpected player-summary size.')
 def __enter__(self):
  import base64
  recovery=state_file().parent/'edition-launch-summary-recovery.json'
  atomic_bytes(recovery,json.dumps(dict(shared=str(self.shared),original_base64=base64.b64encode(self.before).decode(),edition_summary_sha256=__import__('hashlib').sha256(self.staged).hexdigest()),indent=2).encode())
  atomic_bytes(self.shared,self.staged);return self
 def __exit__(self,*args):
  # Preserve a native startup sequence-number update if the edition hasn't
  # already written a newer summary into its isolated folder.
  current=self.shared.read_bytes()
  if current!=self.staged and self.target.read_bytes()==self.staged:atomic_bytes(self.target,current)
  atomic_bytes(self.shared,self.before)
  (state_file().parent/'edition-launch-summary-recovery.json').unlink(missing_ok=True)

def recover_summary():
 p=state_file().parent/'edition-launch-summary-recovery.json'
 if not p.exists():return
 import base64,hashlib
 if p.stat().st_size>2_000_000:raise RuntimeError('Invalid interrupted-launch recovery record.')
 value=json.loads(p.read_text());shared=parent()/'PlantsVsZombies/userdata/users.dat'
 if Path(value['shared'])!=shared or linked(shared):raise RuntimeError('Recovery path differs.')
 original=base64.b64decode(value['original_base64'],validate=True);current=shared.read_bytes()
 if current!=original and hashlib.sha256(current).hexdigest()!=value['edition_summary_sha256']:raise RuntimeError('An interrupted launcher left a changed player summary. Its backup is preserved in '+str(p))
 if current!=original:atomic_bytes(shared,original)
 p.unlink()

@contextmanager
def launch_lock():
 k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_wchar_p];k.CreateMutexW.restype=ctypes.c_void_p;k.CloseHandle.argtypes=[ctypes.c_void_p]
 ctypes.set_last_error(0);handle=k.CreateMutexW(None,False,'Local\\LawnLab.EditionLauncher');error=ctypes.get_last_error()
 if not handle:raise ctypes.WinError(error)
 if error==183:k.CloseHandle(handle);raise RuntimeError('Another LawnLab game launch is already in progress.')
 try:yield
 finally:k.CloseHandle(handle)

def verify_achievements(engine,changes):
 if edition(engine)!='goty':raise ValueError('Classic has no achievement fields.')
 g=engine.runtime.game;_,root=root_info(engine);path=Path(root)/'userdata'/f'user{g.read(g.user()+0x20,"uint")}.dat'
 if linked(path)or path.stat().st_size>1_000_000:raise RuntimeError('Unexpected profile file for achievement verification.')
 data=path.read_bytes()
 if len(data)<820 or struct.unpack_from('<i',data)[0]!=12:raise RuntimeError('The achievement save has an unsupported format.')
 count=struct.unpack_from('<i',data,816)[0];offset=820+count*0x58
 if not 0<=count<=200 or len(data)<offset+40:raise RuntimeError('The saved GOTY achievement section is missing. Classic may have rewritten a shared save.')
 # This native GOTY build serializes earned/shown as interleaved byte pairs.
 for key,value in changes.items():
  if data[offset+key*2]!=int(value)or data[offset+key*2+1]!=int(value):raise RuntimeError('Achievement flags did not persist to the native save file.')
 return True

def launch(kind,path=None,timeout=90):
 with launch_lock():return _launch(kind,path,timeout)

def _launch(kind,path=None,timeout=90):
 """Launch then redirect at the first Main Menu; no background watcher needed."""
 import subprocess,pymem.process
 from trainer_backend import PvZTrainer
 if kind not in BUILDS:raise ValueError('Choose GOTY or Classic.')
 if any(p.szExeFile.decode(errors='replace').lower()in('plantsvszombies.exe','popcapgame1.exe')for p in pymem.process.list_processes()):raise RuntimeError('Close both PVZ games before using the isolated launcher.')
 recover_summary()
 value=settings()
 if not value.get('enabled'):prepare()
 executable=Path(path or value.get('executables',{}).get(kind,''))
 if not executable.is_file():raise RuntimeError('Choose the installed game executable in LawnLab first.')
 from resource_mods import game_edition
 if game_edition(executable.parent)!=kind:raise RuntimeError('The selected installation is a different edition.')
 remember_executable(kind,executable)
 summary=LaunchSummary(kind);summary.__enter__()
 try:return _launch_and_redirect(kind,executable,timeout)
 finally:summary.__exit__()

@contextmanager
def game_dll_search():
 """Do not inherit PyInstaller's current-directory-excluding DLL search."""
 from ctypes import wintypes as w
 k=ctypes.WinDLL('kernel32',use_last_error=True)
 k.GetDllDirectoryW.argtypes=[w.DWORD,w.LPWSTR];k.GetDllDirectoryW.restype=w.DWORD
 k.SetDllDirectoryW.argtypes=[w.LPCWSTR];k.SetDllDirectoryW.restype=w.BOOL
 buffer=ctypes.create_unicode_buffer(32768);length=k.GetDllDirectoryW(len(buffer),buffer)
 if length>=len(buffer):raise RuntimeError('DLL search directory is unexpectedly long; game was not launched.')
 old=buffer.value if length else None
 if not k.SetDllDirectoryW(None):raise ctypes.WinError(ctypes.get_last_error())
 try:yield
 finally:
  if not k.SetDllDirectoryW(old):raise RuntimeError('Could not restore LawnLab DLL search directory.')

def start_game(kind,executable):
 # The short scope covers CreateProcess/ShellExecute, not the game lifetime.
 with game_dll_search():return _start_game(kind,executable)

def _start_game(kind,executable):
 """Classic's old wrapper misforwards a quoted argv[0] to -changedir.

 Keep the full verified path as CreateProcess's application name, and use
 its existing space-free Windows short name for the legacy command line.
 ShellExecute is the normal double-click fallback when 8.3 names are absent.
 """
 import subprocess
 if kind!='classic':return subprocess.Popen([str(executable)],cwd=str(executable.parent))
 from ctypes import wintypes as w
 k=ctypes.WinDLL('kernel32',use_last_error=True)
 k.GetShortPathNameW.argtypes=[w.LPCWSTR,w.LPWSTR,w.DWORD];k.GetShortPathNameW.restype=w.DWORD
 buffer=ctypes.create_unicode_buffer(32768);length=k.GetShortPathNameW(str(executable),buffer,len(buffer))
 if 0<length<len(buffer) and not any(c.isspace()or c=='"'for c in buffer.value):
  return subprocess.Popen(buffer.value,executable=str(executable),cwd=str(executable.parent))
 shell=ctypes.WinDLL('shell32',use_last_error=True)
 shell.ShellExecuteW.argtypes=[w.HWND,w.LPCWSTR,w.LPCWSTR,w.LPCWSTR,w.LPCWSTR,ctypes.c_int];shell.ShellExecuteW.restype=ctypes.c_ssize_t
 result=shell.ShellExecuteW(None,'open',str(executable),None,str(executable.parent),1)
 if result<=32:raise RuntimeError('Windows could not launch the Classic wrapper (ShellExecute error '+str(result)+').')

def _launch_and_redirect(kind,executable,timeout):
 import subprocess
 from trainer_backend import PvZTrainer
 start_game(kind,executable)
 end=time.monotonic()+timeout;engine=None;last='Waiting for the game to reach Main Menu.'
 while time.monotonic()<end:
  candidate=PvZTrainer();candidate.defer_save_isolation=True
  try:
   if candidate.attach_process():
    if edition(candidate)!=kind:raise RuntimeError('The launched executable is a different edition.')
    engine=candidate;g=engine.runtime.game
    ui=g.read(g.app()+(0x7FC if kind=='classic'else 0x91C))
    if ui==0 and g.read(g.app()+(0x82C if kind=='classic'else 0x94C),'uint')==0:
     activate(engine,preload=True)
     last='Save folder selected. Click through the title screen to Main Menu.'
    elif ui==1:
     target=activate(engine,preload=True)
     if kind=='classic':
      import pymem.process
      if not pymem.process.module_from_name(engine.pm.process_handle,'bass.dll'):raise RuntimeError('Classic has not loaded its bass.dll audio library.')
     return target
   last=candidate.last_error or last
  except Exception as error:last=str(error)
  finally:
   candidate.shutdown()
   if candidate.pm:candidate.pm.close_process()
  time.sleep(.25)
 raise RuntimeError('Save isolation did not finish: '+last+' Close the game and retry the LawnLab launcher.')



def progress_overview(engine=None):
 """Read saved-file stages and current memory root without switching saves."""
 import struct
 result={'active_root':None,'active_stage':None,'profile_id':1,'edition':None,'rows':[]}
 if engine is not None and getattr(engine,'is_connected',False)and isinstance(getattr(engine,'build_label',None),str):
  g=engine.runtime.game;result.update(active_root=root_info(engine)[1],active_stage=g.read(g.user()+0x4C if edition(engine)=='goty'else g.user()+0x24),profile_id=g.read(g.user()+0x20,'uint'),edition=edition(engine))
 for kind,title,folder in [('legacy','Original EXEs — shared old progress',parent()/'PlantsVsZombies/userdata'),('goty','GOTY — separate progress',save_root('goty')/'userdata'),('classic','Classic — separate progress',save_root('classic')/'userdata')]:
  path=folder/f"user{result['profile_id']}.dat";stage=None
  if path.is_file():
   with path.open('rb')as f:header=f.read(8)
   if len(header)==8:stage=struct.unpack_from('<i',header,4)[0]
  result['rows'].append(dict(kind=kind,title=title,folder=str(folder),stage=stage))
 return result
