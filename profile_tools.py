"""Named GOTY profile edits. No arbitrary offsets or save-file identities accepted."""
import struct,time
from studio_models import integer

ACHIEVEMENTS=['Home Lawn Security','Nobel Peas Prize','Better Off Dead','China Shop','SPUDOW!','Explodonator','Morticulturalist',"Don't Pea in the Pool",'Roll Some Heads','Grounded','Zombologist','Penny Pincher','Sunny Days','Popcorn Party','Good Morning','No Fungus Among Us','Beyond the Grave','Immortal','Towering Wisdom','Mustache Mode']
# name: label, profile offset, minimum/maximum DISPLAY value, multiplier, bias
PROFILE_FIELDS={
 'coins':('Coin units (one unit = $10)',0x50,0,99999999,1,0),
 'adventure':('Next Adventure stage (1–50)',0x4C,1,50,1,0),
 'completed':('Completed Adventure runs',0x54,0,9999,1,0),
 'seed_slots':('Seed slots for future battles',0x23C,6,10,1,-6),
 'tree_height':('Tree of Wisdom height (feet)',0x11C,0,2000000000,1,0),
 'best_vasebreaker':('Longest streak — Vasebreaker Endless',0x144,0,1000000,1,0),
 'best_izombie':('Longest streak — I, Zombie Endless',0x16C,0,1000000,1,0),
 'best_survival_day':('Best flags — Survival Endless Day',0x80,0,1000000,1,0),
 'best_survival_night':('Best flags — Survival Endless Night',0x84,0,1000000,1,0),
 'best_survival_pool':('Best flags — Survival Endless Pool',0x88,0,1000000,1,0),
 'best_survival_fog':('Best flags — Survival Endless Fog',0x8C,0,1000000,1,0),
 'best_survival_roof':('Best flags — Survival Endless Roof',0x90,0,1000000,1,0),
 'minigames':('Minigames unlocked',0x348,0,1,1,0),
 'puzzle':('Puzzle mode unlocked',0x34C,0,1,1,0),
 'survival':('Survival mode unlocked',0x360,0,1,1,0),
 'mushroom_garden':('Mushroom garden owned',0x230,0,1,1,0),
 'aquarium_garden':('Aquarium garden owned',0x24C,0,1,1,0),
 'wheelbarrow':('Wheelbarrow owned',0x234,0,1,1,0),
 'tree_owned':('Tree of Wisdom owned',0x254,0,1,1,0),
}
GARDEN_CELLS={0:[(x,y)for y in range(4)for x in range(8)],1:[(x,0)for x in range(8)],2:[(0,0)],3:[(x,0)for x in range(8)]}
AQUATIC={16,19,24,43}

