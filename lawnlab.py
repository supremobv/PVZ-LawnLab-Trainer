"""LawnLab: Qt desktop interface for the original PVZ Trainer memory engine."""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
import sys
import traceback

from PySide6.QtCore import Qt, QObject, QRunnable, QThreadPool, QTimer, Signal, QSize, QRectF
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QComboBox, QSpinBox,
    QMessageBox, QCheckBox, QSizePolicy,
)
from trainer_engine import PvZTrainer, PLANT_NAMES, ROW_NAMES

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
LOGO = ROOT / 'assets' / 'lawnlab.svg'


@dataclass(frozen=True)
class Feature:
    category: str
    title: str
    description: str
    method: str
    state: str = ''
    editor: str = ''
    destructive: bool = False


FEATURES = [
    Feature('Sun & economy', 'Infinite sunshine', 'Keep your sun reserves at 9,999.', 'toggle_infinite_sun', 'infinite_sun_active'),
    Feature('Sun & economy', 'Free planting', 'Plant seeds without spending sun.', 'toggle_prevent_spend', 'prevent_spend_active'),
    Feature('Sun & economy', 'Auto collect', 'Pick up falling sunshine automatically.', 'toggle_auto_collect', 'auto_collect_active'),
    Feature('Sun & economy', 'Bigger sun pickups', 'Add 1,000 sun with every pickup.', 'toggle_collect_1000_sun', 'collect_1000_sun_active'),
    Feature('Sun & economy', 'Planting bonus', 'Earn 2,000 sun when you plant.', 'toggle_planting_adds_sun', 'planting_adds_sun_active'),
    Feature('Sun & economy', 'Sun limit', 'Choose an amount and keep it locked.', 'toggle_sun_lock', 'sun_lock_active', 'sun'),
    Feature('Sun & economy', 'Uncap sunshine', 'Remove the original sun ceiling.', 'toggle_unlock_sun_limit', 'unlock_sun_limit_active'),
    Feature('Sun & economy', 'Coin balance', 'Choose the balance used by the money patch.', 'toggle_money_changer', 'money_changer_active', 'money'),
    Feature('Plants', 'Instant recharge', 'Seed packets are ready without the wait.', 'toggle_no_cooldown', 'no_cooldown_active'),
    Feature('Plants', 'Plant anywhere', 'Relax the usual placement restrictions.', 'toggle_plant_anywhere', 'plant_anywhere_active'),
    Feature('Plants', 'Invincible plants', 'Give your lawn a little extra staying power.', 'toggle_invincible_plants', 'invincible_plants_active'),
    Feature('Plants', 'Plant changer', 'Replace the selected seed with another plant.', 'toggle_plant_changer', 'plant_changer_active', 'plant'),
    Feature('Plants', 'Rapid fire', 'Remove the firing delay between attacks.', 'toggle_rapid_fire', 'rapid_fire_active'),
    Feature('Plants', 'Firing delay', 'Fine-tune the delay between shots.', 'toggle_fast_shoot', 'fast_shoot_active', 'delay'),
    Feature('Plants', 'Projectile changer', 'Choose the projectile fired by your plants.', 'toggle_bullet_changer', 'bullet_changer_active', 'bullet'),
    Feature('Plants', 'Zombotany protection', 'Protect plants from Zombotany projectiles.', 'toggle_unhittable_plants_zombotany', 'unhittable_plants_active'),
    Feature('Zombies', 'One-hit knockout', 'Defeat zombies with a single hit.', 'toggle_one_hit_kill', 'one_hit_kill_active'),
    Feature('Zombies', 'Freeze the horde', 'Pause zombie movement on the lawn.', 'toggle_stop_zombies', 'stop_zombies_active'),
    Feature('Zombies', 'Pause spawning', 'Stop new zombies from joining the wave.', 'toggle_stop_spawning', 'stop_spawning_active'),
    Feature('Zombies', 'Invincible zombies', 'Make the opposition impossible to defeat.', 'toggle_invincible_zombies', 'invincible_zombies_active'),
    Feature('Zombies', 'Choose a lane', 'Send new zombies into a selected row.', 'toggle_move_zombie_row', 'move_zombie_row_active', 'row'),
    Feature('Zombies', 'Zombie preview', 'Show all zombie types in the level preview.', 'toggle_show_all_zombies', 'show_all_zombies_active'),
    Feature('Lawn & world', 'Play in background', 'Keep the game running when you switch windows.', 'toggle_run_in_background', 'run_in_background_active'),
    Feature('Lawn & world', 'Clear the fog', 'See the whole lawn on foggy nights.', 'toggle_no_fog', 'no_fog_active'),
    Feature('Lawn & world', 'See inside vases', 'Reveal the contents in Vasebreaker.', 'toggle_see_vase', 'see_vase_active'),
    Feature('Lawn & world', 'Daytime mushrooms', 'Keep mushrooms awake during the day.', 'toggle_mushrooms_awake', 'mushrooms_awake_active'),
    Feature('Lawn & world', 'Always butter', 'Make Kernel-pult throw butter every time.', 'toggle_lock_butter', 'lock_butter_active'),
    Feature('Lawn & world', 'No craters', 'Keep Doom-shroom from leaving a crater.', 'toggle_no_crater', 'no_crater_active'),
    Feature('Lawn & world', 'No ice trails', 'Keep Zomboni from icing over your lawn.', 'toggle_no_ice_trail', 'no_ice_trail_active'),
    Feature('Lawn & world', 'Quiet jack-in-the-box', 'Prevent the jack-in-the-box explosion.', 'toggle_zombie_not_explode', 'zombie_not_explode_active'),
    Feature('Lawn & world', 'Faster conveyor', 'Bring the next seed packet along sooner.', 'toggle_fast_belt', 'fast_belt_active'),
    Feature('Lawn & world', 'Keep the shovel', 'Leave the shovel selected after digging.', 'toggle_lock_shovel', 'lock_shovel_active'),
    Feature('Lawn & world', 'Game pace', 'Choose how quickly your game runs.', 'set_game_speed', editor='speed'),
    Feature('Level actions', 'Restore lawn mowers', 'Bring back your last line of defense.', 'restore_lawn_mowers'),
    Feature('Level actions', 'Clear the horde', 'Remove all zombies from the current lawn.', 'kill_all_zombies', destructive=True),
    Feature('Level actions', 'Spawn the wave', 'Bring the zombie wave onto the lawn now.', 'spawn_all_zombies_now', destructive=True),
    Feature('Level actions', 'Clear all plants', 'Start fresh with an empty lawn.', 'clear_all_plants', destructive=True),
    Feature('Level actions', 'Finish this level', 'Complete the current level immediately.', 'instant_win', destructive=True),
    Feature('Level actions', 'Fragile plants', 'Make plants die instantly when damaged.', 'toggle_instant_plant_death', 'instant_plant_death_active'),
]
CATEGORIES = ['All controls', 'Sun & economy', 'Plants', 'Zombies', 'Lawn & world', 'Level actions']

