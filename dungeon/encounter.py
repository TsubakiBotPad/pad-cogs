import logging

class Encounter(object):
    """Just a container for an encounter, Used for creating an embed later.
    Could make this into a model and use a Graph instead of making calls to database..."""
    def __init__(self, **e):
        # all encounters should have the following:
        self.name_en = e['name_en']
        self.name_jp = e['name_jp']
        self.name_kr = e['name_kr']
        self.encounter_id = e['encounter_id']
        self.level = e['level']
        self.hp = e['hp']
        self.atk = e['atk']
        self.defense = e['defense']

        # Encounters may or may not have the following
        self.groups = e['groups']

