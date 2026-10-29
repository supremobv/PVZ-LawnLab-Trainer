"""Windowed-game page arrows and wheel input limited to its native seed bank."""
import ctypes
from ctypes import wintypes as w
from PySide6.QtCore import Qt,QTimer,Signal,QPoint,QSettings
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget,QHBoxLayout,QPushButton,QLabel

class MouseData(ctypes.Structure):
 _fields_=[('point',w.POINT),('mouseData',w.DWORD),('flags',w.DWORD),('time',w.DWORD),('extra',ctypes.c_size_t)]

class OverlayPreferences:
 def __init__(self,settings=None):self.settings=settings if settings is not None else QSettings('LawnLab','SeedOverlay')
 @property
 def position(self):
  try:return (max(0,min(290,int(self.settings.value('x',110)))),max(0,min(574,int(self.settings.value('y',86)))))
  except (ValueError,TypeError):return (110,86)
 @property
 def visible(self):return str(self.settings.value('visible','true')).lower()not in ('false','0')
 def move(self,x,y):
  self.settings.setValue('x',max(0,min(290,int(x))));self.settings.setValue('y',max(0,min(574,int(y))))
 def show(self,value):self.settings.setValue('visible',bool(value))

class DragCaption(QLabel):
 def mousePressEvent(self,event):
  if event.button()==Qt.MouseButton.LeftButton:self.parentWidget().begin_drag(event.globalPosition().toPoint());event.accept()
  else:super().mousePressEvent(event)
 def mouseMoveEvent(self,event):
  if event.buttons()&Qt.MouseButton.LeftButton:self.parentWidget().drag_to(event.globalPosition().toPoint());event.accept()
  else:super().mouseMoveEvent(event)
 def mouseReleaseEvent(self,event):
  if event.button()==Qt.MouseButton.LeftButton:self.parentWidget().end_drag();event.accept()
  else:super().mouseReleaseEvent(event)

