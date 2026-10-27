"""Connection fallback and handle-cleanup checks; all process calls are mocked."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch, call
from trainer_engine import PvZTrainer


class ConnectionTests(unittest.TestCase):
    def test_auto_falls_back_to_plants_executable(self):
        engine = PvZTrainer()
        process = Mock(process_handle=123)
        with patch('trainer_engine.pymem.Pymem', side_effect=[RuntimeError('not found'), process]) as opened, patch('trainer_engine.pymem.process.module_from_name', return_value=SimpleNamespace(lpBaseOfDll=0x400000)):
            self.assertTrue(engine.attach_process())
        self.assertEqual(opened.call_args_list, [
            call('popcapgame1.exe', exact_match=True, ignore_case=True),
            call('PlantsVsZombies.exe', exact_match=True, ignore_case=True),
        ])
        self.assertEqual(engine.attached_process_name, 'PlantsVsZombies.exe')
        self.assertEqual(engine.base_address, 0x400000)

    def test_manual_choice_does_not_attach_another_game(self):
        engine = PvZTrainer()
        engine.process_name = 'PlantsVsZombies.exe'
        with patch('trainer_engine.pymem.Pymem', side_effect=RuntimeError('not found')) as opened:
            self.assertFalse(engine.attach_process())
        self.assertEqual(opened.call_count, 1)
        self.assertIsNone(engine.pm)

    def test_failed_module_lookup_closes_the_handle(self):
        engine = PvZTrainer()
        engine.process_name = 'PlantsVsZombies.exe'
        process = Mock()
        with patch('trainer_engine.pymem.Pymem', return_value=process), patch('trainer_engine.pymem.process.module_from_name', return_value=None):
            self.assertFalse(engine.attach_process())
        process.close_process.assert_called_once()
        self.assertFalse(engine.is_connected)

    def test_detection_does_not_open_process_memory(self):
        engine = PvZTrainer()
        with patch('trainer_engine.pymem.process.process_from_name', side_effect=[None, object()]), patch('trainer_engine.pymem.Pymem') as opened:
            self.assertTrue(engine.check_game_running())
        opened.assert_not_called()


if __name__ == '__main__':
    unittest.main()
