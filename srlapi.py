import requests
import json
from srlmodels import SRLEntrant, SRLRace, RaceState
import logging
logger = logging.getLogger('main')

all_races_url = 'http://api.speedrunslive.com:81/races'
single_race_url = 'http://api.speedrunslive.com:81/races/'

def get_all_races() -> list[SRLRace]:
    '''Returns all races in srl's API'''

    r = requests.get(all_races_url)
    races = []
    if r.status_code == 200:
        races = json.loads(r.text)['races']
        return [SRLRace(**race) for race in races]

def find_race_with_user(user) -> SRLRace:
    '''Returns the most recent race with a given user'''
    races = get_all_races()
    if not races:
        return

    result = [x for x in races if not racestate_is_finished(x.state)
            and contains_user(x.entrants.values(), user)]

    if result:
        # logger.info(result)
        # return the newest race
        result.sort(key=lambda x: x.time, reverse=True)
        return result[0]

def get_single_race(race_id) -> SRLRace:
    '''Returns a race given an srl race_id'''
    r = requests.get(f'{single_race_url}{race_id}')
    if r.status_code == 200:
        if race := json.loads(r.text):
            return SRLRace(**race)

def racestate_is_finished(state: RaceState) -> bool:
    return state in {RaceState.COMPLETE, RaceState.TERMINATED}

def contains_user(entrants: set[SRLEntrant], user: str) -> bool:
    '''Returns True if the user is in the set and the state is correct'''
    for entrant in entrants:
        if user.lower() in {entrant.twitch, entrant.displayname.lower()}:
            if entrant.statetext in {'Entered', 'Ready'}:
                return True

    return False
