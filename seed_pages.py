"""Paged native seed cards; at most the existing 1–10 slots are ever written."""
import math
from studio_models import integer

class SeedDeck:
 def __init__(self,game):self.g=game;self.active=False;self.page=0;self.cards=[];self.states={}
 def layout(self):
  classic=getattr(self.g.engine,'build_label','').startswith('Classic')
  return dict(bank=0x144 if classic else 0x15C,clock=0x5568 if classic else 0x5580,cursor=0x138 if classic else 0x150,mode=0x7F8 if classic else 0x918,level=0x5550 if classic else 0x5568)
 def clock(self):return self.g.read(self.g.board()+self.layout()['clock'])
 def packet(self,index):return self.bank+0x28+index*0x50
 def read_packet(self,index):
  a=self.packet(index);g=self.g
  return dict(type=g.read(a+0x34),imitater=g.read(a+0x38),elapsed=g.read(a+0x24),total=g.read(a+0x28),active=g.read(a+0x48,'byte'),refreshing=g.read(a+0x49,'byte'),used=g.read(a+0x4C),clock=self.clock())
 def write_packet(self,index,state):
  g=self.g;a=self.packet(index)
  for key,off in [('type',0x34),('imitater',0x38),('elapsed',0x24),('total',0x28),('used',0x4C)]:g.write(a+off,state[key])
  for key,off in [('active',0x48),('refreshing',0x49)]:g.write(a+off,state[key],'byte')
 def check(self,held=True):
  g=self.g;token=g.lawn_token()
  if token!=self.owner or g.pointer(g.board()+self.layout()['bank'])!=self.bank or g.read(self.bank+0x24)!=self.capacity:raise RuntimeError('The lawn or seed bank changed. Restart the scrolling deck on this lawn.')
  if held and g.read(g.pointer(g.board()+self.layout()['cursor'])+0x30)!=0:raise RuntimeError('Place or cancel the plant held by the cursor before changing pages.')
 def snapshot(self):
  self.check(False)
  for i,kind in enumerate(self.visible):
   state=self.read_packet(i)
   if state['type']!=kind:raise RuntimeError('A seed card changed outside the scrolling deck. Stop the deck before using the slot editor.')
   if kind>=0:self.states[kind]=state
 def start(self,cards):
  if not isinstance(cards,list)or not cards or len(cards)>48 or len(set(cards))!=len(cards):raise ValueError('Choose 1–48 different named plants.')
  for kind in cards:integer(kind,0,47,'Plant')
  g=self.g
  with g.lock,g.frozen():
   if self.active:self.stop()
   if g.read(g.app()+self.layout()['mode'])not in range(16):raise ValueError('Scrolling cards support normal Adventure and Survival lawns, not conveyor/minigame seed banks.')
   if g.read(g.app()+self.layout()['mode'])==0 and g.read(g.board()+self.layout()['level'])in range(5,51,5):raise ValueError('Adventure conveyor/special levels are not supported by the scrolling deck.')
   native=g.seed_bank();self.capacity=len(native);self.bank=g.pointer(g.board()+self.layout()['bank']);self.owner=g.lawn_token()
   self.original=[self.read_packet(i)for i in range(self.capacity)]
   if any(not 0<=s['type']<=48 or(s['type']==48 and not 0<=s['imitater']<48)for s in self.original):raise ValueError('The native bank contains an invalid seed. Restart PVZ before starting a deck.')
   if len({(s['type'],s['imitater'])for s in self.original})!=self.capacity:raise ValueError('Use a normal bank without duplicate cards before starting the scrolling deck.')
   self.cards=cards[:];self.states={s['type']:dict(s)for s in self.original};self.visible=[s['type']for s in self.original];self.page=0;self.active=True
   g.seed_deck=self
   try:self.show(0,capture=False)
   except Exception:self.active=False;raise
  return self.pages
 @property
 def pages(self):return math.ceil(len(self.cards)/self.capacity)if self.cards else 0
 def state(self,kind):
  now=self.clock();state=dict(self.states.get(kind,dict(type=kind,imitater=-1,elapsed=0,total=0,active=1,refreshing=0,used=0,clock=now)))
  if state['refreshing']:
   state['elapsed']+=max(0,now-state['clock'])
   if state['elapsed']>state['total']:state.update(elapsed=0,active=1,refreshing=0)
  state['clock']=now;return state
 def show(self,page,capture=True):
  if not self.active:raise RuntimeError('Start the scrolling deck first.')
  integer(page,0,self.pages-1,'Seed page');g=self.g
  with g.lock,g.frozen():
   self.check()
   if capture:self.snapshot()
   visible=self.cards[page*self.capacity:(page+1)*self.capacity]
   # Survival repick indexes ChosenSeeds[packet.type] without a bounds check.
   # Never put SEED_NONE (-1) in a counted slot: it overwrites button pointers.
   padding=self.cards+[s['type']for s in self.original if 0<=s['type']<48]+list(range(48))
   for kind in padding:
    if len(visible)>=self.capacity:break
    if kind not in visible:visible.append(kind)
   before=[self.read_packet(i)for i in range(self.capacity)]
   try:
    for i,kind in enumerate(visible):
     state=self.state(kind)
     self.write_packet(i,state)
   except Exception:
    for i,state in enumerate(before):self.write_packet(i,state)
    raise
   self.visible=visible;self.page=page
  return f'Seed page {page+1}/{self.pages}'
 def step(self,delta):return self.show((self.page+delta)%self.pages)
 def poll(self):
  if not self.active:return False
  try:
   with self.g.lock:self.check(False)
  except Exception:
   # The native chooser owns the bank now; never restore an old round over it.
   self.active=False;return False
  return True
 def stop(self):
  if not self.active:return
  g=self.g
  try:
   with g.lock,g.frozen():
    self.check(False);self.snapshot()
    for i,original in enumerate(self.original):
     state=self.state(original['type'])if original['type']in self.states else original
     self.write_packet(i,state)
  except RuntimeError:
   # An old board or externally modified bank is never overwritten.
   pass
  finally:self.active=False