STYLE = """
QWidget { background: #111a15; color: #eceee6; font-family: 'Segoe UI'; font-size: 13px; }
QFrame#sidebar { background: #17221b; border-right: 1px solid #2b372e; }
QLabel { background: transparent; }
QLabel#muted { color: #9ca99e; }
QLabel#eyebrow { color: #a2b18f; font-size: 10px; font-weight: 700; letter-spacing: 2px; }
QLabel#pageTitle { font-size: 28px; font-weight: 700; }
QFrame#card { background: #1b271f; border: 1px solid #324133; border-radius: 14px; }
QFrame#card[active="true"] { border: 1px solid #9cc879; background: #203123; }
QLabel#cardTitle { font-size: 15px; font-weight: 600; }
QPushButton { border: 1px solid #3b4b3c; border-radius: 8px; padding: 9px 14px; background: #253528; font-weight: 600; }
QPushButton:hover { background: #344b36; border-color: #85a977; }
QPushButton:pressed { background: #16271a; }
QPushButton:disabled { color: #839083; border-color: #364237; background: #222e24; }
QPushButton#primary { background: #badc8d; color: #172414; border: none; }
QPushButton#primary:hover { background: #cdeba7; }
QPushButton#nav { background: transparent; border: none; text-align: left; padding: 13px 15px; color: #aab6a9; }
QPushButton#nav:checked { background: #2c3e2b; color: #d9efbd; }
QPushButton#nav:hover { background: #243328; }
QPushButton#danger { color: #ebba9b; }
QLineEdit, QComboBox, QSpinBox { background: #111c15; border: 1px solid #3a4a3b; border-radius: 7px; padding: 8px 10px; min-height: 18px; selection-background-color: #607f45; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: #badc8d; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView { background: #223126; color: #edf0e6; selection-background-color: #425b36; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #111a15; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: #435344; border-radius: 4px; min-height: 35px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #283b2b; color: #f0f2e8; border: 1px solid #70865a; }
"""


