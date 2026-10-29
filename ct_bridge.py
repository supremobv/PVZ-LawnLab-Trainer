"""Opt-in CE control adapter. Local files carry a bounded command vocabulary only."""
import os,re,time
from pathlib import Path
from trainer_backend import PvZTrainer,NAMES

VALUES={'plant_size':('set_plant_size_percent',25,300),'zombie_size':('set_zombie_size_percent',25,300),'drop':('set_sunflower_drop_value',0,3),'sun':('set_sun_lock_amount',0,9999),'money':('set_money_amount',0,99999999),
        'plant':('set_plant_changer_value',0,47),'bullet':('set_bullet_changer_value',0,12),
        'row':('set_move_zombie_row_value',0,5),'delay':('set_fast_shoot_delay',1,255),
        'speed':('set_game_speed',1,50)}
ACTIONS={'remove_all_graves','restore_lawn_mowers','kill_all_zombies','spawn_all_zombies_now','clear_all_plants','instant_win','move_existing_zombies'}
BRIDGE_VERSION='5.14'

def dispatch(engine,words):
    if words==['PING']:return
    if words==['RESET']:engine.reset_all();return
    if len(words)==3 and words[0]=='TOGGLE' and words[1]in NAMES and words[2]in ('0','1'):
        engine._toggle(words[1],words[2]=='1');return
    if len(words)==3 and words[0]=='VALUE' and words[1]in VALUES:
        method,lo,hi=VALUES[words[1]]
        if not re.fullmatch(r'-?\d{1,10}',words[2]):raise ValueError('Use an integer value.')
        value=int(words[2])
        if not lo<=value<=hi:raise ValueError(f'Value must be {lo}–{hi}.')
        getattr(engine,method)(value);return
    if len(words)==2 and words[0]=='ACTION' and words[1]in ACTIONS:
        getattr(engine,words[1])();return
    raise ValueError('Unsupported CT command.')

def atomic(path,text):
    temp=path.with_suffix('.tmp');temp.write_text(text,encoding='utf-8',newline='\n');temp.replace(path)

def serve(engine,folder,lease=20):
    request=folder/'request';response=folder/'response';last=0
    while True:
        heartbeat=folder/'heartbeat'
        if time.time()-heartbeat.stat().st_mtime>lease:return
        if not request.exists():time.sleep(.03);continue
        if request.stat().st_size>512:raise ValueError('CT request exceeds the size limit.')
        text=request.read_text(encoding='utf-8');request.unlink()
        words=text.split('|');ident=words.pop(0)
        if not ident.isdecimal()or len(ident)>10 or int(ident)<=last:raise ValueError('Out-of-order CT request.')
        last=int(ident);stop=words==['STOP'];error=''
        try:
            if stop:engine.reset_all()
            else:dispatch(engine,words)
            if engine.last_error:raise RuntimeError(engine.last_error)
        except Exception as failure:error=str(failure).replace('\n',' ').replace('\r',' ')[:2000]
        flags=','.join(sorted(n for n in NAMES if getattr(engine,n+'_active',False)))
        atomic(response,('ERROR'if error else'OK')+'|'+ident+'\n'+flags+'\n'+error)
        if stop:return

def main(arguments=None):
    import sys
    args=sys.argv[1:]if arguments is None else arguments
    if len(args)!=2 or not re.fullmatch('[0-9a-f]{32}',args[0])or not args[1].isdecimal():raise ValueError('Invalid CT session.')
    folder=Path(os.environ['LOCALAPPDATA'])/'LawnLab/ce'/args[0];folder.mkdir(parents=True,exist_ok=False)
    atomic(folder/'heartbeat','start');engine=PvZTrainer();engine.target_pid=int(args[1])
    try:
        if not engine.attach_process():raise RuntimeError(engine.last_error or 'Open a supported PVZ process first.')
        if engine.pm.process_id!=int(args[1]):raise RuntimeError('CE selected a different PVZ process. Close duplicate game instances.')
        atomic(folder/'ready','OK|'+BRIDGE_VERSION);serve(engine,folder)
    except Exception as error:
        atomic(folder/'ready','ERROR\n'+str(error));engine.log('ct-error',error)
    finally:
        try:
            if engine.runtime:engine.reset_all()
        except Exception as error:engine.log('ct-cleanup-failed',error);atomic(folder/'cleanup-error',str(error))
        finally:
            engine.shutdown()
            if engine.pm:engine.pm.close_process()
            atomic(folder/'stopped','stopped')

if __name__=='__main__':main()

