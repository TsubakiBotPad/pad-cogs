import json
import re
from collections import defaultdict
from typing import Set, List, Tuple, Optional, Mapping, Union, Iterable, Any

from Levenshtein import jaro_winkler
from tsutils import rmdiacritics

from dadguide.find_monster_tokens import Token, SPECIAL_TOKEN_TYPES
from dadguide.models.monster_model import MonsterModel

SERIES_TYPE_PRIORITY = {
    "regular": 4,
    "event": 4,
    "seasonal": 3,
    "ghcollab": 2,
    "collab": 1,
    "lowpriority": 0,
    None: 0
}


class MonsterMatch:
    def __init__(self, score=0, name=None, mod=None):
        self.score = score
        if name is None:
            self.name = set()
        if mod is None:
            self.mod = set()

    def __repr__(self):
        return str((self.score, [t[0] for t in self.name], [t[0] for t in self.mod]))


MatchMap = Mapping[MonsterModel, MonsterMatch]


class FindMonster:
    MODIFIER_JW_DISTANCE = .95
    TOKEN_JW_DISTANCE = .8

    def __init__(self, dgcog, flags: Mapping[str, Any]):
        self.dgcog = dgcog
        self.flags = flags

    def _merge_multi_word_tokens(self, tokens: List[str]) -> List[str]:
        result = []
        skip = 0
        multi_word_tokens_sorted = sorted(self.dgcog.index.multi_word_tokens,
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
                            or self.calc_ratio_modifier(tokens[c1 + c2], token2) < self.TOKEN_JW_DISTANCE:
                        break
                else:
                    skip = len(mwt) - 1
                    result.append("".join(mwt))
                    break
            else:
                result.append(token1)
        return result

    def _monster_has_modifier(self, monster: MonsterModel, token: Token, matches: MatchMap) -> bool:
        if not token.matches(monster):
            return False

        if len(token.value) < 6:
            if token.value in self.dgcog.index.modifiers[monster]:
                matches[monster].mod.add((token.value, token.value))
                matches[monster].score += 1
                return True
        else:
            closest = max(self.dgcog.index.modifiers[monster], key=lambda m: self.calc_ratio_modifier(token, m))
            ratio = self.calc_ratio_modifier(closest, token.value)
            if ratio > self.MODIFIER_JW_DISTANCE:
                matches[monster].mod.add((token.value, closest))
                matches[monster].score += ratio
                return True
        return False

    def _string_to_token(self, value: str) -> Token:
        if (negated := value.startswith('-')):
            value = value.lstrip('-')
        if (exact := bool(re.fullmatch(r'".+"', value))):
            value = value[1:-1]
        if re.fullmatch(r'.+-.+', value):
            for special in SPECIAL_TOKEN_TYPES:
                if re.fullmatch(special.RE_MATCH, value):
                    return special(value, negated=negated, exact=exact, database=self.dgcog.database)
        return Token(value, negated=negated, exact=exact)

    def _interpret_query(self, tokenized_query: List[str]) -> Tuple[Set[Token], Set[Token]]:
        modifiers = []
        name = set()
        longmods = [p for p in self.dgcog.index.all_modifiers if len(p) > 8]
        lastmodpos = False

        # Suffixes
        for i, value in enumerate(tokenized_query[::-1]):
            token = self._string_to_token(value)

            if any(self.calc_ratio_modifier(m, token.value.split('-')[0], .1) > self.MODIFIER_JW_DISTANCE
                   for m in self.dgcog.index.suffixes):
                # TODO: Store this as a list of regexes.  Don't split on '-' anymore.
                modifiers.append(token)
            else:
                if i != 0:
                    tokenized_query = tokenized_query[:-i]
                break

        # Prefixes
        for i, value in enumerate(tokenized_query):
            token = self._string_to_token(value)

            if token.value in self.dgcog.index.all_modifiers or (
                    any(self.calc_ratio_modifier(token, m, .1) > self.MODIFIER_JW_DISTANCE for m in longmods)
                    and token.value not in self.dgcog.index.all_name_tokens
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
            name.add(self._string_to_token(value))

        # Allow modifiers to match as name tokens if they're alone (Fix for hel and cloud)
        if not name and modifiers and lastmodpos:
            if self.dgcog.index.manual[modifiers[-1].full_value]:
                name.add(modifiers[-1])
                modifiers = modifiers[:-1]

        return set(modifiers), name

    def _process_name_tokens(self, name_query_tokens: Set[Token], matches: MatchMap) -> Optional[Set[MonsterModel]]:
        matched_mons = None

        for name_token in name_query_tokens:
            if name_token.negated:
                invalid = self._get_valid_monsters_from_name_token(name_token, matches, mult=-10)
                if matched_mons is not None:
                    matched_mons.difference_update(invalid)
                else:
                    matched_mons = set(self.dgcog.database.get_all_monsters()).difference(invalid)
            else:
                valid = self._get_valid_monsters_from_name_token(name_token, matches)
                if matched_mons is not None:
                    matched_mons.intersection_update(valid)
                else:
                    matched_mons = valid

        return matched_mons

    def _get_valid_monsters_from_name_token(self, token: Token, matches: MatchMap,
                                            mult: Union[int, float] = 1) -> Set[MonsterModel]:
        valid_monsters = set()
        all_monsters_name_tokens_scores = {nt: self.calc_ratio_name(token, nt) for nt in
                                           self.dgcog.index.all_name_tokens}
        matched_tokens = sorted((nt for nt, s in all_monsters_name_tokens_scores.items() if s > self.TOKEN_JW_DISTANCE),
                                key=lambda nt: all_monsters_name_tokens_scores[nt], reverse=True)
        matched_tokens += [t for t in self.dgcog.index.all_name_tokens if t.startswith(token.value)]
        for match in matched_tokens:
            score = all_monsters_name_tokens_scores[match]
            for matched_monster in self.dgcog.index.manual[match]:
                if matched_monster not in valid_monsters and token.matches(matched_monster):
                    matches[matched_monster].name.add((token.value, match, '(manual)'))
                    matches[matched_monster].score += (score + .001) * mult
                    valid_monsters.add(matched_monster)
            for matched_monster in self.dgcog.index.name_tokens[match]:
                if matched_monster not in valid_monsters and token.matches(matched_monster):
                    matches[matched_monster].name.add((token.value, match, '(name)'))
                    matches[matched_monster].score += score * mult
                    valid_monsters.add(matched_monster)
            for matched_monster in self.dgcog.index.fluff_tokens[match]:
                if matched_monster not in valid_monsters and token.matches(matched_monster):
                    matches[matched_monster].name.add((token.value, match, '(fluff)'))
                    matches[matched_monster].score += score * mult / 2
                    valid_monsters.add(matched_monster)

        return valid_monsters

    def _process_modifiers(self, mod_tokens: Set[Token], potential_evos: Set[MonsterModel],
                           matches: MatchMap) -> Set[MonsterModel]:
        for mod_token in mod_tokens:
            potential_evos = {m for m in potential_evos if
                              self._monster_has_modifier(m, mod_token, matches) ^ mod_token.negated}
            if not potential_evos:
                return set()
        return potential_evos

    def get_priority_tuple(self, monster: MonsterModel, tokenized_query: List[str] = None,
                           matches: MatchMap = None) -> Tuple[Any, ...]:
        """Get the priority tuple for a monster.  
        
        This is a comparable tuple that's used to sort how well a monster matches a query.
        """
        if matches is None:
            matches = defaultdict(MonsterMatch)
        if tokenized_query is None:
            tokenized_query = []

        return (matches[monster].score,
                not self.dgcog.database.graph.monster_is_evo_gem(monster),
                # Don't deprio evos with new modifier
                not monster.is_equip if not {m[0] for m in matches[monster].mod}.intersection(
                    {'new', 'base'}) else True,
                # Match na on id overlap
                bool(monster.monster_id > 10000 and re.search(r"\d{4}", " ".join(tokenized_query))),
                SERIES_TYPE_PRIORITY.get(monster.series.series_type),
                monster.on_na if monster.series.series_type == "collab" else True,
                self.dgcog.database.graph.monster_is_rem_evo(monster),
                not all(t.value in [0, 12, 14, 15] for t in monster.types),
                not any(t.value in [0, 12, 14, 15] for t in monster.types),
                -self.dgcog.database.graph.get_base_id(monster),
                monster.on_na if self.flags['na_prio'] else True,
                not monster.is_equip,
                monster.rarity,
                monster.monster_no_na)

    def _get_monster_evos(self, matched_mons: Set[MonsterModel], matches: MatchMap) -> Set[MonsterModel]:
        monster_evos = set()
        for monster in sorted(matched_mons, key=lambda m: matches[m].score, reverse=True):
            for evo in self.dgcog.database.graph.get_alt_monsters(monster):
                monster_evos.add(evo)
                if matches[evo].score < matches[monster].score:
                    matches[evo].name = {(t[0], t[1],
                                          f'(from evo {monster.monster_id})') for t in matches[monster].name}
                    matches[evo].score = matches[monster].score - .003

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
        mod_tokens, name_query_tokens = self._interpret_query(tokenized_query)

        name_query_tokens.difference_update({'|'})

        for mod_token in mod_tokens:
            if mod_token.value not in self.dgcog.index.all_modifiers:
                async with self.dgcog.config.typo_mods() as typo_mods:
                    typo_mods.append(mod_token.value)

        matches = defaultdict(MonsterMatch)
        if name_query_tokens:
            matched_mons = self._process_name_tokens(name_query_tokens, matches)
            if not matched_mons:
                # No monsters match the given name tokens
                return None, {}, set()
            matched_mons = self._get_monster_evos(matched_mons, matches)
        else:
            # There are no name tokens in the query
            matched_mons = {*self.dgcog.database.get_all_monsters()}
            monster_score = defaultdict(int)

        # Expand search to the evo tree
        matched_mons = self._process_modifiers(mod_tokens, matched_mons, matches)
        if not matched_mons:
            # no modifiers match any monster in the evo tree
            return None, {}, set()

        # Return most likely candidate based on query.
        mon = self.get_most_eligable_monster(matched_mons, tokenized_query, matches)

        return mon, matches, matched_mons

    async def find_monster_debug(self, query: str) -> \
            Tuple[Optional[MonsterModel], MatchMap, Set[MonsterModel], int]:
        """Get debug info from a search.

        This gives info that isn't necessary for non-debug functions.  Consider using
        findmonster or findmonsters instead."""
        await self.dgcog.wait_until_ready()

        query = rmdiacritics(query).lower().replace(",", "")
        tokenized_query = query.split()
        mw_tokenized_query = self._merge_multi_word_tokens(tokenized_query)

        best_monster, matches_dict, valid_monsters = max(
            await self._find_monster_search(tokenized_query),
            await self._find_monster_search(mw_tokenized_query)
            if tokenized_query != mw_tokenized_query else (None, {}, set()),

            key=lambda t: t[1].get(t[0], MonsterMatch()).score
        )

        self.dgcog.historic_lookups[query] = best_monster.monster_id if best_monster else -1
        json.dump(self.dgcog.historic_lookups, open(self.dgcog.historic_lookups_file_path, "w+"))

        return best_monster, matches_dict, valid_monsters, 0

    async def find_monster(self, query: str) -> Optional[MonsterModel]:
        """Get the best matching monster for a query.  Returns None if no eligable monsters exist."""
        matched_monster, _, _, _ = await self.find_monster_debug(query)
        return matched_monster

    async def find_monsters(self, query: str) -> List[MonsterModel]:
        """Get a list of monsters sorted by how well they match"""
        _, matches, monsters, _ = await self.find_monster_debug(query)
        return sorted(monsters, key=lambda m: self.get_priority_tuple(m, matches=matches), reverse=True)

    def calc_ratio_modifier(self, s1: Union[Token, str], s2: str, prefix_weight: float = .05) -> float:
        """Calculate the modifier distance between two tokens"""
        if isinstance(s1, Token):
            if s1.exact:
                return 1.0 if s1.value == s2 else 0.0
            s1 = s1.value

        return jaro_winkler(s1, s2, prefix_weight)

    def calc_ratio_name(self, token: Union[Token, str], full_word: str, prefix_weight: float = .05) -> float:
        """Calculate the name distance between two tokens"""
        string = token.value if isinstance(token, Token) else token

        mw = self.dgcog.index.mwt_to_len[full_word] != 1
        jw = jaro_winkler(string, full_word, prefix_weight)

        if isinstance(token, Token) and token.exact and string != full_word:
            return 0.0

        if string.isdigit() and full_word.isdigit() and string != full_word:
            return 0.0

        if full_word == string:
            score = 1.0
        elif len(string) >= 3 and full_word.startswith(string):
            score = .995
            if mw and jw < score:
                return score
        else:
            score = jw

        if mw:
            score = score ** 10 * self.dgcog.index.mwt_to_len[full_word]

        return score
