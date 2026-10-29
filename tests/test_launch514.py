import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from edition_saves import game_dll_search,start_game
class GameDLLSearch(unittest.TestCase):
 def kernel(self):
  def get(n,buf):buf.value=r'C:\LawnLab\_internal';return len(buf.value)
  return SimpleNamespace(GetDllDirectoryW=Mock(side_effect=get),SetDllDirectoryW=Mock(return_value=1))
 def test_normal_search_during_spawn_restored_afterward(self):
  k=self.kernel()
  def spawn(*args):self.assertEqual(k.SetDllDirectoryW.call_args.args,(None,));return 'child'
  with patch('ctypes.WinDLL',return_value=k),patch('edition_saves._start_game',side_effect=spawn):self.assertEqual(start_game('classic',None),'child')
  self.assertEqual(k.SetDllDirectoryW.call_args_list[-1].args,(r'C:\LawnLab\_internal',))
 def test_failed_spawn_still_restores_parent(self):
  k=self.kernel()
  with patch('ctypes.WinDLL',return_value=k),self.assertRaises(OSError):
   with game_dll_search():raise OSError('spawn failed')
  self.assertEqual(k.SetDllDirectoryW.call_args_list[-1].args,(r'C:\LawnLab\_internal',))
 def test_clear_failure_prevents_launch(self):
  k=self.kernel();k.SetDllDirectoryW.return_value=0
  with patch('ctypes.WinDLL',return_value=k),patch('edition_saves._start_game')as spawn,self.assertRaises(OSError):start_game('classic',None)
  spawn.assert_not_called()
