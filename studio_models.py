"""Strict JSON schemas and the bounded practice-spawn scheduler."""
import math,time
from collections import Counter
STACK_BLOCKED={16,30,33,35,47}
def plant_layer(kind):return 0 if kind in (16,33)else 2 if kind==30 else 3 if kind==35 else 1

ZOMBIES=['Normal','Flag','Conehead','Pole vault','Buckethead','Newspaper','Screen door','Football','Dancing','Backup dancer','Ducky tube','Snorkel','Zomboni','Bobsled team','Dolphin rider','Jack-in-the-box','Balloon','Digger','Pogo','Yeti','Bungee','Ladder','Catapult','Gargantuar','Imp','Dr. Zomboss','Peashooter zombie','Wall-nut zombie','Jalapeno zombie','Gatling zombie','Squash zombie','Tall-nut zombie','Giga-gargantuar']
EFFECTS={'Normal pea':0,'Chilling pea':1,'Melon splash':3,'Winter melon splash (slow)':5,'Fire splash':6,'Butter stun':12}
SCENES=['Day','Night','Pool','Fog','Roof','Moon roof']

def integer(value,low,high,label='Value'):
    if type(value)is not int or not low<=value<=high:raise ValueError(f'{label} must be an integer from {low} to {high}.')
    return value

def formation(value,require_support=True,allow_cattail=False):
    if not isinstance(value,dict)or value.get('version')not in (1,2):raise ValueError('Invalid formation document.')
    keys={'version','scene','plants'}|({'stack'}if value['version']==2 else set())
    if set(value)!=keys:raise ValueError('Invalid formation fields.')
    stack=value.get('stack',False)
    if type(stack)is not bool:raise ValueError('Stacking must be true or false.')
    scene=integer(value['scene'],0,5);rows=6 if scene in (2,3)else 5
    plants=value['plants']
    if not isinstance(plants,list)or len(plants)>250:raise ValueError('Formation is too large.')
    result=[];used=set();counts=Counter();owners={}
    for p in plants:
        if not isinstance(p,dict)or set(p)!={'type','row','col','imitater'}:raise ValueError('Invalid formation plant.')
        kind=integer(p['type'],0,47);r=integer(p['row'],1,rows);c=integer(p['col'],1,8 if kind==47 else 9)
        if type(p['imitater'])is not bool:raise ValueError('Invalid imitater flag.')
        layer=plant_layer(kind)
        key=(r,c,layer)
        if key in used and(not stack or kind in STACK_BLOCKED or owners[key]in STACK_BLOCKED):raise ValueError('Formation has overlapping plants in the same layer. Enable ordinary-plant stacking to share a cell.')
        counts[key]+=1
        if counts[key]>8:raise ValueError('At most 8 ordinary plants may share one cell.')
        used.add(key);owners.setdefault(key,kind)
        if kind==47:
            if (r,c+1,layer)in used:raise ValueError('Cob cannon overlaps another plant.')
            used.add((r,c+1,layer));owners[(r,c+1,layer)]=kind;counts[(r,c+1,layer)]=1
        result.append(dict(type=kind,row=r,col=c,imitater=p['imitater']))
    result.sort(key=lambda p:(0 if p['type']in (16,33)else 2 if p['type']==30 else 3 if p['type']==35 else 1,p['row'],p['col']))
    bases={(p['row'],p['col']):p['type']for p in result if p['type']in (16,33)}
    for p in result:
        r,c,t=p['row'],p['col'],p['type'];water=scene in (2,3)and r in (3,4)
        if t in (16,19,24)and not water:raise ValueError('Aquatic plants require a pool row.')
        for column in (c,c+1)if t==47 else(c,):
            if require_support and water and t not in (16,19,24)and not(t==43 and allow_cattail)and bases.get((r,column))!=16:raise ValueError('Formation needs lily pads beneath every occupied pool cell.')
            if require_support and scene in (4,5)and t!=33 and bases.get((r,column))!=33:raise ValueError('Formation needs pots beneath every occupied roof cell.')
    return dict(version=value['version'],scene=scene,plants=result,**({'stack':stack}if value['version']==2 else{}))

def wave_plan(value):
    if not isinstance(value,dict)or set(value)!={'version','entries'}or value['version']!=1:raise ValueError('Invalid wave document.')
    entries=value['entries']
    if not isinstance(entries,list)or not 1<=len(entries)<=100:raise ValueError('Use 1–100 wave entries.')
    result=[];count=0
    for e in entries:
        if not isinstance(e,dict)or set(e)!={'type','row','quantity','interval_ms','delay_ms'}:raise ValueError('Invalid wave entry.')
        kind=integer(e['type'],0,32)
        if kind==25:raise ValueError('Dr. Zomboss requires the dedicated boss stage.')
        row=integer(e['row'],1,6);quantity=integer(e['quantity'],1,100);count+=quantity
        result.append(dict(type=kind,row=row,quantity=quantity,interval_ms=integer(e['interval_ms'],50,60000),delay_ms=integer(e['delay_ms'],0,600000)))
    if count>500:raise ValueError('A practice wave is limited to 500 zombies.')
    return {'version':1,'entries':result}

class SpawnSchedule:
    def __init__(self,clock=time.monotonic):self.clock=clock;self.queue=[];self.board=None;self.error=''
    def start(self,value,board,rows):
        plan=wave_plan(value);queue=[];now=self.clock()
        for e in plan['entries']:
            if e['row']>rows:raise ValueError('This wave uses a row absent from the current lawn.')
            for i in range(e['quantity']):queue.append((now+(e['delay_ms']+i*e['interval_ms'])/1000,e['type'],e['row']))
        self.queue=sorted(queue);self.board=board;self.error=''
    def cancel(self):self.queue=[];self.board=None
    def tick(self,board,spawn):
        if self.board is None:return 0
        if board!=self.board:self.cancel();self.error='Spawn queue cancelled: lawn changed.';return 0
        count=0
        while self.queue and self.queue[0][0]<=self.clock()and count<4:
            _,kind,row=self.queue.pop(0)
            try:spawn(kind,row)
            except Exception as error:self.cancel();self.error=str(error);raise
            count+=1
        if not self.queue:self.board=None
        return count
