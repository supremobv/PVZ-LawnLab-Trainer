"""Choose an exact supported executable, ignoring Classic's launcher wrapper."""
from pathlib import Path
import hashlib
from verified_engine import PvZTrainer as GotyTrainer,NAMES
from studio_engine import StudioGame as GotyGame,HASH
from profile_tools import ProfileTools as GotyProfile
from classic_verified_engine import PvZTrainer as ClassicTrainer
from classic_studio_engine import StudioGame as ClassicGame
from classic_profile_tools import ProfileTools as ClassicProfile
from runtime_image import classic_guard

GotyTrainer.studio_game_class=GotyGame
GotyTrainer.profile_tools_class=GotyProfile
GotyTrainer.build_label='GOTY 1.2.0.1073'
ClassicTrainer.studio_game_class=ClassicGame
ClassicTrainer.profile_tools_class=ClassicProfile
ClassicTrainer.build_label='Classic 1.0.0.1051'

def candidates(name='auto',pid=None):
    import pymem,pymem.process
    found=[];errors=[];processes=[(p.szExeFile.decode(errors='replace'),p.th32ProcessID)for p in pymem.process.list_processes()]
    if any(n.lower()=='pvza11y.exe'for n,_ in processes):raise RuntimeError('Close PvZA11y and restart PVZ before connecting LawnLab; these controllers must run separately.')
    for filename,process_id in processes:
        if filename.lower()not in ('plantsvszombies.exe','popcapgame1.exe'):continue
        if pid and process_id!=pid:continue
        if name!='auto'and filename.lower()!=name.lower():continue
        pm=None
        try:
            pm=pymem.Pymem(process_id)
            module=pymem.process.module_from_name(pm.process_handle,filename)
            if module.SizeOfImage==0x415000 and hashlib.sha256(Path(module.filename).read_bytes()).hexdigest()==HASH:backend=GotyTrainer
            elif module.SizeOfImage==0x394000:
                from types import SimpleNamespace
                classic_guard(SimpleNamespace(pm=pm,attached_process_name=filename,base_address=module.lpBaseOfDll));backend=ClassicTrainer
            else:continue
            found.append((process_id,backend))
        except Exception as error:errors.append(str(error))
        finally:
            if pm:pm.close_process()
    if len(found)>1:raise RuntimeError('More than one supported game is open. Close one, or select its process explicitly in Cheat Engine.')
    if not found:raise RuntimeError('Open a supported GOTY 1.2.0.1073 or Classic 1.0.0.1051 game. '+('; '.join(errors)[:400]))
    return found[0]

class PvZTrainer:
    safe_runtime_enabled=True
    def __init__(self):object.__setattr__(self,'_backend',GotyTrainer())
    def __getattr__(self,name):return getattr(self._backend,name)
    def __setattr__(self,name,value):
        if name=='_backend':object.__setattr__(self,name,value)
        else:setattr(self._backend,name,value)
    def shutdown(self):return self._backend.shutdown()
    def attach_process(self):
        try:
            if self._backend.is_connected:raise RuntimeError('Disconnect the existing game first.')
            defer=getattr(self,'defer_save_isolation',False)
            pid,kind=candidates(self.process_name,getattr(self,'target_pid',None));backend=kind()
            backend.process_name=self.process_name;backend.target_pid=pid;object.__setattr__(self,'_backend',backend)
            if not backend.attach_process():return False
            from edition_saves import settings,activate
            if settings().get('enabled')and not defer:activate(backend)
            return True
        except Exception as error:
            self.last_error=str(error)
            if self._backend.is_connected:
                self._backend.shutdown()
                if self._backend.pm:self._backend.pm.close_process()
                self._backend.pm=None;self._backend.is_connected=False
            return False
