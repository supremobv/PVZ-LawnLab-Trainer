"""PopCap PAK v0 resource rewriting; preserve order, names and file times."""
import struct

def decode(raw):
 if len(raw)>200_000_000:raise ValueError('PAK exceeds the supported size.')
 data=bytes(x^0xF7 for x in raw)
 if data[:8]!=bytes.fromhex('c04ac0ba00000000'):raise ValueError('Unsupported PAK header.')
 offset=8;index=[];total=0;names=set()
 while True:
  if offset>=len(data):raise ValueError('Truncated PAK index.')
  flag=data[offset];offset+=1
  if flag==0x80:break
  if flag!=0 or offset>=len(data):raise ValueError('Invalid PAK index.')
  size=data[offset];offset+=1
  if offset+size+12>len(data):raise ValueError('Truncated PAK record.')
  name=data[offset:offset+size].decode('ascii').replace('\\','/');offset+=size
  length=struct.unpack_from('<I',data,offset)[0];stamp=data[offset+4:offset+12];offset+=12
  key=name.casefold()
  if key in names:raise ValueError('Duplicate PAK name.')
  names.add(key);index.append((name,total,length,stamp));total+=length
  if len(index)>50000 or total>200_000_000:raise ValueError('PAK index is too large.')
 if offset+total!=len(data):raise ValueError('PAK data size differs.')
 return[(name,data[offset+start:offset+start+length],stamp)for name,start,length,stamp in index]

def encode(records):
 header=bytearray(bytes.fromhex('c04ac0ba00000000'));payload=[]
 for name,data,stamp in records:
  name=name.replace('/','\\').encode('ascii')
  if not 1<=len(name)<=255 or len(stamp)!=8:raise ValueError('Invalid PAK record.')
  header+=b'\0'+bytes([len(name)])+name+struct.pack('<I',len(data))+stamp;payload.append(data)
 header+=b'\x80';raw=bytes(header)+b''.join(payload)
 if len(raw)>200_000_000:raise ValueError('Rewritten PAK is too large.')
 return bytes(x^0xF7 for x in raw)

def replace(raw,updates):
 records=decode(raw);pending={name.casefold():(name,data)for name,data in updates.items()};result=[]
 for name,data,stamp in records:
  change=pending.pop(name.casefold(),None);result.append((name,change[1]if change else data,stamp))
 for name,data in pending.values():result.append((name,data,b'\0'*8))
 result=encode(result)
 # Read back every changed payload before handing the archive to the writer.
 check={n.casefold():data for n,data,stamp in decode(result)}
 if any(check[n.casefold()]!=data for n,data in updates.items()):raise RuntimeError('PAK rewrite verification failed.')
 return result
