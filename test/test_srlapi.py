import unittest
from unittest import mock
import srlapi

def mocked_request_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, text, status_code):
            self.text = text
            self.status_code = status_code

        def text(self):
            return self.text

    if args[0] == srlapi.all_races_url:
        return MockResponse('{\n"count" : "103",\n"races" :\n[\n{\n"id": "k5ilw", "game": {"id": 6, "name": "Pok\\u00e9mon Red/Blue", "abbrev": "pkmnredblue", "popularity": 805.0, "popularityrank": 1}, "goal": "any% glitchless no it", "time": 1633114882, "state": 3, "statetext": "In Progress", "filename": "", "numentrants": 8, "entrants": {"Araya": {"displayname": "Araya", "place": 9994, "time": -3, "message": "", "statetext": "Ready", "twitch": "arayalol", "trueskill": "980"}, "crafted": {"displayname": "crafted", "place": 9994, "time": -3, "message": "", "statetext": "Ready", "twitch": "craftedite", "trueskill": "920"}, "vidgmaddiict": {"displayname": "vidgmaddiict", "place": 9994, "time": -3, "message": "", "statetext": "Ready", "twitch": "vidgmaddiict", "trueskill": "839"}, "Simple": {"displayname": "Simple", "place": 9994, "time": -3, "message": "", "statetext": "Ready", "twitch": "GoodAtBeingSimple", "trueskill": "802"}, "Grogir": {"displayname": "Grogir", "place": 9994, "time": -3, "message": "", "statetext": "Ready", "twitch": "grogir", "trueskill": "759"}, "kchill333": {"displayname": "kchill333", "place": 9994, "time": -3, "message": "", "statetext": "Ready", "twitch": "kchill333", "trueskill": "648"}, "Abdalain": {"displayname": "Abdalain", "place": 9994, "time": -3, "message": "", "statetext": "Ready", "twitch": "abdalain", "trueskill": "625"}, "Xminiblinder": {"displayname": "Xminiblinder", "place": 9994, "time": -3, "message": "", "statetext": "Ready", "twitch": "Xminiblinder", "trueskill": "582"}}},{"id": "354c1", "game": {"id": 5730, "name": "Hyperdimension Neptunia Re;Birth2: Sisters Generation", "abbrev": "rebirth2", "popularity": 53.0, "popularityrank": 20}, "goal": "NG Conquest Ending", "time": 1632568740, "state": 3, "statetext": "In Progress", "filename": "", "numentrants": 3, "entrants": {"IIvgmII": {"displayname": "IIvgmII", "place": 9994, "time": -3, "message": "", "statetext": "Ready", "twitch": "iivgmii", "trueskill": "754"}, "marenthyu": {"displayname": "marenthyu", "place": 9994, "time": -3, "message": "", "statetext": "Ready", "twitch": "marenthyu", "trueskill": "742"}, "ravspect": {"displayname": "ravspect", "place": 9994, "time": -3, "message": "", "statetext": "Forfeit", "twitch": "ravspect", "trueskill": "88"}}}]}', 200)
    elif args[0] == f'{srlapi.single_race_url}k5ilw':
        return MockResponse('{"id": "k5ilw", "game": {"id": 6, "name": "Pok\\u00e9mon Red/Blue", "abbrev": "pkmnredblue", "popularity": 805.0, "popularityrank": 1}, "goal": "any% glitchless no it", "time": 1633114882, "state": 3, "statetext": "In Progress", "filename": "", "numentrants": 8, "entrants": {"Araya": {"displayname": "Araya", "place": 9994, "time": -3, "message": "", "statetext": "Ready", "twitch": "arayalol", "trueskill": "980"}, "crafted": {"displayname": "crafted", "place": 9994, "time": -3, "message": "", "statetext": "Ready", "twitch": "craftedite", "trueskill": "920"}, "vidgmaddiict": {"displayname": "vidgmaddiict", "place": 9994, "time": -3, "message": "", "statetext": "Ready", "twitch": "vidgmaddiict", "trueskill": "839"}, "Simple": {"displayname": "Simple", "place": 9994, "time": -3, "message": "", "statetext": "Ready", "twitch": "GoodAtBeingSimple", "trueskill": "802"}, "Grogir": {"displayname": "Grogir", "place": 9994, "time": -3, "message": "", "statetext": "Ready", "twitch": "grogir", "trueskill": "759"}, "kchill333": {"displayname": "kchill333", "place": 9994, "time": -3, "message": "", "statetext": "Ready", "twitch": "kchill333", "trueskill": "648"}, "Abdalain": {"displayname": "Abdalain", "place": 9994, "time": -3, "message": "", "statetext": "Ready", "twitch": "abdalain", "trueskill": "625"}, "Xminiblinder": {"displayname": "Xminiblinder", "place": 9994, "time": -3, "message": "", "statetext": "Ready", "twitch": "Xminiblinder", "trueskill": "582"}}}', 200)

    return MockResponse(None, 404)

class TestSRLAPI(unittest.TestCase):
    @mock.patch('requests.get', side_effect=mocked_request_get)
    def test_get_all_races(self, mock_get):
        races = srlapi.get_all_races()
        self.assertTrue(len(races) == 2)
        self.assertTrue('Araya' in races[0].entrants)
        self.assertTrue('ravspect' in races[1].entrants)

    @mock.patch('requests.get', side_effect=mocked_request_get)
    def test_get_single_race(self, mock_get):
        race = srlapi.get_single_race('k5ilw')
        self.assertIsNotNone(race)
        self.assertTrue(race.id, 'k5ilw')

    @mock.patch('requests.get', side_effect=mocked_request_get)
    def test_find_race_with_user(self, mock_get):
        race = srlapi.find_race_with_user('arayalol')
        self.assertIsNotNone(race)

        race_tw = srlapi.find_race_with_user('arayalol')
        self.assertIsNotNone(race_tw)

        race_none = srlapi.find_race_with_user('arayayayaya')
        self.assertIsNone(race_none)

        race_ff = srlapi.find_race_with_user('ravspect')
        self.assertIsNone(race_ff)


if __name__ == '__main__':
    unittest.main()
