"""GOTY 1.2.0.1073 fields confirmed against this executable's instructions."""
FRAME_DURATION=0x4B4
SEED_RECHARGE=(0x91E55,'7e14','9090')
FREE_PLANTING=((0x1E842,'7f0c','9090'),(0x1E844,'2bf3','9090'),(0x1E88F,'0f9ec0','b00190'))
WAVE_COUNTDOWN=0x55B4
HUGE_WAVE_COUNTDOWN=0x55BC
PAUSED=0x17C
ROW_TYPES=0x5F0
SHOOT_GUARD=(0x6320B,'ff4e588b4658')
COIN_ARRAY=(0xFC,0xD8,0x38,0xD0)
COIN_COLLECT=0x34DC0
RAPID_INTERVAL=5

def one_hit_code(origin,target):
    """A positive hit goes straight through equipment to native body damage."""
    import struct
    p=lambda n:struct.pack('<I',n&0xffffffff)
    base=target-0x1421C1
    # EDI=zombie, EBP=incoming damage, EBX=flags; death guards already ran.
    code=b'\x85\xed\x0f\x8e'+p(16)+b'\x53\x68'+p(2_000_000)
    code+=b'\xe8'+p(base+0x141CA0-(origin+len(code)+5))
    code+=b'\xe9'+p(base+0x142238-(origin+len(code)+5))
    code+=bytes.fromhex('8bc583f949')
    return code+b'\xe9'+p(target-(origin+len(code)+5))

def rapid_direct_code(origin,target):
    """Use the game's direct-fire path, with headroom in its projectile pool."""
    import struct
    p=lambda n:struct.pack('<I',n&0xffffffff)
    base=target-0x6286F
    code=b'\x8b\x46\x04\x81\xb8\xf0\0\0\0'+p(700)
    # If the allocated projectile count is high, use the existing no-target return.
    code+=b'\x0f\x83'+p(base+0x6285D-(origin+len(code)+6))
    return code+b'\xe9'+p(base+0x62BCB-(origin+len(code)+5))

def shooting_guard_code(origin,target):
    """Let an in-progress firing animation finish before starting another."""
    import struct
    pack=lambda n:struct.pack('<I',n&0xffffffff)
    # Both conditional branches reach popfd + the original dec/load instructions.
    code=b'\x9c\x83\xbe\x90\0\0\0\0\x0f\x8e'+pack(17)
    code+=b'\x83\x7e\x58\x01\x0f\x8f'+pack(7)+b'\xc7\x46\x58\x02\0\0\0'
    code+=b'\x9d'+bytes.fromhex(SHOOT_GUARD[1])
    return code+b'\xe9'+pack(target-(origin+len(code)+5))

def lane_code(parameter,original,origin,target):
    """Replace the row passed to Zombie::Initialize, preserving registers/flags.

    At RVA132A12: EDI=Zombie, [EDI+4]=Board, [EBP+8]=row, [EBP+C]=type.
    Skip absent lanes, boss and incompatible aquatic/land combinations.
    """
    import struct
    pack=lambda n:struct.pack('<I',n&0xffffffff)
    code=bytearray();labels={};fixups=[]
    def emit(b):code.extend(b)
    def mark(name):labels[name]=len(code)
    def branch(op,label):
        emit(op);fixups.append((len(code),label));emit(b'\0'*4)
    emit(b'\x9c\x51\x8b\x4f\x04\x85\xc9');branch(b'\x0f\x84','fallback')
    emit(b'\x8b\x07\x83\xb8\x1c\x09\0\0\x03');branch(b'\x0f\x85','fallback')
    emit(b'\x8b\x15'+pack(parameter))
    emit(b'\x83\xfa\x05');branch(b'\x0f\x87','fallback')
    for terrain,label in [(1,'land'),(2,'water')]:
        emit(b'\x83\xbc\x91'+pack(ROW_TYPES)+bytes([terrain]));branch(b'\x0f\x84',label)
    branch(b'\xe9','fallback')
    mark('water')
    for kind in (0,1,2,4,10,11,14,16,20):
        emit(b'\x83\x7d\x0c'+bytes([kind]));branch(b'\x0f\x84','apply')
    branch(b'\xe9','fallback')
    mark('land')
    for kind in (10,11,14,25):
        emit(b'\x83\x7d\x0c'+bytes([kind]));branch(b'\x0f\x84','fallback')
    mark('apply');emit(b'\x89\x55\x08')
    mark('fallback');emit(b'\x59\x9d'+original);emit(b'\xe9'+pack(target-(origin+len(code)+5)))
    for position,label in fixups:code[position:position+4]=pack(labels[label]-(position+4))
    return bytes(code)


