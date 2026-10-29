"""Reversible, credited resource packs. No executable/DLL/script installation."""
import hashlib,json,os,struct,uuid,zipfile
from pathlib import Path,PurePosixPath
from studio_storage import atomic_bytes,linked

MAX_FILE=32_000_000;MAX_PACK=200_000_000
PREFIXES={'images','sounds','music','properties'}
EXTENSIONS={'.png','.jpg','.jpeg','.wav','.ogg','.mo3','.txt','.xml'}
def library():return Path(os.getenv('LOCALAPPDATA',Path.home()))/'LawnLab/mods'
def digest(data):return hashlib.sha256(data).hexdigest()
def running():
 import pymem.process
 return any(p.szExeFile.decode(errors='replace').lower()in('plantsvszombies.exe','popcapgame1.exe')for p in pymem.process.list_processes())
def relative(name):
 if not isinstance(name,str)or '\\'in name or ':'in name:raise ValueError('Use relative forward-slash resource paths.')
 p=PurePosixPath(name)
 if p.is_absolute()or not p.parts or any(x in ('..','.')for x in p.parts):raise ValueError('Invalid resource path.')
 reserved={'CON','PRN','AUX','NUL',*[f'COM{i}'for i in range(1,10)],*[f'LPT{i}'for i in range(1,10)]}
 if any(part.rstrip(' .')!=part or part.split('.')[0].upper()in reserved for part in p.parts):raise ValueError('Reserved Windows resource path.')
 if p.parts[0].lower()not in PREFIXES or p.suffix.lower()not in EXTENSIONS:raise ValueError('Only image, audio and text resource files are supported.')
 if p.name.lower()in('partner.xml','partner.xml.sig','zombatartos.txt'):raise ValueError('Partner settings and game legal notices are not mod resources.')
 return p.as_posix()
def validate_content(name,data):
 relative(name)
 if not 0<len(data)<=MAX_FILE:raise ValueError('Resource size is invalid.')
 if name.lower().endswith('.xml'):
  import xml.etree.ElementTree as ET
  if b'<!DOCTYPE'in data.upper()or b'<!ENTITY'in data.upper():raise ValueError('External XML entities are not supported.')
  tree=ET.fromstring(data)
  for element in tree.iter():
   path=element.attrib.get('path')
   if path is not None:
    normalized=path.replace('\\','/')
    if ':'in normalized or normalized.startswith('/')or'..'in PurePosixPath(normalized).parts:raise ValueError('Resource XML paths must remain relative to the game resources.')
 if name.lower().endswith(('.png','.jpg','.jpeg')):
  from PySide6.QtGui import QImage
  image=QImage.fromData(data)
  if image.isNull()or image.width()>8192 or image.height()>8192:raise ValueError('Invalid or oversized mod image.')
def target_path(root,name):
 root=Path(root).resolve();path=root/relative(name)
 current=path
 while current!=root:
  if linked(current):raise ValueError('Linked resource paths are refused.')
  current=current.parent
 if root not in path.resolve().parents:raise ValueError('Resource escapes the game directory.')
 return path
def internal_target(root,name):
 if name=='main.pak':
  root=Path(root).resolve();p=root/'main.pak'
  if linked(p):raise ValueError('Linked PAK file is refused.')
  return p
 return target_path(root,name)
def game_edition(root):
 from studio_engine import HASH
 p=Path(root)/'PlantsVsZombies.exe'
 if not p.is_file():raise ValueError('Choose the installed game folder containing PlantsVsZombies.exe.')
 value=digest(p.read_bytes())
 if value==HASH:return'goty'
 if value=='9397ca2dc3a4560eba5f87aef40fd800786ba0312716729ccbdbda185abee27d'and(Path(root)/'main.pak').is_file():return'classic'
 raise ValueError('This resource installer supports the verified GOTY and Classic installations only.')
