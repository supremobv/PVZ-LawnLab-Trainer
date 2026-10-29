import copy,unittest
from unittest.mock import Mock
import test_studio
from profile_tools import ProfileTools,PROFILE_FIELDS

class ProfileTests(unittest.TestCase):
 def setUp(self):
  self.f=test_studio.EditorTests('test_dashboard_counts');self.f.setUp();self.g=self.f.g;self.m=self.f.m;self.t=ProfileTools(self.g);self.u=self.f.user
  self.m.put(self.f.app+0x91c,1);self.m.put(self.u+0x4c,1);self.m.put(self.u+0x3a4,3)
  for slot in(18,19,25):self.m.put(self.u+0x1e8+slot*4,1)
 def test_named_fields_encode_coin_units_and_seed_count(self):
  self.t.edit({'coins':12345,'seed_slots':10,'tree_height':777})
  self.assertEqual((self.g.read(self.u+0x50),self.g.read(self.u+0x23c)),(12345,4))
  self.assertEqual(self.t.read()['values']['tree_height'],777)
 def test_invalid_profile_fields_make_no_writes(self):
  before=dict(self.m.bytes)
  for changes in ({'coins':-1},{'seed_slots':11},{'adventure':0},{'raw_address':2},{'minigames':True}):
   with self.assertRaises(ValueError):self.t.edit(changes)
   self.assertEqual(self.m.bytes,before)
 def test_changed_player_and_live_battle_are_refused(self):
  before=dict(self.m.bytes)
  with self.assertRaisesRegex(RuntimeError,'active player'):self.t.edit({'coins':100},(self.u,99))
  self.assertEqual(before,self.m.bytes);self.m.put(self.f.app+0x91c,3)
  with self.assertRaisesRegex(RuntimeError,'Main Menu'):self.t.edit({'coins':100})
  with self.assertRaisesRegex(RuntimeError,'Main Menu'):self.t.add(0,0)
 def test_achievement_arrays_are_separate_from_level(self):
  self.t.achievements({0:True,19:True});data=self.t.read()
  self.assertTrue(data['earned'][0]);self.assertTrue(data['shown'][19]);self.assertEqual(self.g.read(self.u+0x4c),1)
  self.t.achievements({19:False});self.assertFalse(self.t.read()['earned'][19])
  with self.assertRaises(ValueError):self.t.achievements({20:True})
 def test_adds_distinct_bounded_garden_places(self):
  self.t.add(8,1,8);plants=[p for p in self.g.garden()if p['garden']==1]
  self.assertEqual(len({(p['x'],p['y'])for p in plants}),8)
  before=dict(self.m.bytes)
  with self.assertRaisesRegex(ValueError,'free places'):self.t.add(8,1)
  self.assertEqual(before,self.m.bytes)
 def test_aquarium_requires_aquatic_and_owned_destination(self):
  with self.assertRaisesRegex(ValueError,'Aquarium'):self.t.add(0,3)
  self.m.put(self.u+0x24c,0)
  with self.assertRaisesRegex(ValueError,'unlock'):self.t.add(19,3)
 def test_move_checks_stamp_capacity_and_preserves_slot(self):
  self.t.add(8,1);p=self.g.garden()[1];self.t.move(1,2,p['stamp']);q=self.g.garden()[1]
  self.assertEqual((q['index'],q['garden']),(1,2))
  with self.assertRaisesRegex(RuntimeError,'collection changed'):self.t.move(1,0,p['stamp'])
  with self.assertRaisesRegex(ValueError,'free places'):self.t.add(0,2)
 def test_bulk_waters_once_and_fertilizes_only_eligible(self):
  self.t.add(8,1,2);self.f.native.calls.clear();self.t.bulk('water',1)
  self.assertEqual(len(self.f.native.calls),1);self.assertTrue(all(p['fed']==1 for p in self.g.garden()if p['garden']==1))
  result=self.t.bulk('fertilize',1);self.assertIn('skipped 2',result)
  self.t.bulk('water',1);self.t.bulk('water',1);self.t.bulk('fertilize',1)
  self.assertTrue(all(p['age']==1 for p in self.g.garden()if p['garden']==1))
  self.assertEqual(self.g.garden()[0]['age'],3)
 def test_failed_save_rolls_back_profile_memory(self):
  self.f.native.poisoned=False;self.g.save_profile=Mock(side_effect=[OSError('save failed'),None]);before=self.m.read_bytes(self.u+0x24,0x500)
  with self.assertRaises(OSError):self.t.edit({'coins':12345})
  self.assertEqual(before,self.m.read_bytes(self.u+0x24,0x500))

 def test_coin_lock_refuses_overwritten_saved_balance(self):
  self.g.engine.money_changer_active=True
  with self.assertRaisesRegex(ValueError,'Coin balance lock'):self.t.edit({'coins':100})
  self.assertFalse(self.f.native.calls)
 def test_single_garden_action_rejects_stale_saved_slot(self):
  p=self.g.garden()[0];self.m.put(self.u+0x380,0)
  with self.assertRaisesRegex(RuntimeError,'collection changed'):self.g.garden_edit(0,'water',stamp=p['stamp'])
  self.assertEqual(self.g.read(self.u+0x380+0x28),0)

class PlayerUITests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):test_studio.StudioUITests.setUpClass()
 def setUp(self):self.f=test_studio.StudioUITests('test_all_seven_workspaces_and_default_hotkeys_are_off');self.f.setUp();self.ui=self.f.studio
 def tearDown(self):self.f.tearDown()
 def test_selected_slot_is_named_and_read_only(self):
  self.ui.show_garden([dict(index=0,type=1,garden=0,age=0,fed=0,feedings=3,need=1,x=0,y=0)])
  self.assertTrue(self.ui.garden_index.isReadOnly());self.assertIn('Sunflower',self.ui.garden_selection.text());self.assertIn('slot 0',self.ui.garden_selection.text())
 def test_player_read_does_not_enable_any_edits(self):
  data=dict(owner=(123,1),garden_count=2,values={k:v[2]for k,v in PROFILE_FIELDS.items()},earned=[True]*20,shown=[True]*20)
  p=self.ui.player_panel;p.show_snapshot(data)
  self.assertFalse(any(c.isChecked()for c in p.checks.values()));self.assertEqual(p.awards.rowCount(),20)
 def test_aquarium_dropdown_filters_invalid_types(self):
  self.ui.new_garden.setCurrentIndex(3)
  self.assertFalse(self.ui.new_garden_plant.model().item(0).isEnabled());self.assertTrue(self.ui.new_garden_plant.model().item(19).isEnabled());self.assertEqual(self.ui.new_garden_count.maximum(),8)
 def test_profile_apply_requires_read_and_changed_fields(self):
  p=self.ui.player_panel;self.ui.persistent=Mock();p.apply_fields();self.ui.persistent.assert_not_called();self.assertIn('Read',self.ui.status.text())

 def test_reconnect_replaces_old_studio_native_session(self):
  from unittest.mock import patch
  from studio_engine import StudioGame
  engine=self.ui.owner.engine;engine.studio_game_class=StudioGame;engine.is_connected=True;engine.base_address=0x400000;engine.pm=object()
  def guard(game):game._checked=engine.pm
  try:
   with patch('studio_ui.StudioGame.guard',guard):
    first=self.ui.game();first.schedule.queue=[(0,0,1)];engine.pm=object();second=self.ui.game()
    self.assertIsNot(first,second);self.assertFalse(first.schedule.queue);self.assertIsNone(second.native)
  finally:engine.is_connected=False;engine.pm=None;self.ui.session=None
