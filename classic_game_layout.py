"""Classic 1.0.0.1051 fields and x86 calling conventions."""
import struct
import game_layout as goty
FRAME_DURATION=0x454
SEED_RECHARGE=(0x87296,'7e14','9090')
FREE_PLANTING=((0x1BA72,'7f0c','9090'),(0x1BA74,'2bf3','9090'),(0x1BABF,'0f9ec0','b00190'))
WAVE_COUNTDOWN=0x559C
HUGE_WAVE_COUNTDOWN=0x55A4
PAUSED=0x164
ROW_TYPES=0x5D8
SHOOT_GUARD=(0x5F8A9,'834658ff8b4658')
COIN_ARRAY=(0xE4,0xD8,0x38,0xD0)
COIN_COLLECT=0x32060
RAPID_INTERVAL=5
SHOP_STOCK_EXTRA=(0x8AA8E,'0f94c0','30c090')
SHOP_CAP_HOOKS={'shop_seed_cap':(0x8CAD7,6),'shop_mower_cap':(0x8CC1C,6),'shop_tree_preserve':(0x8CCE4,6)}
SHOP_CAP_ORIGINAL={'shop_seed_cap':'01b014020000','shop_mower_cap':'01b0e4010000','shop_tree_preserve':'89b2f4000000'}
BANK_CAP=goty.BANK_CAP
BANK_PATCHES=[(a,'9f860100',BANK_CAP.to_bytes(4,'little').hex())for a in (0x30A74,0x30A7D,0x3CD0B,0x3CD14,0x3D184,0x3D18D,0x3D714,0x3D71D,0x4C265,0x4C26E,0x4CE93,0x4CEA6,0x6279D,0x627A6,0x8CAAC,0x8CAB5,0x8D0D1,0x11DD8F,0x11DD98)]
SNAIL_PATCHES=[(0x122090,'6a00e8b8a50f00','b001c204009090'),(0x1220C0,'6a00e888a50f00','b001c390909090')]
p=lambda n:struct.pack('<I',n&0xffffffff)

def one_hit_code(origin,target):
    base=target-0x1317FF
    # ESI=zombie. BodyDamage takes zombie, damage, flags on the stack.
    code=b'\x85\xed\x0f\x8e'+p(17)+b'\x53\x68'+p(2_000_000)+b'\x56'
    code+=b'\xe8'+p(base+0x1312D0-(origin+len(code)+5))
    code+=b'\xe9'+p(base+0x131877-(origin+len(code)+5))
    code+=bytes.fromhex('83f9498bc5')
    return code+b'\xe9'+p(target-(origin+len(code)+5))

def rapid_direct_code(origin,target):
    base=target-0x5EF3D
    code=b'\x8b\x46\x04\x81\xb8\xd8\0\0\0'+p(700)
    code+=b'\x0f\x83'+p(base+0x5EF2E-(origin+len(code)+6))
    return code+b'\xe9'+p(base+0x5F272-(origin+len(code)+5))

def shooting_guard_code(origin,target):
    # Same guard, but replay Classic's seven-byte decrement/load sequence.
    return goty.shooting_guard_code(origin,target).replace(bytes.fromhex(goty.SHOOT_GUARD[1]),bytes.fromhex(SHOOT_GUARD[1]))[:-4]+p(target-(origin+len(goty.shooting_guard_code(origin,target))+1))

def lane_code(parameter,original,origin,target):
    code=bytearray();labels={};fixups=[]
    def emit(b):code.extend(b)
    def branch(op,label):emit(op);fixups.append((len(code),label));emit(b'\0'*4)
    emit(bytes.fromhex('9c52518b4f0485c9'));branch(b'\x0f\x84','fallback')
    emit(bytes.fromhex('8b0783b8fc07000003'));branch(b'\x0f\x85','fallback')
    emit(b'\x8b\x15'+p(parameter)+b'\x83\xfa\x05');branch(b'\x0f\x87','fallback')
    for terrain,label in ((1,'land'),(2,'water')):
        emit(b'\x83\xbc\x91'+p(ROW_TYPES)+bytes([terrain]));branch(b'\x0f\x84',label)
    branch(b'\xe9','fallback');labels['water']=len(code)
    for kind in (0,1,2,4,10,11,14,16,20):
        emit(b'\x83\x7d\x0c'+bytes([kind]));branch(b'\x0f\x84','apply')
    branch(b'\xe9','fallback');labels['land']=len(code)
    for kind in (10,11,14,25):
        emit(b'\x83\x7d\x0c'+bytes([kind]));branch(b'\x0f\x84','fallback')
    labels['apply']=len(code);emit(b'\x8b\xf2')
    labels['fallback']=len(code);emit(b'\x59\x5a\x9d'+original)
    emit(b'\xe9'+p(target-(origin+len(code)+5)))
    for pos,label in fixups:code[pos:pos+4]=p(labels[label]-pos-4)
    return bytes(code)

def sunflower_drop_code(parameter,origin,target):
    # Generate using the shared logic, substituting only verified return sites.
    code=goty.sunflower_drop_code(parameter,origin,target)
    fakebase=target-0xF406;base=target-0xCB16
    for old,new in ((0x634B8,0x5FAE7),(0x634F5,0x5FB22),(0x6351C,0x5FB49)):
        code=code.replace(p(fakebase+old),p(base+new))
    return code

def shop_stock_code(origin,target):
    code=goty.shop_stock_code(origin,target)
    return code.replace(bytes.fromhex('8b83680100008b804c09000081bcb8e8010000'),bytes.fromhex('8b83500100008b802c08000081bcb8c0010000'))

def shop_purchase_code(name,origin,target,original):
    offsets={'shop_seed_cap':(0x23C,0x214),'shop_mower_cap':(0x20C,0x1E4),'shop_tree_preserve':(0x11C,0xF4)}
    code=goty.shop_purchase_code(name,origin,target,original)
    old,new=offsets[name]
    return code.replace(p(old),p(new))

