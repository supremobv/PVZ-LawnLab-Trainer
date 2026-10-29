"""Small verified x86 calls; update-loop gating avoids DataArray races."""
import ctypes,struct,time
from ctypes import wintypes
from contextlib import contextmanager
from game_layout import FRAME_DURATION

def u32(n):return struct.pack('<I',n&0xffffffff)
def push(n):return b'\x68'+u32(n)
def mov(reg,n):return bytes([{'eax':0xB8,'ecx':0xB9,'edx':0xBA,'ebx':0xBB,'ebp':0xBD,'esi':0xBE,'edi':0xBF}[reg]])+u32(n)
def call(origin,target):return b'\xE8'+u32(target-origin-5)

class ThreadEntry(ctypes.Structure):
    _fields_=[(n,ctypes.c_uint32)for n in ('size','usage','id','pid','priority','delta','flags')]
class Wow64Context(ctypes.Structure):
    _fields_=[('flags',ctypes.c_uint32),('debug',ctypes.c_uint32*6),('floating',ctypes.c_byte*112),
              ('segments',ctypes.c_uint32*4),('registers',ctypes.c_uint32*7),('eip',ctypes.c_uint32),
              ('cs',ctypes.c_uint32),('eflags',ctypes.c_uint32),('esp',ctypes.c_uint32),('ss',ctypes.c_uint32),('extended',ctypes.c_byte*512)]

