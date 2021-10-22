from peewee import *

db = SqliteDatabase('db/blacklist.db', pragmas={
    'journal_mode': 'wal',
    'cache_size': -1*64000,
    'foreign_keys': 1,
    'ignore_check_constraints': 0,
    'synchronous': 0
})

class BaseModel(Model):
    class Meta:
        database = db

class Blacklist(BaseModel):
    username = CharField(unique=True)

def create_table() -> None:
    db.create_tables([Blacklist])

def add_user(user) -> None:
    '''Adds a user to the blacklist'''
    Blacklist.insert(username = user).on_conflict(action='IGNORE').execute()

def remove_user(user) -> None:
    '''Removes a user from the blacklist'''
    Blacklist.delete().where(Blacklist.username == user).execute()

def check_user(user) -> bool:
    '''Returns true if the specified user is in the blacklist'''
    return bool(Blacklist.get_or_none(Blacklist.username == user))
