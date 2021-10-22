from peewee import *

db = SqliteDatabase('db/races.db', pragmas={
    'journal_mode': 'wal',
    'cache_size': -1*64000,
    'foreign_keys': 1,
    'ignore_check_constraints': 0,
    'synchronous': 0
})

class BaseModel(Model):
    class Meta:
        database = db

class RaceDB(BaseModel):
    race_id = CharField(unique=True)
    finished = BooleanField(default=False)

def create_table() -> None:
    db.create_tables([RaceDB])

def add_race(race) -> None:
    RaceDB.insert(race_id = race).on_conflict(action='IGNORE').execute()

def update_race(race, finished) -> None:
    '''Updates the status of a race in the database'''
    RaceDB.update(finished=finished).where(RaceDB.race_id == race).execute()

def check_race_is_finished(race) -> bool:
    '''Returns true if a specified race in the database is finished'''
    r = RaceDB.get_or_none(RaceDB.race_id == race)
    if r:
        return r.finished
    return False

def delete_race(race) -> None:
    RaceDB.delete().where(RaceDB.race_id == race).execute()

def check_race(race) -> bool:
    '''Returns true if a specified race is in the database

    A race in the database means that it is being tracked,
    or was being tracked at some point in the past
    '''

    return bool(RaceDB.get_or_none(RaceDB.race_id == race))

def delete_all_active_races() -> int:
    '''Deletes all races if they are not finished'''
    rows = RaceDB.delete().where(RaceDB.finished == False).execute()
    return rows