class ResultSignals(QObject):
    done = Signal(object, str)


class Job(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.signals = ResultSignals()

    def run(self):
        try:
            self.signals.done.emit(self.fn(), '')
        except Exception:
            self.signals.done.emit(None, traceback.format_exc())


class Switch(QCheckBox):
    def __init__(self):
        super().__init__()
        self.setFixedSize(46, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip('Enable or disable this control')

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#b4d58b' if self.isChecked() else '#485647'))
        p.drawRoundedRect(QRectF(1, 3, 44, 23), 11.5, 11.5)
        p.setBrush(QColor('#23331e' if self.isChecked() else '#c8cfc2'))
        p.drawEllipse(QRectF(25 if self.isChecked() else 5, 7, 15, 15))


class GardenBanner(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(151)
        box = QVBoxLayout(self)
        box.setContentsMargins(25, 19, 240, 18)
        box.addWidget(label('A LITTLE SUN. A LOT OF POSSIBILITIES.', 'eyebrow'))
        title = label('Make the lawn your own.')
        title.setStyleSheet('font-size: 25px; font-weight: 700; color: #f1f0df;')
        box.addWidget(title)
        subtitle = label('Fine-tune your next adventure, one switch at a time.', 'muted')
        subtitle.setWordWrap(True)
        box.addWidget(subtitle)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor('#405338'), 1))
        p.setBrush(QColor('#263b27'))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 17, 17)
        p.save()
        p.setClipRect(self.width() - 220, 1, 219, self.height() - 2)
        for i in range(6):
            for j in range(5):
                x, y = self.width() - 219 + i * 43, j * 39 - 8
                p.setPen(QPen(QColor('#3b5032'), 1))
                p.drawRoundedRect(x, y, 36, 32, 6, 6)
        p.restore()
        p.drawPixmap(self.width() - 157, 12, 126, 126, QIcon(str(LOGO)).pixmap(126, 126))


def label(text, name=''):
    widget = QLabel(text)
    widget.setObjectName(name)
    return widget


