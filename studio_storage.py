"""Validated local documents and checksummed game-save snapshots."""
from pathlib import Path
import hashlib,json,os,re,tempfile,time,uuid

SAVE_NAME=re.compile(r'(?:users|user\d+|game\d+_\d+)\.dat',re.I)
def linked(path):return path.is_symlink()or getattr(path,'is_junction',lambda:False)()

def safe_name(name):
    if not isinstance(name,str)or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _-]{0,47}',name):raise ValueError('Use 1–48 letters, numbers, spaces, underscores or hyphens.')
    if name.upper()in {'CON','PRN','AUX','NUL',*[f'COM{i}'for i in range(1,10)],*[f'LPT{i}'for i in range(1,10)]}:raise ValueError('Reserved Windows name.')
    return name

def read_json(path,limit=2_000_000):
    p=Path(path)
    if p.stat().st_size>limit:raise ValueError('Document too large.')
    return json.loads(p.read_text(encoding='utf-8'))

def atomic_bytes(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    # tempfile.mkstemp may retry TMP_MAX times on Windows PermissionError:
    # os.access(W_OK) can report true for protected Program Files directories.
    # Retry only real name collisions, never access-denied errors.
    for attempt in range(8):
        tmp=path.parent/('.lawnlab-'+uuid.uuid4().hex)
        try:
            fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_BINARY',0),0o600);break
        except FileExistsError:continue
        except PermissionError as error:
            raise PermissionError('Windows denied writing '+str(path.parent)+'. For protected game folders, disconnect the trainer and restart LawnLab as administrator.')from error
    else:raise FileExistsError('Could not allocate a unique temporary file after 8 attempts.')
    try:
        with os.fdopen(fd,'wb')as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()

class Documents:
    def __init__(self,root=None):self.root=Path(root or Path(os.getenv('LOCALAPPDATA',Path.home()))/'LawnLab')
    def save(self,kind,name,value):
        if kind not in ('formations','waves','profiles'):raise ValueError('Unknown document category.')
        path=self.root/kind/(safe_name(name)+'.json')
        atomic_bytes(path,json.dumps(value,indent=2).encode());return path
    def load(self,kind,name):
        if kind not in ('formations','waves','profiles'):raise ValueError('Unknown category.')
        return read_json(self.root/kind/(safe_name(name)+'.json'))
    def names(self,kind):
        path=self.root/kind
        return sorted(p.stem for p in path.glob('*.json'))if path.exists()else[]

class SaveBackups:
    def __init__(self,source=None,root=None,running=lambda:False):
        self.source=Path(source or Path(os.getenv('PROGRAMDATA','C:/ProgramData'))/'PopCap Games/PlantsVsZombies/userdata')
        self.root=Path(root or Path(os.getenv('LOCALAPPDATA',Path.home()))/'LawnLab/backups')
        self.running=running
    def _folder(self):
        if not self.source.is_dir()or linked(self.source):raise ValueError('Choose a real PVZ userdata folder, without links/junctions.')
        return self.source.resolve()
    def files(self):
        folder=self._folder();items=[]
        for p in folder.iterdir():
            if SAVE_NAME.fullmatch(p.name):
                if not p.is_file()or p.is_symlink()or p.resolve().parent!=folder:raise ValueError('Linked or invalid save file.')
                items.append(p)
        if not any(p.name.lower()=='users.dat'for p in items):raise ValueError('users.dat was not found in this folder.')
        return sorted(items)
    def create(self,label='manual'):
        items=self.files();blobs={};stats={}
        for p in items:
            before=p.stat();data=p.read_bytes();after=p.stat()
            if before.st_size!=after.st_size or before.st_mtime_ns!=after.st_mtime_ns:raise RuntimeError('The game wrote a save during backup; retry after closing it.')
            if len(data)>64_000_000:raise ValueError('Unexpectedly large save file.')
            blobs[p.name]=data
            stats[p.name]=(after.st_size,after.st_mtime_ns)
        if [p.name for p in self.files()]!=[p.name for p in items]or any((p.stat().st_size,p.stat().st_mtime_ns)!=stats[p.name]for p in items):raise RuntimeError('Save set changed during backup; retry after closing PVZ.')
        stamp=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
        target=self.root/stamp;target.mkdir(parents=True,exist_ok=False)
        for name,data in blobs.items():atomic_bytes(target/name,data)
        manifest={'version':1,'label':str(label)[:80],'files':{n:hashlib.sha256(d).hexdigest()for n,d in blobs.items()},'game_running':bool(self.running())}
        atomic_bytes(target/'manifest.json',json.dumps(manifest,indent=2).encode());return stamp
    def names(self):return sorted((p.name for p in self.root.iterdir()if p.is_dir()and(p/'manifest.json').is_file()),reverse=True)if self.root.exists()else[]
    def validate(self,name):
        if not re.fullmatch(r'\d{8}-\d{6}-[0-9a-f]{8}',name):raise ValueError('Invalid backup ID.')
        folder=self.root/name
        if linked(folder)or folder.resolve().parent!=self.root.resolve():raise ValueError('Linked backup refused.')
        manifest=read_json(folder/'manifest.json');files=manifest.get('files')
        if manifest.get('version')!=1 or not isinstance(files,dict)or not files or len(files)>10000:raise ValueError('Invalid backup manifest.')
        blobs={}
        for n,digest in files.items():
            if not SAVE_NAME.fullmatch(n):raise ValueError('Invalid save filename in backup.')
            p=folder/n
            if p.is_symlink()or p.stat().st_size>64_000_000:raise ValueError('Invalid backup file.')
            data=p.read_bytes()
            if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Backup checksum mismatch.')
            blobs[n]=data
        if 'users.dat'not in {n.lower()for n in blobs}:raise ValueError('Backup has no users.dat.')
        return blobs
    def restore(self,name):
        if self.running():raise RuntimeError('Close PVZ before restoring saves.')
        blobs=self.validate(name);self._folder()
        recovery=self.create('before-restore')
        # A complete recovery snapshot exists before any target mutation.
        try:
            for n,data in blobs.items():
                if self.running():raise RuntimeError('PVZ started during restore; close it and restore the recovery snapshot.')
                atomic_bytes(self.source/n,data)
            for p in self.files():
                if p.name not in blobs:
                    if self.running():raise RuntimeError('PVZ started during restore.')
                    p.unlink()
        except Exception as error:raise RuntimeError(f'Restore interrupted; recovery backup: {recovery}. {error}')from error
        return recovery
