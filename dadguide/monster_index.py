import csv
import io
import re
from collections import defaultdict

import aiohttp
from redbot.core.utils import AsyncIter
from tsutils import aobject

from .token_mappings import *

SHEETS_PATTERN = 'https://docs.google.com/spreadsheets/d/1EoZJ3w5xsXZ67kmarLE4vfrZSIIIAfj04HXeZVST3eY' \
                 '/pub?gid={}&single=true&output=csv'
NICKNAME_OVERRIDES_SHEET = SHEETS_PATTERN.format('0')
GROUP_TREENAMES_OVERRIDES_SHEET = SHEETS_PATTERN.format('2070615818')
PANTHNAME_OVERRIDES_SHEET = SHEETS_PATTERN.format('959933643')
NAME_TOKEN_ALIAS_SHEET = SHEETS_PATTERN.format('1229125459')


class MonsterIndex2(aobject):
    async def __ainit__(self, monsters, db):
        self.graph = db.graph

        self.monster_id_to_nickname = defaultdict(set)
        self.monster_id_to_nametokens = defaultdict(set)
        self.monster_id_to_treename = defaultdict(set)
        self.series_id_to_pantheon_nickname = defaultdict(set, {m.series_id: {m.series.name_en.lower().replace(" ", "")}
                                                                for m
                                                                in db.get_all_monsters()})

        self.multi_word_tokens = {tuple(m.series.name_en.lower().split())
                                  for m
                                  in db.get_all_monsters()
                                  if " " in m.series.name_en}.union(MULTI_WORD_TOKENS)

        self.replacement_tokens = defaultdict(set)

        nickname_data = await sheet_to_reader(NICKNAME_OVERRIDES_SHEET, 4)
        for m_id, name, lp, i in nickname_data:
            if m_id.isdigit() and not i:
                if lp:
                    self.monster_id_to_nametokens[int(m_id)].update(self._name_to_tokens(name))
                else:
                    if " " in name:
                        self.multi_word_tokens.add(tuple(name.lower().split(" ")))
                    self.monster_id_to_nickname[int(m_id)].add(name.lower().replace(" ", ""))

        treenames_data = await sheet_to_reader(GROUP_TREENAMES_OVERRIDES_SHEET, 4)
        for m_id, name, mp, i in treenames_data:
            if m_id.isdigit() and not i:
                if mp:
                    for em_id in self.graph.get_alt_ids_by_id(int(m_id)):
                        self.monster_id_to_nametokens[em_id].update(self._name_to_tokens(name))
                else:
                    if " " in name:
                        self.multi_word_tokens.add(tuple(name.lower().split(" ")))
                    self.monster_id_to_treename[int(m_id)].add(name.lower().replace(" ", ""))

        pantheon_data = await sheet_to_reader(PANTHNAME_OVERRIDES_SHEET, 2)
        for sid, name in pantheon_data:
            if sid.isdigit():
                if " " in name:
                    self.multi_word_tokens.add(tuple(name.lower().split(" ")))
                self.series_id_to_pantheon_nickname[int(sid)].add(name.lower().replace(" ", ""))

        nt_alias_data = await sheet_to_reader(NAME_TOKEN_ALIAS_SHEET, 2)
        next(nt_alias_data)  # Skip over heading
        for token, alias in nt_alias_data:
            self.replacement_tokens[token].add(alias)

        self._known_mods = {x for xs in self.series_id_to_pantheon_nickname.values()
                            for x in xs}.union(KNOWN_MODIFIERS)

        self.manual = self.name_tokens = self.fluff_tokens = self.modifiers = defaultdict(set)
        await self._build_monster_index(monsters)

        self.manual = combine_tokens_dicts(self.manual_nick, self.manual_tree)
        self.all_name_tokens = list(self.manual) + list(self.fluff_tokens) + list(self.name_tokens)
        self.all_modifiers = {p for ps in self.modifiers.values() for p in ps}
        self.suffixes = LEGAL_END_TOKENS

    __init__ = __ainit__

    async def _build_monster_index(self, monsters):
        self.manual_nick = defaultdict(set)
        self.manual_tree = defaultdict(set)
        self.name_tokens = defaultdict(set)
        self.fluff_tokens = defaultdict(set)
        self.modifiers = defaultdict(set)

        async for m in AsyncIter(monsters):
            self.modifiers[m] = await self.get_modifiers(m)

            # ID
            self.name_tokens[str(m.monster_no_na)].add(m)
            if m.monster_id > 10000:
                self.name_tokens[str(m.monster_id)].add(m)
            if m.monster_no_na != m.monster_no_jp:
                self.name_tokens['na' + str(m.monster_no_na)].add(m)
                self.name_tokens['jp' + str(m.monster_no_jp)].add(m)

            # Name Tokens
            nametokens = self._name_to_tokens(m.name_en) + list(self.monster_id_to_nametokens[m.monster_id])
            last_token = m.name_en.split(',')[-1].strip()
            autotoken = True

            # Propagate name tokens throughout all evos
            for me in self.graph.get_alt_monsters(m):
                if last_token != me.name_en.split(',')[-1].strip():
                    autotoken = False
                for t in self.monster_id_to_nametokens[me.monster_id]:
                    if t in nametokens:
                        self.add_name_token(self.name_tokens, t, m)

            # Add important tokens
            if autotoken:
                # Add a consistant last token as important token
                for token in self._name_to_tokens(m.name_en.split(',')[-1].strip()):
                    self.add_name_token(self.name_tokens, token, m)
            elif not self.monster_id_to_nametokens[m.monster_id]:
                # Add name tokens by guessing which ones are important
                for token in self._get_important_tokens(m.name_en) + self._name_to_tokens(m.roma_subname):
                    self.add_name_token(self.name_tokens, token, m)
                    if m.is_equip:
                        possessives = re.findall(r"(\w+)'s", m.name_en.lower())
                        for mevo in self.graph.get_alt_monsters(m):
                            for token2 in possessives:
                                if token2 in self._name_to_tokens(mevo.name_en.lower()):
                                    self.add_name_token(self.name_tokens, token2, mevo)
                    else:
                        for mevo in self.graph.get_alt_monsters(m):
                            if token in self._name_to_tokens(mevo.name_en):
                                self.add_name_token(self.name_tokens, token, mevo)

                # For equips only, add every name token from every other non-equip monster in the tree.
                # This has the effect of making automated name tokens behave slightly more like treenames
                # as opposed to nicknames, but only when dealing with equips, and is valuable so that we get
                # the moving-through-tree effect with higher priority, but without having to add
                # significantly more complicated logic in the lookup later on.
                # Test case: Mizutsune is a nickname for Dark Aurora, ID 4148. Issue: #614
                if m.is_equip:
                    for mevo in self.graph.get_alt_monsters(m):
                        if not mevo.is_equip:
                            for token2 in self._get_important_tokens(mevo.name_en):
                                self.add_name_token(self.name_tokens, token2, m)

            # Fluff tokens
            for token in nametokens:
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

    @staticmethod
    def _name_to_tokens(oname):
        if not oname:
            return []
        oname = oname.lower()
        name = re.sub(r'[\-+\']', ' ', oname)
        name = re.sub(r'[^a-z0-9 ]', '', name)
        return [t.strip() for t in set(name.split() + oname.split()) if t]

    @classmethod
    def _get_important_tokens(cls, oname):
        name = oname.split(", ")
        if len(name) == 1:
            return cls._name_to_tokens(oname)
        *n1, n2 = name
        n1 = ", ".join(n1)
        if tcount(n1) == tcount(n2) or max(tcount(n1), tcount(n2)) < 3:
            return cls._name_to_tokens(oname)
        else:
            return cls._name_to_tokens(min(n1, n2, key=tcount))

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
        if self.graph.true_evo_type_by_monster(m).value == "Reincarnated":
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

        # Story
        def is_story(m, do_transform=True):
            if m.series_id == 196 or any(mat.series_id == 196 for mat in self.graph.evo_mats_by_monster(m)):
                return True
            if do_transform:
                for pt in self.graph.get_transform_monsters(m):
                    if is_story(pt, False):
                        return True
            pe = self.graph.get_prev_evolution_by_monster(m)
            if pe and is_story(pe):
                return True
            return False
        if is_story(m):
            for t in MISC_MAP[MiscModifiers.STORY]:
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
            if not m.on_na:
                for t in MISC_MAP[MiscModifiers.ONLYJP]:
                    modifiers.add(t)
        if m.on_na:
            for t in MISC_MAP[MiscModifiers.INNA]:
                modifiers.add(t)
            if not m.on_jp:
                for t in MISC_MAP[MiscModifiers.ONLYNA]:
                    modifiers.add(t)
        if m.monster_id + 10000 in self.graph.nodes:
            modifiers.add("idjp")
        if m.monster_id > 10000:
            modifiers.add("idna")

        return modifiers

    def add_name_token(self, token_dict, token, m):
        for t in self.replacement_tokens[token.lower()].union({token.lower()}):
            token_dict[t].add(m)
            if t.lower() in self._known_mods and t.lower() not in HAZARDOUS_IN_NAME_PREFIXES:
                self.modifiers[m].add(t.lower())


# TODO: Move this to TSUtils
async def sheet_to_reader(url, length=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            file = io.StringIO(await response.text())
    if length is None:
        return csv.reader(file, delimiter=',')
    else:
        return ((line + [None] * length)[:length] for line in csv.reader(file, delimiter=','))


def combine_tokens_dicts(d1, *ds):
    combined = defaultdict(set, d1)
    for d2 in ds:
        for k, v in d2.items():
            combined[k].update(v)
    return combined


def tcount(tstr):
    tstr = re.sub(r"[^\w ]", "", tstr)
    tstr = re.sub(r"\(.+\)", "", tstr)
    return len([*filter(None, tstr.split())])
