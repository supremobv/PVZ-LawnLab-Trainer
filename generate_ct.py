"""Generate CE controls and an exhaustive source-offset inventory from the current runtime."""
import ast,hashlib,json
from pathlib import Path
import xml.etree.ElementTree as ET
from lawnlab import FEATURES
from verified_engine import GROUPS,HOOKS,HOOK_ORIGINAL
from verified_patches import PATCHES
from studio_engine import HASH,ARRAYS,PLANT_FIELDS,ZOMBIE_FIELDS,SIGNATURES
from game_layout import FRAME_DURATION,SEED_RECHARGE,FREE_PLANTING,SHOOT_GUARD,COIN_ARRAY,COIN_COLLECT,RAPID_INTERVAL,SHOP_STOCK_EXTRA,SHOP_CAP_HOOKS,SHOP_CAP_ORIGINAL,BANK_PATCHES,SNAIL_PATCHES
from profile_tools import PROFILE_FIELDS,ACHIEVEMENTS,GARDEN_CELLS

ROOT=Path(__file__).resolve().parent
SOURCES=('verified_engine.py','verified_patches.py','patch_manager.py','studio_engine.py','studio_native.py','game_layout.py','profile_tools.py','trainer_backend.py','runtime_image.py','edition_saves.py','startup_options.py','seed_pages.py','seed_overlay.py','resource_mods.py','studio_storage.py','studio_models.py','extra_controls.py','pak_resources.py','note_editor.py')

def inventory():
    items=[];hashes={}
    for name in SOURCES:
        data=(ROOT/name).read_bytes();hashes[name]=hashlib.sha256(data).hexdigest();source=data.decode('utf-8-sig');lines=source.splitlines()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node,ast.Constant)and type(node.value)is int:
                literal=ast.get_source_segment(source,node)or''
                if literal.lower().startswith('0x'):
                    items.append(dict(source=name,line=node.lineno,literal=literal,value=node.value,context=lines[node.lineno-1].strip()))
    return {'version':'5.14','executable_sha256':HASH,'image_size':'0x415000','source_sha256':hashes,
            'note':'Hex literals include offsets, RVAs, instruction bytes and Windows flags. Context distinguishes their meaning; do not treat all literals as addresses.',
            'hex_literals':sorted(items,key=lambda x:(x['source'],x['line'],x['value'])),
            'arrays':ARRAYS,'plant_fields':PLANT_FIELDS,'zombie_fields':ZOMBIE_FIELDS,
            'hooks':{n:{'rva':v[0],'length':v[1],'original':HOOK_ORIGINAL[n]}for n,v in HOOKS.items()},
            'patches':PATCHES,'seed_recharge':SEED_RECHARGE,'free_planting':FREE_PLANTING,'shooting_animation_guard':SHOOT_GUARD,'frame_duration_offset':FRAME_DURATION,
            'coin_array':COIN_ARRAY,'coin_collect_rva':COIN_COLLECT,'rapid_interval_ticks':RAPID_INTERVAL,
            'shop_stock_extra':SHOP_STOCK_EXTRA,'shop_purchase_hooks':{n:{'rva':v[0],'length':v[1],'original':SHOP_CAP_ORIGINAL[n]}for n,v in SHOP_CAP_HOOKS.items()},'extended_bank_patches':BANK_PATCHES,'snail_patches':SNAIL_PATCHES,'profile_fields':PROFILE_FIELDS,'achievement_names':ACHIEVEMENTS,'achievement_earned_offset':0x24,'achievement_shown_offset':0x38,'garden_cells':GARDEN_CELLS,
            'native_signatures':{hex(k):v for k,v in SIGNATURES.items()},
            'extra_controls':{'patches':__import__('extra_controls').PATCHES['goty'],'plant_scale_hook':__import__('extra_controls').PLANT_HOOK['goty'],'zombie_scale_field':__import__('extra_controls').ZOMBIE_SCALE,'cob_fire':__import__('extra_controls').COB_FIRE['goty'],'grid_items':__import__('extra_controls').GRID_ITEMS['goty']},
            'features':[{'title':f.title,'method':f.method,'state':f.state,'editor':f.editor}for f in FEATURES]}

