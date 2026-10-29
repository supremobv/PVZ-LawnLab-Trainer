"""Verified GOTY runtime replacing every legacy control used by LawnLab.

The legacy source stays available for historical reference. The GUI routes all
All main controls here; no broad pattern scan, heuristic write, or live-code free.
"""
import ctypes,json,os,struct,threading,time
from pathlib import Path
import pefile
from trainer_engine import PvZTrainer as LegacyTrainer
from studio_engine import StudioGame,HASH
from studio_native import mov,push,call,u32
from verified_patches import PATCHES
from patch_manager import PatchManager
import extra_controls
from game_layout import FRAME_DURATION,SEED_RECHARGE,FREE_PLANTING,WAVE_COUNTDOWN,HUGE_WAVE_COUNTDOWN,PAUSED,SHOOT_GUARD,RAPID_INTERVAL,lane_code,shooting_guard_code,one_hit_code,rapid_direct_code,sunflower_drop_code,shop_stock_code,SHOP_STOCK_EXTRA,SHOP_CAP_HOOKS,SHOP_CAP_ORIGINAL,shop_purchase_code,BANK_CAP,BANK_PATCHES,SNAIL_PATCHES

GROUPS={
 'cattail_land':[],'instant_mines':[],'no_support':[],
 'direct_upgrades':[],'almanac_reveal':[],'plant_size':[],'zombie_size':[],
 'limbo_page':['unlock_limbo_page'],'snail_boost':[],'extended_bank':[],
 'auto_collect':['auto_collected'],'no_cooldown':[],
 'one_hit_kill':[],
 'prevent_spend':[], 'plant_anywhere':['placed_anywhere','placed_anywhere_preview','placed_anywhere_iz'],
 'invincible_plants':['plant_immune_eat','plant_immune_radius','plant_immune_jalapeno','plant_immune_projectile','plant_immune_lob_motion','plant_immune_square','plant_immune_row_area','plant_immune_spike_rock','plant_immune_squish'],
 'instant_plant_death':['_plant_immune_eat','_plant_immune_projectile','_plant_immune_lob_motion','_plant_immune_row_area'],
 'invincible_zombies':['zombie_immune_body_damage','zombie_immune_helm_damage','zombie_immune_shield_damage','zombie_immune_burn_crumble','zombie_immune_radius','zombie_immune_burn_row','zombie_immune_chomper','zombie_immune_mind_controll','zombie_immune_blow_away','zombie_immune_splash','zombie_immune_lawn_mower'],
 'unhittable_plants':['plant_immune_projectile','plant_immune_lob_motion'],
 'run_in_background':['background_running'],'no_fog':['no_fog'],'stop_spawning':['stop_spawning'],
 'stop_zombies':['stop_zombies'],'lock_butter':['lock_butter'],'mushrooms_awake':['mushrooms_awake'],
 'no_crater':['no_crater'],'see_vase':['see_vase'],'no_ice_trail':['no_ice_trail'],
 'zombie_not_explode':['zombie_not_explode'],'unlock_sun_limit':['unlock_sun_limit'],
 'fast_belt':['fast_belt'],'lock_shovel':['lock_shovel'],
}
HOOKS={'collect_1000_sun':(0x1E6E0,6),'planting_adds_sun':(0x1E846,6),'plant_changer':(0xFA10,7),
       'move_zombie_row':(0x132A12,6),'bullet_changer':(0x70E29,5),'fast_shoot':(0x6322C,6)}
HOOKS.update(shop_stock=(0x955C0,8),sunflower_drop=(0xF400,6),one_hit_kill=(0x1421BC,5),rapid_fire=(0x62868,7))
HOOK_ORIGINAL={'collect_1000_sun':'018878550000','planting_adds_sun':'89b778550000','plant_changer':'5153558b6c2410',
               'move_zombie_row':'8b55088b4518','bullet_changer':'89455c8bc6','fast_shoot':'894e5883f812'}
