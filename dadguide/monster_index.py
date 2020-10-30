from token_mappings import *
from collections import defaultdict


class MonsterIndex2:
    def __init__(self, monsters: 'List[DgMonster]', series: 'List[DgSeries]'):
        self.monsters = monsters
        self.series = series
        self.index = defaultdict(set)
        self._build_index()

    def update(self, other: "Mapping[Any, set]"):
        for k,v in other.items:
            self.index[k].update(v)

    def _build_index(self):
        self.index = defaultdict(list)
        self.update(self._build_monster_name_index(self.monsters))
        self.update(self._build_evo_index(self.monsters))
        self.update(self._build_etc_index(self.monsters))
        #self.series_name_index = self._build_series_name_index(self.series)

    def _build_monster_name_index(self, monsters):
        tokens = defaultdict(set)
        for monster in monsters:
            for token in self._name_to_tokens(monster.name_en):
                tokens[token.lower()].add(monster)
        return tokens

    def _build_series_name_index(self, series):
        tokens = set(list)
        for s in series:
            for token in self._name_to_tokens(s.name_en):
                tokens[token.lower()].add(s)
        return tokens

    def _name_to_tokens(self, name):
        name = re.sub(r'[\-+]', ' ', name.lower())
        name = re.sub(r'[^a-z0-9 ]', '', name)
        return [t.strip() for t in name.split() if t]

    def _build_evo_index(self, monsters):
        tokens = defaultdict(list)

        # Base
        # NOTHING HERE.  THIS IS A SPECIAL CASE

        # Evo
        l = {m for m in monsters if m.cur_evo_type.value = 1}
        for t in EVO_PREFIX_MAP[EvoTypes.EVO]:
            tokens[t].update(l)

        # Uvo
        l = {m for m in monsters if m.cur_evo_type.value = 2}
        for t in EVO_PREFIX_MAP[EvoTypes.UVO]:
            tokens[t].update(l)

        # UUvo
        l = {m for m in monsters if m.cur_evo_type.value = 3}
        for t in EVO_PREFIX_MAP[EvoTypes.UUVO]:
            tokens[t].update(l)

        # Transform
        #l = {m for m in monsters if ??????}
        #for t in EVO_PREFIX_MAP[EvoTypes.TRANS]:
        #    tokens[t].update(l)

        # Awoken
        l = {m for m in monsters if '覚醒' in m.name_ja}
        for t in EVO_PREFIX_MAP[EvoTypes.AWOKEN]:
            tokens[t].update(l)

        # Mega Awoken
        l = {m for m in monsters if '極醒' in m.name_ja}
        for t in EVO_PREFIX_MAP[EvoTypes.MEGA]:
            tokens[t].update(l)

        # Reincarnated
        l = {m for m in monsters if '転生' in m.name_ja or m.true_evo_type.value == "Reincarnated"}
        for t in EVO_PREFIX_MAP[EvoTypes.REVO]:
            tokens[t].update(l)

        # Super Reincarnated
        l = {m for m in monsters if '超転生' in m.name_ja or m.true_evo_type.value == "Super Reincarnated"}
        for t in EVO_PREFIX_MAP[EvoTypes.SREVO]:
            tokens[t].update(l)

        # Pixel
        l = {m for m in monsters
                      if m.name_ja.startswith('ドット') or \
                         m.name_en.startswith('pixel') or \
                         m.true_evo_type.value == "Pixel"}
        for t in EVO_PREFIX_MAP[EvoTypes.PIXEL]:
            tokens[t].update(l)

        # Equip
        l = {m for m in monsters if m.is_equip}
        for t in EVO_PREFIX_MAP[EvoTypes.EQUIP]:
            tokens[t].update(l)


        return tokens

    def _build_etc_index(self, monsters):
        tokens = defaultdict(list)

        # Chibi
        l = {m for m in monsters
                    if (m.name_en == lower(m.name_en) and m.name_en != m.name_jp) or \
                       'ミニ' in m.name_ja}
        for t in MISC_PREFIX_MAP[MiscPrefixes.CHIBI]:
            tokens[t].update(l)

        # Farmable
        #l = {m for m in monsters if ?????}
        #for t in MISC_PREFIX_MAP[MiscPrefixes.CHIBI]:
        #    tokens[t].update(l)


        return tokens
