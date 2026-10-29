"""Exact-build lawn/entity editors; separate from the legacy patch engine."""
from contextlib import nullcontext
from pathlib import Path
import hashlib,math,struct,threading,time
import pymem.process
from studio_models import integer,formation,wave_plan,SpawnSchedule,EFFECTS,STACK_BLOCKED,plant_layer
from studio_native import NativeCalls,push,mov,call,u32
from game_layout import COIN_ARRAY,COIN_COLLECT,ROW_TYPES

HASH='1ff5a2dcf009b453b8866783a68e8d04bd0d066abda3f8196d75a677366b2dff'
FORMATS={'int':'<i','uint':'<I','byte':'<B','float':'<f','time':'<q'}
ARRAYS={'plant':(0xC4,0x14C,0x141,0x148),'zombie':(0xA8,0x168,0xEC,0x164),'projectile':(0xE0,0x94,0x50,0x90)}
PLANT_FIELDS={'health':(0x40,'int',1,1000000),'max_health':(0x44,'int',1,1000000),'attack_timer':(0x58,'int',0,60000),'attack_interval':(0x5C,'int',1,60000)}
ZOMBIE_FIELDS={'health':(0xC8,'int',1,1000000),'max_health':(0xCC,'int',1,1000000),'armour':(0xD0,'int',0,1000000),'max_armour':(0xD4,'int',0,1000000),'shield':(0xDC,'int',0,1000000),'max_shield':(0xE0,'int',0,1000000),'speed':(0x34,'float',0,5),'chilled':(0xAC,'int',0,60000),'buttered':(0xB0,'int',0,60000),'frozen':(0xB4,'int',0,60000)}
SIGNATURES={0xFA10:'5153558b6c24105657',0x2CC90:'53558b6c240c5657',0x6B470:'83ec1053558b6c241c',0x52820:'64a1000000006aff',0x52640:'8b87740800005685c0',0x52C70:'8b867008000085c0',0x52800:'518b804c090000',0x1E8A0:'535533db33c05783',0x142240:'51568bf08b466c83'}

