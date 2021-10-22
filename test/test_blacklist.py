import unittest
import blacklist

class TestBlacklist(unittest.TestCase):
    def setUp(self):
        self.fake_user = 'this_is_a_fake_user'

    def tearDown(self):
        blacklist.remove_user(self.fake_user)

    def test_basic_cases(self):
        self.assertFalse(blacklist.check_user(self.fake_user))
        blacklist.add_user(self.fake_user)
        self.assertTrue(blacklist.check_user(self.fake_user), 'Adding blacklist failed')
        blacklist.remove_user(self.fake_user)
        self.assertFalse(blacklist.check_user(self.fake_user), 'Removing blacklist failed')

if __name__ == '__main__':
    unittest.main()
