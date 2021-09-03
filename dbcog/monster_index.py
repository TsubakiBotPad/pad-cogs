import asyncio
import csv
import io
import logging
import re
from typing import Dict, List

import aiohttp
from redbot.core.utils import AsyncIter
from tsutils.enums import Server
from tsutils.formatting import contains_ja
from tsutils.helper_classes import aobject

from .errors import InvalidGraphState
from .models.monster_model import MonsterModel
from .monster_graph import MonsterGraph
from .models.enum_types import DEFAULT_SERVER
from .token_mappings import *

SHEETS_PATTERN = 'https://docs.google.com/spreadsheets/d/1EoZJ3w5xsXZ67kmarLE4vfrZSIIIAfj04HXeZVST3eY' \
                 '/pub?gid={}&single=true&output=csv'
NICKNAME_OVERRIDES_SHEET = SHEETS_PATTERN.format('0')
GROUP_TREENAMES_OVERRIDES_SHEET = SHEETS_PATTERN.format('2070615818')
PANTHNAME_OVERRIDES_SHEET = SHEETS_PATTERN.format('959933643')
NAME_TOKEN_ALIAS_SHEET = SHEETS_PATTERN.format('1229125459')
MODIFIER_OVERRIDE_SHEET = SHEETS_PATTERN.format('2089525837')
TREE_MODIFIER_OVERRIDE_SHEET = SHEETS_PATTERN.format('1372419168')

logger = logging.getLogger('red.pad-cogs.dbcog.monster_index')


