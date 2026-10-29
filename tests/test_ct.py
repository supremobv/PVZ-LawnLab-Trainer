"""Generated CE coverage, bounded adapter commands and Lua parser validation."""
import ctypes,json,os,re,tempfile,time,unittest
from pathlib import Path
from unittest.mock import Mock
import xml.etree.ElementTree as ET
import generate_ct
from ct_bridge import dispatch,serve,BRIDGE_VERSION
from verified_engine import NAMES,GROUPS,HOOKS,HOOK_ORIGINAL
from verified_patches import PATCHES
from lawnlab import FEATURES

class CheatTableTests(unittest.TestCase):
    def test_matching_helper_version_is_required(self):
        lua=(generate_ct.ROOT/'ct_runtime.lua').read_text()
        self.assertIn("ready=='OK|"+BRIDGE_VERSION+"'",lua)
    def test_generated_table_is_current_and_has_unique_ids(self):
        content=generate_ct.build();self.assertEqual((generate_ct.ROOT/'LawnLab-GOTY-1.2.0.1073.CT').read_bytes(),content)
        tree=ET.fromstring(content);ids=[x.text for x in tree.findall('.//ID')];self.assertEqual(len(ids),len(set(ids)))
        self.assertIsNone(tree.find('LuaScript')) # No table-load execution.
    def test_every_control_has_an_enable_and_disable_route(self):
        text=generate_ct.build().decode()
        for name in NAMES:
            self.assertIn('TOGGLE|'+name+'|1',text);self.assertIn('TOGGLE|'+name+'|0',text)
        for f in FEATURES:
            self.assertIn(f.title,'\n'.join(ET.fromstring(text).itertext()))
    def test_catalog_has_all_current_patch_and_hook_records(self):
        data=generate_ct.inventory();self.assertEqual(data['patches'],PATCHES)
        for name,(rva,size)in HOOKS.items():
            self.assertEqual(data['hooks'][name],{'rva':rva,'length':size,'original':HOOK_ORIGINAL[name]})
        content=generate_ct.build().decode()
        for keys in GROUPS.values():
            for key in keys:
                for rva,old,new in PATCHES[key]:self.assertIn(f'module+{rva:X}',content)
    def test_manifest_is_current(self):
        self.assertEqual(json.loads((generate_ct.ROOT/'LawnLab-addresses.json').read_text()),json.loads(json.dumps(generate_ct.inventory())))
    def test_reference_scripts_never_write_or_call_backend(self):
        tree=ET.fromstring(generate_ct.build());refs=next(e for e in tree.findall('.//CheatEntry')if 'ADDRESS REFERENCE' in e.findtext('Description',''))
        for script in refs.findall('.//AssemblerScript'):
            self.assertIn('showMessage',script.text);self.assertNotIn('LawnLabCE.command',script.text)
            self.assertRegex(script.text,r'\A\[ENABLE\]\n\{\$lua\}\nif syntaxcheck then return end\nshowMessage\("(?:[^"\\]|\\.)*"\)\n\{\$asm\}\n\[DISABLE\]\n\Z')
    def test_commands_are_whitelisted_and_values_are_bounded(self):
        engine=Mock();dispatch(engine,['TOGGLE','auto_collect','1']);engine._toggle.assert_called_once_with('auto_collect',True)
        dispatch(engine,['VALUE','plant','47']);engine.set_plant_changer_value.assert_called_once_with(47)
        for words in [['ACTION','__dict__'],['TOGGLE','unknown','1'],['VALUE','plant','48'],['VALUE','delay','0'],['VALUE','sun','1;evil'],['ACTION','instant_win','extra']]:
            with self.assertRaises(ValueError):dispatch(engine,words)
    def test_stop_response_and_out_of_order_requests(self):
        engine=Mock(last_error='')
        for name in NAMES:setattr(engine,name+'_active',False)
        with tempfile.TemporaryDirectory()as directory:
            folder=Path(directory);(folder/'heartbeat').write_text('alive');(folder/'request').write_text('1|STOP')
            serve(engine,folder);engine.reset_all.assert_called_once();self.assertEqual((folder/'response').read_bytes(),b'OK|1\n\n')
            (folder/'request').write_text('0|PING')
            with self.assertRaises(ValueError):serve(engine,folder)
    def test_heartbeat_expiry_returns_for_cleanup(self):
        with tempfile.TemporaryDirectory()as directory:
            folder=Path(directory);heart=folder/'heartbeat';heart.write_text('alive');os.utime(heart,(time.time()-30,time.time()-30));serve(Mock(),folder)
    def test_all_embedded_lua_compiles(self):
        dll=Path(os.environ.get('PROGRAMFILES','C:/Program Files'))/'Cheat Engine/lua53-64.dll'
        if not dll.exists():self.skipTest('Local CE Lua DLL is not installed.')
        lua=ctypes.CDLL(str(dll));lua.luaL_newstate.restype=ctypes.c_void_p
        lua.luaL_loadbufferx.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_size_t,ctypes.c_char_p,ctypes.c_char_p]
        lua.lua_tolstring.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p];lua.lua_tolstring.restype=ctypes.c_char_p
        lua.lua_close.argtypes=[ctypes.c_void_p];lua.lua_settop.argtypes=[ctypes.c_void_p,ctypes.c_int]
        state=lua.luaL_newstate()
        try:
            for script in ET.fromstring(generate_ct.build()).findall('.//AssemblerScript'):
                for source in re.findall(r'\{\$lua\}(.*?)(?:\{\$asm\}|$)',script.text,re.S|re.I):
                    code=source.encode();status=lua.luaL_loadbufferx(state,code,len(code),b'LawnLab-CT',None)
                    self.assertEqual(status,0,lua.lua_tolstring(state,-1,None));lua.lua_settop(state,0)
        finally:lua.lua_close(state)