HOOK_ORIGINAL.update(shop_stock='83ffff750332c0c3',sunflower_drop='558bec83e4f8',one_hit_kill='8bc583f949',rapid_fire='8bc6e861550000')
CONTINUOUS={'infinite_sun','sun_lock','money_changer','show_all_zombies','auto_coins','zombie_size','auto_cob'}
NAMES=set(GROUPS)|set(HOOKS)|CONTINUOUS|{'rapid_fire'}
CONFLICTS=[{'infinite_sun','sun_lock'},{'invincible_plants','instant_plant_death'},{'unhittable_plants','instant_plant_death'},{'one_hit_kill','invincible_zombies'},{'rapid_fire','fast_shoot'}]

class VerifiedRuntime:
    def __init__(self,engine):
        self.engine=engine;self.game=StudioGame(engine);self.game.guard();self.base=engine.base_address
        import pymem.process
        module=pymem.process.module_from_name(engine.pm.process_handle,engine.attached_process_name)
        pe=pefile.PE(module.filename)
        try:self.image=pe.get_memory_mapped_image()
        finally:pe.close()
        self.native=self.game._native();self.manager=PatchManager(engine.pm,self.native);self.caves={};self.initialized=set();self.frame_original=None;self.preview_original=None;self.zombie_sizes=extra_controls.ZombieSizes(self.game)
        import startup_options
        startup_options.attach(self)
    def specs(self,name):
        result=[]
        for key in GROUPS.get(name,[]):
            for rva,original,desired in PATCHES[key]:
                old,new=bytes.fromhex(original),bytes.fromhex(desired)
                if self.image[rva:rva+len(old)]!=old:raise RuntimeError('Reference patch does not match the fingerprinted executable: '+key)
                result.append((self.base+rva,old,new))
        if name=='prevent_spend':
            for rva,old,new in FREE_PLANTING:
                original=bytes.fromhex(old)
                if self.image[rva:rva+len(original)]!=original:raise RuntimeError('Free planting instruction mismatch.')
                result.append((self.base+rva,original,bytes.fromhex(new)))
        if name in ('snail_boost','extended_bank'):
            for rva,old,new in (SNAIL_PATCHES if name=='snail_boost'else BANK_PATCHES):
                original=bytes.fromhex(old)
                if self.image[rva:rva+len(original)]!=original:raise RuntimeError('Verified instruction mismatch: '+name)
                result.append((self.base+rva,original,bytes.fromhex(new)))
        if name=='shop_stock':
            rva,old,new=SHOP_STOCK_EXTRA;original=bytes.fromhex(old)
            if self.image[rva:rva+len(original)]!=original:raise RuntimeError('Shop stock instruction mismatch.')
            result.append((self.base+rva,original,bytes.fromhex(new)))
        if name=='no_cooldown':
            rva,original,desired=SEED_RECHARGE;old=bytes.fromhex(original)
            if self.image[rva:rva+len(old)]!=old:raise RuntimeError('Seed recharge instruction mismatch.')
            result.append((self.base+rva,old,bytes.fromhex(desired)))
        result+=extra_controls.specs(self,name)
        return result
    def hook(self,name,delay=None):
        rva,size=(HOOKS|SHOP_CAP_HOOKS)[name];original=self.image[rva:rva+size]
        if original!=bytes.fromhex((HOOK_ORIGINAL|SHOP_CAP_ORIGINAL)[name]):raise RuntimeError('Hook instruction mismatch: '+name)
        if name not in self.caves:
            address=self.native.k.VirtualAllocEx(self.native.handle,None,4096,0x3000,0x40)
            if not address or address>0xffffffff:raise RuntimeError('Could not allocate x86 hook memory.')
            self.caves[name]=address
        address=self.caves[name];parameter=address+0x100;e=self.engine
        if name=='collect_1000_sun':body=b'\x51\xb9'+u32(1000)+original+b'\x59'
        elif name=='planting_adds_sun':body=original+b'\x9c\x81\x87'+u32(0x5578)+u32(2000)+b'\x9d'
        elif name=='plant_changer':body=b'\x52\x8b\x15'+u32(parameter)+b'\x89\x54\x24\x10\x5a'+original
        elif name in SHOP_CAP_HOOKS or name in ('shop_stock','sunflower_drop','move_zombie_row','one_hit_kill','rapid_fire'):body=b''
        elif name=='bullet_changer':body=b'\xa1'+u32(parameter)+b'\x89\x45\x5c\x8b\xc6'
        else:body=b'\x51\x8b\x0d'+u32(parameter)+b'\x89\x4e\x58\x59\x83\xf8\x12'
        code=body+b'\xe9'+u32(self.base+rva+size-(address+len(body)+5))
        if name in SHOP_CAP_HOOKS:code=shop_purchase_code(name,address,self.base+rva+size,original)
        elif name=='shop_stock':code=shop_stock_code(address,self.base+rva+size)
        elif name=='sunflower_drop':code=sunflower_drop_code(parameter,address,self.base+rva+size)
        elif name=='move_zombie_row':code=lane_code(parameter,original,address,self.base+rva+size)
        elif name=='one_hit_kill':code=one_hit_code(address,self.base+rva+size)
        elif name=='rapid_fire':code=rapid_direct_code(address,self.base+rva+size)
        extra=[]
        if name=='fast_shoot':
            guard_rva,guard_hex=SHOOT_GUARD;guard_old=bytes.fromhex(guard_hex)
            if self.image[guard_rva:guard_rva+len(guard_old)]!=guard_old:raise RuntimeError('Shooting animation guard mismatch.')
            guard_code=shooting_guard_code(address+0x200,self.base+guard_rva+len(guard_old))
            extra=[(self.base+guard_rva,guard_old,b'\xe9'+u32(address+0x200-(self.base+guard_rva+5))+b'\x90'*(len(guard_old)-5))]
        if len(code)>=0x100:raise RuntimeError('Hook code would overlap its parameter storage.')
        # Never reallocate/free a hook that another suspended thread may be in.
        values={'sunflower_drop':[4,1,2,3][e.sunflower_drop_value],'plant_changer':e.plant_changer_value,'move_zombie_row':e.move_zombie_row_value,'bullet_changer':e.bullet_changer_value,'fast_shoot':e.fast_shoot_delay if delay is None else delay}
        with self.native.suspended():
            if name not in self.initialized:
                self.native.write_code(address,code)
                if name=='fast_shoot':self.native.write_code(address+0x200,guard_code)
                self.initialized.add(name)
            if name in values:
                old=e.pm.read_bytes(parameter,4)
                try:self.native.write_code(parameter,u32(values[name]))
                except Exception:
                    try:self.native.write_code(parameter,old)
                    except Exception as recovery_error:
                        self.native.poisoned=True
                        raise RuntimeError('Hook parameter recovery failed; restart PVZ before continuing.') from recovery_error
                    raise
        replacement=b'\xe9'+u32(address-(self.base+rva+5))+b'\x90'*(size-5)
        return [(self.base+rva,original,replacement)]+extra
    def enable(self,name):
        if name in self.manager.active:
            self.manager.enable(name,[]);return
        patches=extra_controls.plant_hook(self)if name=='plant_size'else self.hook('fast_shoot',delay=RAPID_INTERVAL)+self.hook('rapid_fire')if name=='rapid_fire'else self.hook(name)if name in HOOKS else self.specs(name)
        if name=='shop_stock':
            patches+=self.specs(name)
            for internal in SHOP_CAP_HOOKS:patches+=self.hook(internal)
        self.manager.enable(name,patches)
    def tick(self):
        g=self.game;e=self.engine;refresh=False
        with self.native.suspended():
            app=g.app();ui=g.read(app+0x91C)
            if e.money_changer_active:g.write(g.user()+0x50,e.money_amount)
            if ui not in (2,3)or g.read(app+0x918)in (43,50):self.preview_original=None;return
            candidate=g.pointer(app+0x868)
            if g.read(candidate+0x5564)>5:self.preview_original=None;return
            board=g.board(playing=False)
            if ui==3:
                if e.infinite_sun_active:g.write(board+0x5578,9999)
                elif e.sun_lock_active:g.write(board+0x5578,e.sun_lock_amount)
            if e.show_all_zombies_active and ui==2:
                old=e.pm.read_bytes(board+0x54EC,33)
                token=(board,g._generation)
                if self.preview_original is None or self.preview_original[:2]!=token:
                    self.preview_original=(*token,old);refresh=True
                flags=bytearray(b'\x01'*33);flags[25]=0
                e.pm.write_bytes(board+0x54EC,bytes(flags),33)
        if refresh:
            with self.native.frozen():
                scene=g.pointer(board+0x174)
                specs=[(self.base+a,bytes.fromhex(o),bytes.fromhex(n))for a,o,n in PATCHES['hack_street_zombies']]
                self.manager.enable('preview-action',specs)
                try:self.native_action([(0x108E0,'ebx',board,[]),(0x3D350,None,0,[scene])])
                finally:self.manager.disable('preview-action')
        if getattr(e,'zombie_size_active',False)and ui==3:self.zombie_sizes.apply(e.zombie_size_percent)
        if e.auto_coins_active and ui==3:self.game.collect_coins()
        if e.auto_cob_active and ui==3:extra_controls.auto_cob(self)
    def restore_preview(self):
        if self.preview_original:
            with self.native.suspended():
                try:
                    board=self.game.board(playing=False)
                    if (board,self.game._generation)==self.preview_original[:2]:self.engine.pm.write_bytes(board+0x54EC,self.preview_original[2],33)
                except RuntimeError:pass
            self.preview_original=None
    def speed(self,value):
        if type(value)is not int or value not in (1,2,5,10,20,50):raise ValueError('Unsupported game pace.')
        with self.native.suspended():
            app=self.game.app()
            current=self.game.read(app+FRAME_DURATION)
            if not 1<=current<=100:raise RuntimeError('Unexpected frame duration; no pace write was made.')
            if self.frame_original is None:self.frame_original=(app,current)
            self.game.write(app+FRAME_DURATION,value)
    def restore_speed(self):
        if self.frame_original:
            with self.native.suspended():
                app,value=self.frame_original
                if self.game.app()==app:self.game.write(app+FRAME_DURATION,value)
            self.frame_original=None
    def native_action(self,operations):
        def build(origin,result):
            body=b''
            for rva,register,argument,stack in operations:
                expected=self.image[rva:rva+8]
                if self.engine.pm.read_bytes(self.base+rva,8)!=expected:raise RuntimeError('Action routine bytes differ.')
                for value in stack:body+=push(value)
                if register:body+=mov(register,argument)
                body+=call(origin+len(body),self.base+rva)
            return body
        return self.native.execute(build)

