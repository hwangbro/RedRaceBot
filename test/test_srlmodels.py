import unittest
from srlmodels import SRLRace


class TestSRLModels(unittest.TestCase):
    def test_basic_parse(self):
        race_dict = {'id': 'q7bsl', 'game': {'id': 6, 'name': 'Pokémon Red/Blue', 'abbrev': 'pkmnredblue', 'popularity': 382.0, 'popularityrank': 5}, 'goal': 'any% glitchless no it', 'time': 1624728151, 'state': 3, 'statetext': 'In Progress', 'filename': '', 'numentrants': 4, 'entrants': {'vidgmaddiict': {'displayname': 'vidgmaddiict', 'place': 1, 'time': 6945, 'message': '', 'statetext': 'Finished', 'twitch': '', 'trueskill': '583'}, 'Yujito': {'displayname': 'Yujito', 'place': 2, 'time': 6946, 'message': '', 'statetext': 'Finished', 'twitch': 'yujitoo', 'trueskill': '434'}, 'Abdalain': {'displayname': 'Abdalain', 'place': 9994, 'time': -3, 'message': '', 'statetext': 'Ready', 'twitch': 'abdalain', 'trueskill': '575'}, 'Sidosh': {'displayname': 'Sidosh', 'place': 9998, 'time': -1, 'message': 'PC fucking restarted by itself, so I desperately tried to die cause I was so pissed that I became personal. Sry for any insults', 'statetext': 'Forfeit', 'twitch': 'sidosh', 'trueskill': '511'}}}
        race = SRLRace(**race_dict)

        self.assertEqual(race.id, 'q7bsl')
        self.assertEqual(race.game.id, 6)
        self.assertEqual(race.game.abbrev, 'pkmnredblue')
        self.assertEqual(race.goal, 'any% glitchless no it')
        self.assertEqual(len(race.entrants), 4)
        self.assertEqual(race.entrants['Sidosh'].statetext, 'Forfeit')

        self.assertEqual(race.summary_str(), 'Pokémon Red/Blue Race - any% glitchless no it, with 4 racers: vidgmaddiict, Yujito, Abdalain, Sidosh. Status: In Progress')

if __name__ == '__main__':
    unittest.main()