class MonsterIndex(aobject):
    async def __ainit__(self, graph: MonsterGraph, server: Server = DEFAULT_SERVER):
        self.graph = graph
        self.server = server
        monsters = graph.get_all_monsters(server)

        self.issues = []

        self.monster_id_to_nickname = defaultdict(set)
        self.monster_id_to_nametokens = defaultdict(set)
        self.monster_id_to_forcedfluff = defaultdict(set)
        self.monster_id_to_treename = defaultdict(set)
        self.series_id_to_pantheon_nickname = \
            defaultdict(set, {m.series_id: {m.series.name_en.lower().replace(" ", "")}
                              for m in monsters
                              if m.series.name_en.lower() not in PROBLEMATIC_SERIES_TOKENS})

        self.mwtoken_creators = defaultdict(set)

        self.multi_word_tokens = {tuple(m.series.name_en.lower().split())
                                  for m
                                  in monsters
                                  if " " in m.series.name_en.strip()}.union(MULTI_WORD_TOKENS)

        self.replacement_tokens = defaultdict(set)
        self.remove_mods = defaultdict(set)
        self.treename_overrides = set()

        treenames_data, nickname_data, pantheon_data, nt_alias_data, treemod_data, mod_data = await asyncio.gather(
            sheet_to_reader(GROUP_TREENAMES_OVERRIDES_SHEET,
                            ('base_id', 'new_treename', 'normal_prio', 'overrides')),
            sheet_to_reader(NICKNAME_OVERRIDES_SHEET,
                            ('monster_id', 'name_en', 'normal_prio', 'overrides', 'fluff')),
            sheet_to_reader(PANTHNAME_OVERRIDES_SHEET,
                            ('series_id', 'alias')),
            sheet_to_reader(NAME_TOKEN_ALIAS_SHEET,
                            ('tokens', 'alias')),
            sheet_to_reader(TREE_MODIFIER_OVERRIDE_SHEET,
                            ('base_id', 'modifiers')),
            sheet_to_reader(MODIFIER_OVERRIDE_SHEET,
                            ('monster_id', 'modifiers', 'remove')),
        )

        for data in treenames_data:
            if data['base_id'].isdigit():
                mid = int(data['base_id'])
                name = data['new_treename'].strip().lower()
                try:
                    monster = graph.get_monster(mid, server=server)
                except InvalidGraphState:
                    continue
                if not monster:
                    continue
                if data['overrides']:
                    for evomid in self.graph.get_alt_ids(self.graph.get_monster(mid, server=server)):
                        self.treename_overrides.add(evomid)
                if data['normal_prio']:
                    for evomid in self.graph.get_alt_ids(self.graph.get_monster(mid, server=server)):
                        self.monster_id_to_nametokens[evomid].update(self._name_to_tokens(name))
                else:
                    if " " in name:
                        self.mwtoken_creators[name.lower().replace(" ", "")].add(graph.get_monster(mid, server=server))
                        self.multi_word_tokens.add(tuple(name.lower().split(" ")))
                    self.monster_id_to_treename[mid].add(name.lower().replace(" ", ""))

        for data in nickname_data:
            if data['monster_id'].isdigit():
                mid = int(data['monster_id'])
                name = data['name_en'].strip().lower()
                try:
                    monster = graph.get_monster(mid, server=server)
                except InvalidGraphState:
                    continue
                if not monster:
                    continue
                if data['fluff']:
                    self.monster_id_to_forcedfluff[mid].update(self._name_to_tokens(name))
                    if data['normal_prio'] or data['overrides']:
                        self.issues.append(f"Invalid sheet settings for nickname `{name}`.")
                    continue
                if data['normal_prio']:
                    self.monster_id_to_nametokens[mid].update(self._name_to_tokens(name))
                if data['overrides']:
                    self.treename_overrides.add(mid)
                else:
                    if " " in name:
                        self.mwtoken_creators[name.lower().replace(" ", "")].add(graph.get_monster(mid, server=server))
                        self.multi_word_tokens.add(tuple(name.lower().split(" ")))
                    self.monster_id_to_nickname[mid].add(name.lower().replace(" ", ""))

        for data in pantheon_data:
            if data['series_id'].isdigit():
                sid = int(data['series_id'])
                name = data['alias'].strip().lower()
                if " " in name:
                    self.multi_word_tokens.add(tuple(name.lower().split(" ")))
                self.series_id_to_pantheon_nickname[sid].add(name.lower().replace(" ", ""))

        for data in nt_alias_data:
            self.replacement_tokens[frozenset(re.split(r'[,\s]+', data['tokens']))].add(data['alias'])

        self.manual_prefixes = defaultdict(set)
        for data in mod_data:
            if data['monster_id'].isdigit():
                mid = int(data['monster_id'])
                try:
                    monster = graph.get_monster(mid, server=server)
                except InvalidGraphState:
                    continue
                if not monster:
                    continue
                for mod in data['modifiers'].split(","):
                    mod = mod.strip().lower()
                    if " " in mod:
                        self.multi_word_tokens.add(tuple(mod.lower().split(" ")))
                    mod = mod.lower().replace(" ", "")
                    if data['remove']:
                        self.remove_mods[mid].update(mod)
                    else:
                        self.manual_prefixes[mid].update(get_modifier_aliases(mod))

        for data in treemod_data:
            if data['base_id'].isdigit() and graph.get_monster(int(data['base_id']), server=server):
                mid = int(data['base_id'])
                for mod in data['modifiers'].split(","):
                    mod = mod.strip().lower()
                    if " " in mod:
                        self.multi_word_tokens.add(tuple(mod.split(" ")))
                    mod = mod.replace(" ", "")
                    aliases = get_modifier_aliases(mod)
                    for evomid in self.graph.get_alt_ids(self.graph.get_monster(mid, server=server)):
                        self.manual_prefixes[evomid].update(aliases)

        self._known_mods = {x for xs in self.series_id_to_pantheon_nickname.values()
                            for x in xs}.union(KNOWN_MODIFIERS)

        self.manual_nick = defaultdict(set)
        self.manual_tree = defaultdict(set)
        self.name_tokens = defaultdict(set)
        self.fluff_tokens = defaultdict(set)
        self.modifiers = defaultdict(set)

        await self._build_monster_index(monsters)

        self.manual = combine_tokens_dicts(self.manual_nick, self.manual_tree)
        self.all_name_tokens = combine_tokens_dicts(self.manual, self.fluff_tokens, self.name_tokens)
        self.all_modifiers = {p for ps in self.modifiers.values() for p in ps}
        self.suffixes = LEGAL_END_TOKENS
        self.mwt_to_len = defaultdict(lambda: 1, {"".join(mw): len(mw) for mw in self.multi_word_tokens})

    __init__ = __ainit__

    async def _build_monster_index(self, monsters):
        async for m in AsyncIter(monsters):
            self.modifiers[m] = await self.get_modifiers(m)

            # ID
            self.manual_nick[str(m.monster_no_na)].add(m)
            if m.monster_id > 10000:
                self.manual_nick[str(m.monster_id)].add(m)
            if m.monster_no_na != m.monster_no_jp:
                self.name_tokens['na' + str(m.monster_no_na)].add(m)
                self.name_tokens['jp' + str(m.monster_no_jp)].add(m)

            # Name Tokens
            nametokens = self._name_to_tokens(m.name_en)
            last_token = m.name_en.split(',')[-1].strip()
            alt_monsters = self.graph.get_alt_monsters(m)
            autotoken = len([me for me in alt_monsters if not me.is_equip]) > 1

            for jpt in m.name_ja.split(" "):
                self.name_tokens[jpt].add(m)

            # Propagate name tokens throughout all evos
            for me in alt_monsters:
                for t in self.monster_id_to_nametokens[me.monster_id]:
                    if t in nametokens:
                        self.add_name_token(self.name_tokens, t, m)
                if me.is_equip or contains_ja(me.name_en):
                    continue
                if last_token != me.name_en.split(',')[-1].strip():
                    autotoken = False

            # Find likely treenames
            treenames = set()
            regexes = [
                r"(?:Awoken|Reincarnated) (.*)",
                r".*, (.*'s Gem)",
            ]
            for me in alt_monsters:
                for r in regexes:
                    match = re.match(r, me.name_en)
                    if match:
                        treenames.add(match.group(1))

            # Add important tokens
            for token in self.monster_id_to_nametokens[m.monster_id]:
                self.add_name_token(self.name_tokens, token, m)
            if m.monster_id in self.treename_overrides:
                pass
            elif autotoken:
                # Add a consistant last token as important token
                for token in self._name_to_tokens(m.name_en.split(',')[-1].strip()):
                    self.add_name_token(self.name_tokens, token, m)
            else:
                # Add name tokens by guessing which ones are important
                for token in self._get_important_tokens(m.name_en, treenames) + self._name_to_tokens(m.roma_subname):
                    self.add_name_token(self.name_tokens, token, m)
                    if m.is_equip:
                        possessives = re.findall(r"(\w+)'s", m.name_en.lower())
                        for mevo in alt_monsters:
                            for token2 in possessives:
                                if token2 in self._name_to_tokens(mevo.name_en.lower()):
                                    self.add_name_token(self.name_tokens, token2, mevo)
                    else:
                        for mevo in alt_monsters:
                            if token in self._name_to_tokens(mevo.name_en):
                                self.add_name_token(self.name_tokens, token, mevo)

                # For equips only, add every name token from every other non-equip monster in the tree.
                # This has the effect of making automated name tokens behave slightly more like treenames
                # as opposed to nicknames, but only when dealing with equips, and is valuable so that we get
                # the moving-through-tree effect with higher priority, but without having to add
                # significantly more complicated logic in the lookup later on.
                # Test case: Mizutsune is a nickname for Dark Aurora, ID 4148. Issue: #614
                if m.is_equip:
                    for mevo in alt_monsters:
                        if not mevo.is_equip:
                            for token2 in self._get_important_tokens(mevo.name_en, treenames):
                                if token2 not in HAZARDOUS_IN_NAME_MODS:
                                    self.add_name_token(self.name_tokens, token2, m)

            # Fluff tokens
            for token in nametokens + list(self.monster_id_to_forcedfluff[m.monster_id]):
                if m in self.name_tokens[token.lower()]:
                    continue
                self.add_name_token(self.fluff_tokens, token, m)

            # Monster Nickname
            for nick in self.monster_id_to_nickname[m.monster_id]:
                self.add_name_token(self.manual_nick, nick, m)

            # Tree Nickname
            base_id = self.graph.get_base_id(m)
            for nick in self.monster_id_to_treename[base_id]:
                self.add_name_token(self.manual_tree, nick, m)

    def add_name_token(self, token_dict, token, m, depth=5):
        if depth <= 0:
            logger.warning(f"Depth exceeded with token {token}.  Aborting.")
            return

        token_dict[token.lower()].add(m)
        if token.lower() in self._known_mods and token.lower() not in HAZARDOUS_IN_NAME_MODS:
            self.modifiers[m].add(token.lower())

        # Replacements
        for ts in (k for k in self.replacement_tokens if token.lower() in k and all(m in token_dict[t] for t in k)):
            for t in self.replacement_tokens[ts]:
                self.add_name_token(token_dict, t, m, depth - 1)

    @staticmethod
    def _name_to_tokens(oname):
        if not oname:
            return []
        oname = oname.lower().replace(',', '')
        name = re.sub(r'[\-+\']', ' ', oname)
        name = re.sub(r'[^a-z0-9 ]', '', name)
        return [t.strip() for t in set(name.split() + oname.split()) if t]

    @classmethod
    def _get_important_tokens(cls, oname, treenames=None):
        if treenames is None:
            treenames = set()

        if contains_ja(oname):
            return list(treenames)

        name = oname.split(", ")
        if len(name) == 1:
            return cls._name_to_tokens(oname)
        *n1, n2 = name
        n1 = ", ".join(n1)
        if treenames.intersection((n1, n2)):
            return [t for n in treenames.intersection((n1, n2)) for t in cls._name_to_tokens(n)]
        elif token_count(n1) == token_count(n2) or max(token_count(n1), token_count(n2)) < 3:
            return cls._name_to_tokens(oname)
        else:
            return cls._name_to_tokens(min(n1, n2, key=token_count))

    async def get_modifiers(self, monster: MonsterModel):
        modifiers = self.manual_prefixes[monster.monster_id].union({'monster'})

        basemon = self.graph.get_base_monster(monster)

        # Main Color
        modifiers.update(COLOR_MAP[monster.attr1])

        # Sub Color
        modifiers.update(SUB_COLOR_MAP[monster.attr2])
        if monster.attr1.value == 6:
            modifiers.update(COLOR_MAP[monster.attr2])

        # Both Colors
        modifiers.update(DUAL_COLOR_MAP[(monster.attr1, monster.attr2)])

        # Type
        for mt in monster.types:
            modifiers.update(TYPE_MAP[mt])

        # Series
        modifiers.add("series" + str(monster.series_id))
        if monster.series_id in self.series_id_to_pantheon_nickname:
            modifiers.update(self.series_id_to_pantheon_nickname[monster.series_id])

        # Rarity
        modifiers.add(str(monster.rarity) + "*")
        modifiers.add(str(basemon.rarity) + "*b")

        # Base
        if self.graph.monster_is_base(monster):
            modifiers.update(EVO_MAP[EvoTypes.BASE])

        special_evo = ('覚醒' in monster.name_ja or 'awoken' in monster.name_en or '転生' in monster.name_ja or
                       self.graph.true_evo_type(monster).value == "Reincarnated" or
                       'reincarnated' in monster.name_en or
                       self.graph.true_evo_type(monster).value == "Super Reincarnated" or
                       monster.is_equip or '極醒' in monster.name_ja)

        # Evo
        self.add_numbered_modifier(monster, modifiers, EVO_MAP[EvoTypes.EVO],
                                   lambda m: (self.graph.monster_is_normal_evo(m)
                                              or self.graph.monster_is_first_evo(m)))

        # Uvo
        self.add_numbered_modifier(monster, modifiers, EVO_MAP[EvoTypes.UVO],
                                   lambda m: (self.graph.monster_is_reversible_evo(m)
                                              and not special_evo))

        # UUvo
        self.add_numbered_modifier(monster, modifiers, EVO_MAP[EvoTypes.UUVO],
                                   self.graph.monster_is_second_ultimate)

        # Transform
        self.add_numbered_modifier(monster, modifiers, EVO_MAP[EvoTypes.TRANS],
                                   lambda m: not self.graph.monster_is_transform_base(m))
        self.add_numbered_modifier(monster, modifiers, EVO_MAP[EvoTypes.BASETRANS],
                                   lambda m: (self.graph.monster_is_transform_base(m)
                                              and self.graph.get_next_transform(m)))

        # Awoken
        self.add_numbered_modifier(monster, modifiers, EVO_MAP[EvoTypes.AWOKEN],
                                   lambda m: '覚醒' in m.name_ja or 'awoken' in m.name_en.lower())

        # Mega Awoken
        self.add_numbered_modifier(monster, modifiers, EVO_MAP[EvoTypes.MEGA],
                                   lambda m: '極醒' in m.name_ja or 'mega awoken' in m.name_en.lower())

        # Reincarnated
        self.add_numbered_modifier(monster, modifiers, EVO_MAP[EvoTypes.REVO],
                                   lambda m: self.graph.true_evo_type(m).value == "Reincarnated")

        # Super Reincarnated
        self.add_numbered_modifier(monster, modifiers, EVO_MAP[EvoTypes.SREVO],
                                   lambda m: self.graph.true_evo_type(m).value == "Super Reincarnated")

        # Pixel
        self.add_numbered_modifier(monster, modifiers, EVO_MAP[EvoTypes.PIXEL],
                                   lambda m: (m.name_ja.startswith('ドット') or m.name_en.startswith('pixel')
                                              or self.graph.true_evo_type(m).value == "Pixel"),
                                   else_mods=EVO_MAP[EvoTypes.NONPIXEL])

        # Awakenings
        for aw in monster.awakenings:
            try:
                modifiers.update(AWOKEN_SKILL_MAP[AwokenSkills(aw.awoken_skill_id)])
            except ValueError:
                logger.warning(f"Invalid awoken skill ID: {aw.awoken_skill_id}")
                self.issues.append(f"Invalid awoken skill ID: {aw.awoken_skill_id}")

        # Numbered Equips
        self.add_numbered_modifier(monster, modifiers, AWOKEN_SKILL_MAP[AwokenSkills.EQUIP],
                                   lambda m: m.is_equip)

        # Chibi
        self.add_numbered_modifier(monster, modifiers, MISC_MAP[MiscModifiers.CHIBI],
                                   lambda m: (m.name_en == m.name_en.lower() and m.name_en != m.name_ja
                                              or 'ミニ' in m.name_ja or '(chibi)' in m.name_en))

        # Series Type
        if monster.series.series_type == 'regular':
            modifiers.update(MISC_MAP[MiscModifiers.REGULAR])
        if monster.series.series_type == 'event':
            modifiers.update(MISC_MAP[MiscModifiers.EVENT])
        if monster.series.series_type == 'seasonal':
            modifiers.update(MISC_MAP[MiscModifiers.SEASONAL])
        if monster.series.series_type in ('collab', 'ghcollab'):
            modifiers.update(MISC_MAP[MiscModifiers.COLLAB])

        # Story
        def is_story(m, do_transform=True):
            if m.series_id == 196 or any(mat.series_id == 196 for mat in self.graph.evo_mats(m)):
                return True
            if do_transform:
                for pt in self.graph.get_transform_monsters(m):
                    if is_story(pt, False):
                        return True
            pe = self.graph.get_prev_evolution(m)
            if pe and is_story(pe):
                return True
            return False

        if is_story(monster):
            modifiers.update(MISC_MAP[MiscModifiers.STORY])

        # New
        if self.graph.monster_is_new(monster):
            modifiers.update(MISC_MAP[MiscModifiers.NEW])

        # Method of Obtaining
        if self.graph.monster_is_farmable_evo(monster) or self.graph.monster_is_mp_evo(monster):
            modifiers.update(MISC_MAP[MiscModifiers.FARMABLE])

        if self.graph.monster_is_rem_evo(monster):
            modifiers.update(MISC_MAP[MiscModifiers.REM])
        else:
            try:
                if self.graph.monster_is_vendor_exchange(monster):
                    modifiers.update(MISC_MAP[MiscModifiers.MEDAL_EXC])
                    if self.graph.monster_is_black_medal_exchange_evo(monster):
                        modifiers.update(MISC_MAP[MiscModifiers.BLACK_MEDAL])
                    if self.graph.monster_is_currently_exchangable_evo(monster, Server.JP):
                        modifiers.update(MISC_MAP[MiscModifiers.CURRENT_EXCHANGE_JP])
                    if self.graph.monster_is_currently_exchangable_evo(monster, Server.NA):
                        modifiers.update(MISC_MAP[MiscModifiers.CURRENT_EXCHANGE_NA])
                    if self.graph.monster_is_currently_exchangable_evo(monster, Server.KR):
                        modifiers.update(MISC_MAP[MiscModifiers.CURRENT_EXCHANGE_KR])
                    if self.graph.monster_is_permanent_exchange_evo(monster):
                        modifiers.update(MISC_MAP[MiscModifiers.PERMANENT_EXCHANGE])
                    else:
                        modifiers.update(MISC_MAP[MiscModifiers.TEMP_EXCHANGE])

            except InvalidGraphState:
                pass
            if self.graph.monster_is_mp_evo(monster):
                modifiers.update(MISC_MAP[MiscModifiers.MP])

        if monster.sell_mp < 100:
            modifiers.update(MISC_MAP[MiscModifiers.TRADEABLE])

        # Art
        if monster.orb_skin_id:
            modifiers.update(MISC_MAP[MiscModifiers.ORBSKIN])
        if monster.has_animation:
            modifiers.update(MISC_MAP[MiscModifiers.ANIMATED])

        # Server
        if monster.on_jp:
            modifiers.update(MISC_MAP[MiscModifiers.INJP])
            if not monster.on_na:
                modifiers.update(MISC_MAP[MiscModifiers.ONLYJP])
        if monster.on_na:
            modifiers.update(MISC_MAP[MiscModifiers.INNA])
            if not monster.on_jp:
                modifiers.update(MISC_MAP[MiscModifiers.ONLYNA])
        if monster.monster_id + 10000 in self.graph.graph_dict[monster.server_priority].nodes:
            modifiers.add("idjp")
        if monster.monster_id > 10000:
            modifiers.add("idna")

        modifiers.difference_update(self.remove_mods[monster.monster_id])

        return modifiers

    def add_numbered_modifier(self, monster, curr_mods, added_mods, condition, *, else_mods=None):
        if condition(monster):
            curr_mods.update(added_mods)
            ms = [m for m in self.graph.get_alt_monsters(monster) if condition(m)]
            if len(ms) > 1:
                curr_mods.update(f'{mod}-{ms.index(monster) + 1}' for mod in added_mods)
        elif else_mods:
            curr_mods.update(else_mods)


async def sheet_to_reader(url, headers) -> List[Dict[str, str]]:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            reader = csv.reader(io.StringIO(await response.text()), delimiter=',')
    next(reader)
    return [dict(zip(headers, line[:len(headers)])) for line in reader]


def copydict(token_dict):
    copy = defaultdict(set)
    for k, v in token_dict.items():
        copy[k] = v.copy()
    return copy


def combine_tokens_dicts(d1, *ds):
    combined = defaultdict(set, d1.copy())
    for d2 in ds:
        for k, v in d2.items():
            combined[k] = combined[k].union(v)
    return combined


def token_count(tstr):
    tstr = re.sub(r"\(.+\)", "", tstr)
    return len(re.split(r'\W+', tstr))


def get_modifier_aliases(mod):
    output = {mod}
    for mods in ALL_TOKEN_DICTS:
        if mod in mods:
            output.update(mods)
    return output
