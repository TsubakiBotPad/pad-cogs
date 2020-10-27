from token_mappings import *
from collections import defaultdict


class MonsterIndex2:
    def __init__(self, monsters: 'List[DgMonster]', series: 'List[DgSeries]'):
        self.monsters = monsters
        self.series = series
        self.index = defaultdict(list)
        self._build_index()

    def _build_index(self):
        self.index = defaultdict(list)
        self.monster_name_index = self._build_monster_name_index(self.monsters)
        self.series_name_index = self._build_series_name_index(self.series)

    def _build_monster_name_index(self, monsters):
        tokens = defaultdict(list)
        for monster in monsters:
            for token in self._name_to_tokens(monster.name_en):
                tokens[token.lower()].append(monster)
        return tokens

    def _build_series_name_index(self, series):
        tokens = defaultdict(list)
        for s in series:
            for token in self._name_to_tokens(s.name_en):
                tokens[token.lower()].append(s)
        return tokens

    def _name_to_tokens(self, name):
        name = re.sub(r'[\-+]', ' ', name.lower())
        name = re.sub(r'[^a-z0-9 ]', '', name)
        return [t.strip() for t in name.split() if t]
