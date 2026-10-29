"""Fingerprint a locked Classic executable through its mapped PE sections."""
import hashlib
import pefile

CLASSIC_TEXT_SHA256='a53b1b79f1e79f974397640c7e026af9131417bfdd2c0b8b3136615ca440fd7e'

def mapped_image(pm,base):
    pe=pefile.PE(data=pm.read_bytes(base,4096),fast_load=True)
    try:
        data=bytearray(pe.OPTIONAL_HEADER.SizeOfImage)
        data[:pe.OPTIONAL_HEADER.SizeOfHeaders]=pm.read_bytes(base,pe.OPTIONAL_HEADER.SizeOfHeaders)
        for section in pe.sections:
            start=section.VirtualAddress;size=section.Misc_VirtualSize
            data[start:start+size]=pm.read_bytes(base+start,size)
        return bytes(data)
    finally:pe.close()

def classic_guard(engine):
    import pymem.process
    module=pymem.process.module_from_name(engine.pm.process_handle,engine.attached_process_name)
    if not module or module.SizeOfImage!=0x394000:raise RuntimeError('Unsupported Classic image size.')
    from startup_options import normalize_classic
    image=normalize_classic(mapped_image(engine.pm,engine.base_address))
    pe=pefile.PE(data=image,fast_load=True)
    try:
        section=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text')
        digest=hashlib.sha256(image[section.VirtualAddress:section.VirtualAddress+section.Misc_VirtualSize]).hexdigest()
    finally:pe.close()
    if digest!=CLASSIC_TEXT_SHA256:raise RuntimeError('Classic executable code differs. Close other trainers and restart the supported 1.0.0.1051 game.')
    return image
