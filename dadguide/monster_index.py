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
    async def __init__(self, monsters: 'List[DgMonster]', series: 'List[DgSeries]'):
        self.manual, self.tokens, self.prefix = await self._build_monster_index(monsters)

    async def _build_monster_index(self, monsters):
        manual = defaultdict(set)
        tokens = defaultdict(set)
        prefix = defaultdict(lambda: lambda m: False)

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
            if idtognick.get(m._base_monster_id):
                tokens[idtognick[m._base_monster_id]].add(m)
                manual[idtognick[m._base_monster_id]].add(m)

        # Main Color
        for c in COLOR_MAP:
            for t in COLOR_MAP[c]:
                of = prefix[t]
                prefix[t] = lambda m: m.attr1.value == c or of(m)
                prefix['main_attr_'+t] = lambda m: m.attr1.value == c or of(m)

        # Sub Color
        for c in COLOR_MAP:
            for t in COLOR_MAP[c]:
                of = prefix['sub_attr_'+t]
                prefix['sub_attr_'+t] = lambda m: m.attr2.value == c or of(m)

        # Both Colors
        for c1 in COLOR_MAP:
            for c2 in COLOR_MAP:
                for t1 in COLOR_MAP[c1]:
                    for t2 in COLOR_MAP[c2]:
                        of = prefix[t1+t2]
                        prefix[t1+t2] = lambda m: (m.attr1.value == c1 and m.attr2.value == c2) or of(m)
                        prefix[t1+"/"+t2] = lambda m: (m.attr1.value == c1 and m.attr2.value == c2) or of(m)

        # Series
        for s in SERIES_MAP:
            for t in SERIES_MAP[s]:
                of = prefix[t]
                prefix[t] = lambda m: m.series_id == s or of(m)

        # Base
        # NOTHING HERE.  THIS IS A SPECIAL CASE

        special_evo = lambda m: ('覚醒' in m.name_ja or 'awoken' in m.name_en or
        '転生' in m.name_ja or m.true_evo_type.value == "Reincarnated" or 'reincarnated' in m.name_en or \
        m.true_evo_type.value == "Super Reincarnated" or \
        m.is_equip or '極醒' in m.name_ja)

        # Evo
        for t in EVO_PREFIX_MAP[EvoTypes.EVO]:
            of = prefix[t]
            prefix[t] = lambda m: (m.cur_evo_type.value == 1 and not special_evo(m)) or of(m)

        # Uvo
        for t in EVO_PREFIX_MAP[EvoTypes.UVO]:
            of = prefix[t]
            prefix[t] = lambda m: (m.cur_evo_type.value == 2 and not special_evo(m)) or of(m)

        # UUvo
        for t in EVO_PREFIX_MAP[EvoTypes.UUVO]:
            of = prefix[t]
            prefix[t] = lambda m: (m.cur_evo_type.value == 3 and not special_evo(m)) or of(m)

        # Transform
        # for t in EVO_PREFIX_MAP[EvoTypes.TRANS]:
        #     prefix[t] = lambda m: (???) or of(m)

        # Awoken
        for t in EVO_PREFIX_MAP[EvoTypes.AWOKEN]:
            of = prefix[t]
            prefix[t] = lambda m: ('覚醒' in m.name_ja or 'awoken' in m.name_en.lower()) or of(m)

        # Mega Awoken
        for t in EVO_PREFIX_MAP[EvoTypes.MEGA]:
            of = prefix[t]
            prefix[t] = lambda m: ('極醒' in m.name_ja or 'mega awoken' in m.name_en.lower()) or of(m)

        # Reincarnated
        for t in EVO_PREFIX_MAP[EvoTypes.REVO]:
            of = prefix[t]
            prefix[t] = lambda m: ('転生' in m.name_ja or m.true_evo_type.value == "Reincarnated") or of(m)

        # Super Reincarnated
        for t in EVO_PREFIX_MAP[EvoTypes.SREVO]:
            of = prefix[t]
            prefix[t] = lambda m: ('超転生' in m.name_ja or m.true_evo_type.value == "Super Reincarnated") or of(m)

        # Pixel
        for t in EVO_PREFIX_MAP[EvoTypes.PIXEL]:
            of = prefix[t]
            prefix[t] = lambda m: (m.name_ja.startswith('ドット') or
                    m.name_en.startswith('pixel') or
                    m.true_evo_type.value == "Pixel") or of(m)

        # Equip
        for t in EVO_PREFIX_MAP[EvoTypes.EQUIP]:
            of = prefix[t]
            prefix[t] = lambda m: m.is_equip or of(m)

        # Chibi
        for t in MISC_PREFIX_MAP[MiscPrefixes.CHIBI]:
            of = prefix[t]
            prefix[t] = lambda m: ((m.name_en == m.name_en.lower() and m.name_en != m.name_ja) or 'ミニ' in m.name_ja) or of(m)

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
