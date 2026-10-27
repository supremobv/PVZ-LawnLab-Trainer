"""Exercise actual Qt signals with a fake engine; never attach to a real game."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import sys
import time
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from lawnlab import LawnLab, FEATURES, STYLE


class FakeEngine:
    def __init__(self):
        self.is_connected = False
        self.attached_process_name = 'PlantsVsZombies.exe'
        self.fail = False
        self.calls = []
        for feature in FEATURES:
            if feature.state:
                setattr(self, feature.state, False)

    def attach_process(self):
        self.is_connected = True
        return True

    def reset_all(self):
        # Simulate the old reset's omission of the preview toggle.
        for feature in FEATURES:
            if feature.state and feature.state != 'show_all_zombies_active':
                setattr(self, feature.state, False)
        return True

    def __getattr__(self, name):
        def call(*args):
            self.calls.append((name, args))
            if self.fail:
                return False
            for feature in FEATURES:
                if feature.method == name and feature.state:
                    setattr(self, feature.state, args[0])
            return True
        return call


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle('Fusion')
        cls.app.setStyleSheet(STYLE)

    def setUp(self):
        self.engine = FakeEngine()
        self.window = LawnLab(self.engine)
        self.window.timer.stop()
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.engine.is_connected = False
        self.window.close()
        self.app.processEvents()

    def wait(self):
        deadline = time.monotonic() + 5
        while self.window.busy and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.app.processEvents()
        self.assertFalse(self.window.busy)

    def connect(self):
        self.window.connect_button.click()
        self.wait()

    def test_offline_controls_and_navigation(self):
        self.assertTrue(all(not card.isEnabled() for card in self.window.cards))
        self.window.nav['Plants'].click()
        self.assertTrue(all(card.isHidden() == (card.feature.category != 'Plants') for card in self.window.cards))
        self.window.search.setText('recharge')
        visible = [card.feature.title for card in self.window.cards if not card.isHidden()]
        self.assertEqual(visible, ['Instant recharge'])
        self.window.search.setText('not-a-real-control')
        self.assertFalse(self.window.empty.isHidden())

    def test_toggle_rolls_back_on_engine_failure(self):
        self.connect()
        self.engine.fail = True
        card = self.window.cards[0]
        card.toggle.click()
        self.wait()
        self.assertFalse(card.toggle.isChecked())
        self.assertIn('Could not change', self.window.status.text())

    def test_conflicting_controls_and_legacy_reset_gap(self):
        self.connect()
        sun = self.window.cards[0]
        locked = next(c for c in self.window.cards if c.feature.editor == 'sun')
        self.assertEqual(locked.editor.maximum(), 9999)
        sun.toggle.click()
        self.wait()
        locked.toggle.click()
        self.wait()
        self.assertFalse(sun.toggle.isChecked())
        self.assertTrue(locked.toggle.isChecked())
        preview = next(c for c in self.window.cards if c.feature.state == 'show_all_zombies_active')
        self.engine.show_all_zombies_active = True
        self.window.reset_all()
        self.wait()
        self.assertFalse(self.engine.show_all_zombies_active)
        self.assertFalse(preview.toggle.isChecked())
        self.assertEqual(self.window.active_label.text(), '0 active')

    def test_pace_restored_on_reset(self):
        self.connect()
        pace = next(c for c in self.window.cards if c.feature.editor == 'speed')
        pace.editor.setCurrentIndex(3)
        self.window.action(pace)
        self.wait()
        self.assertTrue(self.window.speed_changed)
        self.window.reset_all()
        self.wait()
        self.assertIn(('set_game_speed', (10,)), self.engine.calls)
        self.assertEqual(pace.editor.currentIndex(), 2)


if __name__ == '__main__':
    unittest.main()