class NativeCalls:
    def __init__(self,game):
        self.game=game;self.pm=game.engine.pm;self.handle=self.pm.process_handle;self.depth=0;self.poisoned=False
        k=self.k=ctypes.WinDLL('kernel32',use_last_error=True)
        k.VirtualAllocEx.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_size_t,wintypes.DWORD,wintypes.DWORD];k.VirtualAllocEx.restype=ctypes.c_void_p
        k.VirtualFreeEx.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_size_t,wintypes.DWORD]
        k.VirtualProtectEx.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_size_t,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
        k.FlushInstructionCache.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_size_t]
        k.CreateRemoteThread.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p];k.CreateRemoteThread.restype=wintypes.HANDLE
        k.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
        k.CloseHandle.argtypes=[wintypes.HANDLE]
    def write_code(self,address,data):
        old=wintypes.DWORD()
        if not self.k.VirtualProtectEx(self.handle,address,len(data),0x40,ctypes.byref(old)):raise ctypes.WinError(ctypes.get_last_error())
        try:
            self.pm.write_bytes(address,data,len(data))
            if self.pm.read_bytes(address,len(data))!=data:raise RuntimeError('Code write verification failed.')
            self.k.FlushInstructionCache(self.handle,address,len(data))
        finally:
            ignored=wintypes.DWORD()
            if not self.k.VirtualProtectEx(self.handle,address,len(data),old.value,ctypes.byref(ignored)):raise ctypes.WinError(ctypes.get_last_error())
    @contextmanager
    def suspended(self,regions=()):
        """Brief code/data transaction; no allocation is freed under a paused PC."""
        if self.poisoned:raise RuntimeError('Restart PVZ after the pending native-call timeout.')
        self.game.guard();nt=ctypes.WinDLL('ntdll')
        nt.NtSuspendProcess.argtypes=[wintypes.HANDLE];nt.NtSuspendProcess.restype=ctypes.c_long
        nt.NtResumeProcess.argtypes=[wintypes.HANDLE];nt.NtResumeProcess.restype=ctypes.c_long
        for attempt in range(50):
            if nt.NtSuspendProcess(self.handle)<0:raise RuntimeError('Could not pause PVZ for a memory transaction.')
            try:busy=bool(regions)and any(a<=ip<a+n for ip in self.thread_ips()for a,n in regions)
            except Exception:
                nt.NtResumeProcess(self.handle);raise
            if not busy:break
            if nt.NtResumeProcess(self.handle)<0:raise RuntimeError('Could not resume PVZ while waiting for an instruction boundary.')
            time.sleep(.001)
        else:raise RuntimeError('PVZ is executing a patch region. No bytes changed; retry this control.')
        try:yield
        finally:
            if not self.poisoned and nt.NtResumeProcess(self.handle)<0:raise RuntimeError('Could not resume PVZ.')
    def thread_ips(self):
        k=self.k
        k.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD];k.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
        k.Thread32First.argtypes=[wintypes.HANDLE,ctypes.POINTER(ThreadEntry)];k.Thread32Next.argtypes=k.Thread32First.argtypes
        k.OpenThread.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenThread.restype=wintypes.HANDLE
        k.Wow64GetThreadContext.argtypes=[wintypes.HANDLE,ctypes.POINTER(Wow64Context)];k.Wow64GetThreadContext.restype=wintypes.BOOL
        snapshot=k.CreateToolhelp32Snapshot(4,0)
        if not snapshot or snapshot==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
        result=[]
        try:
            entry=ThreadEntry();entry.size=ctypes.sizeof(entry);ok=k.Thread32First(snapshot,ctypes.byref(entry))
            while ok:
                if entry.pid==self.pm.process_id:
                    thread=k.OpenThread(0x48,False,entry.id)
                    if not thread:raise ctypes.WinError(ctypes.get_last_error())
                    try:
                        context=Wow64Context();context.flags=0x10001
                        if not k.Wow64GetThreadContext(thread,ctypes.byref(context)):raise ctypes.WinError(ctypes.get_last_error())
                        result.append(context.eip)
                    finally:k.CloseHandle(thread)
                ok=k.Thread32Next(snapshot,ctypes.byref(entry))
        finally:k.CloseHandle(snapshot)
        if not result:raise RuntimeError('No suspended game-thread contexts were available.')
        return result
    @contextmanager
    def frozen(self):
        if self.poisoned:raise RuntimeError('A native call timed out. Restart PVZ before continuing.')
        if self.depth:
            self.depth+=1
            try:yield
            finally:self.depth-=1
            return
        self.game.guard();site=self.game.base+0x1D6C6D
        if self.pm.read_bytes(site,2)!=b'\xEB\xC8':raise RuntimeError('Update-loop bytes differ; stop other trainers or restart PVZ.')
        self.write_code(site+1,b'\xFE');self.depth=1
        try:
            time.sleep(min(.2,max(.03,self.game.read(self.game.app()+FRAME_DURATION)/1000*2)))
            yield
        finally:
            self.depth=0
            if not self.poisoned:self.write_code(site+1,b'\xC8')
    def execute(self,build):
        with self.frozen():
            address=self.k.VirtualAllocEx(self.handle,None,65536,0x3000,0x40)
            if not address or address>0xffffffff:raise RuntimeError('Could not allocate x86 call memory.')
            thread=None;done=False
            try:
                body=build(address+2,address+0xF000)
                code=b'\x9c\x60'+body+b'\x61\x9d\x33\xc0\xc2\x04\x00'
                if len(code)>=0xF000:raise ValueError('Native request is too large.')
                self.write_code(address,code)
                thread=self.k.CreateRemoteThread(self.handle,None,0,address,None,0,None)
                if not thread:raise ctypes.WinError(ctypes.get_last_error())
                status=self.k.WaitForSingleObject(thread,5000)
                if status!=0:
                    self.poisoned=True
                    raise RuntimeError('Native call timed out. PVZ updates remain blocked to avoid concurrent mutation; restart the game. Call memory is retained.')
                done=True;return self.game.read(address+0xF000,'uint')
            finally:
                if thread:self.k.CloseHandle(thread)
                if not thread or done:self.k.VirtualFreeEx(self.handle,address,0,0x8000)
    def execute_main(self,build,timeout=20):
        """Run a one-shot widget/loading action on PVZ's own loop thread.

        The tiny loop trampoline and its code allocation are retained until exit;
        a late instruction pointer can therefore never execute freed memory.
        """
        if self.depth or self.poisoned:raise RuntimeError('Restart PVZ before launching another stage.')
        self.game.guard();site=self.game.base+0x1D6C6D;stub=site+6
        if self.pm.read_bytes(site,2)!=b'\xeb\xc8' or self.pm.read_bytes(stub,5)!=b'\xcc'*5:raise RuntimeError('Game loop bytes changed; restart PVZ and close other trainers.')
        address=self.k.VirtualAllocEx(self.handle,None,65536,0x3000,0x40)
        if not address or address>0xffffffff:raise RuntimeError('Could not allocate a game-thread request.')
        flag=address+0xF000;result=flag+4
        body=build(address+25,result)
        code=b'\x9c\x60\x83\x3d'+u32(flag)+b'\x00\x0f\x85'+u32(10+len(body)+10)
        code+=b'\xc7\x05'+u32(flag)+u32(1)+body+b'\xc7\x05'+u32(flag)+u32(2)
        code+=b'\x61\x9d\xe9'+u32(self.game.base+0x1D6C37-(address+len(code)+7))
        if len(code)>=0xE000:raise ValueError('Stage request is too large.')
        self.write_code(address,code);installed=False
        try:
            with self.suspended(((site,2),(stub,5))):
                installed=True;self.write_code(stub,b'\xe9'+u32(address-stub-5));self.write_code(site,b'\xeb\x04')
            end=time.monotonic()+timeout
            while self.game.read(flag)!=2:
                if time.monotonic()>end:
                    self.poisoned=True;raise RuntimeError('Stage loading did not finish on the game thread. Restart PVZ; request memory is retained.')
                time.sleep(.02)
            return self.game.read(result,'uint')
        finally:
            # Wait outside the short patch spans; the retained cave remains valid.
            if installed:
                poisoned=self.poisoned;self.poisoned=False;restore_failed=False
                try:
                    with self.suspended(((site,2),(stub,5))):
                        self.write_code(site,b'\xeb\xc8');self.write_code(stub,b'\xcc'*5)
                except Exception:
                    restore_failed=True;raise
                finally:self.poisoned=poisoned or restore_failed
