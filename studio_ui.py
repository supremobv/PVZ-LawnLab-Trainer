"""Lawn Studio: editors, scenarios, storage and game-focused hotkeys."""
import ctypes,json,time,sys
from pathlib import Path
from ctypes import wintypes
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QKeySequence,QIcon
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTabWidget,
    QComboBox,QSpinBox,QDoubleSpinBox,QCheckBox,QLineEdit,QTableWidget,QTableWidgetItem,
    QScrollArea,QFormLayout,QGroupBox,QMessageBox,QFileDialog,QKeySequenceEdit,QAbstractItemView)
from trainer_engine import PLANT_NAMES
from studio_engine import StudioGame,PLANT_FIELDS,ZOMBIE_FIELDS
from studio_models import ZOMBIES,EFFECTS,SCENES,formation,wave_plan,integer
from studio_storage import Documents,SaveBackups
from lawn_canvas import LawnPlanCanvas
from studio_labels import plant_name,zombie_name,equipment,named,HELMETS,SHIELDS,GARDENS,GROWTH,NEEDS,FIELD_LABELS,FIELD_HELP,GUIDES,EFFECT_HELP,PRODUCERS,SHOOTERS

def spin(low,high,value):
    w=QSpinBox();w.setRange(low,high);w.setValue(value);return w
def combo(items):
    w=QComboBox();w.addItems(items);return w
def row(*widgets):
    w=QWidget();layout=QHBoxLayout(w);layout.setContentsMargins(0,0,0,0)
    for item in widgets:layout.addWidget(QLabel(item)if isinstance(item,str)else item)
    return w
def table(headers):
    w=QTableWidget(0,len(headers));w.setHorizontalHeaderLabels(headers);w.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    w.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);w.horizontalHeader().setStretchLastSection(True);w.setMinimumHeight(145);w.resizeColumnsToContents();return w
def fill(widget,records,keys):
    widget.setRowCount(len(records))
    for i,record in enumerate(records):
        for j,key in enumerate(keys):widget.setItem(i,j,QTableWidgetItem(str(record.get(key,''))))
    widget.resizeColumnsToContents()

HOTKEY_ACTIONS={'Sun lock':'toggle_infinite_sun','Instant recharge':'toggle_no_cooldown','Pause spawning':'toggle_stop_spawning','Freeze zombies':'toggle_stop_zombies','Cancel spawn queue':None}
DEFAULT_KEYS={'Sun lock':'F6','Instant recharge':'F7','Pause spawning':'F8','Freeze zombies':'F9','Cancel spawn queue':'F10'}
def parse_hotkey(text):
    if not isinstance(text,str):raise ValueError('Invalid hotkey.')
    if not text:return None
    pieces=text.split('+');last=pieces[-1];mods=pieces[:-1]
    if any(m not in ('Ctrl','Alt','Shift')for m in mods)or len(set(mods))!=len(mods):raise ValueError('Use Ctrl, Alt or Shift with F1–F12.')
    if not last.startswith('F')or not last[1:].isdigit()or not 1<=int(last[1:])<=12:raise ValueError('Hotkeys must use F1–F12, optionally Ctrl/Alt/Shift.')
    if last=='F4'and set(mods)=={'Alt'}:raise ValueError('Alt+F4 is reserved for closing the game.')
    return 0x70+int(last[1:])-1,set(mods)

class GameHotkeys:
    def __init__(self,studio):
        self.studio=studio;self.down=set();self.user=ctypes.WinDLL('user32')
        self.user.GetForegroundWindow.restype=wintypes.HWND
        self.user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
        self.user.GetAsyncKeyState.argtypes=[ctypes.c_int];self.user.GetAsyncKeyState.restype=ctypes.c_short
    def poll(self):
        owner=self.studio.owner
        if not self.studio.hotkeys_enabled.isChecked()or not owner.engine.is_connected:self.down.clear();return
        try:pid=owner.engine.pm.process_id
        except Exception:return
        fg=wintypes.DWORD();self.user.GetWindowThreadProcessId(self.user.GetForegroundWindow(),ctypes.byref(fg))
        if fg.value!=pid:self.down.clear();return
        actual={name for name,key in [('Ctrl',0x11),('Alt',0x12),('Shift',0x10)]if self.user.GetAsyncKeyState(key)&0x8000}
        now=set()
        for name,editor in self.studio.key_editors.items():
            try:binding=parse_hotkey(editor.keySequence().toString(QKeySequence.SequenceFormat.PortableText))
            except ValueError:continue
            if binding and binding[1]==actual and self.user.GetAsyncKeyState(binding[0])&0x8000:now.add(name)
        for name in now-self.down:
            if not owner.busy:self.studio.hotkey_action(name)
        self.down=now

