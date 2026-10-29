"""A local, editable lawn plan; drawing never reads or changes PVZ memory."""
from PySide6.QtCore import Qt,Signal,QRectF
from PySide6.QtGui import QPainter,QColor,QPen,QFont
from PySide6.QtWidgets import QWidget,QToolTip
from studio_labels import plant_name

class LawnPlanCanvas(QWidget):
    cellClicked=Signal(int,int,bool)
    def __init__(self,parent=None):
        super().__init__(parent);self.scene=0;self.plants=[];self.setMinimumSize(650,360);self.setMouseTracking(True)
        self.setAccessibleName('Editable lawn plan: click to paint a plant; right-click to erase a cell')
    def set_plan(self,scene,plants):self.scene=scene;self.plants=list(plants);self.update()
    def grid(self):return QRectF(35,28,self.width()-45,self.height()-40)
    def cell_at(self,pos):
        rect=self.grid();rows=6 if self.scene in (2,3)else 5
        if not rect.contains(pos):return None
        return min(rows,int((pos.y()-rect.top())/(rect.height()/rows))+1),min(9,int((pos.x()-rect.left())/(rect.width()/9))+1)
    def mousePressEvent(self,event):
        cell=self.cell_at(event.position())
        if cell:self.cellClicked.emit(*cell,event.button()==Qt.MouseButton.RightButton)
    def mouseMoveEvent(self,event):
        cell=self.cell_at(event.position())
        if cell:
            names=[plant_name(p['type'])for p in self.plants if(p['row'],p['col'])==cell or(p['type']==47 and p['row']==cell[0]and p['col']+1==cell[1])]
            self.setToolTip(f'Row {cell[0]}, column {cell[1]}\n'+('\n'.join(names)or'Empty — click to add the selected plant'))
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.fillRect(self.rect(),QColor('#101c14'))
        rect=self.grid();rows=6 if self.scene in (2,3)else 5;cw,ch=rect.width()/9,rect.height()/rows
        p.setPen(QColor('#d8e7ca'))
        for c in range(9):p.drawText(QRectF(rect.left()+c*cw,0,cw,24),Qt.AlignmentFlag.AlignCenter,str(c+1))
        for r in range(rows):
            p.drawText(QRectF(0,rect.top()+r*ch,30,ch),Qt.AlignmentFlag.AlignCenter,str(r+1))
            for c in range(9):
                color=('#28748a'if r in (2,3)and self.scene in (2,3)else '#824f39'if self.scene in (4,5)else '#34572f'if self.scene in (1,3)else '#427936')
                cell=QRectF(rect.left()+c*cw,rect.top()+r*ch,cw,ch);p.fillRect(cell,QColor(color).lighter(110 if(c+r)%2 else 100));p.setPen(QPen(QColor('#a8cc8a'),1));p.drawRect(cell)
        for r in range(1,rows+1):
            for c in range(1,10):
                items=[v for v in self.plants if(v['row'],v['col'])==(r,c)]
                if not items:continue
                main=next((v for v in reversed(items)if v['type']not in (16,33,30)),items[-1]);kind=main['type']
                cx=rect.left()+(c-.5)*cw;cy=rect.top()+(r-.5)*ch
                p.setPen(QPen(QColor('#183921'),3));p.drawLine(int(cx),int(cy),int(cx),int(cy+ch*.2))
                if kind in (1,41):
                    import math
                    p.setBrush(QColor('#f3c653'))
                    for angle in range(0,360,45):
                        dx,dy=math.cos(math.radians(angle))*15,math.sin(math.radians(angle))*15
                        p.drawEllipse(QRectF(cx+dx-7,cy+dy-12,14,14))
                    p.setBrush(QColor('#644731'));p.drawEllipse(QRectF(cx-12,cy-17,24,24));p.setPen(QColor('#fff1b6'))
                    p.drawText(QRectF(cx-12,cy-18,24,24),Qt.AlignmentFlag.AlignCenter,'☺')
                elif kind in (0,5,7,18,28,40):
                    p.setBrush(QColor('#91d3eb'if kind==5 else'#a4cd57'));p.drawEllipse(QRectF(cx-17,cy-19,29,27))
                    p.drawRect(QRectF(cx+2,cy-14,20,15));p.setBrush(QColor('#294b2e'));p.drawEllipse(QRectF(cx+17,cy-14,7,15));p.drawEllipse(QRectF(cx-7,cy-13,3,4))
                else:
                    p.setBrush(QColor('#bd8d50'if kind in (3,23)else'#bed55f'));p.drawEllipse(QRectF(cx-16,cy-17,32,29));p.setPen(QColor('#182418'))
                    p.setFont(QFont('Segoe UI',9,QFont.Weight.Bold));p.drawText(QRectF(cx-18,cy-16,36,26),Qt.AlignmentFlag.AlignCenter,str(kind))
                name=plant_name(kind).split(' (ID')[0];p.setPen(QColor('#ffffff'));p.setFont(QFont('Segoe UI',8))
                p.drawText(QRectF(cx-cw/2+2,cy+13,cw-4,ch/2-10),Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,name)
                if len(items)>1:p.drawText(QRectF(cx+12,cy-26,30,18),Qt.AlignmentFlag.AlignCenter,f'×{len(items)}')
        p.end()
