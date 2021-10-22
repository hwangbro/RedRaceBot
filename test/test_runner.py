import sys

import unittest
from runner import Runner, RunnerSet
from trackedsplits import RBYSplits
from timestamp import Timestamp, parse_timestamp, ForfeitTimestamp, BlankTimestamp, SkipTimestamp
from srlmodels import SRLEntrant

class TestRunner(unittest.TestCase):
    def setUp(self):
        self.model = SRLEntrant('hwangbro', '9994', -3, '', 'Ready', 'hwangbroxd', '100')
        self.model2 = SRLEntrant('araya', 9993, -2, '', 'Ready', 'arayalol', '999')
        self.model3 = SRLEntrant('franchewbacca', 9992, -1, '', 'Ready', 'franchewbacca', '100')

        self.runner = Runner(self.model)
        self.runner2 = Runner(self.model2)
        self.runner3 = Runner(self.model3)

        self.splits = RBYSplits()

    def test_basic_splits(self):
        nido = self.splits['Nido']
        nido_ts = parse_timestamp('RealTime "Nido" 7:20.80')
        self.runner.add_split(nido, nido_ts)
        self.assertTrue(self.runner.completed_split(nido))
        self.assertEqual(self.runner.get_split_time(nido).total_ms, 440800)
        self.assertEqual(self.runner.latest_split[0], nido)

        self.runner.undo_split(nido)
        self.assertFalse(self.runner.completed_split(nido), 'Undo split failed')

        nido_ts = parse_timestamp('RealTime "Nido" 7:58.00')
        self.runner.add_split(nido, nido_ts)
        self.assertTrue(self.runner.completed_split(nido), 'Resplit failed')
        self.assertEqual(self.runner.get_split_time(nido).total_ms, 478000)

    def test_forfeit(self):
        lance = self.splits['Lance']
        self.runner.update_status('Forfeit')
        self.assertEqual(self.runner.get_split_time(lance).total_ms, sys.maxsize)

        self.runner.update_status('Ready')
        self.assertIsNone(self.runner.get_split_time(lance))

    def test_latest_split(self):
        n_a_split = self.splits['N/A']
        split, ts = self.runner.latest_split
        self.assertEqual(split.Name, 'N/A')
        self.assertTrue(isinstance(ts, BlankTimestamp))
        nido = self.splits['Nido']
        nido_ts = parse_timestamp('RealTime "Nido" 7:20.80')
        brock = self.splits['Brock']
        brock_ts = parse_timestamp('RealTime "Brock" 11:58.70')
        nido_skip = parse_timestamp('RealTime "Nido" -')

        self.assertFalse(self.runner.completed_split(nido))
        self.runner.add_split(nido, nido_ts)
        self.assertEqual(self.runner.latest_split[1], nido_ts)
        self.runner.undo_split(nido)
        self.assertEqual(self.runner.latest_split[0], n_a_split)
        self.runner.add_split(nido, nido_skip)
        self.assertEqual(self.runner.latest_split[0], n_a_split, 'Skipped splits should not be counted in latest')
        self.runner.add_split(brock, brock_ts)
        self.assertEqual(self.runner.latest_split[1], brock_ts)

    def test_get_split_time(self):
        nido = self.splits['Nido']
        nido_ts = parse_timestamp('RealTime "Nido" 7:20.80')
        ff_ts = ForfeitTimestamp()
        self.runner.add_split(nido, nido_ts)

        self.assertEqual(self.runner.get_split_time(nido), nido_ts)
        self.assertIsNone(self.runner.get_split_time(self.splits['Brock']))

        self.runner.ignored = True
        self.assertEqual(self.runner.get_split_time(nido), BlankTimestamp())
        self.runner.ignored = False

        self.runner.update_status('Forfeit')
        self.assertEqual(str(self.runner.get_split_time(nido)), str(ff_ts))

    def test_update_status(self):
        self.assertFalse(self.runner.forfeit)
        self.runner.update_status('Forfeit')
        self.assertTrue(self.runner.forfeit)
        self.assertTrue(self.runner.finished)

    def test_user_matches(self):
        self.assertTrue(self.runner.user_matches('hwangbroxd'))
        self.assertTrue(self.runner.user_matches('hwangbro'))
        self.assertTrue(self.runner.user_matches('HwaNGBroXD'))
        self.assertFalse(self.runner.user_matches('HwangbroXDD'))

    def test_split_order(self):
        nido = self.splits['Nido']
        nido_ts1 = parse_timestamp('RealTime "Nido" 06:42.35')
        nido_ts2 = parse_timestamp('RealTime "Nido" 07:20.80')
        nido_ts3 = parse_timestamp('RealTime "Nido" 07:25.12')
        self.runner.add_split(nido, nido_ts1)
        self.runner2.add_split(nido, nido_ts2)
        self.runner3.add_split(nido, nido_ts3)

        runners = [self.runner3, self.runner2, self.runner]
        runners.sort(key=lambda x: x.split_order(nido))

        self.assertEqual(runners[0], self.runner)
        self.assertEqual(runners[1], self.runner2)
        self.assertEqual(runners[2], self.runner3)

        self.runner2.update_status('Forfeit')

        runners.sort(key=lambda x: x.split_order(nido))
        self.assertEqual(runners[0], self.runner)
        self.assertEqual(runners[1], self.runner3)
        self.assertEqual(runners[2], self.runner2)

    def test_latest_split_order(self):
        nido = self.splits['Nido']
        brock = self.splits['Brock']
        misty = self.splits['Misty']

        nido_ts1 = parse_timestamp('RealTime "Nido" 06:42.35')
        nido_ts2 = parse_timestamp('RealTime "Nido" 06:43.35')
        brock_ts1 = parse_timestamp('RealTime "Brock" 12:30.00')
        misty_ts1 = parse_timestamp('RealTime "Misty" 38:39.00')

        self.runner.add_split(brock, brock_ts1)
        self.runner2.add_split(nido, nido_ts2)
        self.runner3.add_split(nido, nido_ts1)

        runners = [self.runner3, self.runner2, self.runner]

        runners.sort(key=lambda x: x.latest_split_order)
        self.assertEqual(runners[0], self.runner)
        self.assertEqual(runners[1], self.runner3)
        self.assertEqual(runners[2], self.runner2)

        self.runner2.add_split(misty, misty_ts1)

        runners.sort(key=lambda x: x.latest_split_order)
        self.assertEqual(runners[0], self.runner2)
        self.assertEqual(runners[1], self.runner)
        self.assertEqual(runners[2], self.runner3)

    def test_completed_split(self):
        nido = self.splits['Nido']
        self.runner.add_split(nido, SkipTimestamp('Nido'))
        self.assertTrue(self.runner.completed_split(self.splits['Nido']))

    def test_announcement_standing_str(self):
        nido_ts1 = parse_timestamp('RealTime "Nido" 06:42.35')
        self.runner.add_split(self.splits['Nido'], nido_ts1)
        self.assertEqual(self.runner.announcement_standing_str(self.splits['Nido']), 'hwangbro - 06:42.35')

    def test_announcement_standing_str_skipped(self):
        nido_ts1 = parse_timestamp('RealTime "Nido" -')
        self.runner.add_split(self.splits['Nido'], nido_ts1)
        self.assertEqual(self.runner.announcement_standing_str(self.splits['Nido']), 'hwangbro - Skipped')

    def test_latest_standing_str(self):
        nido_ts1 = parse_timestamp('RealTime "Nido" 06:42.35')
        self.runner.add_split(self.splits['Nido'], nido_ts1)
        self.assertEqual(self.runner.latest_standing_str(), 'hwangbro: (Nidoran 06:42.35)')

    def test_latest_standing_str_empty(self):
        self.assertEqual(self.runner.latest_standing_str(), 'hwangbro: (N/A)')

