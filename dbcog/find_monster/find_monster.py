import re
from collections import defaultdict
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Set, Tuple, Union

from tsutils.enums import Server
from tsutils.formatting import rmdiacritics
from tsutils.query_settings.query_settings import QuerySettings

from dbcog.find_monster.extra_info import ExtraInfo
from dbcog.find_monster.tokens.find_monster_tokens import EPSILON, MODIFIER_JW_DISTANCE, MatchData, MatchMap, \
    MonsterInfo, MonsterMatch, QueryToken, SpecialToken, \
    TOKEN_JW_DISTANCE, TokenMatch, calc_ratio_modifier, calc_ratio_name, string_to_token
from dbcog.models.monster_model import MonsterModel

SERIES_TYPE_PRIORITY = {
    "regular": 4,
    "event": 4,
    "seasonal": 3,
    "ghcollab": 2,
    "collab": 1,
    "lowpriority": 0,
    None: 0
}


class FindMonster:
    TOKEN_JW_DISTANCE = TOKEN_JW_DISTANCE
    MODIFIER_JW_DISTANCE = MODIFIER_JW_DISTANCE

    def __init__(self, dbcog, flags: Dict[str, Any]):
        self.dbcog = dbcog
        self.flags = flags
        self.index = self.dbcog.indexes[Server(flags['server'])]

    async def _process_settings(self, original_query: str) -> str:
        qs = QuerySettings.extract(self.flags, original_query)

        self.index = await self.dbcog.get_index(qs.server)

        return re.sub(r'\s*(--|—)\w+(:{.+?})?(?:\s+|$)', ' ', original_query)

    def _merge_multi_word_tokens(self, tokens: List[str]) -> List[str]:
        result = []
        skip = 0

        multi_word_tokens_sorted = sorted(self.index.multi_word_tokens,
                                          key=lambda x: (len(x), len(''.join(x))),
                                          reverse=True)
        for c1, token1 in enumerate(tokens):
            if skip:
                skip -= 1
                continue
            for mwt in multi_word_tokens_sorted:
                if len(mwt) > len(tokens) - c1:
                    continue
                for c2, token2 in enumerate(mwt):
                    if (tokens[c1 + c2] != token2 and len(token2) < 5) \
                            or self.calc_ratio_modifier(tokens[c1 + c2], token2) < TOKEN_JW_DISTANCE:
                        break
                else:
                    skip = len(mwt) - 1
                    result.append("".join(tokens[c1:c1 + len(mwt)]))
                    break
            else:
                result.append(token1)
        return result

    async def _monster_has_modifier(self, monster: MonsterModel, token: QueryToken, matches: MatchMap) -> bool:
        score, match = await token.matches(monster, self.index)
        if not score:
            return False ^ token.negated

        matches[monster].score += score
        matches[monster].mod.add(match)
        return True ^ (token.negated and match.match_data.can_negate)

    async def _interpret_query(self, tokenized_query: List[str]) -> Tuple[Set[QueryToken], Set[QueryToken]]:
        modifiers = []
        name = set()
        longmods = [p for p in self.index.all_modifiers if len(p) > 8]
        lastmodpos = False

        # Suffixes
        if len(tokenized_query) > 1:
            for i, value in enumerate(tokenized_query[::-1]):
                token = await string_to_token(value, self.dbcog)

                if any(self.calc_ratio_modifier(m, token.value.split('-')[0], .1) > MODIFIER_JW_DISTANCE
                       for m in self.index.suffixes) or isinstance(token, SpecialToken):
                    # TODO: Store this as a list of regexes.  Don't split on '-' anymore.
                    modifiers.append(token)
                else:
                    if i != 0:
                        tokenized_query = tokenized_query[:-i]
                    break

        # Prefixes
        for i, value in enumerate(tokenized_query):
            token = await string_to_token(value, self.dbcog)

            if isinstance(token, SpecialToken) or token.value in self.index.all_modifiers \
                    or (any(self.calc_ratio_modifier(token, m, .1) > MODIFIER_JW_DISTANCE for m in longmods)
                        and token.value not in self.index.all_name_tokens
                        and len(token.value) >= 8):
                lastmodpos = not token.negated
                modifiers.append(token)
            else:
                tokenized_query = tokenized_query[i:]
                break
        else:
            tokenized_query = []

        # Name Tokens
        for value in tokenized_query:
            name.add(await string_to_token(value, self.dbcog))

        # Allow modifiers to match as name tokens if they're alone (Fix for hel and cloud)
        if not name and modifiers and lastmodpos:
            if self.index.manual[modifiers[-1].value]:
                name.add(modifiers[-1])
                modifiers = modifiers[:-1]

        return set(modifiers), name

    async def _process_name_tokens(self, name_query_tokens: Set[QueryToken], matches: MatchMap) \
            -> Optional[Set[MonsterModel]]:
        matched_mons = None

        for name_token in name_query_tokens:
            if name_token.negated:
                invalid = await self._get_valid_monsters_from_name_token(name_token, matches, mult=-10)
                if matched_mons is not None:
                    matched_mons.difference_update(invalid)
                else:
                    matched_mons = set(self.dbcog.database.get_all_monsters(self.index.server)).difference(invalid)
            else:
                valid = await self._get_valid_monsters_from_name_token(name_token, matches)
                if matched_mons is not None:
                    matched_mons.intersection_update(valid)
                else:
                    matched_mons = valid

        return matched_mons

    async def _get_valid_monsters_from_name_token(self, token: QueryToken, matches: MatchMap,
                                                  mult: Union[int, float] = 1) -> Set[MonsterModel]:
        valid_monsters = set()
        all_monsters_name_tokens_scores = {nt: self.calc_ratio_name(token, nt) for nt in
                                           self.index.all_name_tokens}
        matched_tokens = sorted((nt for nt, s in all_monsters_name_tokens_scores.items() if s > TOKEN_JW_DISTANCE),
                                key=lambda nt: all_monsters_name_tokens_scores[nt], reverse=True)
        matched_tokens += [t for t in self.index.all_name_tokens if t.startswith(token.value)]
        for match in matched_tokens:
            score = all_monsters_name_tokens_scores[match]

            async def do_matching(monsters: Set[MonsterModel], value: float, name_type: str) -> None:
                for matched_monster in monsters:
                    if matched_monster not in valid_monsters and await token.matches(matched_monster, self.index):
                        matches[matched_monster].name.add(
                            TokenMatch(token.value, match, MatchData(token, name_type=name_type)))
                        matches[matched_monster].score += value
                        valid_monsters.add(matched_monster)

            await do_matching(self.index.manual[match], (score + EPSILON) * mult, 'manual')
            await do_matching(self.index.name_tokens[match], score * mult, 'name')
            await do_matching(self.index.fluff_tokens[match], score * mult / 2, 'fluff')

        return valid_monsters

    async def _process_modifiers(self, mod_tokens: Set[QueryToken], potential_evos: Set[MonsterModel],
                                 matches: MatchMap) -> Set[MonsterModel]:
        for mod_token in mod_tokens:
            potential_evos = {m for m in potential_evos if
                              await self._monster_has_modifier(m, mod_token, matches)}
            if not potential_evos:
                return set()
        return potential_evos

    def get_priority_tuple(self, monster: MonsterModel, tokenized_query: List[str] = None, matches: MatchMap = None) \
            -> Tuple[Any, ...]:
        """Get the priority tuple for a monster.

        This is a comparable tuple that's used to sort how well a monster matches a query.
        """
        if matches is None:
            matches = defaultdict(MonsterMatch)
        if tokenized_query is None:
            tokenized_query = []

        or_prio_score = sum(match.match_data.or_index[0]
                            for match in matches[monster].mod
                            if match.match_data.or_index is not None)

        return (matches[monster].score,
                -or_prio_score if self.flags['ormod_prio'] else 0,
                not self.dbcog.database.graph.monster_is_evo_gem(monster),
                # Don't deprio evos with new modifier
                not monster.is_equip if not {m[0] for m in matches[monster].mod}.intersection(
                    {'new', 'base'}) else True,
                # Match na on id overlap
                bool(monster.monster_id > 50000 and re.search(r"\d{4}", " ".join(tokenized_query))),
                SERIES_TYPE_PRIORITY.get(monster.series.series_type),
                monster.on_na if monster.series.series_type == "collab" else True,
                self.dbcog.database.graph.monster_is_rem_evo(monster),
                not all(t.value in [0, 12, 14, 15] for t in monster.types),
                not any(t.value in [0, 12, 14, 15] for t in monster.types),
                -self.dbcog.database.graph.get_base_id(monster),
                monster.on_na if self.flags['na_prio'] else True,
                not monster.is_equip,
                self.dbcog.database.graph.get_adjusted_rarity(monster),
                -or_prio_score,
                monster.monster_no)

    def _get_monster_evos(self, matched_mons: Set[MonsterModel], matches: MatchMap) -> Set[MonsterModel]:
        monster_evos = set()
        for monster in sorted(matched_mons, key=lambda m: matches[m].score, reverse=True):
            for evo in self.dbcog.database.graph.get_alt_monsters(monster):
                monster_evos.add(evo)
                if matches[evo].score < matches[monster].score:
                    matches[evo].name = {
                        TokenMatch(t[0], t[1], MatchData(t.match_data.token, from_evo=monster.monster_id))
                        for t in matches[monster].name}
                    matches[evo].score = matches[monster].score - EPSILON * 3

        return monster_evos

    def get_most_eligable_monster(self, monsters: Iterable[MonsterModel], tokenized_query: List[str] = None,
                                  matches: MatchMap = None) -> MonsterModel:
        """Get the most eligable monster from a list of monsters and debug info from a query"""
        if matches is None:
            matches = defaultdict(MonsterMatch)
        if tokenized_query is None:
            tokenized_query = []

        return max(monsters, key=lambda m: self.get_priority_tuple(m, tokenized_query, matches))

    async def _find_monster_search(self, tokenized_query: List[str]) -> \
            Tuple[Optional[MonsterModel], MatchMap, Set[MonsterModel]]:
        mod_tokens, name_query_tokens = await self._interpret_query(tokenized_query)

        name_query_tokens.difference_update({'|'})

        def merge_dicts(*dicts: Dict[str, Set]) -> DefaultDict[str, Set]:
            o = defaultdict(set)
            for d in dicts:
                for k, vs in d.items():
                    o[k].update(vs)
            return o

        for mod_token in mod_tokens:
            if mod_token.value not in self.index.all_modifiers:
                async with self.dbcog.config.typo_mods() as typo_mods:
                    typo_mods.append(mod_token.value)

        matches = defaultdict(MonsterMatch)
        if name_query_tokens:
            matched_mons = await self._process_name_tokens(name_query_tokens, matches)
            if not matched_mons:
                # No monsters match the given name tokens
                return None, {}, set()
            matched_mons = self._get_monster_evos(matched_mons, matches)
        else:
            # There are no name tokens in the query
            matched_mons = {*self.dbcog.database.get_all_monsters(self.index.server)}
            monster_score = defaultdict(int)

        # Expand search to the evo tree
        matched_mons = await self._process_modifiers(mod_tokens, matched_mons, matches)
        if not matched_mons:
            # no modifiers match any monster in the evo tree
            return None, {}, set()

        # Return most likely candidate based on query.
        mon = self.get_most_eligable_monster(matched_mons, tokenized_query, matches)

        return mon, matches, matched_mons

    async def find_monster_debug(self, query: str) -> Tuple[MonsterInfo, ExtraInfo]:
        """Get debug info from a search.

        This gives info that isn't necessary for non-debug functions.  Consider using
        findmonster or findmonsters instead."""
        await self.dbcog.wait_until_ready()

        query = query.split('//')[0]  # Remove comments
        query = rmdiacritics(query).lower().replace(",", "")
        query = re.sub(r'(\s|^)\'(\S+)\'(\s|$)', r'\1"\2"\3', query)  # Replace ' with " around tokens
        # Keep some spaces
        query = re.sub(r':=?r?("[^"]+"|\'[^\']+\')', lambda m: m.group(0).replace(' ', '\0'), query)
        query = re.sub(r'\[[^[]+]', lambda m: m.group(0).replace(' ', '\0'), query)
        query = re.sub(r'\([^(]+\)', lambda m: m.group(0).replace(' ', '\0'), query)

        tokenized_query = (await self._process_settings(query)).split()
        tokenized_query = [token.replace('\0', ' ') for token in tokenized_query]
        mw_tokenized_query = self._merge_multi_word_tokens(tokenized_query)
        best_monster, matches_dict, valid_monsters = max(
            await self._find_monster_search(tokenized_query),
            await self._find_monster_search(mw_tokenized_query)
            if tokenized_query != mw_tokenized_query else (None, {}, set()),

            key=lambda t: t[1].get(t[0], MonsterMatch()).score
        )

        monster_info = MonsterInfo(best_monster, matches_dict, valid_monsters)
        extra_info = ExtraInfo.build_extra_info(matches_dict)
        return monster_info, extra_info

    async def find_monster(self, query: str) -> Tuple[Optional[MonsterModel], ExtraInfo]:
        """Get the best matching monster for a query.  Returns None if no eligable monsters exist."""
        m_info, e_info = await self.find_monster_debug(query)
        return m_info.matched_monster, e_info

    async def find_monsters(self, query: str) -> Tuple[List[MonsterModel], ExtraInfo]:
        """Get a list of monsters sorted by how well they match"""
        m_info, e_info = await self.find_monster_debug(query)
        return sorted(m_info.valid_monsters,
                      key=lambda m: self.get_priority_tuple(m, matches=m_info.monster_matches),
                      reverse=True), e_info

    def calc_ratio_modifier(self, s1: Union[QueryToken, str], s2: str, prefix_weight: float = .05) -> float:
        return calc_ratio_modifier(s1, s2, prefix_weight)

    def calc_ratio_name(self, token: Union[QueryToken, str], full_word: str, prefix_weight: float = .05) -> float:
        """Calculate the name distance between two tokens"""
        return calc_ratio_name(token, full_word, prefix_weight, self.index)
