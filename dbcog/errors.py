class InvalidGraphState(KeyError):
    pass


class InvalidMonsterId(KeyError):
    def __init__(self, monster_id: int):
        self.monster_id = monster_id

    def __str__(self):
        return '{} is not found in the graph'.format(str(self.monster_id))
