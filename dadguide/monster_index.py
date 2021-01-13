import csv
import difflib
import io
import re

import aiohttp
from redbot.core.utils import AsyncIter
from tsutils import aobject

from .token_mappings import *

SHEETS_PATTERN = 'https://docs.google.com/spreadsheets/d/1EoZJ3w5xsXZ67kmarLE4vfrZSIIIAfj04HXeZVST3eY' \
                 '/pub?gid={}&single=true&output=csv'
NICKNAME_OVERRIDES_SHEET = SHEETS_PATTERN.format('0')
GROUP_TREENAMES_OVERRIDES_SHEET = SHEETS_PATTERN.format('2070615818')
PANTHNAME_OVERRIDES_SHEET = SHEETS_PATTERN.format('959933643')


class MonsterIndex2(aobject):
    async def __ainit__(self, monsters, db):
        self.graph = db.graph

        self.monster_id_to_nickname = defaultdict(set)
        self.monster_id_to_treename = defaultdict(set)
        self.series_id_to_pantheon_nickname = defaultdict(set, {m.series_id: {m.series.name_en.lower().replace(" ", "")}
                                                                for m
                                                                in db.get_all_monsters()})

        self.multi_word_tokens = {tuple(m.series.name_en.lower().split())
                                  for m
                                  in db.get_all_monsters()
                                  if " " in m.series.name_en}

        nickname_data = await sheet_to_reader(NICKNAME_OVERRIDES_SHEET)
        for name, m_id, *data in nickname_data:
            _, i, *_ = data + [None, None]
            if m_id.isdigit() and not i:
                if " " in name:
                    self.multi_word_tokens.add(tuple(name.lower().split(" ")))
                self.monster_id_to_nickname[int(m_id)].add(name.lower().replace(" ", ""))

        treenames_data = await sheet_to_reader(GROUP_TREENAMES_OVERRIDES_SHEET)
        for m_id, name, *data in treenames_data:
            _, i, *_ = data + [None, None]
            if m_id.isdigit() and not i:
                if " " in name:
                    self.multi_word_tokens.add(tuple(name.lower().split(" ")))
                self.monster_id_to_treename[int(m_id)].add(name.lower().replace(" ", ""))

        pantheon_data = await sheet_to_reader(PANTHNAME_OVERRIDES_SHEET)
        for name, _, sid, *_ in pantheon_data:
            if sid.isdigit():
                if " " in name:
                    self.multi_word_tokens.add(tuple(name.lower().split(" ")))
                self.series_id_to_pantheon_nickname[int(sid)].add(name.lower().replace(" ", ""))

        self.manual = self.tokens = self.modifiers = defaultdict(set)
        await self._build_monster_index(monsters)
        self.manual = combine_tokens(self.manual_nick, self.manual_tree)
        self.name_tokens = list(self.manual) + list(self.tokens)
        self.all_modifiers = {p for ps in self.modifiers.values() for p in ps}

    __init__ = __ainit__

    async def _build_monster_index(self, monsters):
        self.manual_nick = defaultdict(set)
        self.manual_tree = defaultdict(set)
        self.tokens = defaultdict(set)
        self.modifiers = defaultdict(set)

        async for m in AsyncIter(monsters):
            self.modifiers[m] = await self.get_modifiers(m)

            # ID
            self.tokens[str(m.monster_id)].add(m)
            self.tokens[str(m.monster_id % 10000)].add(m)

            # Name Tokens
            for token in self._name_to_tokens(m.name_en):
                self.tokens[token.lower()].add(m)
                for repl in TOKEN_REPLACEMENTS[token.lower()]:
                    self.tokens[repl].add(m)
                for pas in MODIFIER_MAPS.values():
                    if token in pas:
                        self.modifiers[m].update(pas)

            # Monster Nickname
            for nick in self.monster_id_to_nickname[m.monster_id]:
                self.manual_nick[nick].add(m)

            # Tree Nickname
            base_id = self.graph.get_base_id(m)
            for nick in self.monster_id_to_treename[base_id]:
                self.manual_tree[nick].add(m)

    @staticmethod
    def _name_to_tokens(oname):
        oname = oname.lower()
        name = re.sub(r'[\-+]', ' ', oname)
        name = re.sub(r'[^a-z0-9 ]', '', name)
        return [t.strip() for t in set(name.split() + oname.split()) if t]

    async def get_modifiers(self, m):
        modifiers = set()

        basemon = self.graph.get_base_monster(m)

        # Main Color
        for t in COLOR_MAP[m.attr1]:
            modifiers.add(t)

        # Sub Color
        for t in SUB_COLOR_MAP[m.attr2]:
            modifiers.add(t)
        if m.attr1.value == 6:
            for t in COLOR_MAP[m.attr2]:
                modifiers.add(t)

        # Both Colors
        for t in DUAL_COLOR_MAP[(m.attr1, m.attr2)]:
            modifiers.add(t)

        # Type
        for mt in m.types:
            for t in TYPE_MAP[mt]:
                modifiers.add(t)

        # Series
        if m.series_id in self.series_id_to_pantheon_nickname:
            for t in self.series_id_to_pantheon_nickname[m.series_id]:
                modifiers.add(t)

        # Rarity
        modifiers.add(str(m.rarity) + "*")
        modifiers.add(str(basemon.rarity) + "*b")

        # Base
        if self.graph.monster_is_base(m):
            for t in EVO_MAP[EvoTypes.BASE]:
                modifiers.add(t)

        special_evo = ('覚醒' in m.name_ja or 'awoken' in m.name_en or '転生' in m.name_ja or
                       self.graph.true_evo_type_by_monster(m).value == "Reincarnated" or
                       'reincarnated' in m.name_en or
                       self.graph.true_evo_type_by_monster(m).value == "Super Reincarnated" or
                       m.is_equip or '極醒' in m.name_ja)

        # Evo
        if self.graph.cur_evo_type_by_monster(m).value == 1 and not special_evo:
            for t in EVO_MAP[EvoTypes.EVO]:
                modifiers.add(t)

        # Uvo
        if self.graph.cur_evo_type_by_monster(m).value == 2 and not special_evo:
            for t in EVO_MAP[EvoTypes.UVO]:
                modifiers.add(t)

        # UUvo
        if self.graph.cur_evo_type_by_monster(m).value == 3 and not special_evo:
            for t in EVO_MAP[EvoTypes.UUVO]:
                modifiers.add(t)

        # Transform
        if not self.graph.monster_is_transform_base(m):
            for t in EVO_MAP[EvoTypes.TRANS]:
                modifiers.add(t)

        # Awoken
        if '覚醒' in m.name_ja or 'awoken' in m.name_en.lower():
            for t in EVO_MAP[EvoTypes.AWOKEN]:
                modifiers.add(t)

        # Mega Awoken
        if '極醒' in m.name_ja or 'mega awoken' in m.name_en.lower():
            for t in EVO_MAP[EvoTypes.MEGA]:
                modifiers.add(t)

        # Reincarnated
        if '転生' in m.name_ja or self.graph.true_evo_type_by_monster(m).value == "Reincarnated":
            for t in EVO_MAP[EvoTypes.REVO]:
                modifiers.add(t)

        # Super Reincarnated
        if '超転生' in m.name_ja or self.graph.true_evo_type_by_monster(m).value == "Super Reincarnated":
            for t in EVO_MAP[EvoTypes.SREVO]:
                modifiers.add(t)

        # Pixel
        if (m.name_ja.startswith('ドット') or
                m.name_en.startswith('pixel') or
                self.graph.true_evo_type_by_monster(m).value == "Pixel"):
            for t in EVO_MAP[EvoTypes.PIXEL]:
                modifiers.add(t)
        else:
            for t in EVO_MAP[EvoTypes.NONPIXEL]:
                modifiers.add(t)

        # Awakenings
        for aw in m.awakenings:
            for t in AWOKEN_MAP[Awakenings(aw.awoken_skill_id)]:
                modifiers.add(t)

        # Chibi
        if (m.name_en == m.name_en.lower() and m.name_en != m.name_ja) or \
                'ミニ' in m.name_ja or '(chibi)' in m.name_en:
            for t in MISC_MAP[MiscModifiers.CHIBI]:
                modifiers.add(t)

        # Method of Obtaining
        if self.graph.monster_is_farmable_evo(m) or self.graph.monster_is_mp_evo(m):
            for t in MISC_MAP[MiscModifiers.FARMABLE]:
                modifiers.add(t)

        if self.graph.monster_is_mp_evo(m):
            for t in MISC_MAP[MiscModifiers.MP]:
                modifiers.add(t)

        if self.graph.monster_is_rem_evo(m):
            for t in MISC_MAP[MiscModifiers.REM]:
                modifiers.add(t)

        # Server
        if m.on_jp:
            for t in MISC_MAP[MiscModifiers.INJP]:
                modifiers.add(t)
        if m.on_na:
            for t in MISC_MAP[MiscModifiers.INNA]:
                modifiers.add(t)
        if m.monster_id + 10000 in self.graph.nodes:
            modifiers.add("idjp")
        if m.monster_id > 10000:
            modifiers.add("idna")

        return modifiers


def calc_ratio(s1, s2):
    return difflib.SequenceMatcher(None, s1, s2).ratio()


# TODO: Move this to TSUtils
async def sheet_to_reader(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            file = io.StringIO(await response.text())
    return csv.reader(file, delimiter=',')


def combine_tokens(d1, d2):
    do = defaultdict(set, d1)
    for k, v in d2.items():
        do[k].update(v)
    return do