class ControlCard(QFrame):
    def __init__(self, feature, window):
        super().__init__(window.content)
        self.feature, self.window = feature, window
        self.setObjectName('card')
        self.setProperty('active', False)
        self.setMinimumHeight(135 if not feature.editor else 184)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        box = QVBoxLayout(self)
        box.setContentsMargins(18, 15, 18, 16)
        box.setSpacing(9)
        row = QHBoxLayout()
        title = label(feature.title, 'cardTitle')
        row.addWidget(title, 1)
        self.toggle = Switch() if feature.state else None
        if self.toggle:
            self.toggle.setAccessibleName(feature.title)
            self.toggle.toggled.connect(lambda checked: window.change(self, checked))
            row.addWidget(self.toggle)
        box.addLayout(row)
        desc = label(feature.description, 'muted')
        desc.setWordWrap(True)
        box.addWidget(desc)
        self.editor = None
        if feature.editor:
            self.editor = self.make_editor(feature.editor)
            self.editor.setAccessibleName(feature.title + ' value')
            box.addWidget(self.editor)
        if not feature.state:
            self.action = QPushButton('Apply pace' if feature.editor else 'Run action  ↗')
            self.action.setObjectName('danger' if feature.destructive else '')
            self.action.clicked.connect(lambda: window.action(self))
            box.addWidget(self.action, alignment=Qt.AlignmentFlag.AlignLeft)

    def make_editor(self, kind):
        if kind in ('sun', 'money', 'delay'):
            w = QSpinBox()
            w.setRange(0, {'sun': 9999, 'money': 9999999, 'delay': 255}[kind])
            w.setValue({'sun': 9999, 'money': 99999, 'delay': 2}[kind])
            w.setGroupSeparatorShown(True)
        else:
            w = QComboBox()
            values = {
                'plant': PLANT_NAMES, 'row': ROW_NAMES,
                'bullet': ['Pea', 'Snow pea', 'Cabbage', 'Melon', 'Puff', 'Winter melon', 'Fire pea', 'Star', 'Spike', 'Basketball', 'Kernel', 'Cob cannon', 'Butter'],
                'speed': ['0.2×  ·  Slow motion', '0.5×  ·  Take it easy', '1×  ·  Original pace', '2×  ·  Fast forward', '5×  ·  Extra fast', '10×  ·  Maximum'],
            }
            w.addItems(values[kind])
            if kind == 'speed':
                w.setCurrentIndex(2)
        # Configure values before enabling patches, rather than writing on every edit.
        return w

    def set_checked(self, value):
        if self.toggle:
            self.toggle.blockSignals(True)
            self.toggle.setChecked(value)
            self.toggle.blockSignals(False)
        self.setProperty('active', value)
        self.style().unpolish(self)
        self.style().polish(self)
        if self.editor:
            self.editor.setEnabled(not value)


