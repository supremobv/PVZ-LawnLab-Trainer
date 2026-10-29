"""Reviewed GOTY/Classic upgrade, Almanac and entity-size controls.

Only the Almanac's own availability/drawing predicates are changed. Profile
progress, purchases and Yeti spawn eligibility are never rewritten.
"""
import math,struct

PATCHES={
 'goty':{
  'cattail_land':[(0x10E1F,'7511','eb11')],
  'instant_mines':[(0x61C66,'741f','eb1f')],
  'no_support':[(0x10BDD,'7527','eb27'),(0x10C3E,'7416','eb16')],
  'direct_upgrades':[(0x10DDF,'751a','eb1a'),(0xFF0E,'7511','eb11'),(0x205A0,'515357','b001c3')],
  'almanac_reveal':[(0x343E,'84c0','0c01'),(0x4BC2,'84c0','0c01'),
    (0x4C50,'51538bd8','b001c390'),(0x4D50,'8b8084010000','b001c3909090'),
    (0x42DE,'8b842440010000','e9600000009090'),(0x44C1,'753e','eb3e'),(0x46B0,'754b','eb4b')]},
 'classic':{
  'cattail_land':[(0xE4AC,'7511','eb11')],
  'instant_mines':[(0x5E338,'741f','eb1f')],
  'no_support':[(0xE26A,'7527','eb27'),(0xE2CB,'7416','eb16')],
  'direct_upgrades':[(0xE46C,'751a','eb1a'),(0xD51E,'7511','eb11'),(0x1D7D0,'5183f828','b001c390')],
  'almanac_reveal':[(0x2224,'84c0','0c01'),(0x3983,'84c0','0c01'),
    (0x3A10,'51558b6c240c','b001c2040090'),(0x3B30,'8b806c010000','b001c3909090'),
    (0x30E7,'8b8c2430010000','e95f0000009090'),(0x32A7,'7540','eb40'),(0x348C,'754a','eb4a')]}}
PLANT_HOOK={'goty':0x6786A,'classic':0x63E22}
PLANT_ORIGINAL=bytes.fromhex('d95d24d944241cd95d34')
ZOMBIE_SCALE=0x11C
COB_FIRE={'goty':(0x6A810,'51d90598db6f0053'),'classic':(0x66D50,'51d9058893670053')}
COB_STATE=0x3C
COB_RELOAD=0x54
COB_READY=37
COB_ARMING=35
GRID_ITEMS={'goty':(0x134,0x502B0,'8b0e8b4634c64620'),'classic':(0x11C,0x4D000,'8b0e8b463485c0c6')}

def remove_graves(runtime):
 """Remove only live gravestones through GridItemDie, including effects."""
 g=runtime.game;offset,rva,signature=GRID_ITEMS[edition(runtime.engine)]
 with g.lock,runtime.native.frozen():
  board=g.board();count=g.read(board+offset+4)
  if not 0<=count<=4096:raise RuntimeError('Invalid grid-item array bound; nothing was removed.')
  if not count:return 0
  data=g.pointer(board+offset);blob=g.engine.pm.read_bytes(data,count*0xEC);addresses=[]
  for i in range(count):
   cell=blob[i*0xEC:(i+1)*0xEC]
   ident=struct.unpack_from('<I',cell,0xE8)[0]
   if cell[0x20]or not ident>>16 or struct.unpack_from('<i',cell,8)[0]!=1:continue
   if struct.unpack_from('<I',cell,4)[0]!=board:raise RuntimeError('Grid item belongs to another lawn; nothing was removed.')
   col,row=struct.unpack_from('<ii',cell,0x10)
   if not 0<=col<9 or not 0<=row<g.rows():raise RuntimeError('Invalid grave position; nothing was removed.')
   addresses.append(data+i*0xEC)
  if runtime.image[rva:rva+8]!=bytes.fromhex(signature):raise RuntimeError('Grave removal routine differs from this build.')
  if addresses:runtime.native_action([(rva,'esi',a,[])for a in addresses])
  return len(addresses)