class TestRunnerSet(unittest.TestCase):
    def setUp(self):
        self.model = SRLEntrant('hwangbro', '9994', -3, '', 'Ready', 'hwangbroxd', '100')
        self.model2 = SRLEntrant('araya', 9993, -2, '', 'Ready', 'arayalol', '999')
        self.model3 = SRLEntrant('franchewbacca', 9992, -1, '', 'Ready', 'franchewbacca', '100')

        self.runner = Runner(self.model)
        self.runner2 = Runner(self.model2)
        self.runner3 = Runner(self.model3)

        self.runner_set = RunnerSet([self.runner, self.runner2, self.runner3])

        self.splits = RBYSplits()
        self.nido_split = self.splits['Nido']
        self.nido_ts = Timestamp('Nido', 0, 7, 52, 0)
        self.done_split = self.splits['Done']

    def test_finished_normal(self):
        self.assertFalse(self.runner_set.finished)
        self.runner.finished = True
        self.runner2.finished = True
        self.assertFalse(self.runner_set.finished)
        self.runner3.finished = True
        self.assertTrue(self.runner_set.finished)

    def test_finished_with_one_ff(self):
        self.assertFalse(self.runner_set.finished)
        self.runner.finished = True
        self.runner2.finished = True
        self.assertFalse(self.runner_set.finished)
        self.runner3.update_status('Forfeit')
        self.assertTrue(self.runner_set.finished)

    def test_finished_with_all_ff(self):
        self.assertFalse(self.runner_set.finished)
        self.runner.update_status('Forfeit')
        self.runner2.update_status('Forfeit')
        self.assertFalse(self.runner_set.finished)
        self.runner3.update_status('Forfeit')
        self.assertTrue(self.runner_set.finished)

    def test_get(self):
        self.assertIsNotNone(self.runner_set.get('hwangbro'))
        self.assertIsNotNone(self.runner_set.get('hwangbroxd'))
        self.assertIsNotNone(self.runner_set.get('hwangbroXD'))
        self.assertIsNone(self.runner_set.get('hwang'))

    def test_user_ignore(self):
        self.assertTrue(self.runner_set.user_ignore('hwangbro', True))
        self.assertTrue(self.runner.ignored)
        self.assertFalse(self.runner_set.user_ignore('hwang', True))
        self.assertTrue(self.runner_set.user_ignore('hwangbroXD', False))
        self.assertFalse(self.runner.ignored)

    def test_split_is_complete_normal(self):
        self.assertFalse(self.runner_set.split_is_complete(self.nido_split))
        self.runner.add_split(self.nido_split, self.nido_ts)
        self.runner2.add_split(self.nido_split, self.nido_ts)
        self.assertFalse(self.runner_set.split_is_complete(self.nido_split))
        self.runner3.add_split(self.nido_split, self.nido_ts)
        self.assertTrue(self.runner_set.split_is_complete(self.nido_split))

    def test_split_is_complete_one_ff(self):
        self.assertFalse(self.runner_set.split_is_complete(self.nido_split))
        self.runner.add_split(self.nido_split, self.nido_ts)
        self.runner2.update_status('Forfeit')
        self.assertFalse(self.runner_set.split_is_complete(self.nido_split))
        self.runner3.add_split(self.nido_split, self.nido_ts)
        self.assertTrue(self.runner_set.split_is_complete(self.nido_split))

    def test_split_is_complete_one_ignored(self):
        self.assertFalse(self.runner_set.split_is_complete(self.nido_split))
        self.runner.add_split(self.nido_split, self.nido_ts)
        self.runner2.ignored = True
        self.assertFalse(self.runner_set.split_is_complete(self.nido_split))
        self.runner3.add_split(self.nido_split, self.nido_ts)
        self.assertTrue(self.runner_set.split_is_complete(self.nido_split))

    def test_split_is_complete_subset(self):
        subset = {self.runner, self.runner2}
        self.assertFalse(self.runner_set.split_is_complete(self.nido_split, subset))
        self.runner.add_split(self.nido_split, self.nido_ts)
        self.runner2.add_split(self.nido_split, self.nido_ts)
        self.assertTrue(self.runner_set.split_is_complete(self.nido_split, subset))

    def test_add_split_time_normal(self):
        self.runner_set.add_split_time('hwangbro', self.nido_split, self.nido_ts)
        self.assertTrue(self.nido_split in self.runner.splits)

    def test_add_split_time_undo(self):
        skip_ts = SkipTimestamp('Nido')
        self.runner_set.add_split_time('hwangbro', self.nido_split, self.nido_ts)
        self.assertTrue(self.nido_split in self.runner.splits)
        self.runner_set.add_split_time('hwangbro', self.nido_split, skip_ts)
        self.assertFalse(self.nido_split in self.runner.splits)

    def test_add_split_time_skip(self):
        skip_ts = SkipTimestamp('Nido')
        self.runner_set.add_split_time('hwangbro', self.nido_split, skip_ts)
        self.assertTrue(self.nido_split in self.runner.splits)
        self.assertEqual(self.runner.latest_split[0].Name, 'N/A')

    def test_finish_user_skipped(self):
        skip_ts = SkipTimestamp('Done')
        self.runner_set.finish_user('hwangbro', self.done_split, skip_ts)
        self.assertFalse(self.runner.finished)

    def test_finish_user_normal(self):
        done_ts = Timestamp('Done', 1, 52, 0, 0)
        self.runner_set.finish_user('hwangbro', self.done_split, done_ts)
        self.assertTrue(self.runner.finished)

    def test_finish_user_ignored(self):
        self.runner.ignored = True
        done_ts = Timestamp('Done', 1, 52, 0, 0)
        self.runner_set.finish_user('hwangbro', self.done_split, done_ts)
        self.assertTrue(self.runner.finished)
        self.assertFalse(self.runner.ignored)

    def test_check_subset_announce(self):
        self.runner.watched_runners = {'arayalol'}
        self.runner2.add_split(self.nido_split, self.nido_ts)
        ret = self.runner_set.check_subset_announce(self.nido_split)
        self.assertEqual(ret, {self.runner})

    def test_check_subset_announce_two(self):
        self.runner.watched_runners = {'arayalol'}
        self.runner3.watched_runners = {'arayalol', 'hwangbroxd'}
        self.runner2.add_split(self.nido_split, self.nido_ts)
        ret = self.runner_set.check_subset_announce(self.nido_split)
        self.assertEqual(ret, {self.runner})

        self.runner.add_split(self.nido_split, self.nido_ts)
        ret = self.runner_set.check_subset_announce(self.nido_split)
        self.assertEqual(ret, {self.runner3})

    def test_check_global_announce(self):
        self.assertEqual(self.runner_set.check_global_announce(self.nido_split), (False, False))
        self.runner.add_split(self.nido_split, self.nido_ts)
        self.runner2.add_split(self.nido_split, self.nido_ts)
        self.assertEqual(self.runner_set.check_global_announce(self.nido_split), (False, False))
        self.runner3.add_split(self.nido_split, self.nido_ts)
        self.assertEqual(self.runner_set.check_global_announce(self.nido_split), (True, False))

    def test_check_global_announce_done(self):
        self.assertEqual(self.runner_set.check_global_announce(self.done_split), (False, False))
        self.runner.add_split(self.done_split, self.nido_ts)
        self.runner2.add_split(self.done_split, self.nido_ts)
        self.assertEqual(self.runner_set.check_global_announce(self.done_split), (False, False))
        self.runner3.add_split(self.done_split, self.nido_ts)
        self.runner.finished = True
        self.runner2.finished = True
        self.runner3.finished = True
        self.assertEqual(self.runner_set.check_global_announce(self.done_split), (True, True))

    def test_watchlist(self):
        self.runner.watched_runners = {'arayalol'}
        self.assertEqual(self.runner_set.watchlist('hwangbroxd'), {'arayalol'})

    def test_reset_watchlist(self):
        self.runner.watched_runners = {'arayalol'}
        self.assertIsNotNone(self.runner_set.watchlist('hwangbroxd'))
        self.runner_set.reset_watchlist('hwangbroxd')
        self.assertEqual(self.runner_set.watchlist('hwangbroxd'), set())

    def test_set_watchlist_all_valid(self):
        ret = self.runner_set.set_watchlist('hwangbroxd', 'araya, franchewbacca')
        self.assertEqual(ret, {'arayalol', 'franchewbacca'})

    def test_set_watchlist_one_invalid(self):
        ret = self.runner_set.set_watchlist('hwangbroxd', 'arayalol, franchewbacca, juanlyways')
        self.assertEqual(ret, {'arayalol', 'franchewbacca'})

    def test_standings(self):
        self.runner.add_split(self.done_split, Timestamp('Done', 1, 52, 0, 0))
        self.runner2.add_split(self.done_split, Timestamp('Done', 1, 50, 0, 0))
        self.runner3.add_split(self.done_split, Timestamp('Done', 1, 51, 0, 0))
        self.runner.finished = True
        self.runner2.finished = True
        self.runner3.finished = True

        exp_standings = '1. araya: (01:50:00.00)\n2. franchewbacca: (01:51:00.00)\n3. hwangbro: (01:52:00.00)'
        self.assertEqual(exp_standings, self.runner_set.standings(False))

    def test_standings_spoiler(self):
        self.runner.add_split(self.done_split, Timestamp('Done', 1, 52, 0, 0))
        self.runner2.add_split(self.done_split, Timestamp('Done', 1, 50, 0, 0))
        self.runner3.add_split(self.done_split, Timestamp('Done', 1, 51, 0, 0))
        self.runner.finished = True
        self.runner2.finished = True
        self.runner3.finished = True

        exp_standings = '||1. araya: (01:50:00.00)\n2. franchewbacca: (01:51:00.00)\n3. hwangbro: (01:52:00.00)||'
        self.assertEqual(exp_standings, self.runner_set.standings(True))

    def test_overall_standings_list_same_split(self):
        self.runner.add_split(self.nido_split, Timestamp('Nido', 0, 6, 50, 0))
        self.runner2.add_split(self.nido_split, Timestamp('Nido', 0, 7, 0, 0))
        self.runner3.add_split(self.nido_split, Timestamp('Nido', 0, 7, 30, 0))
        exp_standings = [
            '1. hwangbro: (Nidoran 06:50.00)',
            '2. araya: (Nidoran 07:00.00)',
            '3. franchewbacca: (Nidoran 07:30.00)'
        ]
        self.assertEqual(self.runner_set.overall_standings_list(), exp_standings)

    def test_overall_standings_list_different_splits(self):
        self.runner.add_split(self.nido_split, Timestamp('Nido', 0, 6, 50, 0))
        self.runner2.add_split(self.splits['Brock'], Timestamp('Brock', 0, 11, 50, 0))
        self.runner3.add_split(self.splits['Misty'], Timestamp('Misty', 0, 38, 0, 0))
        exp_standings = [
            '1. franchewbacca: (Misty 38:00.00)',
            '2. araya: (Brock 11:50.00)',
            '3. hwangbro: (Nidoran 06:50.00)'
        ]
        self.assertEqual(self.runner_set.overall_standings_list(), exp_standings)

    def test_overall_standings_list_one_ff(self):
        self.runner.add_split(self.nido_split, Timestamp('Nido', 0, 6, 50, 0))
        self.runner2.add_split(self.splits['Brock'], Timestamp('Brock', 0, 11, 50, 0))
        self.runner3.update_status('Forfeit')
        exp_standings = [
            '1. araya: (Brock 11:50.00)',
            '2. hwangbro: (Nidoran 06:50.00)',
            'N/A. franchewbacca: (Forfeit)'
        ]

        self.assertEqual(self.runner_set.overall_standings_list(), exp_standings)

    def test_overall_standings_list_one_ff_one_none(self):
        self.runner2.add_split(self.splits['Brock'], Timestamp('Brock', 0, 11, 50, 0))
        self.runner3.update_status('Forfeit')
        exp_standings = [
            '1. araya: (Brock 11:50.00)',
            '2. hwangbro: (N/A)',
            'N/A. franchewbacca: (Forfeit)'
        ]

        self.assertEqual(self.runner_set.overall_standings_list(), exp_standings)

    def test_overall_standings_list_all_finished(self):
        self.runner.add_split(self.done_split, Timestamp('Done', 1, 52, 0, 0))
        self.runner2.add_split(self.done_split, Timestamp('Done', 1, 50, 0, 0))
        self.runner3.add_split(self.done_split, Timestamp('Done', 1, 51, 0, 0))
        self.runner.finished = True
        self.runner2.finished = True
        self.runner3.finished = True

        exp_standings = [
            '1. araya: (01:50:00.00)',
            '2. franchewbacca: (01:51:00.00)',
            '3. hwangbro: (01:52:00.00)'
        ]

        self.assertEqual(self.runner_set.overall_standings_list(True), exp_standings)

    def test_overall_standings_list_one_unfinished(self):
        self.runner.add_split(self.done_split, Timestamp('Done', 1, 52, 0, 0))
        self.runner2.add_split(self.done_split, Timestamp('Done', 1, 50, 0, 0))
        self.runner3.add_split(self.nido_split, Timestamp('Nido', 7, 51, 0, 0))
        self.runner.finished = True
        self.runner2.finished = True

        exp_standings = [
            '1. araya: (01:50:00.00)',
            '2. hwangbro: (01:52:00.00)',
            'N/A. franchewbacca: (N/A)'
        ]

        self.assertEqual(self.runner_set.overall_standings_list(True), exp_standings)

    def test_overall_standings_finished_comments(self):
        self.runner.add_split(self.done_split, Timestamp('Done', 1, 52, 0, 0))
        self.runner2.add_split(self.done_split, Timestamp('Done', 1, 50, 0, 0))
        self.runner3.add_split(self.done_split, Timestamp('Done', 1, 51, 0, 0))
        self.runner.finished = True
        self.runner2.finished = True
        self.runner3.finished = True
        self.runner.message = 'Unlucky'
        self.runner2.message = 'Always lucky'
        self.runner3.message = 'Time save for next run'

        exp_standings = [
            '1. araya: (01:50:00.00) (Always lucky)',
            '2. franchewbacca: (01:51:00.00) (Time save for next run)',
            '3. hwangbro: (01:52:00.00) (Unlucky)'
        ]

        self.assertEqual(self.runner_set.overall_standings_list(True, True), exp_standings)

    def test_split_standings_normal(self):
        self.runner.add_split(self.nido_split, Timestamp('Nido', 0, 6, 50, 0))
        self.runner2.add_split(self.nido_split, Timestamp('Nido', 0, 7, 0, 0))
        self.runner3.add_split(self.nido_split, Timestamp('Nido', 0, 7, 30, 0))
        exp_standings = 'Nidoran split standings:'
        exp_standings += ' 1. hwangbro - 06:50.00.'
        exp_standings += ' 2. araya - 07:00.00.'
        exp_standings += ' 3. franchewbacca - 07:30.00.'

        self.assertEqual(self.runner_set.split_standings(self.nido_split, self.runner_set), exp_standings)

    def test_split_standings_missing_one(self):
        self.runner.add_split(self.nido_split, Timestamp('Nido', 0, 6, 50, 0))
        self.runner2.add_split(self.nido_split, Timestamp('Nido', 0, 7, 0, 0))
        exp_standings = 'Nidoran split standings:'
        exp_standings += ' 1. hwangbro - 06:50.00.'
        exp_standings += ' 2. araya - 07:00.00.'

        self.assertEqual(self.runner_set.split_standings(self.nido_split, self.runner_set), exp_standings)

    def test_split_standings_one_ff(self):
        self.runner.add_split(self.nido_split, Timestamp('Nido', 0, 6, 50, 0))
        self.runner2.add_split(self.nido_split, Timestamp('Nido', 0, 7, 0, 0))
        self.runner3.update_status('Forfeit')
        exp_standings = 'Nidoran split standings:'
        exp_standings += ' 1. hwangbro - 06:50.00.'
        exp_standings += ' 2. araya - 07:00.00.'
        exp_standings += ' N/A. franchewbacca - Forfeit.'

        self.assertEqual(self.runner_set.split_standings(self.nido_split, self.runner_set), exp_standings)

if __name__ == '__main__':
    unittest.main()
