"""Generate the Classic backend from shared logic and reviewed version maps.

Never infer offsets at runtime. Context-specific overrides avoid collisions
between equally numbered fields in unrelated structures. Run after editing the
shared implementation. Reference bytes live in classic_data.json.
"""
import ast,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
NATIVE={0xFA10:0xD120,0x2CC90:0x2A0F0,0x6B470:0x679B0,0x52820:0x4F560,0x52640:0x4F380,0x52C70:0x4F9E0,0x52800:0x4F540,0x1E8A0:0x1BAD0,0x142240:0x131880,0x62190:0x5E860,0xECD0:0xC3E0,0xE510:0xBC70,0x5C5D0:0x58D10,0x108E0:0xDF70,0x3D350:0x3A140}
APP={0x329670:0x2A9EC0,0x91C:0x7FC,0x918:0x7F8,0x868:0x768,0x94C:0x82C}
BOARD={0x5564:0x554C,0x5568:0x5550,0x5578:0x5560,0x5580:0x5568,0x5594:0x557C,0x557C:0x5564,0x54EC:0x54D4,0x174:0x15C,0x178:0x160,0x17C:0x164,0x6CC:0x6B4}
GARDEN={0x378:0x350,0x380:0x358,0x1E8:0x1C0}
IMPORTS={n:'classic_'+n for n in ('studio_engine','studio_native','game_layout','verified_patches')}

class Convert(ast.NodeTransformer):
    def __init__(self,module,data):self.module=module;self.scope='';self.data=data
    def visit_ImportFrom(self,node):
        node.module=IMPORTS.get(node.module,node.module);return node
    def visit_FunctionDef(self,node):
        old=self.scope
        if not old:self.scope=node.name
        node=self.generic_visit(node);self.scope=old;return node
    def visit_Constant(self,node):
        if type(node.value)is not int:return node
        mapping={}
        if self.module in ('studio_engine','verified_engine'):mapping=NATIVE|APP|BOARD
        if self.module=='studio_engine':
            if self.scope in ('garden','garden_edit','garden_inventory'):mapping|=GARDEN
            if self.scope in ('seed_bank','set_seed'):mapping|={0x15C:0x144}
            if self.scope=='enable_effect':mapping|={0x70E29:0x6C769}
            if self.scope=='launch_level':mapping|={0x4C:0x24}
            if self.scope in ('set_projectile_damage','reset'):mapping|={0x31E900:0x29F1C0}
        if self.module=='verified_engine':
            if self.scope=='tick':mapping|={0x50:0x28}
            if self.scope=='restore_lawn_mowers':mapping|={0x118:0x100,0x11C:0x104}
        if self.module=='studio_native':mapping={0x1D6C6D:0x152013,0x1D6C37:0x151FF0}
        if self.module=='profile_tools':mapping=APP|GARDEN
        return ast.copy_location(ast.Constant(mapping.get(node.value,node.value)),node)
    def visit_Assign(self,node):
        names=[x.id for x in node.targets if isinstance(x,ast.Name)]
        name=names[0]if len(names)==1 else''
        if not self.scope:
            overrides={}
            if self.module=='studio_engine':overrides={'HASH':self.data['text_sha256'],'ARRAYS':{'plant':(0xAC,0x14C,0x141,0x148),'zombie':(0x90,0x15C,0xEC,0x158),'projectile':(0xC8,0x94,0x50,0x90)},'SIGNATURES':{int(k):v for k,v in self.data['signatures'].items()}}
            if self.module=='verified_engine':overrides={'HOOKS':{k:tuple(v)for k,v in self.data['hooks'].items()},'HOOK_ORIGINAL':self.data['hook_original']}
            if self.module=='profile_tools':
                from profile_tools import PROFILE_FIELDS
                overrides={'PROFILE_FIELDS':{k:(v[0],v[1]-0x28,*v[2:])for k,v in PROFILE_FIELDS.items()}}
            if name in overrides:node.value=ast.parse(repr(overrides[name]),mode='eval').body;return node
        if self.module=='profile_tools'and name=='HAS_ACHIEVEMENTS':node.value=ast.Constant(False);return node
        return self.generic_visit(node)

def generate():
    data=json.loads((ROOT/'classic_data.json').read_text())
    outputs={}
    for module in ('studio_engine','studio_native','verified_engine','profile_tools'):
        source=(ROOT/(module+'.py')).read_text(encoding='utf-8-sig')
        if module=='studio_engine':
            start=source.index('                m=pymem.process.module_from_name')
            end=source.index('            self._checked=',start)
            source=source[:start]+"                from runtime_image import classic_guard\n                runtime=getattr(self.engine,'runtime',None)\n                shared=getattr(runtime,'game',None)\n                if shared is not None and shared is not self and shared._checked is self.engine.pm:\n                    self._classic_image=runtime.image\n                else:self._classic_image=classic_guard(self.engine)\n"+source[end:]
            # Classic sleeping uses EAX, not GOTY's EDI (used in trainer only).
        if module=='verified_engine':
            start=source.index('        import pymem.process\n',source.index('class VerifiedRuntime:'))
            end=source.index('        self.native=',start)
            source=source[:start]+'        self.image=self.game._classic_image\n'+source[end:]
            # Assigned hook dictionaries above include all entries; do not overwrite them.
            source='\n'.join(line for line in source.splitlines()if not line.startswith(('HOOKS.update(','HOOK_ORIGINAL.update(')))+'\n'
            source=source.replace("(0x62190,'edi'","(0x62190,'eax'")
        tree=Convert(module,data).visit(ast.parse(source));ast.fix_missing_locations(tree)
        result=ast.unparse(tree)+'\n'
        if module=='studio_native':
            result=result.replace("b'\\xeb\\xc8'","b'\\x74\\xdb'").replace("b'\\xeb\\xc8'","b'\\x74\\xdb'").replace("b'\\xc8'","b'\\xdb'")
            # ast.unparse uses uppercase escape spelling only for literal uppercase bytes.
            result=result.replace("b'\\xEB\\xC8'","b'\\x74\\xdb'").replace("b'\\xC8'","b'\\xdb'")
        outputs['classic_'+module+'.py']='# Generated by generate_classic.py; edit shared source/version map.\n'+result
    return outputs

def main():
    for name,source in generate().items():(ROOT/name).write_text(source,encoding='utf-8')
if __name__=='__main__':main()