def cob_target(zombies,read):
 """Prefer the hostile on-screen zombie closest to the house."""
 eligible=[z for z in zombies if z['health']>0 and z['state']not in (1,2,3)
           and math.isfinite(z['x'])and math.isfinite(z['y'])
           and 0<=z['x']<=760 and -80<=z['y']<=540
           and not read(z['address']+0xB8,'byte')]
 return min(eligible,key=lambda z:(z['x'],z['id']))if eligible else None

def auto_cob(runtime):
 """Skip only arming wait; use native fire and preserve charging/shooting.

 Re-read object identities while the update loop is gated. No cached pointers,
 global mouse clicks, or writes to the native ready/firing states are used.
 """
 g=runtime.game;n=runtime.native;kind=edition(runtime.engine)
 def snapshot():
  app=g.app();ui,mode,board,paused,count=(0x7FC,0x7F8,0x768,0x164,0xD8)if kind=='classic'else(0x91C,0x918,0x868,0x17C,0xF0)
  if g.read(app+ui)!=3 or g.read(app+mode)in (43,50):return [],None
  b=g.board()
  if g.read(b+paused,'byte')or g.read(b+count)>=700:return [],None
  plants=[p for p in g.entities('plant')if p['type']==47 and p['health']>0
          and not g.read(p['address']+0x134)and not g.read(p['address']+0x143,'byte')]
  return plants,cob_target(g.entities('zombie'),g.read)if plants else None
 with g.lock,n.suspended():
  plants,target=snapshot()
  if not target:return 0
  for p in plants:
   if g.read(p['address']+COB_STATE)==COB_ARMING and g.read(p['address']+COB_RELOAD)>0:g.write(p['address']+COB_RELOAD,0)
  if not any(g.read(p['address']+COB_STATE)==COB_READY for p in plants):return 0
 with g.lock,n.frozen():
  plants,target=snapshot()
  if not target:return 0
  rva,signature=COB_FIRE[kind]
  if runtime.image[rva:rva+8]!=bytes.fromhex(signature):raise RuntimeError('Cob Cannon firing routine differs from this build.')
  ready=[p for p in plants if g.read(p['address']+COB_STATE)==COB_READY][:32]
  x=max(40,min(780,round(target['x']+40)));y=max(80,min(580,round(target['y']+80)))
  if ready:runtime.native_action([(rva,'eax',p['address'],[y,x])for p in ready])
  return len(ready)

def edition(engine):return 'classic' if getattr(engine,'build_label','').startswith('Classic') else 'goty'

def percent(value):
 if type(value)is not int or not 25<=value<=300:raise ValueError('Size must be 25–300 percent; 100 is normal.')
 return value

def specs(runtime,name):
 result=[]
 for rva,old,new in PATCHES[edition(runtime.engine)].get(name,[]):
  old=bytes.fromhex(old)
  if runtime.image[rva:rva+len(old)]!=old:raise RuntimeError('Extra control instruction mismatch: '+name)
  result.append((runtime.base+rva,old,bytes.fromhex(new)))
 return result

def plant_scale_code(parameter,origin,target,kind):
 """Multiply native body X/Y scales with balanced x87 stack and saved flags.

 EBX=plant, EBP=validated body Reanimation. Restrict to the current battle
 board; Almanac, seed previews and Zen Garden keep their native appearance.
 """
 p=lambda x:struct.pack('<I',x&0xffffffff)
 ui,mode,board=(0x7FC,0x7F8,0x768)if kind=='classic'else(0x91C,0x918,0x868)
 guard=b'\x8b\x03\x83\xb8'+p(ui)+b'\x03';checks=[]
 # Conditional near jumps are resolved to the register/flags cleanup below.
 body=bytearray(b'\x9c\x50'+guard)
 def skip(op):
  body.extend(op);checks.append(len(body));body.extend(b'\0'*4)
 skip(b'\x0f\x85')
 for special in (43,50):
  body.extend(b'\x83\xb8'+p(mode)+bytes([special]));skip(b'\x0f\x84')
 body.extend(b'\x8b\x80'+p(board)+b'\x85\xc0');skip(b'\x0f\x84')
 body.extend(b'\x3b\x43\x04');skip(b'\x0f\x85')
 body.extend(b'\xd8\x0d'+p(parameter)) # fmul ST0, float multiplier
 for at in checks:body[at:at+4]=p(len(body)-(at+4))
 body.extend(b'\x58\x9d')
 guard=bytes(body)
 code=guard+b'\xd9\x5d\x24\xd9\x44\x24\x1c'+guard+b'\xd9\x5d\x34'
 return code+b'\xe9'+p(target-(origin+len(code)+5))

