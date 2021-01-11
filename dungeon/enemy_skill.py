import logging

class EnemySkill(object):
    def __init__(self, **es):
        # skills should have the following
        self.name_en = es['name_en']
        self.name_jp = es['name_jp']
        self.name_kr = es['name_kr']
        self.effect_en = es['effect_en']
        self.effect_jp = es['effect_jp']
        self.effect_kr = es['effect_kr']

        # This may or may not exist.
        self.condition: str = es['condition']
        # some other stuff I could add are the processsed effects