class ProfileTools:
    HAS_ACHIEVEMENTS=True
    def __init__(self,game):self.g=game
    def owner(self):return(self.g.user(),self.g.read(self.g.user()+0x20,'uint'),getattr(self.g.engine.pm,'process_id',0))
    def check_owner(self,owner):
        if owner is not None and tuple(owner)!=self.owner():raise RuntimeError('The active player changed. Read the profile again before applying edits.')
    def menu_only(self):
        if self.g.read(self.g.app()+0x91C)!=1:raise RuntimeError('Return to PVZ Main Menu before adding or moving saved garden plants. Then re-enter the garden to display them.')
    def _commit(self,writes,owner=None,verify=None):
        g=self.g;self.check_owner(owner);before=[]
        try:
            for address,data in writes:
                before.append((address,g.engine.pm.read_bytes(address,len(data))));g.engine.pm.write_bytes(address,data,len(data))
                if g.engine.pm.read_bytes(address,len(data))!=data:raise RuntimeError('Profile write verification failed.')
            g.save_profile()
            if verify:verify()
        except Exception:
            if not g._native().poisoned:
                for address,data in reversed(before):g.engine.pm.write_bytes(address,data,len(data))
                if before:g.save_profile()
            raise
    def _field(self,address,value,kind='int'):return(address,struct.pack({'int':'<i','time':'<q'}[kind],value))
    def read(self):
        g=self.g
        with g.lock,g.frozen():
            u=g.user();values={k:(g.read(u+v[1])-v[5])*v[4]for k,v in PROFILE_FIELDS.items()}
            earned=g.engine.pm.read_bytes(u+0x24,20)if self.HAS_ACHIEVEMENTS else bytes(20);shown=g.engine.pm.read_bytes(u+0x38,20)if self.HAS_ACHIEVEMENTS else bytes(20)
            if any(b not in (0,1)for b in earned+shown):raise RuntimeError('Achievement flags do not match the verified profile layout.')
            length=g.read(u+0x14,'uint');capacity=g.read(u+0x18,'uint');name='Local player'
            if 0<length<=256 and capacity>=length:
                data=g.engine.pm.read_bytes(u+4 if capacity<16 else g.pointer(u+4),length);name=data.decode('utf-8',errors='replace')
            return dict(achievements_supported=self.HAS_ACHIEVEMENTS,name=name,owner=self.owner(),values=values,earned=list(map(bool,earned)),shown=list(map(bool,shown)),garden_count=len(g.garden()))
    def edit(self,values,owner=None):
        if not isinstance(values,dict)or not values or set(values)-set(PROFILE_FIELDS):raise ValueError('Choose at least one supported profile field.')
        if 'coins'in values and getattr(self.g.engine,'money_changer_active',False):raise ValueError('Turn off Coin balance lock before editing saved coins.')
        for key,value in values.items():
            label,off,lo,hi,scale,bias=PROFILE_FIELDS[key];integer(value,lo,hi,label)
            if value%scale:raise ValueError('Coin balances must be multiples of $10.')
        g=self.g
        with g.lock,g.frozen():
            self.menu_only();self.check_owner(owner);u=g.user()
            if values.get('coins',0)>99999:g.engine.toggle_extended_bank(True)
            self._commit([self._field(u+PROFILE_FIELDS[k][1],v//PROFILE_FIELDS[k][4]+PROFILE_FIELDS[k][5])for k,v in values.items()],owner)
        return len(values)
    def achievements(self,changes,owner=None):
        if not self.HAS_ACHIEVEMENTS:raise ValueError('This Classic build has no native GOTY achievement flags.')
        if not isinstance(changes,dict)or not changes:raise ValueError('Change at least one achievement checkbox first.')
        for key,value in changes.items():
            integer(key,0,19,'Achievement ID')
            if type(value)is not bool:raise ValueError('Achievement state must be checked or unchecked.')
        g=self.g
        with g.lock:
            self.menu_only();self.check_owner(owner)
            verified=getattr(g.engine,'build_label','')=='GOTY 1.2.0.1073'
            if verified:
                from edition_saves import settings,prepare,activate,verify_achievements
                if not settings().get('enabled'):g.save_profile();prepare()
                activate(g.engine)
            with g.frozen():
                u=g.user();writes=[]
                for key,value in changes.items():
                    # Mark awarded flags as shown too, avoiding a burst of popups.
                    writes.extend([(u+0x24+key,bytes([value])),(u+0x38+key,bytes([value]))])
                self._commit(writes,owner,(lambda:verify_achievements(g.engine,changes))if verified else None)
        return len(changes)
    def bulk(self,action,garden=None,age=3):
        if action not in ('water','fertilize','growth','needs','chocolate'):raise ValueError('Unsupported bulk garden action.')
        if garden is not None:integer(garden,0,3,'Garden')
        if action=='growth':integer(age,0,3,'Growth')
        g=self.g;now=int(time.time());changed=skipped=0
        with g.lock,g.frozen():
            u=g.user();writes=[]
            for plant in g.garden():
                if garden is not None and plant['garden']!=garden:continue
                a=u+0x380+plant['index']*0x58
                if action=='fertilize'and(plant['age']>=3 or plant['fed']<max(1,plant['feedings'])):skipped+=1;continue
                changed+=1
                if action in ('water','needs'):
                    writes.extend([self._field(a+0x18,now,'time'),self._field(a+0x28,min(max(1,plant['feedings']),plant['fed']+1))])
                if action in ('growth','fertilize'):
                    value=age if action=='growth'else plant['age']+1
                    writes.extend([self._field(a+0x24,value),self._field(a+0x28,0),self._field(a+0x30,0),self._field(a+0x40,now,'time')])
                elif action=='needs':writes.extend([self._field(a+0x30,0),self._field(a+0x38,now,'time')])
                elif action=='chocolate':writes.append(self._field(a+0x48,now,'time'))
            if writes:self._commit(writes)
        return f'Updated {changed} plants; skipped {skipped} plants not ready for fertilizer. Re-read the collection; re-enter the garden to refresh visuals.'
    def free_cells(self,garden,records):
        used={(p['x'],p['y'])for p in records if p['garden']==garden}
        return[p for p in GARDEN_CELLS[garden]if p not in used]
    def destination(self,kind,garden):
        integer(garden,0,3,'Destination garden');integer(kind,0,47,'Plant')
        if garden==3 and kind not in AQUATIC:raise ValueError('Aquarium accepts only Lily Pad, Tangle Kelp, Sea-shroom or Cattail.')
        slot={1:18,2:19,3:25}.get(garden)
        if slot is not None and not self.g.read(self.g.user()+0x1E8+slot*4):raise ValueError('Buy or unlock the destination garden/wheelbarrow first.')
    def add(self,kind,garden,quantity=1,age=0):
        integer(kind,0,47,'Plant');integer(quantity,1,32,'Quantity');integer(age,0,3,'Growth')
        g=self.g
        with g.lock,g.frozen():
            self.menu_only();self.destination(kind,garden);records=g.garden();free=self.free_cells(garden,records)
            if len(records)+quantity>200 or len(free)<quantity:raise ValueError(f'Only {len(free)} free places in this garden. No plants were added.')
            u=g.user();writes=[]
            for i,(x,y)in enumerate(free[:quantity]):
                raw=bytearray(0x58)
                for off,v in [(0,kind),(4,garden),(8,x),(12,y),(0x24,age),(0x2C,3)]:struct.pack_into('<i',raw,off,v)
                writes.append((u+0x380+(len(records)+i)*0x58,bytes(raw)))
            writes.append(self._field(u+0x378,len(records)+quantity));self._commit(writes)
        return f'Added {quantity} saved plants. Re-enter the destination garden to display them.'
    def move(self,index,garden,stamp=None):
        integer(index,0,199,'Saved plant slot');g=self.g
        with g.lock,g.frozen():
            self.menu_only();records=g.garden();p=next((p for p in records if p['index']==index),None)
            if p is None:raise ValueError('Read the collection and select an existing plant.')
            if stamp is not None and tuple(stamp)!=p['stamp']:raise RuntimeError('The collection changed. Read it again before moving a plant.')
            self.destination(p['type'],garden)
            if p['garden']==garden:return 'This plant is already in the selected garden.'
            free=self.free_cells(garden,records)
            if not free:raise ValueError('The destination garden has no free places.')
            a=g.user()+0x380+index*0x58;x,y=free[0]
            self._commit([self._field(a+4,garden),self._field(a+8,x),self._field(a+12,y)])
        return 'Plant moved. Re-enter the destination garden to display it.'


def tools(game):return getattr(game.engine,'profile_tools_class',ProfileTools)(game)
