"""Workbench input constraints, readable labels, plans and native-request safety."""
import copy,unittest
from unittest.mock import Mock
from PySide6.QtWidgets import QTableWidgetItem,QComboBox,QSpinBox
import test_studio
from studio_models import formation
from studio_labels import plant_name,zombie_name

class WorkbenchModelTests(unittest.TestCase):
    def setUp(self):
        self.fixture=test_studio.EditorTests('test_dashboard_counts');self.fixture.setUp();self.g=self.fixture.g;self.m=self.fixture.m;self.b=self.fixture.b
    def test_stack_plans_allow_eight_ordinary_plants_but_not_nine(self):
        p=dict(type=0,row=1,col=1,imitater=False)
        value=dict(version=2,scene=0,stack=True,plants=[p]*8);self.assertEqual(len(formation(value)['plants']),8)
        value['plants'].append(p)
        with self.assertRaisesRegex(ValueError,'8'):formation(value)
    def test_foundations_and_cob_footprints_cannot_be_stacked(self):
        for records in [[dict(type=33,row=1,col=1,imitater=False)]*2,[dict(type=47,row=1,col=1,imitater=False),dict(type=0,row=1,col=2,imitater=False)]]:
            with self.assertRaises(ValueError):formation(dict(version=2,scene=0,stack=True,plants=records))
    def test_batch_preflights_the_whole_rectangle(self):
        self.g.place_plant=Mock(return_value={'id':1})
        self.assertEqual(self.g.place_many(0,2,3,2,3),4);self.assertEqual(self.g.place_plant.call_count,4)
        self.g.place_plant.reset_mock()
        with self.assertRaisesRegex(ValueError,'Multiple copies'):self.g.place_many(0,2,2,2,2,copies=2)
        self.g.place_plant.assert_not_called()
    def test_merge_skips_identical_cells_but_never_deletes_another_plant(self):
        self.g.place_plant=Mock(return_value={'id':2});p=dict(type=0,row=1,col=1,imitater=False)
        self.assertEqual(self.g.apply_formation(dict(version=1,scene=0,plants=[p]),merge=True),0)
        p['type']=1
        with self.assertRaisesRegex(ValueError,'different plant'):self.g.apply_formation(dict(version=1,scene=0,plants=[p]),merge=True)
        self.g.place_plant.assert_not_called()
    def test_coin_enumeration_excludes_rewards_dead_and_collecting_objects(self):
        self.m.put(self.b+0xfc,0xa00000);self.m.put(self.b+0x100,4)
        for i,kind in enumerate((1,2,8,3)):
            self.m.put(0xa00000+i*0xd8+0xd0,0x10000+i);self.m.put(0xa00000+i*0xd8+0x58,kind)
        self.m.put(0xa00000+0xd8+0x50,1,'<B');self.m.put(0xa00000+3*0xd8+0x38,1,'<B')
        self.assertEqual(self.g.coins(),[(0xa00000,0x10000)])
    def test_move_checks_terrain_state_and_live_instance_id(self):
        for i in range(5):self.m.put(self.b+0x5f0+i*4,1)
        z=self.g.entities('zombie')[0];self.m.put(z['address']+0x28,1)
        self.assertEqual(self.g.move_zombies(2,selected_ids={z['id']}),{'moved':0,'skipped':1})
        with self.assertRaisesRegex(RuntimeError,'disappeared'):self.g.move_zombies(2,selected_ids={0x99990001})
        self.m.put(z['address']+0x28,0);self.m.put(self.b+0x5564,2);self.m.put(self.b+0x5f0+2*4,2)
        self.assertEqual(self.g.move_zombies(3,{z['id']}),{'moved':0,'skipped':1})

    def test_total_quantity_is_exact_and_insufficient_space_is_atomic(self):
        self.g.place_plant=Mock(return_value={'id':2})
        self.assertEqual(self.g.place_many(0,1,5,1,9,limit=7,available_only=True),7)
        self.assertEqual(self.g.place_plant.call_count,7);self.g.place_plant.reset_mock()
        with self.assertRaisesRegex(ValueError,'Only 44'):self.g.place_many(0,1,5,1,9,limit=45,available_only=True)
        self.g.place_plant.assert_not_called()
    def test_launch_disposes_old_board_before_mode_change_on_game_thread(self):
        import capstone
        from unittest.mock import patch
        with patch.object(self.fixture.native,'execute_main',wraps=self.fixture.native.execute_main)as main:
            self.g.launch_level(7,43);main.assert_called_once()
        calls=[i.operands[0].imm for i in self.disassemble(self.fixture.native.calls[-1])if i.mnemonic=='call']
        self.assertEqual(calls,[0x452640,0x452820])
        self.m.put(self.fixture.app+0x91c,1);self.g.launch_level(7,43)
        calls=[i.operands[0].imm for i in self.disassemble(self.fixture.native.calls[-1])if i.mnemonic=='call']
        self.assertEqual(calls,[0x452c70,0x452640,0x452820])
    def disassemble(self,code):
        import capstone
        d=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);d.detail=True;return list(d.disasm(code,0x40000000))
    def test_launch_refuses_open_menu_before_any_native_call(self):
        self.m.put(self.b+0x17c,1,'<B')
        with self.assertRaisesRegex(RuntimeError,'resume'):self.g.launch_level(7,43)
        self.assertFalse(self.fixture.native.calls)

class WorkbenchUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):test_studio.StudioUITests.setUpClass()
    def setUp(self):
        self.fixture=test_studio.StudioUITests('test_all_seven_workspaces_and_default_hotkeys_are_off');self.fixture.setUp();self.ui=self.fixture.studio
    def tearDown(self):self.fixture.tearDown()
    def test_tabs_have_icons_and_readable_names(self):
        for i in range(8):self.assertFalse(self.ui.tabs.tabIcon(i).isNull())
        self.assertIn('Inspect',self.ui.tabs.tabText(1));self.assertIn('Zombie',self.ui.tabs.tabText(2))
    def test_plan_roundtrip_preserves_names_ids_and_stacks(self):
        self.ui.add_plan_row(0,1,1,2);self.ui.plan_stack.setChecked(True);self.ui.formation_name.setText('Stack test');self.ui.save_plant_plan()
        self.ui.plan_table.setRowCount(0);self.ui.load_plant_plan();self.assertEqual(len(self.ui.plant_plan_value()['plants']),2)
        self.assertIn('Peashooter',self.ui.plan_table.cellWidget(0,0).currentText())
    def test_removing_plan_rows_does_not_break_column_constraints(self):
        self.ui.add_plan_row();self.ui.add_plan_row();self.ui.plan_table.removeRow(0);self.ui.plan_table.cellWidget(0,0).setCurrentIndex(47)
        self.assertEqual(self.ui.plan_table.cellWidget(0,2).maximum(),8)
    def test_wave_editor_uses_named_dropdowns_and_bounded_values(self):
        self.assertIsInstance(self.ui.wave_table.cellWidget(0,0),QComboBox);self.ui.wave_table.cellWidget(0,0).setCurrentIndex(2)
        self.assertIn('Conehead',self.ui.wave_table.cellWidget(0,0).currentText());self.assertEqual(self.ui.wave_value()['entries'][0]['type'],2)
        self.assertEqual(self.ui.wave_table.cellWidget(0,2).maximum(),100);self.assertFalse(self.ui.wave_table.cellWidget(0,0).model().item(25).isEnabled())
    def test_zombie_presets_are_available_from_the_lawn_builder(self):
        self.ui.wave_name.setText('Cone group');self.ui.wave_table.cellWidget(0,0).setCurrentIndex(2);self.ui.save_wave()
        self.assertEqual(self.ui.zombie_setups.currentText(),'Cone group');self.ui.wave_table.cellWidget(0,0).setCurrentIndex(0);self.ui.load_wave()
        self.assertEqual(self.ui.wave_value()['entries'][0]['type'],2)
    def select_cone(self):
        p=dict(id=0x10001,kind='zombie',type=2,row=1,x=300.,y=50.,health=270,max_health=270,armour=370,max_armour=370,shield=0,max_shield=0,helm_type=1,shield_type=0,speed=.3,chilled=0,buttered=0,frozen=0,board=(1,0))
        self.ui.entity_records=[p];self.ui.entity_table.setRowCount(1);self.ui.entity_table.setItem(0,0,QTableWidgetItem('Test'));self.ui.entity_table.selectRow(0);self.ui.select_entity()
    def test_inspector_names_equipment_and_disables_absent_shields(self):
        self.select_cone();self.assertIn('Conehead',self.ui.entity_details.text());self.assertIn('Traffic cone (ID 1)',self.ui.entity_details.text())
        self.assertTrue(self.ui.entity_checks['armour'].isEnabled());self.assertFalse(self.ui.entity_checks['shield'].isEnabled())
        self.assertEqual(self.ui.entity_editors['health'].maximum(),270)
        self.ui.entity_checks['max_health'].setChecked(True);self.ui.entity_editors['max_health'].setValue(1000);self.assertEqual(self.ui.entity_editors['health'].maximum(),1000)
    def test_garden_uses_names_and_only_valid_fertilizing_actions(self):
        self.assertFalse(self.ui.fertilize_button.isEnabled())
        p=dict(index=0,type=0,garden=0,age=0,fed=1,feedings=2,need=1);self.ui.show_garden([p])
        self.assertIn('Peashooter',self.ui.garden_table.item(0,1).text());self.assertIn('Sprout',self.ui.garden_table.item(0,4).text());self.assertFalse(self.ui.fertilize_button.isEnabled())
        p['fed']=2;self.ui.show_garden([p]);self.assertTrue(self.ui.fertilize_button.isEnabled())
        p['age']=3;self.ui.show_garden([p]);self.assertFalse(self.ui.fertilize_button.isEnabled());self.assertEqual(self.ui.growth.count(),4)
    def test_older_profiles_add_new_controls_off(self):
        value=self.ui.settings();value['controls'].pop('toggle_auto_coins');value['controls'].pop('move_existing_zombies')
        result=self.ui.validate_settings(value);self.assertFalse(result['controls']['toggle_auto_coins']['enabled']);self.assertFalse(result['controls']['move_existing_zombies']['enabled'])

    def test_visual_plan_paints_and_erases_named_plants(self):
        self.ui.plan_brush.setCurrentIndex(1);self.ui.paint_plan_cell(2,3)
        value=self.ui.plant_plan_value();self.assertEqual(value['plants'][0]['type'],1)
        self.assertEqual(self.ui.plan_canvas.plants[0]['row'],2)
        self.ui.paint_plan_cell(2,3,True);self.assertEqual(self.ui.plan_table.rowCount(),0)
    def test_pool_canvas_adds_lily_pad_and_keeps_sixth_row(self):
        self.ui.plan_scene.setCurrentIndex(2);self.ui.plan_brush.setCurrentIndex(0);self.ui.paint_plan_cell(3,2)
        value=self.ui.plant_plan_value();self.assertEqual([p['type']for p in value['plants']],[16,0])
        self.ui.paint_plan_cell(6,9);self.assertEqual(self.ui.plan_canvas.plants[-1]['row'],6)
    def test_placement_modes_explain_and_limit_the_total_count(self):
        self.ui.placement_mode.setCurrentIndex(1);self.assertFalse(self.ui.plant_row.isEnabled());self.assertFalse(self.ui.total_plants.isEnabled())
        self.ui.placement_mode.setCurrentIndex(2);self.assertTrue(self.ui.total_plants.isEnabled());self.assertEqual(self.ui.total_plants.maximum(),250)
    def test_older_profiles_add_sunflower_control_off(self):
        value=self.ui.settings();value['controls'].pop('toggle_sunflower_drop')
        result=self.ui.validate_settings(value);self.assertFalse(result['controls']['toggle_sunflower_drop']['enabled'])