class StudioGame:
    def __init__(self,engine,verify=None,native=None):
        self.engine=engine;self.base=engine.base_address;self.lock=getattr(engine,'operation_lock',None)or threading.RLock();self._verify=verify;self._checked=None
        self.native=native;self.schedule=SpawnSchedule();self.effect=None;self.effect_board=None;self.damage_original={};self.edits={}
        self._lawn_seen=None;self._generation=0
    def guard(self):
        if not self.engine.is_connected or not self.engine.pm:raise RuntimeError('Connect to PVZ first.')
        if self._checked is not self.engine.pm:
            if self._verify:self._verify()
            else:
                m=pymem.process.module_from_name(self.engine.pm.process_handle,self.engine.attached_process_name)
                if not m or m.SizeOfImage!=0x415000 or hashlib.sha256(Path(m.filename).read_bytes()).hexdigest()!=HASH:raise RuntimeError('LawnLab requires the verified GOTY 1.2.0.1073 executable. Other builds are not supported.')
            self._checked=self.engine.pm
        return True
    def read(self,a,kind='int'):
        fmt=FORMATS[kind];return struct.unpack(fmt,self.engine.pm.read_bytes(a,struct.calcsize(fmt)))[0]
    def write(self,a,value,kind='int'):
        data=struct.pack(FORMATS[kind],value);self.engine.pm.write_bytes(a,data,len(data))
    def pointer(self,a):
        value=self.read(a,'uint')
        if not 0x10000<value<0x7fff0000:raise RuntimeError('Game object is not available.')
        return value
    def app(self):self.guard();return self.pointer(self.base+0x329670)
    def board(self,playing=True):
        app=self.app()
        if playing and self.read(app+0x91C)!=3:
            self.invalidate_lawn();raise RuntimeError('Open a live lawn first; menu/seed-selection edits are blocked.')
        b=self.pointer(app+0x868);scene=self.read(b+0x5564)
        if not 0<=scene<=5:raise RuntimeError('Unsupported lawn scene.')
        current=(b,scene,self.read(b+0x5568),self.read(b+0x5580))
        if self._lawn_seen is not None and(current[:3]!=self._lawn_seen[:3]or current[3]<self._lawn_seen[3]):self._generation+=1
        self._lawn_seen=current
        return b
    def invalidate_lawn(self):
        if self._lawn_seen is not None:self._generation+=1;self._lawn_seen=None
        self.schedule.cancel();self.edits.clear()
    def lawn_token(self):return self.board(),self._generation
    def scene(self):return self.read(self.board()+0x5564)
    def rows(self):return 6 if self.scene()in (2,3)else 5
    def _native(self):
        if self.native is None:self.native=NativeCalls(self)
        return self.native
    def frozen(self):return self._native().frozen()
    def _signature(self,rva):
        expected=bytes.fromhex(SIGNATURES[rva])
        if self.engine.pm.read_bytes(self.base+rva,len(expected))!=expected:raise RuntimeError('Native routine bytes changed; stop overlapping trainers.')
    def entities(self,kind):
        if kind not in ARRAYS:raise ValueError('Unknown entity kind.')
        b=self.board();token=(b,self._generation);off,stride,dead,identity=ARRAYS[kind];data=self.pointer(b+off);count=self.read(b+off+4)
        if not 0<=count<=4096:raise RuntimeError('Invalid entity-array bound.')
        blob=self.engine.pm.read_bytes(data,count*stride)if count else b'';result=[]
        for i in range(count):
            cell=blob[i*stride:(i+1)*stride]
            get=lambda o,k='int':struct.unpack_from(FORMATS[k],cell,o)[0]
            ident=get(identity,'uint')
            if cell[dead]or not ident>>16:continue
            row=get(0x1C)+1
            if not 1<=row<=6:continue
            record={'id':ident,'address':data+i*stride,'board':token,'kind':kind,'row':row}
            if kind=='plant':
                if cell[0x142]:continue
                record.update(type=get(0x24),col=get(0x28)+1,imitater=get(0x138)==48)
                record.update({k:get(v[0],v[1])for k,v in PLANT_FIELDS.items()})
            elif kind=='zombie':
                record.update(type=get(0x24),x=get(0x2C,'float'),y=get(0x30,'float'),state=get(0x28),helm_type=get(0xC4),shield_type=get(0xD8))
                record.update({k:get(v[0],v[1])for k,v in ZOMBIE_FIELDS.items()})
            else:record.update(type=get(0x5C),x=get(0x30,'float'),y=get(0x34,'float'),motion=get(0x58))
            if kind!='projectile'and not 0<=record['type']<=(52 if kind=='plant'else 32):raise RuntimeError('Entity fields do not match this build.')
            result.append(record)
        if self.lawn_token()!=token:raise RuntimeError('The lawn changed while reading entities.')
        return result
    def telemetry(self):
        app=self.app();result={'ui':self.read(app+0x91C),'mode':self.read(app+0x918),'queued':len(self.schedule.queue)}
        if result['mode']in (43,50):
            self.invalidate_lawn();return dict(result,status=('Zen Garden'if result['mode']==43 else'Tree of Wisdom')+' — saved collection tools available',sun=None,plants=0,zombies=0,queued=0)
        if result['ui']!=3:
            self.invalidate_lawn();return dict(result,status='Open a live lawn',sun=None,plants=0,zombies=0)
        b=self.board();result.update(board=b,scene=self.scene(),rows=self.rows(),sun=self.read(b+0x5578),wave=self.read(b+0x5594),waves=self.read(b+0x557C),plants=len(self.entities('plant')),zombies=len(self.entities('zombie')),status='Live lawn')
        return result
    def coins(self):
        b=self.board();off,stride,dead,identity=COIN_ARRAY;data=self.pointer(b+off);count=self.read(b+off+4)
        if not 0<=count<=4096:raise RuntimeError('Invalid coin array bound.')
        records=[]
        for i in range(count):
            address=data+i*stride;ident=self.read(address+identity,'uint')
            if ident>>16 and not self.read(address+dead,'byte')and self.read(address+0x58)in (1,2,3)and not self.read(address+0x50,'byte'):
                records.append((address,ident))
        return records
    def collect_coins(self):
        with self.lock:
            if not self.coins():return 0
            with self.frozen():
                coins=self.coins()[:8]
                if not coins:return 0
                if self.engine.pm.read_bytes(self.base+COIN_COLLECT,8)!=bytes.fromhex('558bec83e4f86aff'):raise RuntimeError('Coin collection routine changed; stop other memory editors.')
                def build(origin,result):
                    code=b''
                    for address,ident in coins:
                        code+=mov('ecx',address);code+=call(origin+len(code),self.base+COIN_COLLECT)
                    return code
                self._native().execute(build);return len(coins)
    def move_zombies(self,row,selected_ids=None):
        integer(row,1,self.rows(),'Destination row');moved=skipped=0
        with self.lock,self.frozen():
            b=self.board();terrain=self.read(b+ROW_TYPES+(row-1)*4)
            if terrain not in (1,2):raise ValueError('This row is not active on the current lawn.')
            operations=[];zombies=self.entities('zombie')
            if selected_ids is not None and selected_ids-{z['id']for z in zombies}:raise RuntimeError('The selected zombie disappeared. Refresh the list.')
            for z in zombies:
                if selected_ids is not None and z['id']not in selected_ids:continue
                if z['row']==row:continue
                old_terrain=self.read(b+ROW_TYPES+(z['row']-1)*4)
                if old_terrain!=terrain or z['type']in (8,9,10,11,13,14,16,17,20,22,25)or z['state']!=0:skipped+=1;continue
                operations.append(z)
            if operations:
                self._signature(0x142240)
                def build(origin,result):
                    code=b''
                    for z in operations:
                        address=z['address'];delta=(row-z['row'])*10000
                        code+=b'\xc7\x05'+u32(address+0x1c)+u32(row-1)+b'\x81\x05'+u32(address+0x20)+u32(delta)
                        code+=mov('eax',address)+push(row-1);code+=call(origin+len(code),self.base+0x142240)
                        code+=b'\xd9\x1d'+u32(result)+b'\xa1'+u32(result)+b'\xa3'+u32(address+0x30)
                        code+=b'\xf3\x0f\x2c\x05'+u32(result)+b'\xa3'+u32(address+0xC)
                    return code
                self._native().execute(build);moved=len(operations)
        return {'moved':moved,'skipped':skipped}
    def place_plant(self,kind,row,col,imitater=False,stack=False):
        if self.engine.plant_changer_active:raise ValueError('Disable the legacy Plant changer before placing an explicit plant type.')
        integer(kind,0,47,'Plant');integer(row,1,self.rows(),'Row');integer(col,1,8 if kind==47 else 9,'Column')
        if type(imitater)is not bool:raise ValueError('Invalid imitater flag.')
        if type(stack)is not bool:raise ValueError('Invalid stacking flag.')
        if imitater:raise ValueError('Imitater placement is not enabled until its transformation routine is verified. Use a normal plant.')
        with self.lock,self.frozen():
            b=self.board();scene=self.scene();existing=self.entities('plant')
            if len(existing)>=250:raise ValueError('This lawn has reached the Studio limit of 250 plants.')
            layer=lambda t:0 if t in (16,33)else 2 if t==30 else 3 if t==35 else 1
            cells={col,col+1}if kind==47 else{col}
            for p in existing:
                occupied={p['col'],p['col']+1}if p['type']==47 else{p['col']}
                if p['row']==row and layer(p['type'])==layer(kind)and cells&occupied:
                    if not stack or kind in STACK_BLOCKED or p['type']in STACK_BLOCKED:raise ValueError('A plant already occupies this layer/cell.')
            if sum(p['row']==row and p['col']==col and layer(p['type'])==layer(kind)for p in existing)>=8:raise ValueError('At most 8 ordinary plants may share one cell.')
            water=scene in (2,3)and row in (3,4)
            if (kind in (16,19,24)or(kind==43 and not getattr(self.engine,'cattail_land_active',False)))and not water:raise ValueError('This aquatic plant requires a pool row.')
            for column in (col,col+1)if kind==47 else(col,):
                if not getattr(self.engine,'no_support_active',False) and water and kind not in (16,19,24,43)and not any(p['type']==16 and p['row']==row and p['col']==column for p in existing):raise ValueError('Place a lily pad in every occupied pool cell first.')
                if not getattr(self.engine,'no_support_active',False) and scene in (4,5)and kind!=33 and not any(p['type']==33 and p['row']==row and p['col']==column for p in existing):raise ValueError('Place a flower pot in every occupied roof cell first.')
            self._signature(0xFA10)
            def build(origin,result):
                payload=push(-1)+push(kind)+mov('eax',row-1)+push(col-1)+push(b)
                return payload+call(origin+len(payload),self.base+0xFA10)+b'\xA3'+u32(result)
            address=self._native().execute(build)
            found=next((p for p in self.entities('plant')if p['address']==address),None)
            if not found:raise RuntimeError('Plant creation did not return a valid entity.')
            return found
    def spawn_zombie(self,kind,row,col=9):
        if self.engine.move_zombie_row_active:raise ValueError('Disable the legacy Choose a lane override before custom spawning.')
        integer(kind,0,32,'Zombie');integer(row,1,self.rows(),'Row');integer(col,1,10,'Column')
        if kind==25:raise ValueError('Dr. Zomboss requires the dedicated boss stage.')
        if kind in (10,11,14)and not(self.scene()in (2,3)and row in (3,4)):raise ValueError('This zombie requires a pool row.')
        if self.scene()in (2,3)and row in (3,4)and kind not in (0,1,2,4,10,11,14,16,20):raise ValueError('This zombie is not enabled on water rows.')
        with self.lock,self.frozen():
            if len(self.entities('zombie'))+(4 if kind==13 else 1)>500:raise ValueError('Spawning would exceed the Studio limit of 500 live zombies.')
            b=self.board();challenge=self.pointer(b+0x178);self._signature(0x2CC90)
            def build(origin,result):
                payload=push(col-1)+push(kind)+mov('eax',row-1)+mov('ecx',challenge)
                return payload+call(origin+len(payload),self.base+0x2CC90)+b'\xA3'+u32(result)
            return self._native().execute(build)
    def start_practice(self,value):
        plan=wave_plan(value)
        if self.engine.move_zombie_row_active:raise ValueError('Turn off Choose a lane before using a setup with explicit lanes. Move existing zombies can still be used separately.')
        with self.lock,self.frozen():
            scene=self.scene();rows=self.rows()
            for entry in plan['entries']:
                kind,lane=entry['type'],entry['row'];water=scene in (2,3)and lane in (3,4)
                if lane>rows:raise ValueError(f'Row {lane} does not exist on this lawn.')
                if kind in (10,11,14)and not water:raise ValueError('Ducky tube, Snorkel and Dolphin rider groups need a pool row (3 or 4).')
                if water and kind not in (0,1,2,4,10,11,14,16,20):raise ValueError('This zombie group is not supported on a water row.')
            planned=sum(e['quantity']*(4 if e['type']==13 else 1)for e in plan['entries'])
            if len(self.entities('zombie'))+planned>500:raise ValueError('The setup plus current zombies would exceed 500 live zombies. Clear some zombies or reduce the setup.')
            self.schedule.start(plan,self.lawn_token(),rows);return len(self.schedule.queue)
    def edit_entity(self,kind,ident,values,owner=None):
        fields=PLANT_FIELDS if kind=='plant'else ZOMBIE_FIELDS if kind=='zombie'else{}
        if not values or set(values)-set(fields):raise ValueError('Unknown or empty entity edit.')
        for key,value in values.items():
            _,fmt,lo,hi=fields[key]
            if fmt=='float':
                if type(value)not in (int,float)or not math.isfinite(value)or not lo<=value<=hi:raise ValueError('Invalid speed.')
            else:integer(value,lo,hi,key)
        with self.lock,self.frozen():
            if owner is not None and owner!=self.lawn_token():raise RuntimeError('The selected entity belongs to an earlier lawn. Refresh the inspector.')
            e=next((p for p in self.entities(kind)if p['id']==ident),None)
            if not e:raise RuntimeError('Entity disappeared or its slot was reused. Refresh the inspector.')
            if e['health']<=0 or(kind=='zombie'and e['state']in (1,2,3)):raise RuntimeError('This object is already dying. Refresh and choose a living object.')
            if values.get('health',e['health'])>values.get('max_health',e['max_health']):raise ValueError('Health cannot exceed maximum health.')
            if kind=='zombie':
                for health,maximum,gear in [('armour','max_armour','helm_type'),('shield','max_shield','shield_type')]:
                    if health in values or maximum in values:
                        if e[gear]==0 and(values.get(health,0)>0 or values.get(maximum,0)>0):raise ValueError('This zombie has no corresponding armour/shield equipment. Spawn an equipped type first.')
                        if values.get(health,e[health])>values.get(maximum,e[maximum]):raise ValueError('Equipment health cannot exceed its maximum; set both fields if increasing the limit.')
            for key,value in values.items():
                off,fmt,_,_=fields[key];token=(e['board'],kind,ident,off,fmt)
                self.edits.setdefault(token,self.read(e['address']+off,fmt));self.write(e['address']+off,value,fmt)
            return e['id']
    def capture_formation(self):
        plants=[{k:p[k]for k in ('type','row','col','imitater')}for p in self.entities('plant')if p['type']<48]
        return formation({'version':2,'scene':self.scene(),'stack':True,'plants':plants},require_support=False)
    def place_many(self,kind,row_start,row_end,col_start,col_end,copies=1,stack=False,skip_occupied=True,auto_bases=True,limit=None,available_only=False):
        integer(kind,0,47,'Plant');integer(row_start,1,self.rows(),'First row');integer(row_end,row_start,self.rows(),'Last row')
        integer(col_start,1,8 if kind==47 else 9,'First column');integer(col_end,col_start,8 if kind==47 else 9,'Last column');integer(copies,1,8,'Copies per cell')
        if any(type(v)is not bool for v in (stack,skip_occupied,auto_bases)):raise ValueError('Invalid placement options.')
        if copies>1 and(not stack or kind in STACK_BLOCKED):raise ValueError('Multiple copies require ordinary-plant stacking. Foundations, pumpkins, coffee and cob cannons cannot be stacked.')
        if limit is not None:integer(limit,1,250,'Total plant quantity')
        with self.lock,self.frozen():
            existing=self.entities('plant');planned=[];scene=self.scene();selected=0
            for row in range(row_start,row_end+1):
                for col in range(col_start,col_end+1,2 if kind==47 else 1):
                    if limit is not None and selected>=limit:break
                    if available_only and kind in (16,19,24)and not(scene in (2,3)and row in (3,4)):continue
                    cells={col,col+1}if kind==47 else{col}
                    if skip_occupied and not stack and any(p['row']==row and plant_layer(p['type'])==plant_layer(kind)and cells&({p['col'],p['col']+1}if p['type']==47 else{p['col']})for p in existing):continue
                    base=16 if scene in (2,3)and row in (3,4)and kind not in (16,19,24)else 33 if scene in (4,5)and kind!=33 else None
                    if auto_bases and not getattr(self.engine,'no_support_active',False) and not(kind==43 and base==16 and getattr(self.engine,'cattail_land_active',False)) and base is not None:
                        for column in sorted(cells):
                            if not any(p['type']==base and p['row']==row and p['col']==column for p in existing+planned):planned.append(dict(type=base,row=row,col=column,imitater=False))
                    amount=min(copies,limit-selected)if limit is not None else copies
                    planned.extend(dict(type=kind,row=row,col=col,imitater=False)for _ in range(amount));selected+=amount
            if limit is not None and selected<limit:raise ValueError(f'Only {selected} available placements fit; requested {limit}. No plants were placed.')
            if not planned:return 0
            return self.apply_formation({'version':2,'scene':scene,'stack':stack,'plants':planned},merge=True)
    def apply_formation(self,value,merge=False):
        value=formation(value,require_support=not getattr(self.engine,'no_support_active',False),allow_cattail=getattr(self.engine,'cattail_land_active',False))
        if value['scene']!=self.scene():raise ValueError('Formation scene differs from this lawn.')
        if any(p['imitater']for p in value['plants']):raise ValueError('Imitater formations require a separately verified transformation routine.')
        with self.lock,self.frozen():
            existing=self.capture_formation()['plants'];stack=value.get('stack',False)
            if existing and not merge:raise ValueError('Use Add to current lawn or start with an empty lawn. Existing plants are never removed automatically.')
            planned=value['plants']
            if merge and not stack:planned=[p for p in planned if not any((e['type'],e['row'],e['col'])==(p['type'],p['row'],p['col'])for e in existing)]
            if len(existing)+len(planned)>250:raise ValueError('The combined lawn would exceed 250 plants.')
            # Check the whole merged layout before making the first native call.
            if not stack:
                layer=lambda t:0 if t in (16,33)else 2 if t==30 else 3 if t==35 else 1
                if any(e['row']==p['row']and e['col']==p['col']and layer(e['type'])==layer(p['type'])for e in existing for p in planned):raise ValueError('A planned cell already has a different plant. Enable ordinary-plant stacking or choose another cell.')
            formation({'version':2,'scene':value['scene'],'stack':True,'plants':existing+planned},require_support=False)
            if planned:
                self._signature(0x1E8A0)
                def cleanup(origin,result):
                    code=mov('esi',self.board());return code+call(origin+len(code),self.base+0x1E8A0)
                self._native().execute(cleanup)
            created=[]
            try:
                for p in planned:created.append(self.place_plant(p['type'],p['row'],p['col'],stack=stack))
            except Exception as error:raise RuntimeError(f'Formation stopped after {len(created)} plants: {error}')from error
            return len(created)
    def seed_bank(self):
        b=self.board();bank=self.pointer(b+0x15C);count=self.read(bank+0x24)
        if not 1<=count<=10:raise RuntimeError('No editable seed bank in this mode (conveyor/minigame may differ).')
        return [{'slot':i+1,'type':self.read(bank+0x5C+i*0x50),'imitater':self.read(bank+0x60+i*0x50),'elapsed':self.read(bank+0x4C+i*0x50),'total':self.read(bank+0x50+i*0x50)}for i in range(count)]
    def set_seed(self,slot,kind,imitater=False,allow_duplicates=False):
        if getattr(self,'seed_deck',None)and self.seed_deck.active:raise RuntimeError('Stop the scrolling deck before editing individual seed slots.')
        integer(kind,0,47,'Plant');integer(slot,1,10,'Slot')
        with self.lock,self.frozen():
            cards=self.seed_bank()
            if slot>len(cards):raise ValueError('Slot is not present in this seed bank.')
            if not allow_duplicates and any(c['slot']!=slot and c['type']==(48 if imitater else kind)for c in cards):raise ValueError('Duplicate seed; explicitly enable duplicate testing to apply it.')
            bank=self.pointer(self.board()+0x15C)
            self.write(bank+0x5C+(slot-1)*0x50,48 if imitater else kind);self.write(bank+0x60+(slot-1)*0x50,kind if imitater else-1)
            self.write(bank+0x4C+(slot-1)*0x50,self.read(bank+0x50+(slot-1)*0x50))
    def set_wave(self,wave,types):
        integer(wave,1,100,'Wave')
        if not isinstance(types,list)or not 1<=len(types)<=50:raise ValueError('Use 1–50 zombie IDs.')
        for t in types:
            integer(t,0,32,'Zombie')
            if t==25:raise ValueError('Boss spawning requires the boss stage.')
        with self.lock,self.frozen():
            b=self.board();current=self.read(b+0x5594);total=self.read(b+0x557C)
            if not current<wave<=min(total,100):raise ValueError('Choose an upcoming wave within this level.')
            data=struct.pack('<50i',*(types+[-1]*(50-len(types))));self.engine.pm.write_bytes(b+0x6CC+(wave-1)*200,data,len(data))
    def set_projectile_damage(self,kind,damage):
        integer(kind,0,12,'Projectile');integer(damage,0,100000,'Damage');self.guard()
        with self.lock,self.frozen():
            table=self.base+0x31E900
            if self.read(table+kind*12)!=kind:raise RuntimeError('Projectile definition mismatch.')
            self.damage_original.setdefault(kind,self.read(table+kind*12+8));self.write(table+kind*12+8,damage)
    def tick(self):
        with self.lock:
            b=self.lawn_token()
            if self.schedule.queue and self.schedule.queue[0][0]<=self.schedule.clock():
                with self.frozen():self.schedule.tick(b,self.spawn_zombie)
            elif self.schedule.board is not None and b!=self.schedule.board:self.schedule.cancel()
            if self.effect is not None:
                if b!=self.effect_board:self.enable_effect(None);return
                # Creation-time patch avoids racing a projectile's destruction.
    def enable_effect(self,effect):
        if effect is not None and effect not in EFFECTS.values():raise ValueError('Unknown effect.')
        if effect is None and self.effect is None:return
        with self.lock,self.frozen():
            if effect is not None:
                self.effect_board=self.lawn_token()
                if self.effect is None:self._effect_before=(self.engine.bullet_changer_active,self.engine.bullet_changer_value)
                if self.engine.set_bullet_changer_value(effect)is False:raise RuntimeError('Could not set projectile behavior.')
                if not self.engine.bullet_changer_active:
                    address=self.base+0x70E29
                    if self.engine.pm.read_bytes(address,5)!=bytes.fromhex('89455c8bc6'):raise RuntimeError('Projectile creation bytes differ; stop overlapping patches.')
                    if self.engine.toggle_bullet_changer(True)is False:
                        self._native().write_code(address,bytes.fromhex('89455c8bc6'))
                        raise RuntimeError('Could not activate the creation-time projectile patch.')
            elif self.effect is not None:
                enabled,value=self._effect_before
                if getattr(self.engine,'safe_runtime_enabled',False):self.engine.toggle_bullet_changer(False)
                else:
                    address=self.engine.bullet_patch_addr;cave=self.engine.bullet_changer_cave
                    if address:
                        self._native().write_code(address,self.engine.original_bullet_bytes)
                        if cave:self.engine.pm.free(cave)
                        self.engine.bullet_patch_addr=self.engine.bullet_changer_cave=self.engine.original_bullet_bytes=None
                    self.engine.bullet_changer_active=False
                self.engine.set_bullet_changer_value(value)
                if enabled and self.engine.toggle_bullet_changer(True)is False:raise RuntimeError('Previous projectile mode could not be restored.')
            self.effect=effect
    def user(self):return self.pointer(self.app()+0x94C)
    def garden(self):
        u=self.user();count=self.read(u+0x378)
        if not 0<=count<=200:raise RuntimeError('Garden profile layout mismatch.')
        result=[]
        for i in range(count):
            a=u+0x380+i*0x58;p={'index':i,'type':self.read(a),'garden':self.read(a+4),'age':self.read(a+0x24),'fed':self.read(a+0x28),'feedings':self.read(a+0x2C),'need':self.read(a+0x30)}
            p.update(x=self.read(a+8),y=self.read(a+12));p['stamp']=(u,self.read(u+0x20,'uint'),p['type'],p['garden'],p['x'],p['y'],getattr(self.engine.pm,'process_id',0))
            if not 0<=p['type']<48 or not 0<=p['garden']<=3 or not 0<=p['age']<=3:raise RuntimeError('Garden entry failed validation.')
            result.append(p)
        return result
    def garden_edit(self,index,action,value=0,stamp=None):
        integer(index,0,199,'Garden plant')
        if action not in ('water','fertilize','growth'):raise ValueError('Unknown garden action.')
        if action=='growth':integer(value,0,3,'Growth stage')
        with self.lock,self.frozen():
            plant=next((p for p in self.garden()if p['index']==index),None)
            if plant is None:raise ValueError('Garden plant is not present.')
            if stamp is not None and tuple(stamp)!=plant['stamp']:raise RuntimeError('The saved collection changed. Read it again and select the plant before editing.')
            a=self.user()+0x380+index*0x58;now=int(time.time())
            if action=='water':
                self.write(a+0x18,now,'time');self.write(a+0x28,min(1000,plant['fed']+1))
            elif action=='fertilize':
                if plant['age']>=3:raise ValueError('Mature plants do not need fertilizer. Use water or the explicit growth editor.')
                if plant['fed']<max(1,plant['feedings']):raise ValueError('Water this plant until its feeding requirement is met before fertilizing.')
                self.write(a+0x24,plant['age']+1);self.write(a+0x40,now,'time');self.write(a+0x28,0);self.write(a+0x30,0)
            else:
                self.write(a+0x24,value);self.write(a+0x28,0);self.write(a+0x30,0)
            self.save_profile()
    def garden_inventory(self,kind,amount):
        slots={'fertilizer':14,'bug spray':15,'chocolate':26,'tree food':28}
        if kind not in slots:raise ValueError('Unknown supply.')
        integer(amount,0,999,'Supply count')
        with self.lock,self.frozen():self.write(self.user()+0x1E8+slots[kind]*4,1000+amount);self.save_profile()
    def save_profile(self):
        self._signature(0x52800)
        def build(origin,result):
            payload=mov('eax',self.app());return payload+call(origin+len(payload),self.base+0x52800)
        return self._native().execute(build)
    def launch_level(self,level,mode=0):
        integer(level,1,50,'Adventure level');integer(mode,0,73,'Mode')
        if mode not in (*range(16),43):raise ValueError('Mode is not enabled in the verified launcher.')
        with self.lock:
            app=self.app();ui=self.read(app+0x91C)
            if ui not in (1,3):raise RuntimeError('Open the main menu or resume a lawn before launching a stage.')
            if ui==3 and self.read(self.pointer(app+0x868)+0x17C,'byte'):raise RuntimeError('Close the PVZ menu/dialog and resume the lawn before launching a stage.')
            self._signature(0x52820);self._signature(0x52640);self.reset()
            if ui==1:self._signature(0x52C70)
            if hasattr(self.engine,'reset_all'):self.engine.reset_all()
            if mode==0:self.write(self.user()+0x4C,level)
            def build(origin,result):
                # PreNewGame assigns mGameMode before MakeNewBoard destroys the
                # previous board. Dispose it first while its old mode is intact:
                # otherwise entering Garden invokes LeaveGarden on an old lawn.
                payload=b''
                if ui==1:
                    payload+=mov('esi',app);payload+=call(origin+len(payload),self.base+0x52C70)
                payload+=mov('edi',app);payload+=call(origin+len(payload),self.base+0x52640)
                payload+=push(0)+push(mode)+mov('esi',self.app());return payload+call(origin+len(payload),self.base+0x52820)
            result=self._native().execute_main(build);self.invalidate_lawn();return result
    def reset(self):
        if getattr(self,'seed_deck',None):self.seed_deck.stop()
        self.schedule.cancel();self.enable_effect(None);errors=[]
        with self.lock:
            if self.damage_original:
                self.guard()
                for kind,value in list(self.damage_original.items()):
                    self.write(self.base+0x31E900+kind*12+8,value);del self.damage_original[kind]
            if self.edits:
                try:
                    with self.frozen():
                        board=self.lawn_token();maps={k:{p['id']:p for p in self.entities(k)}for k in ('plant','zombie')}
                        for token,value in list(self.edits.items()):
                            owner,kind,ident,off,fmt=token;e=maps[kind].get(ident)
                            if board==owner and e:self.write(e['address']+off,value,fmt)
                            del self.edits[token]
                except Exception:
                    # An absent lawn invalidates all heap owners; never write a previous lawn.
                    if self.read(self.app()+0x91C)!=3:self.edits.clear()
                    else:raise
