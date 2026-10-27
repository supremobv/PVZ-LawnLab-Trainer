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
window = LawnLab()
window.timer.stop()
window.show()
app.processEvents()
window.grab().save(str(root / 'assets' / 'preview.png'))
window.navigate('Plants')
app.processEvents()
window.grab().save(str(root / 'assets' / 'preview-plants.png'))
icon = QIcon(str(LOGO))
icon.pixmap(256, 256).save(str(root / 'assets' / 'lawnlab.png'))
icon.pixmap(256, 256).save(str(root / 'assets' / 'lawnlab.ico'))
window.close()