def build():
    root=ET.Element('CheatTable',CheatEngineTableVersion='45');entries=ET.SubElement(root,'CheatEntries');counter=0
    runtime=(ROOT/'ct_runtime.lua').read_text(encoding='utf-8')
    def entry(parent,title,script=None):
        nonlocal counter
        counter+=1;e=ET.SubElement(parent,'CheatEntry');ET.SubElement(e,'ID').text=str(counter);ET.SubElement(e,'Description').text='"'+title+'"'
        if script is None:
            ET.SubElement(e,'GroupHeader').text='1';return ET.SubElement(e,'CheatEntries')
        ET.SubElement(e,'VariableType').text='Auto Assembler Script';ET.SubElement(e,'AssemblerScript').text=script
        return counter
    def script(command,disable='',prefix=''):
        return '[ENABLE]\n{$lua}\nif syntaxcheck then return end\n'+runtime+'\n'+prefix+'\n'+command+"\n{$asm}\n[DISABLE]\n{$lua}\nif syntaxcheck then return end\n"+disable+'\n{$asm}'
    groups=entry(entries,'LawnLab 5.14 — verified CT controller')
    sessions=entry(groups,'Session — attach CE to PVZ, disconnect LawnLab GUI before enabling')
    entry(sessions,'Start verified controller / reset and stop on disable',script("LawnLabCE.command('PING')","if LawnLabCE and LawnLabCE.folder and not LawnLabCE.syncing then LawnLabCE.command('STOP') end"))
    entry(sessions,'Reset all controls (one-shot; uncheck afterward)',script("LawnLabCE.command('RESET')"))
    params=entry(groups,'Parameters — set before enabling the matching control')
    for key,default,limit in [('plant_size',100,'25–300 percent; 100 normal'),('zombie_size',100,'25–300 percent; relative to native size'),('drop',0,'0 sun, 1 silver, 2 gold, 3 diamond; Sunflower and Twin Sunflower only'),('sun',9999,'0–9999'),('money',10000,'0–99999999 stored units; ×$10'),('plant',0,'0–47'),('bullet',0,'0–12'),('row',0,'0–5; zero-based; must exist on lawn'),('delay',1,'1–255; firing animations finish before restarting'),('speed',10,'1,2,5,10,20,50 ms/frame')]:
        code=f"local value=inputQuery('LawnLab CT','{key}: {limit}','{default}')\nif value then assert(value:match('^%d+$'),'Use an integer');LawnLabCE.command('VALUE|{key}|'..value) end"
        entry(params,key+' — '+limit+' (prompt)',script(code))
    controls={};record_map={}
    for feature in FEATURES:
        group=controls.setdefault(feature.category,None)
        if group is None:group=controls[feature.category]=entry(groups,feature.category)
        if feature.state:
            name=feature.state.removesuffix('_active')
            recordID=counter+1;prefix=f"LawnLabCE.records['{name}']={recordID}"
            record_map[name]=recordID
            enable=f"if not LawnLabCE.syncing then LawnLabCE.command('TOGGLE|{name}|1') end"
            disable=f"if LawnLabCE and LawnLabCE.folder and not LawnLabCE.syncing then LawnLabCE.command('TOGGLE|{name}|0') end"
            entry(group,feature.title,script(enable,disable,prefix))
        elif feature.method=='set_game_speed':
            entry(group,feature.title+' — use the speed parameter',script("showMessage('Use Parameters > speed. Reset all restores the previous pace.')"))
        else:
            prompt="if messageDialog('Run this one-time lawn action? Reset cannot undo it.',mtConfirmation,mbYes,mbNo)~=mrYes then error('Cancelled') end\n"
            entry(group,feature.title+' (one-shot; confirm)',script(prompt+f"LawnLabCE.command('ACTION|{feature.method}')"))
    refs=entry(groups,'ADDRESS REFERENCE — read-only scripts; check to display details')
    def reference(parent,label,details):
        # Read-only reference scripts cannot freeze/write these code or heap addresses.
        quoted=json.dumps(label+'\n\n'+details,ensure_ascii=False)
        code='[ENABLE]\n{$lua}\nif syntaxcheck then return end\nshowMessage('+quoted+')\n{$asm}\n[DISABLE]\n'
        entry(parent,label,code)
    pointers=entry(refs,'Pointer chains — hexadecimal offsets, dereference at each bracket')
    base='module+329670';app='['+base+']';board='['+app+'+868]';user='['+app+'+94C]'
    fields={'Sun':(board+'+5578','int'),'Current wave':(board+'+5594','int'),'Total waves':(board+'+557C','int'),
        'Lawn clock':(board+'+5580','int'),'Scene':(board+'+5564','int'),'Level':(board+'+5568','int'),
        'Spawn countdown':(board+'+55B4','int'),'UI state':(app+'+91C','int'),'Game mode':(app+'+918','int'),
        'Frame duration':(app+f'+{FRAME_DURATION:X}','int'),'Coins (game units)':(user+'+50','int'),'Adventure progress':(user+'+4C','int'),
        'Seed packet count':('['+board+'+15C]+24','int'),'Garden count':(user+'+378','int'),
        'Mower array':(board+'+118','pointer'),'Mower bound':(board+'+11C','int'),
        'Challenge':(board+'+178','pointer'),'Street preview':(board+'+174','pointer'),'Zombie preview mask':(board+'+54EC','33 bytes')}
    for label,(chain,kind)in fields.items():reference(pointers,label,chain+'\nType: '+kind+'\nmodule is the selected, fingerprinted executable (either supported filename).')
    entities=entry(refs,'Entities — slot formulas, field offsets and generation checks')
    for kind,(offset,stride,dead,identity)in ARRAYS.items():
        detail=f'array=[Board+{offset:X}], capacity=[Board+{offset+4:X}], slot=array+i*{stride:X}\nDead flag +{dead:X}; generation ID +{identity:X}. Slots are reused: never keep a raw entity address across lawns or deaths.'
        reference(entities,kind+' array / stride',detail)
        mapping=PLANT_FIELDS if kind=='plant'else ZOMBIE_FIELDS if kind=='zombie'else {'type':(0x5C,'int',0,12),'x':(0x30,'float',0,0),'y':(0x34,'float',0,0),'motion':(0x58,'int',0,0)}
        for name,(off,fmt,lo,hi)in mapping.items():reference(entities,kind+' '+name+f' +{off:X}',detail+f'\nField +{off:X}; type {fmt}; verified edit range {lo}–{hi}.')
    layouts=entry(refs,'Studio structures / tables')
    for label,detail in [
        ('Common entity fields','row +1C (zero-based); type +24. Plant col +28; imitater +138; squished +142. Zombie phase +28; x +2C, y +30; helm type +C4; shield TYPE +D8, shield HP +DC.'),
        ('Seed bank','bank=[Board+15C]; count +24; slot stride 50. Slot 0 elapsed +4C, total +50, type +5C, imitater +60. LawnLab requires 1–10 packets.'),
        ('Natural wave list','Board+6CC+(wave-1)*C8, 50 int32 zombie IDs per wave. -1 terminates the remaining list. Only upcoming waves within the level are edited.'),
        ('Projectile definitions','module+31E900+type*C; ID +0, shared damage +8. Types 0–12. Damage changes affect all matching projectiles.'),
        ('Potted plants','Profile+380+i*58; count Profile+378. Type +0, garden +4, last-water time +18 (int64), growth +24, fed +28, feeding requirement +2C, need +30, last-fertilizer time +40 (int64).'),
        ('Garden supplies','Profile+1E8+slot*4; fertilizer slot14, bug spray15, chocolate26, tree food28 (decimal). Stored amount=1000+displayed amount.'),
        ('Mower layout','array=[Board+118]; storage bound [Board+11C] can exceed 6; stride48; dead+30; row+14; generation ID+44. At most 6 live, valid records. Native restoration runs the delete queue before creating replacements.'),
        ('Update gate / call allocation','module+1D6C6D EB C8; temporary EB FE gates the update loop. Remote call allocation 10000 bytes; result +F000. A timeout keeps executing allocation and gate blocked. Restart PVZ; never manually free a pending call.'),
        ('Retained hooks','Each runtime hook has one 1000-byte allocation retained until game exit. Dynamic DWORD parameter at cave+100. Cave addresses are runtime allocations, never static offsets.')]:reference(layouts,label,detail)
    reference(layouts,'Stage transition on the game loop','Main loop site module+1D6C6D, EB C8; temporary EB 04 routes through padding at +1D6C73 (five CC bytes). Retained one-shot request allocation, flag +F000, result +F004. Menu selector cleanup +52C70 (ESI=App) if needed; dispose old Board +52640 (EDI=App) BEFORE PreNewGame +52820 changes App+918 mode. Request code is retained until game exit; loop bytes restore after completion.')
    reference(layouts,'Upgrade planting, automatic Cob Cannons, Almanac and size controls','extra_controls.py contains separate reviewed GOTY/Classic maps. GOTY packet requirements +205A0; upgrade branches +10DDF/+FF0E; Almanac-only spans +343E,+4BC2,+4C50,+4D50,+42DE,+44C1,+46B0. Plant UpdateReanim tail +6786A, EBX plant / EBP body Reanimation; matrix scales +24/+34. Zombie native scale +11C is journaled by live DataArray identity. Percent range 25-300; original sizes restored on disable. Automatic Cob Cannons use native Fire +6A810, EAX=plant, stack X/Y (RET 8), plant state +3C (35 arming, 36 loading, 37 ready, 38 firing), reload +54; target positions zombie +2C/+30, friendly +B8. Paused/projectile-pool guards apply.')
    reference(layouts,'Sunflower production drops','AddCoin entry hook module+F400. Filters return sites +634B8, +634F5, +6351C and plant IDs 1 or 41 only. Stack type +C and motion +10 at entry. Parameter 0 normal sun, 1 silver, 2 gold, 3 diamond maps to native type 4,1,2,3; coin motion is 3. Sky sun, loot and other producers are unchanged.')
    reference(layouts,'Money coin collection','array=[Board+FC]; stride D8; dead+38; generation ID+D0; type+58; being-collected flag+50. Only types 1 silver, 2 gold, 3 diamond are collected. Native Collect: module+34DC0, ECX=coin. Rewards and gifts are excluded.')
    reference(layouts,'Live zombie row move','Row +1C; float Y +30; integer Y +C; render order +20 changes by 10000 per row. X is preserved. Native Y routine: module+142240, EAX=zombie, push zero-based row. Only same-terrain ordinary live states are moved.')
    reference(layouts,'Local player / achievements / garden additions','Profile=[App+94C]. Identity: name SSO buffer +4 (length +14, capacity +18), immutable ID+20. 20 earned bytes +24, 20 popup-shown bytes +38. Edits require Main Menu and a backup. Garden count+378, records+380 stride58: type+0, garden+4, grid X+8, grid Y+C, growth+24, feeds+28, feeds required+2C, need+30; 64-bit timestamps +18,+38,+40,+48. Main 32 grid places, Mushroom/Aquarium 8 each, Wheelbarrow 1; global count<=200. No array compaction in add/move operations.')
    for key,(label,offset,lo,hi,scale,bias)in PROFILE_FIELDS.items():reference(layouts,'Player data — '+label,f'Profile+{offset:X}; displayed value=(stored - {bias}) * {scale}; allowed displayed range {lo}–{hi}. Use the backed-up Player data editor for writes. Read-only CT reference.')
    reference(layouts,'Achievement IDs', '\n'.join(f'{i}: {name}'for i,name in enumerate(ACHIEVEMENTS)))
    from edition_saves import BUILDS
    reference(layouts,'Isolated edition saves',json.dumps(BUILDS,indent=2)+'\nNative global MSVC string: buffer +4, length +14, capacity +18. Only validated equal-length edition roots are changed. GOTY user.dat earned/shown flags are serialized as interleaved byte pairs at 334+gardenCount*58 (hex). Launcher paths persist for this game process; Reset all does not revert the save root.')
    reference(layouts,'Scrollable seed-card pages','Existing native bank count is never increased above ten. Packet base = Bank+28+i*50. Per-packet fields: elapsed+24, total+28, type+34, imitater+38, active+48, refreshing+49, timesUsed+4C. Hidden cooldowns use Board+5580 game ticks. Main Menu/lawn transitions invalidate the deck; cursor=[Board+150], cursor type+30 must be zero before a page change. Full deck/overlay workflow is in the GUI.')
    reference(layouts,'Shop restock','Entry module+955C0: EBX=StoreScreen, EDI=item. Store+168=App. Items 0–29 may repeat at normal prices. Supplies 14/15/28 have a bounded count. Daily-Marigold result +9567E: 0F94C0 to 30C090; native full-garden check remains. Purchase guards retain seed cap 4 (ten slots), mower cap 2 and existing positive Tree height. Rebuying an owned unlock does not add another garden.')
    patches=entry(refs,'Patch sites — original bytes / replacement bytes')
    keys=set(k for values in GROUPS.values()for k in values)|{'init_lawn_mowers','lawn_mower_initialize','hack_street_zombies'}
    for key in sorted(keys):
        for rva,old,new in PATCHES[key]:reference(patches,f'{key} — module+{rva:X}',f'RVA {rva:X}\nOriginal: {old}\nPatched: {new}\nReference only. Use the control backend for ownership and restoration.')
    for label,records in [('Free planting',FREE_PLANTING),('Instant recharge',(SEED_RECHARGE,)),('Extended coin bank',BANK_PATCHES),('Snail awake and chocolate boost',SNAIL_PATCHES)]:
        for rva,old,new in records:reference(patches,f'{label} — module+{rva:X}',f'Original: {old}\nPatched: {new}')
    reference(patches,'Daily Marigold stock result',f'module+{SHOP_STOCK_EXTRA[0]:X}; original {SHOP_STOCK_EXTRA[1]}; replacement {SHOP_STOCK_EXTRA[2]}. Owned by Shop restock; full-garden branch is preserved.')
    hooks=entry(refs,'Hooks / native functions — module-relative RVAs')
    for name,(rva,size)in HOOKS.items():reference(hooks,f'{name} hook — module+{rva:X}',f'Original {HOOK_ORIGINAL[name]}; {size} whole bytes. Cave and parameter addresses are allocated per process, not static. Managed by the shared verified backend.')
    for name,(rva,size)in SHOP_CAP_HOOKS.items():reference(hooks,f'{name} purchase guard — module+{rva:X}',f'Original {SHOP_CAP_ORIGINAL[name]}; {size} whole bytes. Shared ownership with Shop restock; no separately enabled hook.')
    reference(hooks,'Rapid fire / firing delay — animation guard',f'module+{SHOOT_GUARD[0]:X}; original {SHOOT_GUARD[1]}. Firing delay preserves animations. Rapid fire uses interval {RAPID_INTERVAL} plus the direct-fire hook; it pauses acceleration at 700 allocated projectiles to leave capacity headroom.')
    functions={**SIGNATURES,0x142240:'compute zombie Y for a row; EAX=zombie; push row',0x34DC0:'collect coin; ECX=coin',0x141CA0:'body damage; EDI=zombie; push flags, push damage',0x142180:'normal zombie damage entry; ECX=zombie; EAX=flags; push damage',0x1E8A0:'process dead-object delete queue; ESI=Board',0x62190:'plant sleeping state; EDI=plant; push sleeping flag',0xECD0:'board completion; ECX=Board',0xE510:'rebuild mowers; push Board',0x5C5D0:'delete mower; EAX=mower',0x108E0:'clear street preview; EBX=Board',0x3D350:'rebuild street preview; push street object'}
    for rva,signature in sorted(functions.items()):reference(hooks,f'Native routine module+{rva:X}',str(signature)+'\nReference only; calling convention, loop gating and argument validation are required. Use LawnLab for Studio creation/garden/stage actions.')
    ET.SubElement(root,'UserdefinedSymbols')
    ET.SubElement(root,'Comments').text='LawnLab 5.14 / Primo @supremobv. Exact GOTY hash: '+HASH+'. Controls require the companion LawnLab.exe. References never write memory. Detailed usage: CHEAT-ENGINE.md. Generated by generate_ct.py.'
    # Register every toggle on session startup, including automatically enabled
    # dependencies such as Extended coin bank before its checkbox is first used.
    records='{'+','.join('['+json.dumps(k)+']='+str(v)for k,v in sorted(record_map.items()))+'}'
    for node in root.iter('AssemblerScript'):node.text=node.text.replace('records={}','records='+records)
    ET.indent(root,space='  ')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)+b'\n'

