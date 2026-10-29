"""All-or-nothing patch ownership, shared identical patches and retained hooks."""
class PatchManager:
    def __init__(self,memory,backend):self.memory=memory;self.backend=backend;self.active={}
    def enable(self,name,patches):
        if name in self.active:
            with self.backend.suspended():
                for a,original,desired in self.active[name]:
                    if self.memory.read_bytes(a,len(desired))!=desired:raise RuntimeError('An active patch was changed by another tool.')
            return
        with self.backend.suspended(regions=[(a,len(o))for a,o,n in patches]):
            for index,(a,original,desired)in enumerate(patches):
                for b,old,new in patches[:index]:
                    if a<b+len(old)and b<a+len(original)and(a,original,desired)!=(b,old,new):raise RuntimeError('Conflicting spans inside one control.')
            for a,original,desired in patches:
                if len(original)!=len(desired)or not original:raise ValueError('Invalid patch span.')
                shared=False
                for owned in self.active.values():
                    for b,old,new in owned:
                        if a<b+len(old)and b<a+len(original):
                            if (a,original,desired)!=(b,old,new):raise RuntimeError('Conflicting patch spans; disable the overlapping control first.')
                            shared=True
                expected=desired if shared else original
                if self.memory.read_bytes(a,len(original))!=expected:raise RuntimeError(f'Unexpected instruction bytes at {a:#x}; restart PVZ and stop other trainers.')
            applied=[]
            try:
                for patch in patches:
                    a,original,desired=patch
                    if any(patch in items for items in self.active.values()):continue
                    applied.append(patch);self.backend.write_code(a,desired)
            except Exception:
                # Keep a journal even if rollback itself fails.
                self.active[name]=applied
                try:
                    for a,original,desired in reversed(applied):self.backend.write_code(a,original)
                except Exception as rollback:
                    self.backend.poisoned=True
                    raise RuntimeError('Patch rollback failed. PVZ remains paused; restart the game. Journal retained.')from rollback
                del self.active[name];raise
            self.active[name]=list(patches)
    def disable(self,name):
        if name not in self.active:return
        with self.backend.suspended(regions=[(a,len(o))for a,o,n in self.active[name]]):
            for a,original,desired in self.active[name]:
                if self.memory.read_bytes(a,len(original))not in (original,desired):raise RuntimeError('Restore conflict: another tool changed a managed patch. Journal retained.')
            before=[(a,self.memory.read_bytes(a,len(old)))for a,old,new in self.active[name]]
            try:
                for patch in reversed(self.active[name]):
                    if any(patch in items for owner,items in self.active.items()if owner!=name):continue
                    self.backend.write_code(patch[0],patch[1])
            except Exception:
                try:
                    for a,data in before:
                        if self.memory.read_bytes(a,len(data))!=data:self.backend.write_code(a,data)
                except Exception as rollback:
                    self.backend.poisoned=True
                    raise RuntimeError('Restore rollback failed. PVZ remains paused; restart it. Journal retained.')from rollback
                raise
            del self.active[name]
    def reset(self):
        for name in list(self.active):self.disable(name)