class SeedOverlay(QWidget):
 turn=Signal(int)
 positionChanged=Signal(int,int)
 def __init__(self,studio,preferences=None):
  super().__init__(None,Qt.WindowType.Tool|Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.WindowDoesNotAcceptFocus)
  self.studio=studio;self.deck=None;self.hwnd=None;self.bounds=None;self.hook=None
  self.preferences=preferences if preferences is not None else OverlayPreferences();self.drag_anchor=None;self.logical_scale=1
  self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating);self.setStyleSheet('background:#1a3022;color:#eaf6d3;border-radius:5px;')
  box=QHBoxLayout(self);box.setContentsMargins(3,2,3,2)
  back=QPushButton('◀');forward=QPushButton('▶');self.caption=DragCaption();self.caption.setCursor(Qt.CursorShape.SizeAllCursor);self.caption.setToolTip('Drag this label to move the page bar. Position is saved.');box.addWidget(back);box.addWidget(self.caption,1);box.addWidget(forward)
  back.clicked.connect(lambda:self.turn.emit(-1));forward.clicked.connect(lambda:self.turn.emit(1));self.turn.connect(self.change)
  self.timer=QTimer(self);self.timer.setInterval(160);self.timer.timeout.connect(self.sync)
  self.user=ctypes.WinDLL('user32',use_last_error=True);self.user.GetForegroundWindow.restype=w.HWND
  self.user.GetWindowThreadProcessId.argtypes=[w.HWND,ctypes.POINTER(w.DWORD)];self.user.IsWindowVisible.argtypes=[w.HWND]
  self.user.IsIconic.argtypes=[w.HWND]
  self.user.GetClientRect.argtypes=[w.HWND,ctypes.POINTER(w.RECT)];self.user.ClientToScreen.argtypes=[w.HWND,ctypes.POINTER(w.POINT)]
  self.callback_type=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,ctypes.c_int,w.WPARAM,w.LPARAM)
  self.user.SetWindowsHookExW.argtypes=[ctypes.c_int,self.callback_type,w.HINSTANCE,w.DWORD];self.user.SetWindowsHookExW.restype=w.HHOOK
  self.user.CallNextHookEx.argtypes=[w.HHOOK,ctypes.c_int,w.WPARAM,w.LPARAM];self.user.CallNextHookEx.restype=ctypes.c_ssize_t
  self.user.UnhookWindowsHookEx.argtypes=[w.HHOOK]
 def start(self,deck):
  self.stop();self.deck=deck;pid=self.studio.owner.engine.pm.process_id;found=[]
  callback=ctypes.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
  @callback
  def visit(hwnd,param):
   actual=w.DWORD();self.user.GetWindowThreadProcessId(hwnd,ctypes.byref(actual))
   if actual.value==pid and self.user.IsWindowVisible(hwnd):found.append(hwnd)
   return True
  self.user.EnumWindows.argtypes=[callback,w.LPARAM];self.user.EnumWindows(visit,0)
  if not found:raise RuntimeError('The game window is not available for the seed overlay.')
  self.hwnd=found[0]
  @self.callback_type
  def mouse(code,message,param):
   if code>=0 and message in(0x20A,0x20E):
    event=ctypes.cast(param,ctypes.POINTER(MouseData)).contents
    direction=self.wheel_direction(message,ctypes.c_short(event.mouseData>>16).value,event.point.x,event.point.y,self.user.GetForegroundWindow())
    if direction:self.turn.emit(direction);return 1
   return self.user.CallNextHookEx(self.hook,code,message,param)
  self.mouse_callback=mouse;self.hook=self.user.SetWindowsHookExW(14,mouse,None,0)
  if not self.hook:raise ctypes.WinError(ctypes.get_last_error())
  self.timer.start();self.sync()
 def wheel_direction(self,message,delta,x,y,foreground):
  if message not in(0x20A,0x20E)or not delta or not self.bounds or not self.deck or not self.deck.active or foreground!=self.hwnd:return 0
  left,top,right,bottom=self.bounds
  if not(left<=x<=right and top<=y<=bottom):return 0
  return (1 if delta>0 else-1)if message==0x20E else(-1 if delta>0 else 1)
 def change(self,delta):
  if not self.deck or not self.deck.active:return
  self.studio.run(lambda:self.deck.step(delta),lambda result:(self.caption.setText(result),self.studio.status.setText(result)),quiet=True)
 def set_bar_visible(self,visible):
  self.preferences.show(visible)
  if not visible:self.hide()
  if self.deck:self.sync()
 def set_position(self,x,y):
  self.preferences.move(x,y)
  if self.deck:self.sync()
 def begin_drag(self,point):self.drag_anchor=(point,self.preferences.position)
 def drag_to(self,point):
  if not self.drag_anchor:return
  anchor,(x,y)=self.drag_anchor;delta=point-anchor;scale=max(.01,self.logical_scale)
  self.preferences.move(x+delta.x()/scale,y+delta.y()/scale);self.sync()
 def end_drag(self):
  self.drag_anchor=None;self.preferences.settings.sync();self.positionChanged.emit(*self.preferences.position)
 def sync(self):
  if not self.deck or not self.deck.active or not self.studio.owner.engine.is_connected:self.stop();return
  if getattr(self.studio.owner,'busy',False):self.hide();self.bounds=None;return
  if not self.deck.poll():
   self.studio.seed_pages.label.setText('Deck stopped at a lawn/round change. Start it again after choosing seeds.');self.stop();return
  if self.user.IsIconic(self.hwnd):self.hide();self.bounds=None;return
  rect=w.RECT();origin=w.POINT()
  if not self.user.GetClientRect(self.hwnd,ctypes.byref(rect))or not self.user.ClientToScreen(self.hwnd,ctypes.byref(origin)):self.stop();return
  pid=w.DWORD();foreground=self.user.GetForegroundWindow();self.user.GetWindowThreadProcessId(foreground,ctypes.byref(pid))
  if foreground!=self.hwnd and pid.value!=__import__('os').getpid():self.hide();self.bounds=None;return
  width=rect.right;height=rect.bottom;scale=min(width/800,height/600);left=origin.x+(width-800*scale)/2;top=origin.y+(height-600*scale)/2
  self.bounds=(left+80*scale,top,left+660*scale,top+88*scale)
  screen=QGuiApplication.screenAt(QPoint(origin.x,origin.y))or QGuiApplication.primaryScreen();ratio=screen.devicePixelRatio()
  x,y=self.preferences.position;self.logical_scale=scale/ratio
  self.setGeometry(int((left+x*scale)/ratio),int((top+y*scale)/ratio),int(510*scale/ratio),max(24,int(26*scale/ratio)))
  self.caption.setText(f'Seed page {self.deck.page+1}/{self.deck.pages} · drag to move')
  # Hiding the widget must not clear bounds or stop the native wheel hook.
  if self.preferences.visible:self.show()
  else:self.hide()
 def wheelEvent(self,event):
  delta=event.angleDelta().x()or-event.angleDelta().y()
  if delta:self.turn.emit(1 if delta>0 else-1);event.accept()
 def stop(self):
  self.timer.stop();self.hide();self.bounds=None
  if self.hook:self.user.UnhookWindowsHookEx(self.hook);self.hook=None
  self.deck=None;self.drag_anchor=None
