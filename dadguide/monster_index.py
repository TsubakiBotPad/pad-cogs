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
        self.index = await self._build_monster_index(monsters)

    async def _build_monster_index(self, monsters):
        tokens = defaultdict(set)
        nicks = await self._sheet_to_reader(NICKNAME_OVERRIDES_SHEET)
        idtonick = {int(id): nick for nick, id, *_ in nicks if id.isdigit()}
        nicks = await self._sheet_to_reader(GROUP_BASENAMES_OVERRIDES_SHEET)
        idtognick = {int(id): nick for id, nick, *_ in nicks if id.isdigit()}

        async for m in AsyncIter(monsters):
            # Name Tokens
            for token in self._name_to_tokens(m.name_en):
                tokens[token.lower()].add(m)

            # Monster Nickname
            mtokens = idtonick.get(m.monster_id, "").split()
            for t in mtokens:
                tokens[t.lower()].add(m)

            # Group Nickname
            gtokens = idtognick.get(m._base_monster_id, "").split()
            for t in gtokens:
                tokens[t.lower()].add(m)

            # Main Color
            for c in COLOR_MAP:
                if m.attr1.value == c.value:
                    for t in COLOR_MAP[c]:
                        tokens[t].add(m)

            # Sub Color
            for c1 in COLOR_MAP:
                for c2 in COLOR_MAP:
                    if m.attr1.value == c1.value and m.attr2.value == c2.value:
                        for t1 in COLOR_MAP[c1]:
                            for t2 in COLOR_MAP[c2]:
                                tokens[t1+t2].add(m)
                                tokens[t1+"/"+t2].add(m)

            # Series
            for s in SERIES_MAP:
                if m.series_id == s:
                    for t in SERIES_MAP[s]:
                        tokens[t].add(m)

            # Base
            # NOTHING HERE.  THIS IS A SPECIAL CASE

            # Evo
            if m.cur_evo_type.value == 1:
                for t in EVO_PREFIX_MAP[EvoTypes.EVO]:
                    tokens[t].add(m)

            # Uvo
            if m.cur_evo_type.value == 2:
                for t in EVO_PREFIX_MAP[EvoTypes.UVO]:
                    tokens[t].add(m)

            # UUvo
            if m.cur_evo_type.value == 3:
                for t in EVO_PREFIX_MAP[EvoTypes.UUVO]:
                    tokens[t].add(m)

            # Transform
            #if ??????:
            #    for t in EVO_PREFIX_MAP[EvoTypes.TRANS]:
            #        tokens[t].add(m)

            # Awoken
            if '覚醒' in m.name_ja:
                for t in EVO_PREFIX_MAP[EvoTypes.AWOKEN]:
                    tokens[t].add(m)

            # Mega Awoken
            if '極醒' in m.name_ja:
                for t in EVO_PREFIX_MAP[EvoTypes.MEGA]:
                    tokens[t].add(m)

            # Reincarnated
            if '転生' in m.name_ja or m.true_evo_type.value == "Reincarnated":
                for t in EVO_PREFIX_MAP[EvoTypes.REVO]:
                    tokens[t].add(m)

            # Super Reincarnated
            if '超転生' in m.name_ja or m.true_evo_type.value == "Super Reincarnated":
                for t in EVO_PREFIX_MAP[EvoTypes.SREVO]:
                    tokens[t].add(m)

            # Pixel
            if m.name_ja.startswith('ドット') or \
                    m.name_en.startswith('pixel') or \
                    m.true_evo_type.value == "Pixel":
                for t in EVO_PREFIX_MAP[EvoTypes.PIXEL]:
                    tokens[t].add(m)

            # Equip
            if m.is_equip:
                for t in EVO_PREFIX_MAP[EvoTypes.EQUIP]:
                    tokens[t].add(m)

            # Chibi
            if (m.name_en == m.name_en.lower() and m.name_en != m.name_ja) or 'ミニ' in m.name_ja:
                for t in MISC_PREFIX_MAP[MiscPrefixes.CHIBI]:
                    tokens[t].add(m)

            # Farmable
            #if ?????:
            #    for t in MISC_PREFIX_MAP[MiscPrefixes.CHIBI]:
            #        tokens[t].add(m)


        return tokens

    def _name_to_tokens(self, name):
        name = re.sub(r'[\-+]', ' ', name.lower())
        name = re.sub(r'[^a-z0-9 ]', '', name)
        return [t.strip() for t in name.split() if t]

    async def _sheet_to_reader(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                file = io.StringIO(await response.text())
        return csv.reader(file, delimiter=',')