class LawnStudio(QWidget):
    def __init__(self,owner,documents=None,backups=None):
        super().__init__(owner,Qt.WindowType.Window);self.owner=owner;self.session=None;self.buttons=[]
        self.documents=documents or Documents();self.backups=backups or SaveBackups(running=lambda:self.owner.engine.check_game_running())
        source=getattr(owner.engine,'save_source',None)
        if backups is None and isinstance(source,(str,Path)):self.backups.source=Path(source)
        self.setWindowTitle('LawnLab — Lawn Studio');self.resize(1240,860)
        self.setWindowIcon(owner.windowIcon())
        self.setStyleSheet('QTabBar::tab {background:#1b271f;color:#bacbb5;padding:10px 12px;border:1px solid #324133;border-radius:5px;} QTabBar::tab:selected {background:#badc8d;color:#172414;} QGroupBox {border:1px solid #324133;border-radius:10px;margin-top:13px;padding:15px 9px 9px;} QGroupBox::title {subcontrol-origin:margin;left:14px;color:#d8e7ca;font-weight:600;} QHeaderView::section {background:#253528;color:#d8e7ca;padding:6px;border:1px solid #324133;} QCheckBox::indicator {width:16px;height:16px;border:1px solid #718467;border-radius:3px;background:#111c15;} QCheckBox::indicator:checked {background:#badc8d;border-color:#badc8d;}')
        layout=QVBoxLayout(self);title=QLabel('Lawn Studio');title.setObjectName('pageTitle');layout.addWidget(title)
        note=QLabel('Exact-build GOTY / Classic support · One-time edits affect the current lawn. Persistent actions create save backups first. Closing this window hides it; active tools and seed scrolling continue while the main LawnLab controller is connected. Use Stop / restore or Reset all to stop them.');note.setWordWrap(True);layout.addWidget(note)
        self.dashboard=QLabel('Connect to PVZ for live telemetry.');self.dashboard.setObjectName('muted');layout.addWidget(self.dashboard)
        self.tabs=QTabWidget();layout.addWidget(self.tabs,1)
        self.status=QLabel('Choose a tool. Queues stop on lawn changes, Reset all or disconnect.');self.status.setWordWrap(True);layout.addWidget(self.status)
        for name,key,build in [('Lawn builder','lawn',self.build_lawn),('Inspect & edit','entities',self.build_entities),('Zombie waves','waves',self.build_waves),('Seeds & shots','seeds',self.build_seeds),('Stages & Zen Garden','garden',self.build_garden),('Save backups','backups',self.build_backups),('Settings','profiles',self.build_profiles),('Player data','player',self.build_player)]:
            body=QWidget();box=QVBoxLayout(body);guide=self.group(box,GUIDES[key][0]);text=QLabel(GUIDES[key][1]);text.setWordWrap(True);text.setTextFormat(Qt.TextFormat.RichText);guide.addRow(text)
            build(box);box.addStretch();scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(body)
            icon=QIcon(str(Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'assets'/('studio-'+key+'.svg')))
            self.tabs.addTab(scroll,icon,name.replace('&','&&'))
        from extension_ui import ExtensionsPanel
        self.extensions=ExtensionsPanel(self);scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(self.extensions);self.tabs.addTab(scroll,'Mods, notes && launch');self.tabs.setUsesScrollButtons(True)
        self.timer=QTimer(self);self.timer.setInterval(120);self.timer.timeout.connect(self.heartbeat)
        self.last_snapshot=0;self.hotkeys=None
        self.hotkey_timer=QTimer(self);self.hotkey_timer.setInterval(40);self.hotkey_timer.timeout.connect(self.poll_hotkeys)
    def showEvent(self,event):super().showEvent(event);self.timer.start();self.hotkey_timer.start()
    def game(self):
        engine=self.owner.engine
        if not engine.is_connected:raise RuntimeError('Connect LawnLab to PVZ first.')
        if self.session is None or self.session.engine is not engine or self.session._checked is not engine.pm:
            if self.session is not None:self.session.schedule.cancel()
            self.session=getattr(engine,'studio_game_class',StudioGame)(engine)
            source=getattr(engine,'save_source',None)
            if isinstance(source,(str,Path)):
                self.save_folder.setText(str(source));self.backups.source=Path(source)
        self.session.guard();return self.session
    def group(self,box,title):
        w=QGroupBox(title);form=QFormLayout(w);box.addWidget(w);return form
    def button(self,text,fn):
        w=QPushButton(text);w.clicked.connect(lambda checked=False:fn());self.buttons.append(w);return w
    def run(self,fn,callback=None,quiet=False):
        if self.owner.busy:return
        if not quiet:self.status.setText('Working…')
        for b in self.buttons:b.setEnabled(False)
        def done(result,error):
            for b in self.buttons:b.setEnabled(True)
            try:
                if error:
                    self.status.setText(error.strip().splitlines()[-1])
                else:
                    if not quiet:self.status.setText(str(result)[:350]if isinstance(result,(str,Path))else'Done.')
                    if callback:callback(result)
                for card in self.owner.cards:
                    if card.feature.state:card.set_checked(bool(getattr(self.owner.engine,card.feature.state,False)))
                self.update_garden_buttons()
            except Exception as failure:self.status.setText('Could not display the completed result: '+str(failure))
        self.owner.run(fn,done)
    def confirm(self,title,text):return QMessageBox.question(self,title,text)==QMessageBox.StandardButton.Yes
    def persistent(self,label,fn,callback=None):
        if not self.confirm(label,'This changes saved progress or garden data. A backup of on-disk saves will be created first. Continue?'):return
        self.sync_save_folder()
        def operation():
            backup=self.backups.create('before-'+label);result=fn();return f'{label}: done. Backup: {backup}'+(' · '+str(result)if result is not None else'')
        self.run(operation,callback)
    def build_lawn(self,box):
        f=self.group(box,'Place one plant, fill a rectangle, or stack copies');self.plant=combo([plant_name(i)for i in range(48)]);self.plant_row=spin(1,6,1);self.plant_col=spin(1,9,1)
        self.plant_row_end=spin(1,6,1);self.plant_col_end=spin(1,9,1);self.plant_copies=spin(1,8,1)
        self.plant_row.valueChanged.connect(lambda n:self.plant_row_end.setValue(max(n,self.plant_row_end.value())))
        self.plant_col.valueChanged.connect(lambda n:self.plant_col_end.setValue(max(n,self.plant_col_end.value())))
        self.stack_plants=QCheckBox('Allow ordinary plants to share a cell (up to 8)');self.skip_occupied=QCheckBox('Skip occupied cells');self.skip_occupied.setChecked(True)
        self.stack_plants.toggled.connect(lambda checked:self.skip_occupied.setEnabled(not checked))
        self.auto_bases=QCheckBox('Add needed lily pads / flower pots automatically');self.auto_bases.setChecked(True)
        self.plant.currentIndexChanged.connect(lambda i:(self.plant_col.setMaximum(8 if i==47 else 9),self.plant_col_end.setMaximum(8 if i==47 else 9)))
        self.placement_mode=combo(['Selected rectangle','Fill all available lawn cells','Place a total quantity across the lawn']);self.total_plants=spin(1,250,10)
        f.addRow(self.button('Open the visual lawn planner below',self.show_visual_planner))
        f.addRow('Placement area',self.placement_mode);f.addRow('Total quantity (third mode only)',self.total_plants)
        self.placement_mode.currentIndexChanged.connect(self.update_placement_mode)
        f.addRow('Named plant',self.plant);f.addRow('Rows, top → bottom',row('From',self.plant_row,'to',self.plant_row_end));f.addRow('Columns, left → right',row('From',self.plant_col,'to',self.plant_col_end))
        f.addRow('Copies in each cell',self.plant_copies);f.addRow(self.stack_plants);f.addRow(row(self.skip_occupied,self.auto_bases))
        f.addRow(row(self.button('Place plants using selected area / quantity',self.place_batch),self.button('Add rectangle to saved plan',self.add_plant_plan)))
        note=QLabel('Use matching From/To values for one cell. Stacking does not support lily pads, pots, pumpkins, coffee beans or cob cannons. Studio limits a lawn to 250 plants.');note.setWordWrap(True);f.addRow(note)
        self.update_placement_mode()
        f=self.group(box,'Spawn zombies now');self.zombie=combo([zombie_name(i)for i in range(len(ZOMBIES))]);self.zombie.model().item(25).setEnabled(False)
        self.zombie_row=spin(1,6,1);self.zombie_count=spin(1,100,1);self.zombie_interval=spin(50,60000,1000);self.zombie_interval.setSuffix(' ms')
        f.addRow('Zombie',self.zombie);f.addRow('Settings',row('Row',self.zombie_row,'Quantity',self.zombie_count,'Interval ms',self.zombie_interval))
        f.addRow(row(self.button('Start spawning',self.spawn),self.button('Cancel queue',self.cancel_queue)))
        self.zombie_setup_name=QLineEdit('My zombie setup');self.zombie_setups=combo(self.documents.names('waves'))
        f.addRow('Setup name',self.zombie_setup_name);f.addRow('Saved zombie setups',self.zombie_setups)
        f.addRow(row(self.button('Save this zombie group',self.save_zombie_setup),self.button('Spawn saved setup',self.spawn_zombie_setup),self.button('Mix several zombie types',lambda:self.tabs.setCurrentIndex(2))))
        f=self.group(box,'Plan a lawn and save it for later');self.formation_name=QLineEdit('My lawn');self.formations=combo(self.documents.names('formations'));self.plan_scene=combo(SCENES)
        self.plan_brush=combo([plant_name(i)for i in range(48)]);self.plan_erase=QCheckBox('Eraser: click a cell to remove its planned plants')
        f.addRow('Paint with this plant',self.plan_brush);f.addRow(self.plan_erase)
        self.plan_canvas=LawnPlanCanvas();self.plan_canvas.cellClicked.connect(self.paint_plan_cell);f.addRow(self.plan_canvas)
        help=QLabel('Click a square to plan a plant; right-click or enable Eraser to clear it. These are draft changes only. Save stores the plan; Build places it in PVZ. Hover a cell for full names and IDs.');help.setWordWrap(True);f.addRow(help)
        self.plan_table=QTableWidget(0,4);self.plan_table.setHorizontalHeaderLabels(['Named plant','Row','Column','Copies']);self.plan_table.setMinimumHeight(170);f.addRow(self.plan_table)
        f.addRow(row(self.button('Add plan row',self.add_plan_row),self.button('Remove selected plan row',self.remove_plan_row)))
        self.plan_stack=QCheckBox('Allow ordinary-plant stacks in this plan');self.plan_merge=QCheckBox('Add to current lawn; preserve existing plants');self.plan_merge.setChecked(True)
        self.plan_scene.currentIndexChanged.connect(self.refresh_plan_canvas)
        f.addRow('Plan terrain (does not change PVZ)',row(self.plan_scene,self.button('Use current scene',lambda:self.run(lambda:self.game().scene(),lambda n:self.plan_scene.setCurrentIndex(n)))));f.addRow(row(self.plan_stack,self.plan_merge));f.addRow('Name',self.formation_name);f.addRow('Saved plant plans',self.formations)
        f.addRow(row(self.button('Save plan',self.save_plant_plan),self.button('Load plan for editing',self.load_plant_plan),self.button('Build displayed plan',self.build_plant_plan)))
        f.addRow(row(self.button('Capture current lawn to file',self.capture_formation),self.button('Build selected saved file',self.apply_formation)))
        note=QLabel('Plans must match the current scene. Add mode skips identical existing plants; it never removes a different plant. Add lily pads/pots to saved plans before water/roof plants.');note.setWordWrap(True);f.addRow(note)
    def show_visual_planner(self):self.scroll_to(self.plan_canvas)
    def scroll_to(self,widget):
        parent=widget.parentWidget()
        while parent and not isinstance(parent,QScrollArea):parent=parent.parentWidget()
        if parent:parent.ensureWidgetVisible(widget,0,50)
    def update_placement_mode(self,*args):
        mode=self.placement_mode.currentIndex();self.total_plants.setEnabled(mode==2)
        for widget in (self.plant_row,self.plant_row_end,self.plant_col,self.plant_col_end):widget.setEnabled(mode==0)
    def remove_plan_row(self):
        self.plan_table.removeRow(self.plan_table.currentRow());self.refresh_plan_canvas()
    def raw_plan_entries(self):
        entries=[]
        for r in range(self.plan_table.rowCount()):
            widgets=[self.plan_table.cellWidget(r,c)for c in range(4)]
            if any(w is None for w in widgets):continue
            entries.extend(dict(type=widgets[0].currentIndex(),row=widgets[1].value(),col=widgets[2].value(),imitater=False)for _ in range(widgets[3].value()))
        return entries
    def refresh_plan_canvas(self,*args):
        if hasattr(self,'plan_table'):self.plan_canvas.set_plan(self.plan_scene.currentIndex(),self.raw_plan_entries())
    def paint_plan_cell(self,lane,column,erase=False):
        erase=erase or self.plan_erase.isChecked();kind=self.plan_brush.currentIndex();scene=self.plan_scene.currentIndex()
        if not erase and kind==47 and column==9:self.status.setText('Cob Cannon occupies two cells; choose columns 1–8.');return
        if not erase and kind in (16,19,24)and not(scene in (2,3)and lane in (3,4)):
            self.status.setText('This aquatic plant needs a blue pool row.');return
        from studio_models import plant_layer
        for r in range(self.plan_table.rowCount()-1,-1,-1):
            t=self.plan_table.cellWidget(r,0).currentIndex();row=self.plan_table.cellWidget(r,1).value();col=self.plan_table.cellWidget(r,2).value()
            overlaps=row==lane and bool(({col,col+1}if t==47 else{col})&({column,column+1}if kind==47 and not erase else{column}))
            if overlaps and(erase or((not self.plan_stack.isChecked()or kind in (16,30,33,35,47))and plant_layer(t)==plant_layer(kind))):self.plan_table.removeRow(r)
        if not erase:
            base=16 if scene in (2,3)and lane in (3,4)and kind not in (16,19,24)else 33 if scene in (4,5)and kind!=33 else None
            if base is not None:
                for c in (column,column+1)if kind==47 else(column,):
                    if not any(p['type']==base and p['row']==lane and p['col']==c for p in self.raw_plan_entries()):self.add_plan_row(base,lane,c)
            self.add_plan_row(kind,lane,column)
        self.refresh_plan_canvas();self.status.setText('Draft updated. Save plan stores it; Build displayed plan creates it in PVZ.')
    def place_batch(self):
        args=(self.plant.currentIndex(),self.plant_row.value(),self.plant_row_end.value(),self.plant_col.value(),self.plant_col_end.value(),self.plant_copies.value(),self.stack_plants.isChecked(),self.skip_occupied.isChecked(),self.auto_bases.isChecked())
        mode=self.placement_mode.currentIndex();limit=self.total_plants.value()if mode==2 else None
        def operation():
            g=self.game();values=list(args)
            if mode:
                values[1:5]=[1,g.rows(),1,8 if values[0]==47 else 9]
            return g.place_many(*values,limit=limit,available_only=bool(mode))
        self.run(operation,lambda n:self.status.setText(f'Placed {n} plants including foundations.'if n else'No plants placed: all selected cells already contain plants. Disable Skip occupied cells and enable stacking, or choose empty cells.'))
    def add_plan_row(self,kind=0,lane=1,column=1,copies=1):
        r=self.plan_table.rowCount();self.plan_table.insertRow(r);w=combo([plant_name(i)for i in range(48)]);w.setCurrentIndex(kind)
        widgets=(w,spin(1,6,lane),spin(1,8 if kind==47 else 9,column),spin(1,8,copies))
        for c,widget in enumerate(widgets):self.plan_table.setCellWidget(r,c,widget)
        w.currentIndexChanged.connect(lambda i,target=widgets[2]:target.setMaximum(8 if i==47 else 9))
        w.currentIndexChanged.connect(self.refresh_plan_canvas)
        for widget in widgets[1:]:widget.valueChanged.connect(self.refresh_plan_canvas)
        self.refresh_plan_canvas()
    def add_plant_plan(self):
        if self.plant_row_end.value()<self.plant_row.value()or self.plant_col_end.value()<self.plant_col.value():self.status.setText('From must be no greater than To.');return
        for lane in range(self.plant_row.value(),self.plant_row_end.value()+1):
            for column in range(self.plant_col.value(),self.plant_col_end.value()+1,2 if self.plant.currentIndex()==47 else 1):self.add_plan_row(self.plant.currentIndex(),lane,column,self.plant_copies.value())
        if self.stack_plants.isChecked():self.plan_stack.setChecked(True)
        self.status.setText('Added to the displayed plan. Save plan stores it; Build displayed plan places it.')
    def plant_plan_value(self):
        if not self.plan_table.rowCount():raise ValueError('Add at least one named plant to the plan first.')
        entries=[]
        for r in range(self.plan_table.rowCount()):
            kind=self.plan_table.cellWidget(r,0).currentIndex();lane=self.plan_table.cellWidget(r,1).value();column=self.plan_table.cellWidget(r,2).value();copies=self.plan_table.cellWidget(r,3).value()
            entries.extend(dict(type=kind,row=lane,col=column,imitater=False)for _ in range(copies))
        return formation(dict(version=2,scene=self.plan_scene.currentIndex(),stack=self.plan_stack.isChecked(),plants=entries))
    def save_plant_plan(self):
        try:
            value=self.plant_plan_value();self.documents.save('formations',self.formation_name.text(),value);self.reload_names(self.formations,'formations');self.status.setText('Plant plan saved. Nothing was placed.')
        except Exception as error:self.status.setText(str(error))
    def load_plant_plan(self):
        try:
            value=formation(self.documents.load('formations',self.formations.currentText()));self.plan_table.setRowCount(0);self.plan_scene.setCurrentIndex(value['scene']);self.plan_stack.setChecked(value.get('stack',False));self.formation_name.setText(self.formations.currentText())
            from collections import Counter
            counts=Counter((p['type'],p['row'],p['col'])for p in value['plants'])
            for (kind,lane,column),copies in counts.items():self.add_plan_row(kind,lane,column,copies)
            self.refresh_plan_canvas();self.status.setText('Plan loaded for editing. Nothing was placed.')
        except Exception as error:self.status.setText(str(error))
    def build_plant_plan(self):
        try:value=self.plant_plan_value();merge=self.plan_merge.isChecked()
        except Exception as error:self.status.setText(str(error));return
        self.run(lambda:self.game().apply_formation(value,merge=merge),lambda n:self.status.setText(f'Created {n} plants from the plan.'))
    def save_zombie_setup(self):
        try:
            value=wave_plan({'version':1,'entries':[dict(type=self.zombie.currentIndex(),row=self.zombie_row.value(),quantity=self.zombie_count.value(),interval_ms=self.zombie_interval.value(),delay_ms=0)]})
            self.documents.save('waves',self.zombie_setup_name.text(),value);self.reload_names(self.zombie_setups,'waves');self.reload_names(self.wave_saved,'waves');self.status.setText('Zombie setup saved. Nothing spawned.')
        except Exception as error:self.status.setText(str(error))
    def spawn_zombie_setup(self):
        try:self.start_plan(wave_plan(self.documents.load('waves',self.zombie_setups.currentText())))
        except Exception as error:self.status.setText(str(error))
    def spawn(self):
        value={'version':1,'entries':[{'type':self.zombie.currentIndex(),'row':self.zombie_row.value(),'quantity':self.zombie_count.value(),'interval_ms':self.zombie_interval.value(),'delay_ms':0}]}
        self.start_plan(value)
    def start_plan(self,value):
        try:
            g=self.game();count=g.start_practice(value);self.status.setText(f'Queued {count} spawns. Leave Studio open; intervals use real time, and all groups share one start clock.')
        except Exception as error:self.status.setText(str(error))
    def cancel_queue(self):
        if self.session:self.session.schedule.cancel()
        self.status.setText('Spawn queue cancelled.')
    def capture_formation(self):
        name=self.formation_name.text()
        def op():return self.documents.save('formations',name,self.game().capture_formation())
        self.run(op,lambda _:self.reload_names(self.formations,'formations'))
    def apply_formation(self):
        name=self.formations.currentText()
        merge=self.plan_merge.isChecked()
        self.run(lambda:self.game().apply_formation(formation(self.documents.load('formations',name)),merge=merge),lambda n:self.status.setText(f'Created {n} plants from the saved plan.'))
    def build_entities(self,box):
        self.entity_kind=combo(['Plants','Zombies']);box.addWidget(row(self.entity_kind,self.button('Refresh live objects',self.refresh_entities)))
        self.entity_table=table(['Instance','Name + type ID','Row','Column / X','Body HP','Head / held protection']);box.addWidget(self.entity_table)
        for column,width in enumerate((90,230,60,110,120,320)):self.entity_table.setColumnWidth(column,width)
        self.entity_records=[];self.entity_table.itemSelectionChanged.connect(self.select_entity)
        f=self.group(box,'Selected live object — inspect and edit');self.entity_form=f;self.entity_details=QLabel('Refresh, then select a plant or zombie. No fields are edited until you tick them and Apply.');self.entity_details.setWordWrap(True);f.addRow(self.entity_details)
        self.entity_editors={};self.entity_checks={}
        for name,lo,hi,value in [('health',1,1000000,300),('max_health',1,1000000,300),('attack_timer',0,60000,0),('attack_interval',1,60000,150),('armour',0,1000000,0),('max_armour',0,1000000,0),('shield',0,1000000,0),('max_shield',0,1000000,0),('speed',0,5,1),('chilled',0,60000,0),('buttered',0,60000,0),('frozen',0,60000,0)]:
            enabled=QCheckBox(FIELD_LABELS[name]);editor=QDoubleSpinBox()if name=='speed'else QSpinBox();editor.setRange(lo,hi);editor.setValue(value)
            if name=='speed':editor.setDecimals(3);editor.setSingleStep(.05)
            enabled.setToolTip(FIELD_HELP[name]);editor.setToolTip(FIELD_HELP[name]);enabled.setEnabled(False);editor.setEnabled(False)
            self.entity_checks[name]=enabled;self.entity_editors[name]=editor;f.addRow(enabled,editor)
            f.setRowVisible(enabled,False)
        for key in ('max_health','max_armour','max_shield'):
            self.entity_editors[key].valueChanged.connect(self.update_health_limits);self.entity_checks[key].toggled.connect(self.update_health_limits)
        f.addRow(self.button('Apply checked changes',self.edit_entity));f.addRow(self.button('Restore reversible Studio edits',lambda:self.run(lambda:self.game().reset())))
        self.move_selected_row=spin(1,6,1);f.addRow('Move selected zombie',row(self.move_selected_row,self.button('Move to this row now',self.move_selected_zombie)))
        note=QLabel('Changing a maximum does not automatically refill health. Equipment type is read-only: changing helmet HP does not turn a normal zombie into a Conehead. Refresh after edits to see current values.');note.setWordWrap(True);f.addRow(note)
        self.entity_kind.currentIndexChanged.connect(self.clear_entity_selection)
    def clear_entity_selection(self,*args):
        self.entity_records=[];self.entity_table.setRowCount(0);self.entity_details.setText('Refresh the list and select a live object.')
        for key in self.entity_checks:self.entity_checks[key].setChecked(False);self.entity_checks[key].setEnabled(False);self.entity_editors[key].setEnabled(False)
    def refresh_entities(self):
        kind='plant'if self.entity_kind.currentIndex()==0 else'zombie'
        def done(records):
            records=[p for p in records if p['health']>0 and(p['kind']=='plant'or p['state']not in (1,2,3))];self.entity_records=records
            display=[]
            for p in records:
                protection='—'if p['kind']=='plant'else equipment(HELMETS,p['helm_type'])+f": {p['armour']}/{p['max_armour']} HP; "+equipment(SHIELDS,p['shield_type'])+f": {p['shield']}/{p['max_shield']} HP"
                display.append(dict(instance=f"#{p['id']&65535}",type_name=plant_name(p['type'])if p['kind']=='plant'else zombie_name(p['type']),row=p['row'],position=p.get('col',round(p.get('x',0),1)),hp=f"{p['health']}/{p['max_health']}",protection=protection))
            fill(self.entity_table,display,['instance','type_name','row','position','hp','protection'])
        self.run(lambda:self.game().entities(kind),done,quiet=True)
    def selected_entity(self):
        i=self.entity_table.currentRow()
        if not 0<=i<len(self.entity_records):raise ValueError('Select a current entity.')
        return self.entity_records[i]
    def select_entity(self):
        try:p=self.selected_entity()
        except ValueError:return
        title=plant_name(p['type'])if p['kind']=='plant'else zombie_name(p['type'])
        text=f"{title} · live instance #{p['id']&65535}\nRow {p['row']} · "+(f"Column {p['col']}"if p['kind']=='plant'else f"X {p['x']:.1f}, Y {p['y']:.1f}")+f"\nBody health: {p['health']} / {p['max_health']} HP"
        if p['kind']=='zombie':text+='\nHead protection: '+equipment(HELMETS,p['helm_type'])+' · Held protection: '+equipment(SHIELDS,p['shield_type'])
        self.entity_details.setText(text)
        fields=set(PLANT_FIELDS if p['kind']=='plant'else ZOMBIE_FIELDS)
        if p['kind']=='plant'and p['type']not in SHOOTERS|PRODUCERS:fields-={'attack_timer','attack_interval'}
        if p['kind']=='zombie':
            if not p['helm_type']:fields-={'armour','max_armour'}
            if not p['shield_type']:fields-={'shield','max_shield'}
        for name,editor in self.entity_editors.items():
            self.entity_checks[name].setChecked(False);self.entity_checks[name].setEnabled(name in fields);editor.setEnabled(name in fields)
            self.entity_form.setRowVisible(self.entity_checks[name],name in fields)
            if name in ('health','armour','shield'):editor.setMaximum(1000000)
            if name in p:editor.setValue(p[name])
        self.entity_checks['attack_timer'].setText('Ticks until next sun / coin'if p['kind']=='plant'and p['type']in PRODUCERS else FIELD_LABELS['attack_timer'])
        self.entity_checks['attack_interval'].setText('Sun / coin interval (ticks)'if p['kind']=='plant'and p['type']in PRODUCERS else FIELD_LABELS['attack_interval'])
        self.update_health_limits()
    def update_health_limits(self,*args):
        try:p=self.selected_entity()
        except ValueError:return
        for field,maximum in [('health','max_health'),('armour','max_armour'),('shield','max_shield')]:
            if maximum in p:self.entity_editors[field].setMaximum(int(self.entity_editors[maximum].value())if self.entity_checks[maximum].isChecked()else p[maximum])
    def move_selected_zombie(self):
        try:
            p=self.selected_entity()
            if p['kind']!='zombie':raise ValueError('Select a zombie, not a plant.')
            lane=self.move_selected_row.value();ident=p['id'];owner=p['board']
            def op():
                g=self.game()
                if g.lawn_token()!=owner:raise RuntimeError('The lawn changed; refresh before moving this zombie.')
                result=g.move_zombies(lane,{ident});return f"Moved {result['moved']} zombie; skipped {result['skipped']} incompatible/special-state target."
            self.run(op)
        except Exception as error:self.status.setText(str(error))
    def edit_entity(self):
        try:
            p=self.selected_entity();values={k:self.entity_editors[k].value()for k,c in self.entity_checks.items()if c.isChecked()and c.isEnabled()}
            self.run(lambda:self.game().edit_entity(p['kind'],p['id'],values,p['board']))
        except Exception as error:self.status.setText(str(error))
    def build_waves(self,box):
        f=self.group(box,'Reusable zombie setup — one group per row');self.wave_name=QLineEdit('Practice wave');self.wave_saved=combo(self.documents.names('waves'))
        self.wave_table=QTableWidget(0,5);self.wave_table.setHorizontalHeaderLabels(['Zombie name + ID','Lane','How many','Gap (ms)','Start after (ms)']);self.wave_table.setMinimumHeight(200);self.wave_table.setColumnWidth(0,250);f.addRow(self.wave_table)
        f.addRow(row(self.button('Add entry',self.add_wave_entry),self.button('Remove entry',lambda:self.wave_table.removeRow(self.wave_table.currentRow()))))
        f.addRow('Name',self.wave_name);f.addRow('Saved',self.wave_saved)
        f.addRow(row(self.button('Save zombie setup',self.save_wave),self.button('Load setup (no spawn)',self.load_wave),self.button('Spawn this setup',self.run_wave),self.button('Cancel remaining spawns',self.cancel_queue)))
        self.add_wave_entry()
        f=self.group(box,'Replace an upcoming natural wave');self.natural_wave=spin(1,100,1);self.natural_types=QLineEdit('0, 0, 2, 4')
        self.natural_roster=[0,0,2,4];self.natural_types.setReadOnly(True);self.natural_zombie=combo([zombie_name(i)for i in range(len(ZOMBIES))]);self.natural_zombie.model().item(25).setEnabled(False);self.natural_quantity=spin(1,50,1)
        f.addRow('Future game-wave number',self.natural_wave);f.addRow('Add named zombies',row(self.natural_zombie,self.natural_quantity,self.button('Add to list',self.add_natural_group),self.button('Clear list',self.clear_natural_group)))
        f.addRow('This wave will contain',self.natural_types);self.show_natural_group()
        f.addRow(self.button('Apply upcoming wave list',self.edit_wave))
        f.addRow(QLabel('Only future waves within the current level are editable. Practice compositions are scheduled independently; pause normal spawning for an isolated test.'))
    def add_wave_entry(self,record=None):
        n=self.wave_table.rowCount();self.wave_table.insertRow(n)
        self.wave_table.setRowHeight(n,44)
        record=record or dict(type=0,row=1,quantity=5,interval_ms=1000,delay_ms=0)
        kind=combo([zombie_name(i)for i in range(len(ZOMBIES))]);kind.model().item(25).setEnabled(False);kind.setCurrentIndex(record['type'])
        for c,w in enumerate((kind,spin(1,6,record['row']),spin(1,100,record['quantity']),spin(50,60000,record['interval_ms']),spin(0,600000,record['delay_ms']))):self.wave_table.setCellWidget(n,c,w)
    def wave_value(self):
        records=[]
        for r in range(self.wave_table.rowCount()):records.append(dict(zip(('type','row','quantity','interval_ms','delay_ms'),[self.wave_table.cellWidget(r,0).currentIndex()]+[self.wave_table.cellWidget(r,c).value()for c in range(1,5)])))
        return wave_plan({'version':1,'entries':records})
    def save_wave(self):
        try:self.documents.save('waves',self.wave_name.text(),self.wave_value());self.reload_names(self.wave_saved,'waves');self.reload_names(self.zombie_setups,'waves');self.status.setText('Zombie setup saved. Nothing spawned.')
        except Exception as error:self.status.setText(str(error))
    def load_wave(self):
        try:
            value=wave_plan(self.documents.load('waves',self.wave_saved.currentText()));self.wave_table.setRowCount(0)
            for e in value['entries']:
                self.add_wave_entry(e)
            self.status.setText('Wave loaded; nothing spawned.')
        except Exception as error:self.status.setText(str(error))
    def run_wave(self):
        try:self.start_plan(self.wave_value())
        except Exception as error:self.status.setText(str(error))
    def edit_wave(self):
        try:
            wave=self.natural_wave.value();types=list(self.natural_roster)
            if self.confirm('Upcoming wave','Replace this upcoming wave for the current lawn? This is not undone by Reset all.'):self.run(lambda:self.game().set_wave(wave,types))
        except Exception as error:self.status.setText(str(error))
    def show_natural_group(self):
        from collections import Counter
        self.natural_types.setText('; '.join(f'{zombie_name(kind)} ×{count}'for kind,count in Counter(self.natural_roster).items())or'Empty — add a named zombie group first')
    def add_natural_group(self):
        if len(self.natural_roster)+self.natural_quantity.value()>50:self.status.setText('A natural wave list holds at most 50 zombies.');return
        self.natural_roster.extend([self.natural_zombie.currentIndex()]*self.natural_quantity.value());self.show_natural_group()
    def clear_natural_group(self):self.natural_roster=[];self.show_natural_group()
    def build_seeds(self,box):
        from seed_ui import SeedPagesPanel
        f=self.group(box,'Scrollable in-game seed bank');self.seed_pages=SeedPagesPanel(self);f.addRow(self.seed_pages)
        f=self.group(box,'Seed packets — the cards at the top of PVZ');self.seeds_table=table(['Slot (left → right)','Plant name + ID','Imitater copy','Recharge elapsed (ticks)','Recharge total (ticks)']);f.addRow(self.seeds_table)
        f.addRow(self.button('Read current seed cards',lambda:self.run(lambda:self.game().seed_bank(),self.show_seed_bank,quiet=True)))
        self.seed_slot=spin(1,10,1);self.seed_type=combo([plant_name(i)for i in range(48)]);self.seed_imitater=QCheckBox('Use an Imitater card copying this plant');self.seed_duplicates=QCheckBox('Allow the same plant in multiple cards')
        f.addRow('Slot / plant',row(self.seed_slot,self.seed_type));f.addRow(row(self.seed_imitater,self.seed_duplicates))
        f.addRow(self.button('Apply to selected seed slot',self.apply_seed_packet))
        f=self.group(box,'Projectile impact effects and shared damage');self.projectile_effect=combo(list(EFFECTS));self.damage_type=combo(['Pea','Snow pea','Cabbage','Melon','Puff','Winter melon','Fire pea','Star','Spike','Basketball','Kernel','Cob cannon','Butter']);self.damage=spin(0,100000,20)
        f.addRow('Impact behavior',self.projectile_effect)
        self.projectile_detail=QLabel();self.projectile_detail.setWordWrap(True);f.addRow(self.projectile_detail);self.projectile_effect.currentIndexChanged.connect(lambda _:self.projectile_detail.setText(EFFECT_HELP[EFFECTS[self.projectile_effect.currentText()]]));self.projectile_detail.setText(EFFECT_HELP[0])
        f.addRow(row(self.button('Use this effect for future shots',self.apply_projectile_effect),self.button('Restore previous effect',lambda:self.run(lambda:self.game().enable_effect(None)))))
        f.addRow('Shared projectile damage',row(self.damage_type,self.damage))
        f.addRow(self.button('Apply shared projectile damage',self.apply_projectile_damage))
        note=QLabel('Damage range: 0–100,000 HP per hit; 0 means no body damage. This is global for the projectile type, not one selected plant. Cold and butter use native hit effects. Reset restores the damage table, but cannot undo damage already dealt.');note.setWordWrap(True);f.addRow(note)
    def show_seed_bank(self,records):
        self.seed_slot.setMaximum(len(records));fill(self.seeds_table,[dict(p,plant_name='Empty page slot'if p['type']<0 else plant_name(p['type'])if p['type']!=48 else'Imitater (ID 48)',copy=plant_name(p['imitater'])if p['imitater']>=0 else'Not an Imitater')for p in records],['slot','plant_name','copy','elapsed','total'])
    def apply_seed_packet(self):
        args=(self.seed_slot.value(),self.seed_type.currentIndex(),self.seed_imitater.isChecked(),self.seed_duplicates.isChecked());self.run(lambda:self.game().set_seed(*args),lambda _:self.status.setText('Seed card changed. Resume the game for recharge/visual updates.'))
    def apply_projectile_effect(self):
        value=EFFECTS[self.projectile_effect.currentText()];self.run(lambda:self.game().enable_effect(value))
    def apply_projectile_damage(self):
        kind,damage=self.damage_type.currentIndex(),self.damage.value();self.run(lambda:self.game().set_projectile_damage(kind,damage))
    def build_garden(self,box):
        box.addWidget(row(self.button('Saved plant collection',lambda:self.scroll_to(self.garden_table)),self.button('Bulk garden care',lambda:self.scroll_to(self.bulk_scope)),self.button('Add / move plants',lambda:self.scroll_to(self.new_garden)),self.button('Shop restock',lambda:self.scroll_to(self.shop_stock_enable))))
        f=self.group(box,'Level selector');self.level=spin(1,50,1);self.level_modes=combo(['Adventure','Survival Day','Survival Night','Survival Pool','Survival Fog','Survival Roof','Survival Day hard','Survival Night hard','Survival Pool hard','Survival Fog hard','Survival Roof hard','Survival Day endless','Survival Night endless','Survival Pool endless','Survival Fog endless','Survival Roof endless','Zen Garden'])
        f.addRow('Adventure stage (1–50)',self.level);f.addRow('Mode',self.level_modes)
        self.stage_detail=QLabel();f.addRow(self.stage_detail)
        def stage_info(*args):
            n=self.level.value();self.level.setEnabled(self.level_modes.currentIndex()==0);self.stage_detail.setText(f'Adventure {((n-1)//10)+1}-{((n-1)%10)+1} (stage number {n})'if self.level_modes.currentIndex()==0 else'The selected Survival / Garden mode ignores the Adventure stage number. Launch from the main menu or a resumed lawn; close in-game dialogs first. Active trainer controls will reset.')
        self.level.valueChanged.connect(stage_info);self.level_modes.currentIndexChanged.connect(stage_info);stage_info()
        f.addRow(self.button('Launch selected stage',self.launch_level))
        f.addRow(QLabel('Replaces the current lawn and may replace the selected mode’s saved run. Creates an on-disk backup first. Adventure stage also changes profile progress.'))
        f=self.group(box,'Your saved Zen Garden collection — across all gardens');self.garden_table=table(['Saved slot','Plant name + ID','Garden','Place (col, row)','Growth','Water feeds / needed','Current need']);f.addRow(self.garden_table)
        for column,width in enumerate((100,230,145,130,110,170,230)):self.garden_table.setColumnWidth(column,width)
        f.addRow(self.button('Read saved garden collection',self.read_garden))
        self.garden_selection=QLabel('Read the collection, then click a named plant. Slot 0 means its first saved record; it is not a plant ID or a garden-screen square.');self.garden_selection.setWordWrap(True);f.addRow(self.garden_selection)
        self.garden_index=spin(0,199,0);self.garden_index.setReadOnly(True);self.garden_index.setEnabled(False);self.growth=combo(GROWTH);self.growth.setCurrentIndex(3);f.addRow('Selected saved plant slot (choose in table)',self.garden_index)
        self.garden_table.itemSelectionChanged.connect(lambda:self.garden_index.setValue(int(self.garden_table.item(self.garden_table.currentRow(),0).text()))if self.garden_table.currentRow()>=0 and self.garden_table.item(self.garden_table.currentRow(),0)else None)
        self.garden_records=[];self.water_button=self.button('Water now',lambda:self.garden_action('water'));self.fertilize_button=self.button('Fertilize now',lambda:self.garden_action('fertilize'));self.grow_button=self.button('Apply growth',lambda:self.garden_action('growth'))
        f.addRow(row(self.water_button,self.fertilize_button));f.addRow('Growth stage',row(self.growth,self.grow_button))
        self.garden_index.valueChanged.connect(self.update_garden_buttons);self.update_garden_buttons()
        self.supply=combo(['fertilizer','bug spray','chocolate','tree food']);self.supply_count=spin(0,999,20)
        f.addRow('Garden supplies',row(self.supply,self.supply_count,self.button('Apply supplies',self.apply_garden_supply)))
        note=QLabel('Supply count is the displayed count, 0–999. Water increments this plant’s feed count. Fertilizer advances growth only after enough water feeds. Growth applies the named stage directly. All these changes are saved; re-enter Zen Garden to refresh its display.');note.setWordWrap(True);f.addRow(note)
        self.build_garden_batch(box)
    def read_garden(self):self.run(lambda:self.game().garden(),self.show_garden,quiet=True)
    def build_garden_batch(self,box):
        from profile_tools import AQUATIC
        f=self.group(box,'Care for many plants in one action')
        self.bulk_scope=combo(['All saved plants']+GARDENS);self.bulk_action=combo(['Water all','Fertilize eligible young plants','Fulfill current needs','Set growth stage for all','Give chocolate to all']);self.bulk_growth=combo(GROWTH);self.bulk_growth.setCurrentIndex(3);self.bulk_growth.setEnabled(False)
        self.bulk_action.currentIndexChanged.connect(lambda i:self.bulk_growth.setEnabled(i==3))
        f.addRow('Which garden?',self.bulk_scope);f.addRow('Action',self.bulk_action);f.addRow('Growth (growth action only)',self.bulk_growth);f.addRow(self.button('Apply this action to the selected group',self.apply_garden_batch))
        note=QLabel('One backup and one save per batch. Fertilize skips mature or insufficiently watered plants. Fulfill needs clears need/timer requests without raising growth. These trainer actions do not charge supplies. Re-read the list; re-enter the garden for refreshed visuals.');note.setWordWrap(True);f.addRow(note)
        f=self.group(box,'Add plants to an empty garden, or move a selected saved plant')
        self.new_garden=combo(GARDENS);self.new_garden_plant=combo([plant_name(i)for i in range(48)]);self.new_garden_count=spin(1,32,1);self.new_garden_age=combo(GROWTH)
        def restrict(*args):
            n=self.new_garden.currentIndex();self.new_garden_count.setMaximum({0:32,1:8,2:1,3:8}[n])
            for i in range(48):self.new_garden_plant.model().item(i).setEnabled(n!=3 or i in AQUATIC)
            if n==3 and self.new_garden_plant.currentIndex()not in AQUATIC:self.new_garden_plant.setCurrentIndex(16)
        self.new_garden.currentIndexChanged.connect(restrict)
        f.addRow('Destination garden',self.new_garden);f.addRow('Named plant to add',self.new_garden_plant);f.addRow('Quantity',self.new_garden_count);f.addRow('Starting growth',self.new_garden_age)
        f.addRow(row(self.button('Add saved plants (Main Menu)',self.add_saved_plants),self.button('Move selected saved plant here (Main Menu)',self.move_saved_plant)))
        note=QLabel('Return to PVZ Main Menu before adding/moving, then re-enter the destination garden. Main garden: 32 places; Mushroom/Aquarium: 8 each; Wheelbarrow: one carried plant, not a separate garden screen. Buy it or enable Wheelbarrow owned in Player data. In PVZ use its toolbar icon to carry a plant, switch gardens, then place it. Aquarium accepts aquatic plants only. Existing plants are preserved. The garden must already be owned; ownership can also be edited in Player data.');note.setWordWrap(True);f.addRow(note)
        f=self.group(box,'Crazy Dave’s shop — sold-out purchases')
        self.shop_stock_enable=self.button('Enable shop restock',lambda:self.run(lambda:self.owner.engine.toggle_shop_stock(True)));f.addRow(row(self.shop_stock_enable,self.button('Disable shop restock',lambda:self.run(lambda:self.owner.engine.toggle_shop_stock(False)))))
        note=QLabel('Restocks sold-out items, including owned gardens, tools, Snail and Tree, at normal prices. Seed slots remain capped at ten and mower upgrades at two; rebuying the Tree preserves its height. A full garden still blocks another Marigold. Rebuying an already-owned unlock does not add another garden. Locked/coming-soon items still need their normal unlocks. Turn this off or Reset all to restore stock rules.');note.setWordWrap(True);f.addRow(note)
    def apply_garden_batch(self):
        from profile_tools import tools
        scope=self.bulk_scope.currentIndex()-1;action=['water','fertilize','needs','growth','chocolate'][self.bulk_action.currentIndex()];age=self.bulk_growth.currentIndex()
        self.persistent('Bulk garden care',lambda:tools(self.game()).bulk(action,None if scope<0 else scope,age),lambda _:self.read_garden())
    def add_saved_plants(self):
        from profile_tools import tools
        kind,garden,count,age=self.new_garden_plant.currentIndex(),self.new_garden.currentIndex(),self.new_garden_count.value(),self.new_garden_age.currentIndex()
        self.persistent('Add saved garden plants',lambda:tools(self.game()).add(kind,garden,count,age),lambda _:self.read_garden())
    def move_saved_plant(self):
        from profile_tools import tools
        index,garden=self.garden_index.value(),self.new_garden.currentIndex();selected=next((p for p in self.garden_records if p['index']==index),None)
        if selected is None:self.status.setText('Read the garden collection and click the saved plant to move.');return
        stamp=selected.get('stamp');self.persistent('Move saved garden plant',lambda:tools(self.game()).move(index,garden,stamp),lambda _:self.read_garden())
    def build_player(self,box):
        from profile_ui import PlayerDataPanel
        self.player_panel=PlayerDataPanel(self);box.addWidget(self.player_panel)

    def show_garden(self,records):
        self.garden_records=records
        self.garden_index.setMaximum(max(0,len(records)-1));self.garden_index.setEnabled(bool(records))
        fill(self.garden_table,[dict(p,name=plant_name(p['type']),garden_name=named(GARDENS,p['garden']),growth_name=named(GROWTH,p['age']),feeds=f"{p['fed']} / {p['feedings']}",need_name=named(NEEDS,p['need']),place=f"{p.get('x',0)+1}, {p.get('y',0)+1}")for p in records],['index','name','garden_name','place','growth_name','feeds','need_name'])
        if records:self.garden_table.selectRow(min(self.garden_index.value(),len(records)-1))
        self.update_garden_buttons()
    def update_garden_buttons(self,*args):
        if not hasattr(self,'garden_records'):return
        plant=None if self.owner.busy else next((p for p in self.garden_records if p['index']==self.garden_index.value()),None)
        if hasattr(self,'garden_selection'):
            self.garden_selection.setText(f"Selected: {plant_name(plant['type'])} · {named(GARDENS,plant['garden'])} · saved slot {plant['index']}"if plant else'Read the collection, then click a named plant. Slot numbers can change after selling plants.')
        self.water_button.setEnabled(plant is not None);self.grow_button.setEnabled(plant is not None)
        self.fertilize_button.setEnabled(bool(plant and plant['age']<3 and plant['fed']>=max(1,plant['feedings'])))
    def apply_garden_supply(self):
        kind,amount=self.supply.currentText(),self.supply_count.value();self.persistent('Garden supplies',lambda:self.game().garden_inventory(kind,amount))
    def launch_level(self):
        modes=list(range(16))+[43];mode=modes[self.level_modes.currentIndex()];level=self.level.value()
        self.persistent('Launch stage',lambda:self.game().launch_level(level,mode))
    def garden_action(self,action):
        index,growth=self.garden_index.value(),self.growth.currentIndex();self.persistent('Garden '+action,lambda:self.game().garden_edit(index,action,growth),lambda _:self.read_garden())
    def build_backups(self,box):
        f=self.group(box,'Save backup and restore');self.save_folder=QLineEdit(str(self.backups.source));f.addRow('PVZ userdata folder',row(self.save_folder,self.button('Browse',self.choose_saves)))
        self.backup_list=combo(self.backups.names());f.addRow('Snapshots',self.backup_list)
        f.addRow(row(self.button('Create backup',self.backup),self.button('Refresh snapshots',lambda:self.backup_list.clear()or self.backup_list.addItems(self.backups.names())),self.button('Restore selected backup',self.restore_backup)))
        info=QLabel('Backups include users.dat, user*.dat and game*_* saves with SHA-256 checksums. Close PVZ for a complete stable checkpoint; a backup made while playing contains on-disk saves, not unsaved memory. Restore requires PVZ closed and makes a recovery backup first. Files absent from the snapshot are removed from the save set.');info.setWordWrap(True);f.addRow(info)
        f.addRow('Backup storage',QLabel(str(self.backups.root)))
    def choose_saves(self):
        path=QFileDialog.getExistingDirectory(self,'PVZ userdata folder',str(self.backups.source))
        if path:self.save_folder.setText(path)
    def sync_save_folder(self):
        from pathlib import Path
        self.backups.source=Path(self.save_folder.text())
    def backup(self):
        self.sync_save_folder()
        self.run(lambda:self.backups.create(),lambda _:self.refresh_backups())
    def refresh_backups(self):self.backup_list.clear();self.backup_list.addItems(self.backups.names())
    def restore_backup(self):
        self.sync_save_folder();name=self.backup_list.currentText()
        if self.confirm('Restore saves','Close PVZ first. Restore these saved profiles and runs? Existing save files will be overwritten; extra save files will be removed. A recovery snapshot is created before changes.'):
            self.run(lambda:self.backups.restore(name),lambda _:self.refresh_backups())
    def build_profiles(self,box):
        f=self.group(box,'Trainer settings');self.profile_name=QLineEdit('My setup');self.profiles=combo(self.documents.names('profiles'));self.activate_profile=QCheckBox('Activate saved toggle controls after loading (requires connection)')
        f.addRow('Name',self.profile_name);f.addRow('Saved profiles',self.profiles);f.addRow(self.activate_profile)
        f.addRow(row(self.button('Save current settings',self.save_settings),self.button('Load settings',self.load_settings)))
        f=self.group(box,'Hotkeys — only while PVZ has focus');self.hotkeys_enabled=QCheckBox('Enable configured hotkeys');f.addRow(self.hotkeys_enabled);self.key_editors={}
        for name,key in DEFAULT_KEYS.items():
            w=QKeySequenceEdit(QKeySequence(key));w.setMaximumSequenceLength(1);self.key_editors[name]=w;f.addRow(name,w)
        note=QLabel('Use F1–F12 with optional Ctrl/Alt/Shift. No keyboard input is synthesized and keys are not intercepted. Hotkeys trigger once per press, require PVZ focus, and ignore presses while another trainer operation is running. Profiles save bindings; loading never auto-enables hotkeys.');note.setWordWrap(True);f.addRow(note)
    def settings(self):
        controls={}
        for card in self.owner.cards:
            editor=card.editor;value=editor.value()if isinstance(editor,QSpinBox)else editor.currentIndex()if editor is not None else None
            controls[card.feature.method]={'enabled':bool(getattr(self.owner.engine,card.feature.state,False))if card.feature.state else False,'value':value}
        return {'version':1,'controls':controls,'hotkeys':{n:w.keySequence().toString(QKeySequence.SequenceFormat.PortableText)for n,w in self.key_editors.items()}}
    def validate_settings(self,value):
        if not isinstance(value,dict)or set(value)!={'version','controls','hotkeys'}or value['version']!=1:raise ValueError('Invalid trainer profile.')
        known={c.feature.method:c for c in self.owner.cards}
        if not isinstance(value['controls'],dict)or set(value['controls'])-set(known):raise ValueError('Profile controls differ from this LawnLab version.')
        missing=set(known)-set(value['controls'])
        if missing-{'toggle_auto_coins','move_existing_zombies','toggle_sunflower_drop','toggle_shop_stock'}:raise ValueError('Profile controls differ from this LawnLab version.')
        for key in missing:value['controls'][key]={'enabled':False,'value':0 if known[key].editor is not None else None}
        for key,record in value['controls'].items():
            if not isinstance(record,dict)or set(record)!={'enabled','value'}or type(record['enabled'])is not bool:raise ValueError('Invalid profile control.')
            card=known[key];editor=card.editor
            if editor is None:
                if record['value']is not None:raise ValueError('Toggle has an unexpected value.')
            elif isinstance(editor,QSpinBox):integer(record['value'],editor.minimum(),editor.maximum())
            else:integer(record['value'],0,editor.count()-1)
            if not card.feature.state and record['enabled']:raise ValueError('One-time actions cannot be auto-run by a profile.')
        for group in [('toggle_infinite_sun','toggle_sun_lock'),('toggle_invincible_plants','toggle_instant_plant_death'),('toggle_unhittable_plants_zombotany','toggle_instant_plant_death'),('toggle_one_hit_kill','toggle_invincible_zombies'),('toggle_rapid_fire','toggle_fast_shoot')]:
            if sum(value['controls'][k]['enabled']for k in group)>1:raise ValueError('Conflicting controls in profile.')
        if not isinstance(value['hotkeys'],dict)or set(value['hotkeys'])!=set(HOTKEY_ACTIONS):raise ValueError('Invalid hotkey actions.')
        used=set()
        for text in value['hotkeys'].values():
            parse_hotkey(text)
            binding=parse_hotkey(text);canonical=(binding[0],tuple(sorted(binding[1])))if binding else None
            if canonical and canonical in used:raise ValueError('Duplicate hotkeys.')
            used.add(canonical)
        return value
    def save_settings(self):
        try:
            value=self.validate_settings(self.settings());path=self.documents.save('profiles',self.profile_name.text(),value);self.reload_names(self.profiles,'profiles');self.status.setText('Saved '+str(path))
        except Exception as error:self.status.setText(str(error))
    def load_settings(self):
        try:
            value=self.validate_settings(self.documents.load('profiles',self.profiles.currentText()));activate=self.activate_profile.isChecked()
            if activate and not self.owner.engine.is_connected:raise ValueError('Connect before activating saved controls.')
            self.hotkeys_enabled.setChecked(False)
            for name,text in value['hotkeys'].items():self.key_editors[name].setKeySequence(QKeySequence(text))
            for card in self.owner.cards:
                v=value['controls'][card.feature.method]['value']
                if isinstance(card.editor,QSpinBox):card.editor.setValue(v)
                elif card.editor is not None:card.editor.setCurrentIndex(v)
            def op():
                if self.owner.engine.is_connected:
                    if self.session:self.session.reset()
                    if self.owner.engine.reset_all()is False:raise RuntimeError('Could not reset the previous settings.')
                    for card in self.owner.cards:
                        if card.feature.state and getattr(self.owner.engine,card.feature.state,False):getattr(self.owner.engine,card.feature.method)(False)
                    if self.owner.speed_changed and not getattr(type(self.owner.engine),'safe_runtime_enabled',False):self.owner.engine.set_game_speed(10)
                    if activate:
                        for card in self.owner.cards:
                            if value['controls'][card.feature.method]['enabled']:
                                self.owner.prepare(card)
                                if getattr(self.owner.engine,card.feature.method)(True)is False:raise RuntimeError('Could not activate '+card.feature.title)
                return 'Profile loaded. '+('Saved controls activated.'if activate else'Controls and hotkeys remain off.')
            self.run(op,lambda _:setattr(self.owner,'speed_changed',False))
        except Exception as error:self.status.setText(str(error))
    def hotkey_action(self,name):
        method=HOTKEY_ACTIONS[name]
        if method is None:self.cancel_queue();return
        card=next(c for c in self.owner.cards if c.feature.method==method)
        self.owner.change(card,not bool(getattr(self.owner.engine,card.feature.state,False)))
    def poll_hotkeys(self):
        try:
            if self.hotkeys is None:self.hotkeys=GameHotkeys(self)
            self.hotkeys.poll()
        except Exception as error:self.hotkeys_enabled.setChecked(False);self.status.setText('Hotkeys paused: '+str(error))
    def heartbeat(self):
        if not self.owner.engine.is_connected or self.owner.busy:return
        now=time.monotonic();snapshot=now-self.last_snapshot>.8
        active=self.session and(self.session.schedule.queue or self.session.effect is not None)
        if not snapshot and not active:return
        if snapshot:self.last_snapshot=now
        def op():
            g=self.game()
            try:
                if g.schedule.queue or g.effect is not None:g.tick()
                return g.telemetry()if snapshot else None
            except Exception:
                g.schedule.cancel()
                if g.effect is not None:g.enable_effect(None)
                raise
        def done(data):
            if data:
                self.dashboard.setText(f'{data["status"]}  |  Sun: {data.get("sun","—")}  |  Wave: {data.get("wave","—")} / {data.get("waves","—")}  |  Plants: {data["plants"]}  |  Zombies: {data["zombies"]}  |  Queued: {data["queued"]}')
                if data.get('mode')in (43,50)and'Unsupported lawn scene'in self.status.text():self.status.setText('Garden/profile tools are ready. Read the saved collection to select a plant.')
                if data.get('rows'):
                    for widget in (self.plant_row,self.plant_row_end,self.zombie_row,self.move_selected_row):widget.setMaximum(data['rows'])
                if data.get('waves'):
                    total=min(100,data['waves']);self.natural_wave.setRange(min(total,data['wave']+1),total)
        self.run(op,done,quiet=True)
    def reload_names(self,widget,kind):widget.clear();widget.addItems(self.documents.names(kind))
    def closeEvent(self,event):
        # This tool window hides; the main controller owns the live session.
        # Reset/disconnect/main exit still restore all Studio edits explicitly.
        event.ignore();self.hide()