def sunflower_drop_code(parameter,origin,target):
    """Only production calls from Sunflower/Twin Sunflower; sky and loot unchanged."""
    import struct
    p=lambda n:struct.pack('<I',n&0xffffffff)
    base=target-0xF406;code=bytearray();labels={};fixups=[]
    def emit(b):code.extend(b)
    def branch(op,label):emit(op);fixups.append((len(code),label));emit(b'\0'*4)
    emit(b'\x9c\x50\x8b\x44\x24\x08')
    for ret in (0x634B8,0x634F5,0x6351C):
        emit(b'\x3d'+p(base+ret));branch(b'\x0f\x84','plant')
    branch(b'\xe9','done')
    labels['plant']=len(code);emit(b'\x83\x7f\x24\x01');branch(b'\x0f\x84','change')
    emit(b'\x83\x7f\x24\x29');branch(b'\x0f\x85','done')
    labels['change']=len(code);emit(b'\xa1'+p(parameter)+b'\x89\x44\x24\x14')
    emit(b'\x83\xf8\x04');branch(b'\x0f\x84','done')
    emit(b'\xc7\x44\x24\x18\x03\0\0\0')
    labels['done']=len(code);emit(b'\x58\x9d'+bytes.fromhex('558bec83e4f8'))
    emit(b'\xe9'+p(target-(origin+len(code)+5)))
    for pos,label in fixups:code[pos:pos+4]=p(labels[label]-pos-4)
    return bytes(code)


SHOP_STOCK_EXTRA=(0x9567E,'0f94c0','30c090')
def shop_stock_code(origin,target):
    """Stock is repeatable; purchase guards separately preserve capped items."""
    import struct
    p=lambda n:struct.pack('<I',n&0xffffffff);code=bytearray();labels={};fixups=[]
    def emit(b):code.extend(b)
    def branch(op,label):emit(op);fixups.append((len(code),label));emit(b'\0'*4)
    for kind in (14,15,28):
        emit(b'\x83\xff'+bytes([kind]));branch(b'\x0f\x84','supply')
    for kind in (10,11,12):
        emit(b'\x83\xff'+bytes([kind]));branch(b'\x0f\x84','original')
    emit(b'\x83\xff\xff');branch(b'\x0f\x84','zero')
    emit(b'\x83\xff\x1d');branch(b'\x0f\x86','zero');branch(b'\xe9','original')
    labels['supply']=len(code);emit(bytes.fromhex('8b83680100008b804c09000081bcb8e8010000')+p(1_000_000)+bytes.fromhex('0f9dc0c3'))
    labels['zero']=len(code);emit(b'\x30\xc0\xc3')
    labels['original']=len(code);emit(b'\xe9'+p(target-(origin+len(code)+5)))
    for pos,label in fixups:code[pos:pos+4]=p(labels[label]-pos-4)
    return bytes(code)

SHOP_CAP_HOOKS={'shop_seed_cap':(0x976DC,6),'shop_mower_cap':(0x97826,6),'shop_tree_preserve':(0x978EE,6)}
SHOP_CAP_ORIGINAL={'shop_seed_cap':'01b03c020000','shop_mower_cap':'01b00c020000','shop_tree_preserve':'89b21c010000'}
def shop_purchase_code(name,origin,target,original):
    import struct
    p=lambda n:struct.pack('<I',n&0xffffffff)
    off,cap,mod,condition=(0x23C,4,b'\xb8',b'\x8d')if name=='shop_seed_cap'else(0x20C,2,b'\xb8',b'\x8d')if name=='shop_mower_cap'else(0x11C,0,b'\xba',b'\x8f')
    code=b'\x9c\x81'+mod+p(off)+p(cap)+b'\x0f'+condition+p(1+len(original)+5)
    code+=b'\x9d'+original+b'\xe9'+p(target-(origin+len(code)+1+len(original)+5))
    code+=b'\x9d';return code+b'\xe9'+p(target-(origin+len(code)+5))

BANK_CAP=99_999_999
BANK_PATCHES=[(rva,'9f860100',BANK_CAP.to_bytes(4,'little').hex())for rva in(0x33767,0x33770,0x3FF44,0x3FF4D,0x403AC,0x403B5,0x4093A,0x40943,0x4EF45,0x4EF4E,0x4FC13,0x4FC26,0x6617D,0x66186,0x976B1,0x976BA,0x97E22,0x128692,0x12869B)]
SNAIL_PATCHES=[(0x12CA10,'6a00e8ebdc1600','b001c204009090'),(0x12CA40,'6a00e8bbdc1600','b001c390909090')]

