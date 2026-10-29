"""Render the actual application offline, without opening or attaching to a game."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QFont
from lawnlab import LawnLab, configure_app, LOGO

root = Path(__file__).resolve().parent
app = QApplication([])
configure_app(app)
def settle():
    for _ in range(4):app.processEvents()
window = LawnLab()
window.timer.stop()
window.show()
settle()
window.grab().save(str(root / 'assets' / 'preview.png'))
window.navigate('Plants')
settle()
window.grab().save(str(root / 'assets' / 'preview-plants.png'))
icon = QIcon(str(LOGO))
icon.pixmap(256, 256).save(str(root / 'assets' / 'lawnlab.png'))
icon.pixmap(256, 256).save(str(root / 'assets' / 'lawnlab.ico'))
from studio_ui import LawnStudio
studio = LawnStudio(window)
studio.show()
studio.timer.stop();studio.hotkey_timer.stop()
settle()
studio.grab().save(str(root / 'assets' / 'preview-studio.png'))
for index,name in [(1,'entities'),(2,'waves'),(3,'seeds'),(4,'garden'),(5,'backups'),(6,'profiles'),(7,'player'),(8,'extensions')]:
    studio.tabs.setCurrentIndex(index);settle()
    studio.grab().save(str(root / 'assets' / f'preview-studio-{name}.png'))
studio.close()
window.close()

from lawn_canvas import LawnPlanCanvas
canvas=LawnPlanCanvas();canvas.resize(900,440);canvas.show()
canvas.set_plan(2,[dict(type=t,row=r,col=c)for r in range(1,7)for c,t in [(1,1),(2,0),(7,3)]]+[dict(type=16,row=r,col=c)for r in (3,4)for c in (1,2,7)])
settle();canvas.grab().save(str(root/'assets'/'preview-lawn-plan.png'));canvas.close()