def import_pack(filename):
 with zipfile.ZipFile(filename)as archive:
  entries=archive.infolist()
  if len(entries)>2000 or sum(x.file_size for x in entries)>MAX_PACK:raise ValueError('Pack is too large.')
  if len({x.filename.casefold()for x in entries})!=len(entries):raise ValueError('Duplicate archive names.')
  for entry in entries:
   if entry.flag_bits&1 or(entry.external_attr>>16)&0xF000==0xA000:raise ValueError('Encrypted or linked archive entries are refused.')
  if archive.getinfo('lawnlab-mod.json').file_size>64000:raise ValueError('Mod metadata is too large.')
  info=json.loads(archive.read('lawnlab-mod.json'))
  for key in('name','author','source','license','description'):
   if not isinstance(info.get(key),str)or not 1<=len(info[key])<=4000:raise ValueError('Mod metadata needs name, author, source, license and description.')
  if info.get('version')!=1 or not isinstance(info.get('editions'),list)or not info['editions']or set(info['editions'])-{'goty','classic'}:raise ValueError('Declare supported editions: goty and/or classic.')
  files=info.get('files')
  if not isinstance(files,list)or not files or len(files)!=len(set(x.casefold()for x in files)):raise ValueError('Invalid mod file list.')
  allowed={'lawnlab-mod.json','LICENSE.txt','CREDITS.txt'}|{'resources/'+relative(n)for n in files}
  if any(not x.is_dir()and x.filename not in allowed for x in entries):raise ValueError('Archive contains undeclared or executable files.')
  blobs={n:archive.read('resources/'+n)for n in files}
  for n,data in blobs.items():validate_content(n,data)
  if not info['license'].strip()or 'LICENSE.txt'not in archive.namelist():raise ValueError('Include the author’s license in LICENSE.txt.')
  code=uuid.uuid4().hex;folder=library()/'packs'/code
  for n,data in blobs.items():atomic_bytes(folder/'resources'/n,data)
  for n in('LICENSE.txt','CREDITS.txt'):
   if n in archive.namelist():atomic_bytes(folder/n,archive.read(n))
  atomic_bytes(folder/'lawnlab-mod.json',json.dumps(info,indent=2).encode());return code
def packs():
 result=[]
 for p in(library()/'packs').glob('*/lawnlab-mod.json'):
  d=json.loads(p.read_text(encoding='utf-8'));d['id']=p.parent.name;result.append(d)
 return result
def import_folder(folder,metadata,license_text):
 """Convert a loose image/audio/text mod into a credited managed resource ZIP."""
 import tempfile
 root=Path(folder).resolve()
 if(root/'resources').is_dir():root=root/'resources'
 files=[]
 for prefix in sorted(PREFIXES):
  for p in(root/prefix).rglob('*'):
   if p.is_file()and p.suffix.lower()in EXTENSIONS:
    name=p.relative_to(root).as_posix();target_path(root,name);files.append(relative(name))
 if not files or len(files)>1900:raise ValueError('Choose a resource mod folder containing images, sounds, music or properties (up to 1900 files).')
 if sum((root/n).stat().st_size for n in files)>MAX_PACK:raise ValueError('Resource folder is too large.')
 info=dict(metadata,version=1,files=files)
 with tempfile.TemporaryDirectory()as temp:
  p=Path(temp)/'resource-pack.zip'
  with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED)as archive:
   archive.writestr('lawnlab-mod.json',json.dumps(info,indent=2));archive.writestr('LICENSE.txt',license_text)
   for n in files:archive.write(root/n,'resources/'+n)
  return import_pack(p)
def journal_file():return library()/'installed.json'
def installed():return json.loads(journal_file().read_text())if journal_file().exists()else{}
def apply_files(root,blobs,metadata):
 if running():raise RuntimeError('Close both PVZ games before changing resource files.')
 kind=game_edition(root);root=Path(root).resolve();journal=installed();code=uuid.uuid4().hex;backup=library()/'backups'/code;records=[]
 occupied={str(Path(v['game'])/r['name']).casefold()for v in journal.values()for r in v['files']}
 if not blobs or sum(map(len,blobs.values()))>MAX_PACK:raise ValueError('Resource batch is empty or too large.')
 resource_names=list(blobs)
 for name,data in blobs.items():validate_content(name,data)
 if kind=='classic':
  used={n.casefold()for v in journal.values()if v['game']==str(root)for n in v.get('resource_names',[])}
  if used&{n.casefold()for n in blobs}:raise ValueError('An active Classic pack owns one of these resources. Restore it first.')
  from pak_resources import replace
  blobs={'main.pak':replace((root/'main.pak').read_bytes(),blobs)}
 for name,data in blobs.items():
  p=internal_target(root,name)
  if name!='main.pak'and str(p).casefold()in occupied:raise ValueError('Another active resource pack owns '+name+'. Restore it first.')
  before=p.read_bytes()if p.exists()else None
  if before is not None:atomic_bytes(backup/name,before)
  records.append(dict(name=name,before=digest(before)if before is not None else None,after=digest(data)))
 # Write the recovery journal before the first game resource changes.
 journal[code]=dict(game=str(root),edition=kind,metadata=metadata,files=records,resource_names=resource_names,status='installing');atomic_bytes(journal_file(),json.dumps(journal,indent=2).encode())
 try:
  for name,data in blobs.items():atomic_bytes(internal_target(root,name),data)
  journal[code]['status']='active';atomic_bytes(journal_file(),json.dumps(journal,indent=2).encode())
 except Exception:
  for r in reversed(records):
   p=internal_target(root,r['name'])
   # A failed first write has changed nothing. Avoid attempting a forbidden
   # rollback write over identical originals and leaving an installing record.
   if r['before']is not None and p.exists()and digest(p.read_bytes())==r['before']:continue
   if r['before']is None:
    if p.exists()and digest(p.read_bytes())==r['after']:p.unlink()
   else:atomic_bytes(p,(backup/r['name']).read_bytes())
  del journal[code];atomic_bytes(journal_file(),json.dumps(journal,indent=2).encode());raise
 return code

