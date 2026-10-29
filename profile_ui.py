"""Draft-based, named player-data and achievement editors."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QCheckBox,QTableWidgetItem
from profile_tools import tools,PROFILE_FIELDS,ACHIEVEMENTS

class PlayerDataPanel(QWidget):
    def __init__(self,studio):
        super().__init__();self.studio=studio;self.snapshot=None
        from studio_ui import spin,combo,row,table
        box=QVBoxLayout(self);guide=QLabel('Read the active player, tick only the fields you want to change, then Apply. Apply requires PVZ Main Menu and creates a save backup. Other fields remain unchanged. Re-read after editing or changing players.');guide.setWordWrap(True);box.addWidget(guide)
        self.identity=QLabel('No player loaded. The game’s name and profile ID are kept unchanged.');self.identity.setWordWrap(True);self.identity.setTextFormat(Qt.TextFormat.PlainText);box.addWidget(self.identity)
        box.addWidget(studio.button('Read active player data and achievements',self.read))
        box.addWidget(row(studio.button('Jump to progress fields',lambda:studio.scroll_to(self.editors['coins'])),studio.button('Jump to achievement checkboxes',lambda:studio.scroll_to(self.awards))))
        f=studio.group(box,'Editable progress and owned gardens');self.checks={};self.editors={};self.current={}
        for key,(label,off,lo,hi,scale,bias)in PROFILE_FIELDS.items():
            check=QCheckBox(label);edit=combo(['No / locked','Yes / owned'])if hi==1 else spin(lo,hi,lo)
            if key=='coins':edit.setSingleStep(1)
            current=QLabel('Current: —');self.checks[key]=check;self.editors[key]=edit;self.current[key]=current
            edit.setEnabled(False);check.toggled.connect(edit.setEnabled);f.addRow(check,row(edit,current))
        f.addRow(studio.button('Apply checked player-data changes',self.apply_fields))
        self.coin_preview=QLabel();self.editors['coins'].valueChanged.connect(lambda value:self.coin_preview.setText(f'Bank preview: ${value*10:,} (PVZ stores money in $10 units).'));self.editors['coins'].valueChanged.emit(self.editors['coins'].value());f.addRow(self.coin_preview)
        note=QLabel('999999 coin units means $9,999,990. Large balances automatically enable Extended coin bank for this game session. Keep it enabled while spending/earning above the normal ceiling. Seed slots are 6–10 for future battles. Endless records are best scores, not the current run. Only Pool Endless is normally visible in Survival; the other four are hidden variants. Adventure stage changes future progress. Name/ID and Zombatar data stay unchanged.');note.setWordWrap(True);f.addRow(note)
        f=studio.group(box,'Local GOTY achievements — changes remain drafts until Apply')
        self.awards=table(['Achievement ID + name','Earned']);self.awards.setRowCount(20);self.awards.setColumnWidth(0,430);self.awards.setMinimumHeight(350)
        for i,name in enumerate(ACHIEVEMENTS):
            self.awards.setItem(i,0,QTableWidgetItem(f'{i} — {name}'));item=QTableWidgetItem();item.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Unchecked);self.awards.setItem(i,1,item)
        f.addRow(self.awards);f.addRow(row(studio.button('Check all (draft)',lambda:self.check_all(True)),studio.button('Uncheck all (draft)',lambda:self.check_all(False))))
        f.addRow(studio.button('Apply changed achievement checkboxes',self.apply_awards))
        note=QLabel('This edits the 20 local GOTY flags and verifies them in the native save file. Applying achievements prepares separate edition save folders if needed. Use the LawnLab game launchers so Classic cannot overwrite GOTY flags. Awarded flags are marked as already shown to avoid popup spam. Removing a flag does not undo its gameplay progress. This does not edit Steam-account achievements.');note.setWordWrap(True);f.addRow(note)
    def read(self):self.studio.run(lambda:tools(self.studio.game()).read(),self.show_snapshot)
    def show_snapshot(self,data):
        self.snapshot=data;self.identity.setText(f'Active player: {data.get("name","Local player")} · profile ID: {data["owner"][1]} · Saved garden plants: {data["garden_count"]}. Identity/name are unchanged.')
        for key,value in data['values'].items():
            self.checks[key].setChecked(False);self.current[key].setText('Current: '+str(value));edit=self.editors[key]
            if PROFILE_FIELDS[key][3]==1:edit.setCurrentIndex(1 if value else 0)
            else:edit.setValue(value)
        for i,state in enumerate(data['earned']):self.awards.item(i,1).setCheckState(Qt.CheckState.Checked if state else Qt.CheckState.Unchecked)
        self.awards.setEnabled(data.get('achievements_supported',True))
        if not data.get('achievements_supported',True):self.identity.setText(self.identity.text()+' Classic has no native GOTY achievement flags; achievement editing is unavailable.')
    def check_all(self,state):
        for i in range(20):self.awards.item(i,1).setCheckState(Qt.CheckState.Checked if state else Qt.CheckState.Unchecked)
    def apply_fields(self):
        if self.snapshot is None:self.studio.status.setText('Read the active player first.');return
        values={key:(self.editors[key].currentIndex()if PROFILE_FIELDS[key][3]==1 else self.editors[key].value())for key,c in self.checks.items()if c.isChecked()}
        if not values:self.studio.status.setText('Tick at least one player-data field to update.');return
        owner=self.snapshot['owner'];self.studio.persistent('Update player data',lambda:tools(self.studio.game()).edit(values,owner),lambda _:self.read())
    def apply_awards(self):
        if self.snapshot is None:self.studio.status.setText('Read the active player first.');return
        if not self.snapshot.get('achievements_supported',True):self.studio.status.setText('Classic has no native GOTY achievement flags.');return
        changes={i:self.awards.item(i,1).checkState()==Qt.CheckState.Checked for i in range(20)if(self.awards.item(i,1).checkState()==Qt.CheckState.Checked)!=self.snapshot['earned'][i]}
        if not changes:self.studio.status.setText('No achievement checkboxes changed.');return
        owner=self.snapshot['owner'];self.studio.persistent('Edit local achievements',lambda:tools(self.studio.game()).achievements(changes,owner),lambda _:self.read())
