import re
import csv
import aiohttp
import io
from collections import defaultdict
from tsutils import aobject
from redbot.core.utils import AsyncIter

from .token_mappings import *

SHEETS_PATTERN = 'https://docs.google.com/spreadsheets/d/1EoZJ3w5xsXZ67kmarLE4vfrZSIIIAfj04HXeZVST3eY/pub?gid={}&single=true&output=csv'
NICKNAME_OVERRIDES_SHEET = SHEETS_PATTERN.format('0')
GROUP_BASENAMES_OVERRIDES_SHEET = SHEETS_PATTERN.format('2070615818')
PANTHNAME_OVERRIDES_SHEET = SHEETS_PATTERN.format('959933643')


class MonsterIndex2(aobject):
    async def __init__(self, monsters: 'List[MonsterModel]', db):
        self.manual, self.tokens, self.prefix = await self._build_monster_index(monsters, db)

    async def _build_monster_index(self, monsters, db):
        manual = defaultdict(set)
        tokens = defaultdict(set)
        prefix = defaultdict(MonsterFilter)

        nicks = await self._sheet_to_reader(NICKNAME_OVERRIDES_SHEET)
        idtonick = {int(id): nick for nick, id, *_ in nicks if id.isdigit()}
        gnicks = await self._sheet_to_reader(GROUP_BASENAMES_OVERRIDES_SHEET)
        idtognick = {int(id): nick for id, nick, *_ in gnicks if id.isdigit()}

        async for m in AsyncIter(monsters):
            # ID
            tokens[str(m.monster_id)].add(m)

            # Name Tokens
            for token in self._name_to_tokens(m.name_en):
                tokens[token.lower()].add(m)
                for repl in TOKEN_REPLACEMENTS[token.lower()]:
                    tokens[repl].add(m)

            # Monster Nickname
            if idtonick.get(m.monster_id):
                tokens[idtonick[m.monster_id]].add(m)
                manual[idtonick[m.monster_id]].add(m)

            # Group Nickname
            base_id = db.graph.get_base_monster_id(m)
            if idtognick.get(base_id):
                tokens[idtognick[base_id]].add(m)
                manual[idtognick[base_id]].add(m)

        # Main Color
        for c in COLOR_MAP:
            for t in COLOR_MAP[c]:
                prefix[t] |= lambda m: m.attr1.value == c
                prefix['main_attr_'+t] |= lambda m: m.attr1.value == c

        # Sub Color
        for c in COLOR_MAP:
            for t in COLOR_MAP[c]:
                prefix['sub_attr_'+t] |= lambda m: m.attr2.value == c

        # Both Colors
        for c1 in COLOR_MAP:
            for c2 in COLOR_MAP:
                for t1 in COLOR_MAP[c1]:
                    for t2 in COLOR_MAP[c2]:
                        prefix[t1+t2] |= lambda m: m.attr1.value == c1 and m.attr2.value == c2
                        prefix[t1+"/"+t2] |= lambda m: m.attr1.value == c1 and m.attr2.value == c2

        # Series
        for s in SERIES_MAP:
            for t in SERIES_MAP[s]:
                prefix[t] |= lambda m: m.series_id == s

        # Base
        # NOTHING HERE.  THIS IS A SPECIAL CASE

        special_evo = lambda m: ('覚醒' in m.name_ja or 'awoken' in m.name_en or
            '転生' in m.name_ja or m.true_evo_type.value == "Reincarnated" or
            'reincarnated' in m.name_en or m.true_evo_type.value == "Super Reincarnated" or
            m.is_equip or '極醒' in m.name_ja)

        # Evo
        for t in EVO_PREFIX_MAP[EvoTypes.EVO]:
            prefix[t] |= lambda m: m.cur_evo_type.value == 1 and not special_evo(m)

        # Uvo
        for t in EVO_PREFIX_MAP[EvoTypes.UVO]:
            prefix[t] |= lambda m: m.cur_evo_type.value == 2 and not special_evo(m)

        # UUvo
        for t in EVO_PREFIX_MAP[EvoTypes.UUVO]:
            prefix[t] = lambda m: m.cur_evo_type.value == 3 and not special_evo(m)

        # Transform
        # for t in EVO_PREFIX_MAP[EvoTypes.TRANS]:
        #     prefix[t] = lambda m: (???)

        # Awoken
        for t in EVO_PREFIX_MAP[EvoTypes.AWOKEN]:
            prefix[t] |= lambda m: '覚醒' in m.name_ja or 'awoken' in m.name_en.lower()

        # Mega Awoken
        for t in EVO_PREFIX_MAP[EvoTypes.MEGA]:
            prefix[t] |= lambda m: '極醒' in m.name_ja or 'mega awoken' in m.name_en.lower()

        # Reincarnated
        for t in EVO_PREFIX_MAP[EvoTypes.REVO]:
            prefix[t] |= lambda m: '転生' in m.name_ja or m.true_evo_type.value == "Reincarnated"

        # Super Reincarnated
        for t in EVO_PREFIX_MAP[EvoTypes.SREVO]:
            prefix[t] |= lambda m: '超転生' in m.name_ja or m.true_evo_type.value == "Super Reincarnated"
        # Pixel
        for t in EVO_PREFIX_MAP[EvoTypes.PIXEL]:
            prefix[t] |= lambda m: (m.name_ja.startswith('ドット') or
                    m.name_en.startswith('pixel') or
                    m.true_evo_type.value == "Pixel")

        # Equip
        for t in EVO_PREFIX_MAP[EvoTypes.EQUIP]:
            prefix[t] |= lambda m: m.is_equip

        # Chibi
        for t in MISC_PREFIX_MAP[MiscPrefixes.CHIBI]:
            prefix[t] |= lambda m: (m.name_en == m.name_en.lower() and m.name_en != m.name_ja) or 'ミニ' in m.name_ja

        # Farmable
        # for t in MISC_PREFIX_MAP[MiscPrefixes.FARMABLE]:
        #    prefix[t].add(lambda x: ???)


        return manual, tokens, prefix

    def _name_to_tokens(self, oname):
        name = re.sub(r'[\-+]', ' ', oname.lower())
        name = re.sub(r'[^a-z0-9 ]', '', name)
        return [t.strip() for t in set(name.split()+oname.split()) if t]

    async def _sheet_to_reader(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                file = io.StringIO(await response.text())
        return csv.reader(file, delimiter=',')


class MonsterFilter:
    def __init__(self, *funcs):
        self.funcs = funcs

    def __or__(self, other):
        if isinstance(other, MonsterFilter):
            return MonsterFilter(*self.funcs, *other.funcs)
        return MonsterFilter(other, *self.funcs)

    def __call__(self, *args, **kwargs):
        for f in self.funcs:
            if f(*args, **kwargs):
                return True
        return False