def main():
    (ROOT/'LawnLab-GOTY-1.2.0.1073.CT').write_bytes(build())
    (ROOT/'LawnLab-addresses.json').write_text(json.dumps(inventory(),indent=2)+'\n',encoding='utf-8')
    (ROOT/'LawnLab-Classic-1.0.0.1051.CT').write_bytes(build_classic())
    (ROOT/'LawnLab-Classic-addresses.json').write_text(json.dumps(classic_inventory(),indent=2)+'\n',encoding='utf-8')

def classic_inventory():
    import classic_verified_engine as engine,classic_studio_engine as studio,classic_game_layout as layout,classic_profile_tools as profile
    from runtime_image import CLASSIC_TEXT_SHA256
    names=['classic_'+n for n in ('verified_engine.py','verified_patches.py','studio_engine.py','studio_native.py','game_layout.py','profile_tools.py')]+['trainer_backend.py','runtime_image.py','patch_manager.py','edition_saves.py','startup_options.py','seed_pages.py','seed_overlay.py','resource_mods.py','studio_storage.py','studio_models.py','extra_controls.py','pak_resources.py','note_editor.py']
    literals=[];hashes={}
    for name in names:
        source=(ROOT/name).read_text(encoding='utf-8');hashes[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest();lines=source.splitlines()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node,ast.Constant)and type(node.value)is int:
                literals.append(dict(source=name,line=node.lineno,value=node.value,hex=hex(node.value),context=lines[node.lineno-1].strip()))
    return dict(extra_controls={'patches':__import__('extra_controls').PATCHES['classic'],'plant_scale_hook':__import__('extra_controls').PLANT_HOOK['classic'],'zombie_scale_field':__import__('extra_controls').ZOMBIE_SCALE,'cob_fire':__import__('extra_controls').COB_FIRE['classic'],'grid_items':__import__('extra_controls').GRID_ITEMS['classic']},version='5.14',build='Classic 1.0.0.1051',image_size=0x394000,text_sha256=CLASSIC_TEXT_SHA256,note='Mapped .text hash, not an on-disk hash. Classic runtime file is locked. Integer inventory includes flags/ranges/opcodes as well as offsets; inspect context.',source_sha256=hashes,integer_literals=literals,app=dict(root_rva=0x2A9EC0,board=0x768,user=0x82C,mode=0x7F8,ui=0x7FC,frame=0x454),arrays=studio.ARRAYS,plant_fields=studio.PLANT_FIELDS,zombie_fields=studio.ZOMBIE_FIELDS,native_signatures=studio.SIGNATURES,profile_fields=profile.PROFILE_FIELDS,achievements_supported=False,patches=engine.PATCHES,hooks={k:dict(rva=a,length=n,original=engine.HOOK_ORIGINAL[k])for k,(a,n)in engine.HOOKS.items()},layout={k:v for k,v in vars(layout).items()if k.isupper()})

