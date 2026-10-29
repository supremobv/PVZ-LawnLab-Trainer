"""Remembered installation options; these are not native player-profile fields."""
import json,os
from pathlib import Path
from studio_storage import atomic_bytes

LIMBO={'goty':(0x30C80,bytes.fromhex('885864'),bytes.fromhex('385864')),
       'classic':(0x2DF5D,bytes.fromhex('885954'),bytes.fromhex('385954'))}
def state_file():return Path(os.getenv('LOCALAPPDATA',Path.home()))/'LawnLab/startup-options.json'
def settings():
 p=state_file();return json.loads(p.read_text(encoding='utf-8'))if p.exists()else{}
def remembered(kind):return settings().get(kind,{}).get('limbo')is True
def save(kind,value):
 if kind not in LIMBO or type(value)is not bool:raise ValueError('Choose a supported edition and a true/false Limbo setting.')
 data=settings();data[kind]=dict(data.get(kind,{}),limbo=value);atomic_bytes(state_file(),json.dumps(data,indent=2).encode())
def kind(engine):return'classic'if getattr(engine,'build_label','').startswith('Classic')else'goty'
def normalize_classic(image):
 # Accept only this known change, then fingerprint the entire canonical .text.
 rva,old,new=LIMBO['classic']
 if image[rva:rva+len(new)]!=new:return image
 result=bytearray(image);result[rva:rva+len(old)]=old;return bytes(result)
def attach(runtime):
 e=runtime.engine;edition=kind(e);rva,old,new=LIMBO[edition];live=e.pm.read_bytes(runtime.base+rva,len(old))
 if runtime.image[rva:rva+len(old)]!=old:raise RuntimeError('Limbo reference instructions differ.')
 e._remembered_limbo=remembered(edition)
 if live==new:
  runtime.manager.active['limbo_page']=[(runtime.base+rva,old,new)];e.limbo_page_active=True
 elif live!=old:raise RuntimeError('Unexpected Limbo instructions; close overlapping trainers.')
 elif e._remembered_limbo:
  runtime.enable('limbo_page');e.limbo_page_active=True
