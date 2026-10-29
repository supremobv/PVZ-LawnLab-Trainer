"""Explicit UI action to restart this application through Windows UAC."""
import ctypes,subprocess,sys
from ctypes import wintypes as w
from pathlib import Path

def restart(owner):
 if owner.busy:raise RuntimeError('Wait for the current operation to finish before restarting.')
 if owner.engine.is_connected:raise RuntimeError('Disconnect the trainer before restarting as administrator.')
 shell=ctypes.WinDLL('shell32',use_last_error=True)
 if shell.IsUserAnAdmin():raise RuntimeError('LawnLab is already running as administrator. Check the destination folder permissions.')
 executable=Path(sys.executable).resolve()
 args=[]if getattr(sys,'frozen',False)else[str(Path(__file__).resolve().with_name('lawnlab.py'))]
 shell.ShellExecuteW.argtypes=[w.HWND,w.LPCWSTR,w.LPCWSTR,w.LPCWSTR,w.LPCWSTR,ctypes.c_int];shell.ShellExecuteW.restype=ctypes.c_ssize_t
 result=shell.ShellExecuteW(None,'runas',str(executable),subprocess.list2cmdline(args),str(executable.parent),1)
 if result<=32:raise RuntimeError('Windows did not approve the administrator restart. This LawnLab window remains open.')
 owner.close()
