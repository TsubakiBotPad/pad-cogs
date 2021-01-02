import csv
import io
import re

import aiohttp
from redbot.core.utils import AsyncIter
from tsutils import aobject

from .token_mappings import *

SHEETS_PATTERN = 'https://docs.google.com/spreadsheets/d/1EoZJ3w5xsXZ67kmarLE4vfrZSIIIAfj04HXeZVST3eY' \
                 '/pub?gid={}&single=true&output=csv'
NICKNAME_OVERRIDES_SHEET = SHEETS_PATTERN.format('0')
GROUP_BASENAMES_OVERRIDES_SHEET = SHEETS_PATTERN.format('2070615818')
PANTHNAME_OVERRIDES_SHEET = SHEETS_PATTERN.format('959933643')


class MonsterIndex2(aobject):
    async def __ainit__(self, monsters, db):
        self.manual, self.tokens, self.prefix = await self._build_monster_index(monsters, db.graph)

    __init__ = __ainit__

    async def _build_monster_index(self, monsters, graph):
        manual = defaultdict(set)
        tokens = defaultdict(set)
        prefix = defaultdict(set)

        nicks = await self._sheet_to_reader(NICKNAME_OVERRIDES_SHEET)
        idtonick = defaultdict(set)
        for nick, mid, *_ in nicks:
            if mid.isdigit():
                idtonick[int(mid)].add(nick)
        gnicks = await self._sheet_to_reader(GROUP_BASENAMES_OVERRIDES_SHEET)
        idtognick = defaultdict(set)
        for mid, nick, *_ in gnicks:
            if mid.isdigit():
                idtognick[int(mid)].add(nick)

        async for m in AsyncIter(monsters):
            prefix[m] = self.get_prefixes(m, graph)

            # ID
            tokens[str(m.monster_id)].add(m)

            # Name Tokens
            for token in self._name_to_tokens(m.name_en):
                tokens[token.lower()].add(m)
                for repl in TOKEN_REPLACEMENTS[token.lower()]:
                    tokens[repl].add(m)
                for pm in PREFIX_MAPS:
                    for pas in pm.values():
                        if token in pas:
                            prefix[m].update(pas)

            # Monster Nickname
            for nick in idtonick[m.monster_id]:
                tokens[nick].add(m)
                manual[nick].add(m)

            # Tree Nickname
            base_id = graph.get_base_id(m)
            for nick in idtognick[base_id]:
                tokens[nick].add(m)
                manual[nick].add(m)

        return manual, tokens, prefix

    @staticmethod
    def _name_to_tokens(oname):
        oname = oname.lower()
        name = re.sub(r'[\-+]', ' ', oname)
        name = re.sub(r'[^a-z0-9 ]', '', name)
        return [t.strip() for t in set(name.split() + oname.split()) if t]

    @staticmethod
    async def _sheet_to_reader(url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                file = io.StringIO(await response.text())
        return csv.reader(file, delimiter=',')

    @staticmethod
    def get_prefixes(m, graph):
        prefix = set()

        # Main Color
        for t in COLOR_MAP[m.attr1.value]:
            prefix.add(t)
            prefix.add('main_attr_' + t)

        # Sub Color
        for t in COLOR_MAP[m.attr2.value]:
            prefix.add('sub_attr_' + t)

        # Both Colors
        for t1 in COLOR_MAP[m.attr1.value]:
            for t2 in COLOR_MAP[m.attr2.value]:
                prefix.add(t1 + t2)
                prefix.add(t1 + "/" + t2)

        # Series
        if m.series_id in SERIES_MAP:
            for t in SERIES_MAP[m.series_id]:
                prefix.add(t)

        # Base
        if graph.monster_is_base(m):
            for t in EVO_PREFIX_MAP[EvoTypes.BASE]:
                prefix.add(t)

        special_evo = ('覚醒' in m.name_ja or 'awoken' in m.name_en or
                       '転生' in m.name_ja or graph.true_evo_type_by_monster(m).value == "Reincarnated" or
                       'reincarnated' in m.name_en or graph.true_evo_type_by_monster(m).value == "Super Reincarnated" or
                       m.is_equip or '極醒' in m.name_ja)

        # Evo
        if graph.cur_evo_type_by_monster(m).value == 1 and not special_evo:
            for t in EVO_PREFIX_MAP[EvoTypes.EVO]:
                prefix.add(t)

        # Uvo
        if graph.cur_evo_type_by_monster(m).value == 2 and not special_evo:
            for t in EVO_PREFIX_MAP[EvoTypes.UVO]:
                prefix.add(t)

        # UUvo
        if graph.cur_evo_type_by_monster(m).value == 3 and not special_evo:
            for t in EVO_PREFIX_MAP[EvoTypes.UUVO]:
                prefix.add(t)

        # Transform
        if not graph.monster_is_transform_base(m):
            for t in EVO_PREFIX_MAP[EvoTypes.TRANS]:
                prefix.add(t)

        # Awoken
        if '覚醒' in m.name_ja or 'awoken' in m.name_en.lower():
            for t in EVO_PREFIX_MAP[EvoTypes.AWOKEN]:
                prefix.add(t)

        # Mega Awoken
        if '極醒' in m.name_ja or 'mega awoken' in m.name_en.lower():
            for t in EVO_PREFIX_MAP[EvoTypes.MEGA]:
                prefix.add(t)

        # Reincarnated
        if '転生' in m.name_ja or graph.true_evo_type_by_monster(m).value == "Reincarnated":
            for t in EVO_PREFIX_MAP[EvoTypes.REVO]:
                prefix.add(t)

        # Super Reincarnated
        if '超転生' in m.name_ja or graph.true_evo_type_by_monster(m).value == "Super Reincarnated":
            for t in EVO_PREFIX_MAP[EvoTypes.SREVO]:
                prefix.add(t)

        # Pixel
        if (m.name_ja.startswith('ドット') or
                m.name_en.startswith('pixel') or
                graph.true_evo_type_by_monster(m).value == "Pixel"):
            for t in EVO_PREFIX_MAP[EvoTypes.PIXEL]:
                prefix.add(t)
        else:
            for t in EVO_PREFIX_MAP[EvoTypes.NONPIXEL]:
                prefix.add(t)

        # Equip
        if m.is_equip:
            for t in EVO_PREFIX_MAP[EvoTypes.EQUIP]:
                prefix.add(t)

        # Chibi
        if (m.name_en == m.name_en.lower() and m.name_en != m.name_ja) or 'ミニ' in m.name_ja:
            for t in MISC_PREFIX_MAP[MiscPrefixes.CHIBI]:
                prefix.add(t)
        else:
            for t in MISC_PREFIX_MAP[MiscPrefixes.NONCHIBI]:
                prefix.add(t)

        # Farmable
        if graph.monster_is_farmable_evo(m) or graph.monster_is_mp_evo(m):
            for t in MISC_PREFIX_MAP[MiscPrefixes.FARMABLE]:
                prefix.add(t)

        return prefix