def build_classic():
    root=ET.fromstring(build());parent=root.find('./CheatEntries/CheatEntry/CheatEntries')
    for item in list(parent):
        if 'ADDRESS REFERENCE'in(item.findtext('Description')or''):parent.remove(item)
    counter=max(int(n.text)for n in root.iter('ID'))
    def add(parent,title,details=None):
        nonlocal counter
        counter+=1;e=ET.SubElement(parent,'CheatEntry');ET.SubElement(e,'ID').text=str(counter);ET.SubElement(e,'Description').text='"'+title+'"'
        if details is None:ET.SubElement(e,'GroupHeader').text='1';return ET.SubElement(e,'CheatEntries')
        ET.SubElement(e,'VariableType').text='Auto Assembler Script';ET.SubElement(e,'AssemblerScript').text='[ENABLE]\n{$lua}\nif syntaxcheck then return end\nshowMessage('+json.dumps(details,ensure_ascii=False)+')\n{$asm}\n[DISABLE]\n'
    refs=add(parent,'ADDRESS REFERENCE — Classic 1.0.0.1051 only; read-only')
    add(refs,'Upgrade planting, automatic Cob Cannons, Almanac and size controls','Classic packet requirements +1D7D0; upgrade branches +E46C/+D51E; Almanac-only spans +2224,+3983,+3A10,+3B30,+30E7,+32A7,+348C. Classic ZombieIsShown is callee-cleanup RET 4. Plant UpdateReanim tail +63E22; matrix +24/+34. Zombie scale +11C, identity +158. Automatic Cob Cannons use native Fire +66D50, EAX=plant, stack X/Y (RET 8); state +3C, reload +54, zombie X/Y +2C/+30 and friendly +B8. See extra_controls.py and the Classic JSON catalog for original/replacement bytes.')
    data=classic_inventory()
    for key,value in data.items():
        if key in ('source_sha256','integer_literals'):continue
        add(refs,key,json.dumps(value,indent=2,ensure_ascii=False))
    group=add(refs,'Complete source integer inventory — context distinguishes offsets from flags/ranges')
    for name in sorted(data['source_sha256']):
        records=[r for r in data['integer_literals']if r['source']==name]
        add(group,name+' — '+data['source_sha256'][name], '\n'.join(f"L{r['line']}: {r['hex']} ({r['value']}) {r['context']}"for r in records))
    root.find('Comments').text='LawnLab 5.14 Classic 1.0.0.1051; mapped .text SHA256 '+data['text_sha256']+'. Attach to the actual popcapgame1.exe, not the PlantsVsZombies.exe launcher. Native GOTY achievement flags do not exist in Classic. Shared CT helper validates this exact PID and build.'
    ET.indent(root,space='  ');return ET.tostring(root,encoding='utf-8',xml_declaration=True)+b'\n'
if __name__=='__main__':main()