class PvZTrainer(LegacyTrainer):
    safe_runtime_enabled=True
    def __init__(self):
        super().__init__();self.operation_lock=threading.RLock();self.runtime=None;self.last_error='';self._worker_stop=threading.Event();self._safe_worker=None;self._owner_handle=None;self.snail_boost_active=False;self.limbo_page_active=False;self.extended_bank_active=False;self.shop_stock_active=False;self.sunflower_drop_value=0;self.sunflower_drop_active=False;self.auto_coins_active=False;self.last_move_result=None;self._remembered_limbo=False;self.cattail_land_active=False;self.instant_mines_active=False;self.no_support_active=False;self.auto_cob_active=False;self.direct_upgrades_active=False;self.almanac_reveal_active=False;self.plant_size_active=False;self.plant_size_percent=100;self.zombie_size_active=False;self.zombie_size_percent=100
    def claim_owner(self):
        # The named object's lifetime, not thread-affine mutex ownership, is the lease.
        k=ctypes.WinDLL('kernel32',use_last_error=True)
        k.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_wchar_p];k.CreateMutexW.restype=ctypes.c_void_p
        ctypes.set_last_error(0);handle=k.CreateMutexW(None,False,'Local\\LawnLab.PVZ.'+str(self.pm.process_id))
        error=ctypes.get_last_error()
        if not handle:raise ctypes.WinError(error)
        if error==183:
            k.CloseHandle.argtypes=[ctypes.c_void_p];k.CloseHandle(handle)
            raise RuntimeError('This PVZ process is already controlled by LawnLab or its CT helper. Disconnect the other controller first.')
        self._owner_handle=handle
    def attach_process(self):
        if getattr(self,'target_pid',None):
            import pymem,pymem.process
            try:
                self.pm=pymem.Pymem(self.target_pid);module=list(pymem.process.enum_process_module(self.pm.process_handle))[0];self.base_address=module.lpBaseOfDll;self.attached_process_name=Path(module.filename).name;self.is_connected=True
            except Exception as error:self.last_error=str(error);return False
        elif not super().attach_process():return False
        try:self.claim_owner();self.runtime=VerifiedRuntime(self);return True
        except Exception as error:
            self.last_error=str(error);self.shutdown();self.pm.close_process();self.pm=None;self.is_connected=False;return False
    def _runtime(self):
        if not self.is_connected or not self.pm:raise RuntimeError('Connect to a fresh supported PVZ process.')
        if self.runtime is None:self.runtime=VerifiedRuntime(self)
        return self.runtime
    def log(self,action,error=''):
        try:
            path=Path(os.getenv('LOCALAPPDATA',Path.home()))/'LawnLab/logs';path.mkdir(parents=True,exist_ok=True)
            data={'time':time.strftime('%Y-%m-%dT%H:%M:%S'),'action':action,'error':str(error),'enabled':sorted(n for n in NAMES if getattr(self,n+'_active',False))}
            with (path/'controls.jsonl').open('a',encoding='utf-8')as f:f.write(json.dumps(data)+'\n')
        except OSError:pass
    def _start_worker(self):
        if self._safe_worker and self._safe_worker.is_alive():return
        self._worker_stop.clear();self._safe_worker=threading.Thread(target=self._work,daemon=True,name='LawnLab verified data worker');self._safe_worker.start()
    def _work(self):
        while not self._worker_stop.wait(.05):
            with self.operation_lock:
                if not self.is_connected or not self.pm:return
                if self.last_error or not any(getattr(self,k+'_active',False)for k in CONTINUOUS):continue
                try:self._runtime().tick()
                except Exception as error:self.last_error='Automatic writes paused: '+str(error);self.log('worker-error',error)
    def shutdown(self):
        self._worker_stop.set()
        if self._safe_worker and self._safe_worker is not threading.current_thread():
            self._safe_worker.join(2)
            if self._safe_worker.is_alive():raise RuntimeError('Memory worker has not stopped; keep the handle open and retry.')
        if self._owner_handle:
            k=ctypes.WinDLL('kernel32');k.CloseHandle.argtypes=[ctypes.c_void_p];k.CloseHandle(self._owner_handle);self._owner_handle=None
    def _toggle(self,name,state):
        if name not in NAMES:raise ValueError('Unknown verified control.')
        if type(state)is not bool:raise ValueError('A control state must be true or false.')
        with self.operation_lock:
            runtime=self._runtime()
            if name=='limbo_page'and not state and self._remembered_limbo:
                import startup_options
                startup_options.save(startup_options.kind(self),False);self._remembered_limbo=False
            if state and name=='move_zombie_row' and self.move_zombie_row_value>=runtime.game.rows():raise RuntimeError('The selected lane does not exist on this lawn.')
            try:
                if state:
                    if self.last_error:raise RuntimeError('Reset all before enabling more controls: '+self.last_error)
                    for group in CONFLICTS:
                        if name in group:
                            for other in group-{name}:
                                if getattr(self,other+'_active',False):self._toggle(other,False)
                    if name=='cattail_land'and not self.direct_upgrades_active:self._toggle('direct_upgrades',True)
                    runtime.enable(name)
                    setattr(self,name+'_active',True)
                    if name=='move_zombie_row':self.last_move_result=runtime.game.move_zombies(self.move_zombie_row_value+1)
                    if name=='mushrooms_awake' and runtime.game.read(runtime.game.app()+0x91C)==3:
                        with runtime.native.frozen():
                            sleeping=[p for p in runtime.game.entities('plant')if runtime.game.read(p['address']+0x143,'byte')]
                            if sleeping:runtime.native_action([(0x62190,'edi',p['address'],[0])for p in sleeping])
                    if name in CONTINUOUS:
                        runtime.tick();self._start_worker()
                else:
                    if name=='direct_upgrades'and self.cattail_land_active:self._toggle('cattail_land',False)
                    if name=='zombie_size':runtime.zombie_sizes.restore()
                    runtime.manager.disable(name)
                    if name=='show_all_zombies':runtime.restore_preview()
                    setattr(self,name+'_active',False)
                self.log(('enable:'if state else'disable:')+name)
                return True
            except Exception as error:
                setattr(self,name+'_active',name in runtime.manager.active)
                self.last_error=str(error);self.log('control-failed:'+name,error);raise
    def reset_all(self):
        with self.operation_lock:
            runtime=self._runtime()
            runtime.zombie_sizes.restore();runtime.manager.reset();runtime.restore_preview();runtime.restore_speed()
            for name in NAMES:setattr(self,name+'_active',False)
            if self._remembered_limbo:
                runtime.enable('limbo_page');self.limbo_page_active=True
            self.last_error='';self.log('reset');return True
    def _value(self,attr,value,lo,hi,hook=None):
        if type(value)is not int or not lo<=value<=hi:raise ValueError(f'Value must be {lo}–{hi}.')
        with self.operation_lock:
            old=getattr(self,attr)
            if hook=='move_zombie_row'and self.move_zombie_row_active and value>=self._runtime().game.rows():raise RuntimeError('The selected lane does not exist on this lawn.')
            try:
                setattr(self,attr,value)
                if hook and getattr(self,hook+'_active',False):self._runtime().hook(hook)
            except Exception as error:
                setattr(self,attr,old);self.last_error=str(error);self.log('value-failed:'+attr,error);raise
        return True
    def set_limbo_remembered(self,value):
        import startup_options
        if type(value)is not bool:raise ValueError('Limbo preference must be true or false.')
        with self.operation_lock:
            self._toggle('limbo_page',value)
            startup_options.save(startup_options.kind(self),value);self._remembered_limbo=value
        return True
    def set_plant_size_percent(self,v):
        extra_controls.percent(v)
        with self.operation_lock:
            old=self.plant_size_percent;self.plant_size_percent=v
            try:
                if self.plant_size_active:extra_controls.plant_hook(self._runtime())
            except Exception:self.plant_size_percent=old;raise
        return True
    def set_zombie_size_percent(self,v):
        extra_controls.percent(v)
        with self.operation_lock:
            old=self.zombie_size_percent;self.zombie_size_percent=v
            try:
                if self.zombie_size_active:self._runtime().zombie_sizes.apply(v)
            except Exception:self.zombie_size_percent=old;raise
        return True
    def set_sun_lock_amount(self,v):return self._value('sun_lock_amount',v,0,9999)
    def set_money_amount(self,v):
        if type(v)is not int or not 0<=v<=BANK_CAP:raise ValueError('Coin units must be 0–99,999,999; each unit is $10.')
        if v>99999 and self.is_connected:self.toggle_extended_bank(True)
        return self._value('money_amount',v,0,BANK_CAP)
    def set_plant_changer_value(self,v):return self._value('plant_changer_value',v,0,47,'plant_changer')
    def set_bullet_changer_value(self,v):return self._value('bullet_changer_value',v,0,12,'bullet_changer')
    def set_move_zombie_row_value(self,v):return self._value('move_zombie_row_value',v,0,5,'move_zombie_row')
    def move_existing_zombies(self,row=None):
        with self.operation_lock:
            if row is not None:self.set_move_zombie_row_value(row)
            self.last_move_result=self._runtime().game.move_zombies(self.move_zombie_row_value+1)
            return 'Moved {moved} zombies; skipped {skipped} incompatible or special-state zombies.'.format(**self.last_move_result)
    def set_sunflower_drop_value(self,v):return self._value('sunflower_drop_value',v,0,3,'sunflower_drop')
    def set_fast_shoot_delay(self,v):return self._value('fast_shoot_delay',v,1,255,'fast_shoot')
    def set_sun_amount(self,v):
        with self.operation_lock:
            r=self._runtime()
            with r.native.suspended():r.game.write(r.game.board()+0x5578,max(0,min(9999,int(v))))
        return True
    def set_game_speed(self,v):
        with self.operation_lock:self._runtime().speed(v);self.log('pace:'+str(v))
        return True
    def get_game_board(self):
        try:
            r=self._runtime();return r.game.app(),r.game.board(playing=False)
        except RuntimeError:return None,None
    def kill_all_zombies(self):
        with self.operation_lock:
            r=self._runtime()
            with r.native.suspended():
                entities=r.game.entities('zombie')
                for z in entities:r.game.write(z['address']+0x28,3)
        return len(entities)
    def clear_all_plants(self):
        with self.operation_lock:
            r=self._runtime()
            with r.native.frozen():
                plants=r.game.entities('plant');r.native_action([(0x6B470,None,0,[p['address']])for p in plants]+[(0x1E8A0,'esi',r.game.board(),[])])
        return len(plants)
    def spawn_all_zombies_now(self):
        with self.operation_lock:
            if self.stop_spawning_active:raise RuntimeError('Disable Pause spawning before advancing the wave.')
            r=self._runtime()
            with r.native.suspended():
                b=r.game.board();mode=r.game.read(r.game.app()+0x918)
                if mode not in range(16):raise RuntimeError('Wave advancement supports Adventure and Survival; this mode uses a separate spawn system.')
                if r.game.read(b+0x5594)>=r.game.read(b+0x557C):raise RuntimeError('All natural waves have already spawned.')
                previous=r.game.read(b+0x5594)
                if r.game.read(b+PAUSED,'byte'):raise RuntimeError('Resume PVZ before advancing the wave.')
                original_count=r.game.read(b+WAVE_COUNTDOWN);original_huge=r.game.read(b+HUGE_WAVE_COUNTDOWN)
                r.game.write(b+WAVE_COUNTDOWN,1)
                if original_huge>0:r.game.write(b+HUGE_WAVE_COUNTDOWN,1)
            end=time.monotonic()+2
            while time.monotonic()<end:
                if r.game.board()!=b:raise RuntimeError('The lawn changed before the wave advanced.')
                if r.game.read(b+0x5594)>previous:return True
                time.sleep(.01)
            with r.native.suspended():
                if r.game.board()==b and r.game.read(b+0x5594)==previous:
                    if r.game.read(b+WAVE_COUNTDOWN)<=1:r.game.write(b+WAVE_COUNTDOWN,original_count)
                    if original_huge>0 and r.game.read(b+HUGE_WAVE_COUNTDOWN)<=1:r.game.write(b+HUGE_WAVE_COUNTDOWN,original_huge)
            raise RuntimeError('The game did not advance the wave. Finish any tutorial or cutscene and resume normal play before retrying.')
        return True
    def remove_all_graves(self):
        with self.operation_lock:
            count=extra_controls.remove_graves(self._runtime())
            return f'Removed {count} graves from the current lawn. Future graves can still appear.'
    def instant_win(self):
        with self.operation_lock:
            r=self._runtime();r.native_action([(0xECD0,'ecx',r.game.board(),[])])
        return True
    def restore_lawn_mowers(self):
        with self.operation_lock:
            r=self._runtime()
            with r.native.frozen():
                b=r.game.board();data=r.game.pointer(b+0x118);count=r.game.read(b+0x11C)
                if not 0<=count<=4096:raise RuntimeError('Invalid mower array bound.')
                alive=[data+i*0x48 for i in range(count)if not r.game.read(data+i*0x48+0x30,'byte')and r.game.read(data+i*0x48+0x44,'uint')>>16]
                if len(alive)>6 or any(not 0<=r.game.read(p+0x14)<6 for p in alive):raise RuntimeError('Invalid live mower records.')
                specs=[]
                for key in ('init_lawn_mowers','lawn_mower_initialize'):
                    specs.extend((r.base+a,bytes.fromhex(o),bytes.fromhex(n))for a,o,n in PATCHES[key])
                r.manager.enable('mower-action',specs)
                try:
                    actions=[(0x5C5D0,'eax',p,[])for p in alive]
                    # Free dead DataArray slots through the game's own delete queue
                    # before creating replacements, including while the lawn is paused.
                    actions.append((0x1E8A0,'esi',b,[]))
                    actions.append((0xE510,None,0,[b]));r.native_action(actions)
                finally:r.manager.disable('mower-action')
        return True

def _toggle_method(name):
    def method(self,state):return self._toggle(name,state)
    method.__name__='toggle_'+name;return method
for _name in NAMES:setattr(PvZTrainer,'toggle_'+_name,_toggle_method(_name))
# The original UI uses this longer method name for the projectile immunity card.
PvZTrainer.toggle_unhittable_plants_zombotany=_toggle_method('unhittable_plants')
