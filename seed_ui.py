"""Named card-deck editor and in-game paging controls."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QListWidget,QListWidgetItem,QPushButton,QHBoxLayout,QLineEdit,QAbstractItemView,QCheckBox,QSpinBox
from studio_labels import plant_name
from seed_pages import SeedDeck
from seed_overlay import OverlayPreferences

class SeedPagesPanel(QWidget):
 def __init__(self,studio):
  super().__init__();self.studio=studio;self.deck=None;self.overlay=None
  box=QVBoxLayout(self);note=QLabel('Choose plants below, then start a normal Adventure/Survival lawn. Scroll the mouse wheel over the in-game seed bank, use its new ◀/▶ arrows, or use the buttons here. PVZ keeps its existing 1–10 visible slots; pages hold the other cards. Hidden-card cooldowns follow the game clock. Place/cancel a held plant before turning a page. Windowed/borderless mode is required for the overlay. The last page repeats valid cards to fill native slots safely. At Survival repick the deck stops; start it again after choosing seeds. Closing Studio only hides it: scrolling continues while the main LawnLab controller stays connected.');note.setWordWrap(True);box.addWidget(note)
  self.search=QLineEdit();self.search.setPlaceholderText('Find a plant for the scrolling deck');box.addWidget(self.search)
  self.cards=QListWidget();self.cards.setMinimumHeight(190);self.cards.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
  for i in range(48):
   item=QListWidgetItem(plant_name(i));item.setData(Qt.ItemDataRole.UserRole,i);item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Unchecked);self.cards.addItem(item)
  self.search.textChanged.connect(lambda text:[self.cards.item(i).setHidden(text.casefold()not in self.cards.item(i).text().casefold())for i in range(48)])
  box.addWidget(self.cards)
  buttons=QHBoxLayout()
  for title,fn in [('Select all 48',lambda:self.check_all(True)),('Clear selection',lambda:self.check_all(False)),('Start scrolling deck',self.start),('Stop / restore cards',self.stop)]:
   b=QPushButton(title);b.clicked.connect(fn);buttons.addWidget(b)
  box.addLayout(buttons);pages=QHBoxLayout()
  for title,step in [('◀ Previous page',-1),('Next page ▶',1)]:
   button=QPushButton(title);button.clicked.connect(lambda checked=False,delta=step:self.turn(delta));pages.addWidget(button)
  self.label=QLabel('No scrolling deck active.');pages.addWidget(self.label);box.addLayout(pages)
  self.overlay_preferences=OverlayPreferences()
  self.show_bar=QCheckBox('Show in-game page bar (mouse wheel still works when hidden)');self.show_bar.setChecked(self.overlay_preferences.visible);self.show_bar.toggled.connect(self.show_overlay);box.addWidget(self.show_bar)
  positioning=QHBoxLayout();positioning.addWidget(QLabel('Bar position: X'))
  self.bar_x=QSpinBox();self.bar_x.setRange(0,290);self.bar_y=QSpinBox();self.bar_y.setRange(0,574)
  x,y=self.overlay_preferences.position;self.bar_x.setValue(x);self.bar_y.setValue(y)
  positioning.addWidget(self.bar_x);positioning.addWidget(QLabel('Y'));positioning.addWidget(self.bar_y)
  reset=QPushButton('Reset bar position');reset.clicked.connect(lambda:self.update_position(110,86));positioning.addWidget(reset);box.addLayout(positioning)
  self.bar_x.valueChanged.connect(self.move_overlay);self.bar_y.valueChanged.connect(self.move_overlay)
  hint=QLabel('Drag the middle page label in PVZ to move it, or use X/Y here. Position follows the game window and is saved. With the bar hidden, keep PVZ focused and scroll your mouse wheel while pointing at the seed cards.');hint.setWordWrap(True);box.addWidget(hint)
 def show_overlay(self,visible):
  self.overlay_preferences.show(visible)
  if self.overlay:self.overlay.set_bar_visible(visible)
 def move_overlay(self):
  x,y=self.bar_x.value(),self.bar_y.value();self.overlay_preferences.move(x,y)
  if self.overlay:self.overlay.set_position(x,y)
 def update_position(self,x,y):
  for spin,value in ((self.bar_x,x),(self.bar_y,y)):spin.blockSignals(True);spin.setValue(value);spin.blockSignals(False)
  self.move_overlay()
 def check_all(self,state):
  for i in range(48):self.cards.item(i).setCheckState(Qt.CheckState.Checked if state else Qt.CheckState.Unchecked)
 def start(self):
  selected=[self.cards.item(i).data(Qt.ItemDataRole.UserRole)for i in range(48)if self.cards.item(i).checkState()==Qt.CheckState.Checked]
  def operation():
   if self.deck and self.deck.active:self.deck.stop()
   g=self.studio.game();self.deck=SeedDeck(g);return self.deck.start(selected)
  def done(pages):
   from seed_overlay import SeedOverlay
   try:
    if self.overlay:self.overlay.stop()
    self.overlay=SeedOverlay(self.studio,self.overlay_preferences);self.overlay.positionChanged.connect(self.update_position);self.overlay.start(self.deck);self.label.setText(f'{len(selected)} plants · {pages} pages')
   except Exception as error:
    self.deck.stop();self.studio.status.setText('Could not start the in-game overlay: '+str(error))
  self.studio.run(operation,done)
 def turn(self,delta):
  if self.deck and self.deck.active:self.studio.run(lambda:self.deck.step(delta),self.label.setText)
  else:self.studio.status.setText('Start the scrolling deck first.')
 def stop(self):
  if self.overlay:self.overlay.stop()
  if self.deck:self.studio.run(self.deck.stop,lambda _:self.label.setText('Original cards restored where the lawn still exists.'))
