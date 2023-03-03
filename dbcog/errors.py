from sqlite3 import OperationalError


class InvalidGraphState(KeyError):
    pass


class InvalidMonsterId(KeyError):
    def __init__(self, monster_id: int):
        self.monster_id = monster_id

    def __str__(self):
        return '{} is not found in the graph'.format(str(self.monster_id))


class QueryFailure(OperationalError):
    def __str__(self):
        return "query_many failed. Most of the time this is because you need to update pad-cogs, possibly also tsutils. Possibly it's due to a bug in the software or pipeline code."