class LawnLab(QMainWindow):
    def __init__(self, engine=None):
        super().__init__()
        self.engine = engine or PvZTrainer()
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.busy = False
        self.current_category = 'All controls'
        self.close_after_reset = False
        self.speed_changed = False
        self.setWindowTitle('LawnLab — PVZ Trainer')
        self.setWindowIcon(QIcon(str(LOGO)))
        self.resize(1160, 850)
        self.setMinimumSize(970, 700)
        self.build()
        self.update_enabled()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_process)
        self.timer.start(1800)

    def build(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(220)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 25, 18, 20)
        brand = QHBoxLayout()
        mark = QLabel()
        mark.setFixedSize(43, 43)
        mark.setPixmap(QIcon(str(LOGO)).pixmap(43, 43))
        brand.addWidget(mark)
        wordmark = QVBoxLayout()
        wordmark.setSpacing(0)
        name = label('LawnLab')
        name.setStyleSheet('font-size: 23px; font-weight: 700;')
        wordmark.addWidget(name)
        wordmark.addWidget(label('PVZ TRAINER', 'eyebrow'))
        brand.addLayout(wordmark)
        side.addLayout(brand)
        side.addSpacing(32)
        side.addWidget(label('YOUR TOOLKIT', 'eyebrow'))
        side.addSpacing(7)
        self.nav = {}
        icons = ['◈', '☀', '♧', '◎', '▧', '↗']
        for name, icon in zip(CATEGORIES, icons):
            b = QPushButton(f'{icon}    {name.replace("&", "&&")}')
            b.setObjectName('nav')
            b.setCheckable(True)
            b.setChecked(name == self.current_category)
            b.clicked.connect(lambda checked=False, category=name: self.navigate(category))
            side.addWidget(b)
            self.nav[name] = b
        side.addStretch()
        side.addWidget(label('BUILT FOR YOUR LAWN', 'eyebrow'))
        note = label('Developed by Primo\nsupremobv · supremopkv', 'muted')
        note.setStyleSheet('line-height: 1.5; padding-top: 8px;')
        side.addWidget(note)
        about = QPushButton('About && compatibility')
        about.clicked.connect(self.about)
        side.addSpacing(12)
        side.addWidget(about)
        side.addWidget(label('LAWNLab  /  4.0', 'muted'))
        outer.addWidget(sidebar)

        panel = QWidget()
        main = QVBoxLayout(panel)
        main.setContentsMargins(30, 22, 30, 16)
        main.setSpacing(17)
        top = QHBoxLayout()
        top.addWidget(label('PLANTS vs. ZOMBIES  /  GOTY EDITION', 'eyebrow'), 1)
        self.badge = label('●  Not connected')
        self.badge.setStyleSheet('color: #ddb67a; background: #302b20; border-radius: 12px; padding: 6px 12px;')
        top.addWidget(self.badge)
        main.addLayout(top)
        main.addWidget(GardenBanner())

        connection = QHBoxLayout()
        connection.addWidget(label('GAME PROCESS', 'eyebrow'))
        self.process = QComboBox()
        self.process.addItems(['Auto detect', 'popcapgame1.exe', 'PlantsVsZombies.exe'])
        self.process.setMinimumWidth(200)
        connection.addWidget(self.process)
        self.connect_button = QPushButton('Connect to game  ↗')
        self.connect_button.setObjectName('primary')
        self.connect_button.clicked.connect(self.connect_game)
        connection.addWidget(self.connect_button)
        connection.addStretch()
        main.addLayout(connection)

        heading = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(3)
        self.page_title = label('All controls', 'pageTitle')
        self.count = label('', 'muted')
        titles.addWidget(self.page_title)
        titles.addWidget(self.count)
        heading.addLayout(titles, 1)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search your toolkit…')
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(240)
        self.search.setAccessibleName('Search controls')
        self.search.textChanged.connect(self.filter_cards)
        heading.addWidget(self.search)
        main.addLayout(heading)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.grid = QGridLayout(self.content)
        self.grid.setContentsMargins(0, 0, 8, 0)
        self.grid.setSpacing(12)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cards = [ControlCard(f, self) for f in FEATURES]
        self.empty = label('No controls found. Try another search.', 'muted')
        self.empty.setParent(self.content)
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setWidget(self.content)
        main.addWidget(self.scroll, 1)
        footer = QHBoxLayout()
        self.status = label('Start your game, then connect to begin.', 'muted')
        self.status.setWordWrap(True)
        footer.addWidget(self.status, 1)
        self.active_label = label('0 active', 'muted')
        footer.addWidget(self.active_label)
        self.reset_button = QPushButton('Reset all')
        self.reset_button.clicked.connect(self.reset_all)
        footer.addWidget(self.reset_button)
        main.addLayout(footer)
        outer.addWidget(panel, 1)
        self.filter_cards()

    def navigate(self, name):
        self.current_category = name
        self.page_title.setText(name)
        for category, button in self.nav.items():
            button.setChecked(category == name)
        self.filter_cards()
        self.scroll.verticalScrollBar().setValue(0)

    def filter_cards(self):
        while self.grid.count():
            self.grid.takeAt(0)
        query = self.search.text().strip().casefold()
        shown = []
        for card in self.cards:
            f = card.feature
            visible = (self.current_category == 'All controls' or f.category == self.current_category) and query in f'{f.title} {f.description} {f.category}'.casefold()
            card.setVisible(visible)
            if visible:
                shown.append(card)
        for n, card in enumerate(shown):
            self.grid.addWidget(card, n // 2, n % 2)
        if not shown:
            self.grid.addWidget(self.empty, 0, 0, 1, 2)
        self.empty.setVisible(not shown)
        self.count.setText(f'{len(shown)} controls  ·  Pick your own way to play')

    def run(self, fn, callback):
        if self.busy:
            return
        self.busy = True
        self.update_enabled()
        self.job = Job(fn)
        self.job.signals.done.connect(lambda result, error: self.finished(result, error, callback))
        self.pool.start(self.job)

    def finished(self, result, error, callback):
        self.busy = False
        if error:
            self.status.setText('The operation could not finish. Check the game and try again.')
            print(error, file=sys.stderr)
        callback(result, error)
        self.update_enabled()

    def update_enabled(self):
        connected = self.engine.is_connected
        for card in self.cards:
            card.setEnabled(connected and not self.busy)
        self.process.setEnabled(not connected and not self.busy)
        self.connect_button.setEnabled(not self.busy)
        self.connect_button.setText('Disconnect' if connected else 'Connect to game  ↗')
        self.reset_button.setEnabled(connected and not self.busy)
        active = sum(bool(getattr(self.engine, f.state, False)) for f in FEATURES if f.state) + int(self.speed_changed)
        self.active_label.setText(f'{active} active')
        self.badge.setText('●  Connected' if connected else '●  Not connected')
        self.badge.setStyleSheet(f'color: {"#c6e7a5" if connected else "#ddb67a"}; background: {"#2b3f27" if connected else "#302b20"}; border-radius: 12px; padding: 6px 12px;')

    def connect_game(self):
        if self.engine.is_connected:
            self.reset_all(disconnect=True)
            return
        selected = self.process.currentText()
        self.engine.process_name = 'auto' if selected == 'Auto detect' else selected
        self.status.setText('Connecting to your game…')
        def done(result, error):
            if result:
                self.status.setText(f'Connected to {self.engine.attached_process_name}. Open a level to begin.')
            else:
                self.status.setText('Game not found or access denied. Open the selected game process and retry.')
        self.run(self.engine.attach_process, done)

    def prepare(self, card):
        kind = card.feature.editor
        if not kind or kind == 'speed':
            return
        value = card.editor.value() if isinstance(card.editor, QSpinBox) else card.editor.currentIndex()
        method = {'sun': 'set_sun_lock_amount', 'money': 'set_money_amount', 'plant': 'set_plant_changer_value', 'row': 'set_move_zombie_row_value', 'bullet': 'set_bullet_changer_value', 'delay': 'set_fast_shoot_delay'}[kind]
        if getattr(self.engine, method)(value) is False:
            raise RuntimeError('The game rejected the selected value.')

    def change(self, card, checked):
        if self.busy or not self.engine.is_connected:
            card.set_checked(bool(getattr(self.engine, card.feature.state, False)))
            return
        def operation():
            if checked:
                groups = [('infinite_sun_active', 'sun_lock_active'),
                          ('invincible_plants_active', 'instant_plant_death_active'),
                          ('one_hit_kill_active', 'invincible_zombies_active')]
                for group in groups:
                    if card.feature.state in group:
                        for other in FEATURES:
                            if other.state in group and other.state != card.feature.state and getattr(self.engine, other.state, False):
                                if not getattr(self.engine, other.method)(False):
                                    raise RuntimeError('Could not restore the conflicting control.')
                self.prepare(card)
            return getattr(self.engine, card.feature.method)(checked)
        def done(result, error):
            actual = bool(getattr(self.engine, card.feature.state, False))
            for other in self.cards:
                if other.feature.state:
                    other.set_checked(bool(getattr(self.engine, other.feature.state, False)))
            self.status.setText(f'{card.feature.title} {"enabled" if actual else "disabled"}.' if result and not error else f'Could not change {card.feature.title.lower()}. Check that a compatible level is open.')
        self.run(operation, done)

    def action(self, card):
        f = card.feature
        if self.busy or not self.engine.is_connected:
            return
        if f.destructive and QMessageBox.question(self, f.title, f'{f.description}\nThis changes the current level. Continue?') != QMessageBox.StandardButton.Yes:
            return
        def operation():
            method = getattr(self.engine, f.method)
            return method([50, 20, 10, 5, 2, 1][card.editor.currentIndex()]) if f.editor == 'speed' else method()
        def done(result, error):
            success = not error and result is not None and result is not False and (not isinstance(result, int) or result >= 0)
            if success and f.editor == 'speed':
                self.speed_changed = card.editor.currentIndex() != 2
            self.status.setText(f'{f.title}: done.' if success else 'Action unavailable. Check that a compatible level is open.')
        self.run(operation, done)

    def reset_all(self, checked=False, disconnect=False):
        if self.busy or not self.engine.is_connected:
            return
        def operation():
            result = self.engine.reset_all()
            # The legacy reset omits some features, including zombie preview.
            for feature in FEATURES:
                if feature.state and getattr(self.engine, feature.state, False):
                    getattr(self.engine, feature.method)(False)
            speed_ok = self.engine.set_game_speed(10) if self.speed_changed else True
            remaining = [f.title for f in FEATURES if f.state and getattr(self.engine, f.state, False)]
            return bool(result and speed_ok and not remaining)
        def done(result, error):
            for card in self.cards:
                card.set_checked(bool(getattr(self.engine, card.feature.state, False)) if card.feature.state else False)
            if result and not error:
                self.speed_changed = False
                for card in self.cards:
                    if card.feature.editor == 'speed':
                        card.editor.setCurrentIndex(2)
                self.status.setText('Controls reset. Your lawn is back to its original settings.')
                if disconnect or self.close_after_reset:
                    self.release_engine()
                if self.close_after_reset:
                    self.close_after_reset = False
                    self.close()
            else:
                self.close_after_reset = False
                self.status.setText('Some controls could not be restored. Keep the game open and retry Reset all.')
        self.run(operation, done)

    def release_engine(self):
        old = self.engine
        old.is_connected = False
        for name in vars(old):
            if name.endswith('_active'):
                setattr(old, name, False)
        if old.pm:
            try:
                old.pm.close_process()
            except Exception:
                pass
        old.pm = None
        self.engine = PvZTrainer()
        self.speed_changed = False
        for card in self.cards:
            card.set_checked(False)

    def check_process(self):
        if not self.engine.is_connected or self.busy:
            return
        try:
            code = wintypes.DWORD()
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel.GetExitCodeProcess.restype = wintypes.BOOL
            alive = kernel.GetExitCodeProcess(self.engine.pm.process_handle, ctypes.byref(code)) and code.value == 259
        except Exception:
            alive = False
        if not alive:
            self.release_engine()
            self.status.setText('The game closed. Connect again when you are ready.')
            self.update_enabled()

    def about(self):
        QMessageBox.information(self, 'About LawnLab',
            'LawnLab 4.0\nPVZ Trainer developed by Primo.\n'
            'GitHub: supremobv (current) / supremopkv (earlier account).\n\n'
            'Python + Qt (PySide6), with the original pymem engine.\n'
            'The original pvz_trainer.py is preserved.\n\n'
            'Compatibility depends on your exact game executable and build. '
            'The original engine contains a mixture of fixed offsets and pattern-based patches; '
            'the redesigned interface does not certify additional game versions.\n\n'
            'Connect manually, open a level, then enable controls. '
            'Reset all restores enabled patches and normal game speed. '
            'Closing this window while connected also attempts a reset. '
            'Level actions and changed balances cannot be undone by Reset all.')

    def closeEvent(self, event):
        if self.busy:
            event.ignore()
            self.status.setText('Wait for the current operation before closing.')
        elif self.engine.is_connected:
            event.ignore()
            self.close_after_reset = True
            self.reset_all()
        else:
            event.accept()


def configure_app(app):
    # Also make fonts available when rendering through Qt's offscreen platform.
    font_dir = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
    for name in ('segoeui.ttf', 'segoeuib.ttf', 'seguisb.ttf', 'seguisym.ttf'):
        if (font_dir / name).exists():
            QFontDatabase.addApplicationFont(str(font_dir / name))
    app.setApplicationName('LawnLab')
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    app.setFont(QFont('Segoe UI', 10))


def main():
    app = QApplication(sys.argv)
    configure_app(app)
    window = LawnLab()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
