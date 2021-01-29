class EnemySkill(object):
    def __init__(self, id: int, name: str, type: int, idk: str, params):
        self.id = id
        self.name = name
        self.type = type
        self.idk = idk
        self.params = params

    def process(self):
        return "Unknown: [{},{},{},{}]".format(self.id, self.name, self.type, self.params)