def plant_hook(runtime):
 key='plant_size';kind=edition(runtime.engine);rva=PLANT_HOOK[kind]
 if runtime.image[rva:rva+len(PLANT_ORIGINAL)]!=PLANT_ORIGINAL:raise RuntimeError('Plant scale routine differs from this build.')
 if key not in runtime.caves:
  address=runtime.native.k.VirtualAllocEx(runtime.native.handle,None,4096,0x3000,0x40)
  if not address or address>0xffffffff:raise RuntimeError('Could not allocate the plant scale hook.')
  runtime.caves[key]=address
 address=runtime.caves[key];parameter=address+0x300
 data=struct.pack('<f',percent(runtime.engine.plant_size_percent)/100)
 with runtime.native.suspended():
  if key not in runtime.manager.active:runtime.native.write_code(address,plant_scale_code(parameter,address,runtime.base+rva+len(PLANT_ORIGINAL),kind))
  runtime.engine.pm.write_bytes(parameter,data,4)
 return [(runtime.base+rva,PLANT_ORIGINAL,b'\xe9'+struct.pack('<I',(address-runtime.base-rva-5)&0xffffffff)+b'\x90'*(len(PLANT_ORIGINAL)-5))]

class ZombieSizes:
 """Identity-owned scale edits; never restore a recycled DataArray slot."""
 def __init__(self,game):self.game=game;self.token=None;self.saved={}
 def apply(self,value):
  factor=percent(value)/100;g=self.game
  with g.lock,g._native().suspended():
   token=g.lawn_token()
   if self.token!=token:self.saved.clear();self.token=token
   live={z['id']:z for z in g.entities('zombie')}
   self.saved={key:entry for key,entry in self.saved.items()if key in live and live[key]['address']==entry[0]}
   pending=[]
   for ident,z in live.items():
    address=z['address'];current=g.read(address+ZOMBIE_SCALE,'float')
    if not math.isfinite(current)or not .05<=current<=10:raise RuntimeError('Unexpected native zombie scale; no size update was made.')
    entry=self.saved.get(ident);baseline=entry[1]if entry and math.isclose(current,entry[2],rel_tol=1e-5)else current
    result=baseline*factor
    if not .0125<=result<=30:raise RuntimeError('Zombie scale is outside the verified range.')
    pending.append((ident,address,baseline,result))
   for ident,address,baseline,result in pending:
    g.write(address+ZOMBIE_SCALE,result,'float');self.saved[ident]=(address,baseline,result)
 def restore(self):
  g=self.game
  if not self.saved:self.token=None;return
  with g.lock,g._native().suspended():
   try:
    if g.lawn_token()==self.token:
     for z in g.entities('zombie'):
      entry=self.saved.get(z['id'])
      if entry and entry[0]==z['address'] and math.isclose(g.read(z['address']+ZOMBIE_SCALE,'float'),entry[2],rel_tol=1e-5):g.write(z['address']+ZOMBIE_SCALE,entry[1],'float')
   except RuntimeError:
    # Menus invalidate heap ownership; never dereference cached addresses.
    app=g.app();ui,mode=(0x7FC,0x7F8)if edition(g.engine)=='classic'else(0x91C,0x918)
    if g.read(app+ui)==3 and g.read(app+mode)not in (43,50):raise
   self.saved.clear();self.token=None
