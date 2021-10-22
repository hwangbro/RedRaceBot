import sys
import unittest
from timestamp import *


class TestTimestamp(unittest.TestCase):
    def test_normal_split(self):
        ts_str = 'RealTime "Lance" 1:57:22.20'
        ts = parse_timestamp(ts_str)
        self.assertEqual(ts.hours, 1)
        self.assertEqual(ts.minutes, 57)
        self.assertEqual(ts.seconds, 22)
        self.assertEqual(ts.ms, 200)
        self.assertEqual(ts.split_name, 'Lance')
        self.assertEqual(ts.total_ms, 7042200)
        self.assertEqual(str(ts), '[Lance]: 01:57:22.20')
        self.assertEqual(ts.time_string, '01:57:22.20')

    def test_no_hours_in_split(self):
        ts_str = 'RealTime "Route 3" 18:20.98'
        ts = parse_timestamp(ts_str)
        self.assertEqual(ts.hours, 0)
        self.assertEqual(ts.minutes, 18)
        self.assertEqual(ts.seconds, 20)
        self.assertEqual(ts.ms, 980)
        self.assertEqual(ts.split_name, 'Route 3')
        self.assertEqual(ts.total_ms, 1100980)
        self.assertEqual(str(ts), '[Route 3]: 18:20.98')
        self.assertEqual(ts.time_string, '18:20.98')

    def test_skipped_split(self):
        ts_str = 'RealTime "Misty" -'
        ts = parse_timestamp(ts_str)
        self.assertEqual(ts.hours, 0)
        self.assertEqual(ts.minutes, 0)
        self.assertEqual(ts.seconds, 0)
        self.assertEqual(ts.ms, 0)
        self.assertEqual(ts.split_name, 'Misty')
        self.assertTrue(isinstance(ts, SkipTimestamp))
        self.assertEqual(ts.total_ms, sys.maxsize - 2)
        self.assertEqual(str(ts), '[Misty]: Skipped')
        self.assertEqual(ts.time_string, 'Skipped')

    def test_ignore_timestamp(self):
        ts = BlankTimestamp()
        self.assertEqual(ts.total_ms, sys.maxsize - 1)
        self.assertEqual(ts.time_string, 'N/A')
        self.assertEqual(str(ts), 'N/A')

    def test_forfeit_timestamp(self):
        ts = ForfeitTimestamp()
        self.assertEqual(ts.total_ms, sys.maxsize)
        self.assertEqual(ts.time_string, 'Forfeit')
        self.assertEqual(str(ts), 'Forfeit')

if __name__ == '__main__':
    unittest.main()
