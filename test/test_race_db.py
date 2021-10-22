import unittest
import race_db

class TestRaceDB(unittest.TestCase):
    def setUp(self):
        self.fake_race = 'fake_race'

    def tearDown(self):
        race_db.delete_race(self.fake_race)
        race_db.delete_race('abc123')
        race_db.delete_race('abc456')

    def test_basic_cases(self):
        self.assertFalse(race_db.check_race(self.fake_race))
        race_db.add_race(self.fake_race)
        self.assertTrue(race_db.check_race(self.fake_race), 'Adding race failed')
        self.assertFalse(race_db.check_race_is_finished(self.fake_race))
        race_db.update_race(self.fake_race, True)
        self.assertTrue(race_db.check_race_is_finished(self.fake_race), 'Update race failed')
        race_db.delete_race(self.fake_race)
        self.assertFalse(race_db.check_race(self.fake_race), 'Delete race failed')

    def test_delete_all_active_races(self):
        self.assertFalse(race_db.check_race('abc123'))
        self.assertFalse(race_db.check_race('abc456'))
        self.assertEqual(race_db.delete_all_active_races(), 0)
        race_db.add_race('abc123')
        race_db.add_race('abc456')
        self.assertFalse(race_db.check_race_is_finished('abc123'))
        self.assertFalse(race_db.check_race_is_finished('abc456'))
        self.assertEqual(race_db.delete_all_active_races(), 2)

if __name__ == '__main__':
    unittest.main()