def recover_unmodified_installations():
 """Clear interrupted pre-write journals only after verifying every original.

 Keep backups. Never silently repair partial installs or externally changed
 resources; those still require deliberate restoration.
 """
 if running():raise RuntimeError('Close both PVZ games before checking interrupted resource edits.')
 journal=installed();removed=[]
 for code,item in list(journal.items()):
  if item.get('status')!='installing':continue
  root=Path(item['game']);unchanged=True
  for r in item['files']:
   p=internal_target(root,r['name'])
   if r['before']is None:unchanged=unchanged and not p.exists()
   else:unchanged=unchanged and p.is_file()and digest(p.read_bytes())==r['before']
  if unchanged:removed.append(code);del journal[code]
 if removed:atomic_bytes(journal_file(),json.dumps(journal,indent=2).encode())
 return removed
def apply_pack(root,code):
 if not isinstance(code,str)or len(code)!=32 or any(c not in'0123456789abcdef'for c in code):raise ValueError('Invalid installed pack ID.')
 folder=library()/'packs'/code;info=json.loads((folder/'lawnlab-mod.json').read_text());kind=game_edition(root)
 if kind not in info['editions']:raise ValueError('This author does not declare compatibility with '+kind+'.')
 return apply_files(root,{n:(folder/'resources'/relative(n)).read_bytes()for n in info['files']},info)
def restore(code):
 if running():raise RuntimeError('Close both PVZ games before restoring resource files.')
 journal=installed();item=journal[code];root=Path(item['game']);backup=library()/'backups'/code
 if item['edition']=='classic':
  later=False
  for key,value in journal.items():
   if key==code:later=True;continue
   if later and value['game']==item['game']and value['edition']=='classic':raise RuntimeError('Restore newer Classic resource packs / note edits first.')
 # Preflight every target; preserve edits made outside LawnLab.
 current={}
 for r in item['files']:
  p=internal_target(root,r['name'])
  if not p.exists()or digest(p.read_bytes())!=r['after']:raise RuntimeError('Resource changed outside LawnLab: '+r['name']+'. Restore was not applied.')
  current[r['name']]=p.read_bytes()
  if r['before']is not None and digest((backup/r['name']).read_bytes())!=r['before']:raise RuntimeError('Resource backup checksum differs.')
 try:
  for r in item['files']:
   p=internal_target(root,r['name'])
   if r['before']is None:p.unlink()
   else:atomic_bytes(p,(backup/r['name']).read_bytes())
 except Exception:
  for name,data in current.items():atomic_bytes(internal_target(root,name),data)
  raise
 del journal[code];atomic_bytes(journal_file(),json.dumps(journal,indent=2).encode())

def read_resource(root,name):
 """Read loose assets or the user's original XOR-encoded PopCap PAK."""
 p=target_path(root,name)
 archive=Path(root)/'main.pak'
 if archive.is_file():
  from pak_resources import decode
  for entry,data,stamp in decode(archive.read_bytes()):
   if entry.casefold()==name.casefold():return data
 if p.is_file():return p.read_bytes()
 raise FileNotFoundError(name)
