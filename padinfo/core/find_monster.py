import json
import re
from collections import defaultdict
from typing import Set, List, Tuple, Optional, TYPE_CHECKING, Mapping

from Levenshtein import jaro_winkler
from tsutils import rmdiacritics

from padinfo.core.historic_lookups import historic_lookups_id3, historic_lookups_file_path_id3
from padinfo.core.padinfo_settings import settings

if TYPE_CHECKING:
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


def calc_ratio_modifier(s1, s2, dist=.05):
    return jaro_winkler(s1, s2, .05)


def calc_ratio_name(token, full_word, index2, factor=.05):
    mw = index2.mwt_to_len[full_word] != 1
    jw = jaro_winkler(token, full_word, factor)

    if full_word == token:
        score = 1
    elif len(token) >= 3 and full_word.startswith(token):
        score = .995
        if mw and jw < score:
            return score
    else:
        score = jw

    if mw:
        score = score ** 10 * index2.mwt_to_len[full_word]

    return score


class FindMonster:
    MODIFIER_JW_DISTANCE = .95
    TOKEN_JW_DISTANCE = .8

    def merge_multi_word_tokens(self, tokens, valid_multi_word_tokens):
        result = []
        skip = 0
        multi_word_tokens_sorted = sorted(valid_multi_word_tokens,
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
                            or calc_ratio_modifier(tokens[c1 + c2], token2) < self.TOKEN_JW_DISTANCE:
                        break
                else:
                    skip = len(mwt) - 1
                    result.append("".join(mwt))
                    break
            else:
                result.append(token1)
        return result

    def _monster_has_token(self, monster, token, matches, monster_mods):
        if len(token) < 6:
            if token in monster_mods:
                matches[monster].mod.add((token, token))
                matches[monster].score += 1
                return True
        else:
            closest = max(monster_mods, key=lambda m: calc_ratio_modifier(m, token))
            ratio = calc_ratio_modifier(closest, token)
            if ratio > self.MODIFIER_JW_DISTANCE:
                matches[monster].mod.add((token, closest))
                matches[monster].score += ratio
                return True
        return False

    def interpret_query(self, tokenized_query: List[str], index2) -> Tuple[Set[str], Set[str], Set[str], Set[str]]:
        modifiers = []
        negative_modifiers = set()
        name = set()
        negative_name = set()
        longmods = [p for p in index2.all_modifiers if len(p) > 8]
        lastmodpos = False

        for i, token in enumerate(tokenized_query[::-1]):
            negated = token.startswith("-")
            token = token.lstrip('-')
            if any(calc_ratio_modifier(m, token, .1) > self.MODIFIER_JW_DISTANCE for m in index2.suffixes):
                if negated:
                    negative_modifiers.add(token)
                else:
                    modifiers.append(token)
            else:
                if i != 0:
                    tokenized_query = tokenized_query[:-i]
                break

        for i, token in enumerate(tokenized_query):
            negated = token.startswith("-")
            token = token.lstrip('-')
            if token in index2.all_modifiers or (
                    any(calc_ratio_modifier(m, token, .1) > self.MODIFIER_JW_DISTANCE for m in longmods)
                    and token not in index2.all_name_tokens
                    and len(token) >= 8):
                if negated:
                    lastmodpos = False
                    negative_modifiers.add(token)
                else:
                    lastmodpos = True
                    modifiers.append(token)
            else:
                tokenized_query = tokenized_query[i:]
                break
        else:
            tokenized_query = []

        for token in tokenized_query:
            negated = token.startswith("-")
            token = token.lstrip('-')
            if negated:
                negative_name.add(token)
            else:
                name.add(token)

        if not (name or negative_name) and modifiers and lastmodpos:
            if index2.manual[modifiers[-1]]:
                name.add(modifiers[-1])
                modifiers = modifiers[:-1]

        return set(modifiers), negative_modifiers, name, negative_name

    def process_name_tokens(self, name_query_tokens, neg_name_tokens, dgcog, matches):
        matched_mons = None

        for pos_name in name_query_tokens:
            valid = self.get_valid_monsters_from_name_token(pos_name, dgcog.index2, matches)
            if matched_mons is not None:
                matched_mons.intersection_update(valid)
            else:
                matched_mons = valid

        for neg_name in neg_name_tokens:
            invalid = self.get_valid_monsters_from_name_token(neg_name, dgcog.index2, matches, mult=-10)
            if matched_mons is not None:
                matched_mons.difference_update(invalid)
            else:
                matched_mons = set(dgcog.database.get_all_monsters()).difference(invalid)

        return matched_mons

    def get_valid_monsters_from_name_token(self, token, index2, matches, mult=1):
        valid_monsters = set()
        matched_tokens = sorted([nt for nt in index2.all_name_tokens
                                 if calc_ratio_name(token, nt, index2) > self.TOKEN_JW_DISTANCE],
                                key=lambda nt: calc_ratio_name(token, nt, index2), reverse=True)
        matched_tokens += [token for token in index2.all_name_tokens if token.startswith(token)]
        for match in matched_tokens:
            score = calc_ratio_name(token, match, index2)
            for matched_monster in index2.manual[match]:
                if matched_monster not in valid_monsters:
                    matches[matched_monster].name.add((token, match, '(manual)'))
                    matches[matched_monster].score += (score + .001) * mult
                    valid_monsters.add(matched_monster)
            for matched_monster in index2.name_tokens[match]:
                if matched_monster not in valid_monsters:
                    matches[matched_monster].name.add((token, match, '(name)'))
                    matches[matched_monster].score += score * mult
                    valid_monsters.add(matched_monster)
            for matched_monster in index2.fluff_tokens[match]:
                if matched_monster not in valid_monsters:
                    matches[matched_monster].name.add((token, match, '(fluff)'))
                    matches[matched_monster].score += score * mult / 2
                    valid_monsters.add(matched_monster)

        return valid_monsters

    def process_modifiers(self, mod_tokens, neg_mod_tokens, potential_evos, matches, monster_mods):
        for pos_mod_token in mod_tokens:
            potential_evos = {m for m in potential_evos if
                              self._monster_has_token(m, pos_mod_token, matches, monster_mods[m])}
            if not potential_evos:
                return None
        for neg_mod_token in neg_mod_tokens:
            potential_evos = {m for m in potential_evos if
                              not self._monster_has_token(m, neg_mod_token, matches, monster_mods[m])}
            if not potential_evos:
                return None

        return potential_evos

    def get_priority_tuple(self, monster, dgcog, tokenized_query=None, matches=None):
        if matches is None:
            matches = defaultdict(MonsterMatch)
        if tokenized_query is None:
            tokenized_query = []
            
        return (matches[monster].score,
                not monster.is_equip,
                # Match na on id overlap
                bool(monster.monster_id > 10000 and re.search(r"\d{4}", " ".join(tokenized_query))),
                SERIES_TYPE_PRIORITY.get(monster.series.series_type),
                monster.on_na if monster.series.series_type == "collab" else 0,
                dgcog.database.graph.monster_is_rem_evo(monster),
                not all(t.value in [0, 12, 14, 15] for t in monster.types),
                not any(t.value in [0, 12, 14, 15] for t in monster.types),
                -dgcog.database.graph.get_base_id(monster),
                monster.rarity,
                monster.monster_no_na)

    def get_most_eligable_monster(self, monsters, dgcog, tokenized_query=None, matches=None):
        if matches is None:
            matches = defaultdict(MonsterMatch)
        if tokenized_query is None:
            tokenized_query = []

        return max(monsters, key=lambda m: self.get_priority_tuple(m, dgcog, tokenized_query, matches))

    def get_monster_evos(self, database, matched_mons, matches):
        monster_evos = set()
        for monster in sorted(matched_mons, key=lambda m: matches[m].score, reverse=True):
            for evo in database.graph.get_alt_monsters(monster):
                monster_evos.add(evo)
                if matches[evo].score < matches[monster].score:
                    matches[evo].name = {(t[0], t[1],
                                          f'(from evo {monster.monster_id})') for t in matches[monster].name}
                    matches[evo].score = matches[monster].score - .003

        return monster_evos


async def findMonster3(dgcog, query) -> Optional["MonsterModel"]:
    matched_monster = await _findMonster3(dgcog, query)

    monster_no = matched_monster.monster_id if matched_monster else -1
    historic_lookups_id3[query] = monster_no
    json.dump(historic_lookups_id3, open(historic_lookups_file_path_id3, "w+"))

    return matched_monster


async def _findMonster3(dgcog, query) -> Optional["MonsterModel"]:
    await dgcog.wait_until_ready()

    query = rmdiacritics(query).lower().replace(",", "")
    tokenized_query = query.split()
    mw_tokenized_query = find_monster.merge_multi_word_tokens(tokenized_query, dgcog.index2.multi_word_tokens)

    return max(
        await find_monster_search(tokenized_query, dgcog),
        await find_monster_search(mw_tokenized_query, dgcog)
        if tokenized_query != mw_tokenized_query else (None, {}),
        key=lambda t: t[1].get(t[0], MonsterMatch()).score
    )[0]


class MonsterMatch:
    def __init__(self, score=0, name=None, mod=None):
        self.score = score
        if name is None:
            self.name = set()
        if mod is None:
            self.mod = set()

    def __repr__(self):
        return str((self.score, [t[0] for t in self.name], [t[0] for t in self.mod]))


async def find_monster_search(tokenized_query, dgcog) -> \
        Tuple[Optional["MonsterModel"], Mapping["MonsterModel", MonsterMatch], Set["MonsterModel"]]:
    mod_tokens, neg_mod_tokens, name_query_tokens, neg_name_tokens = \
        find_monster.interpret_query(tokenized_query, dgcog.index2)

    name_query_tokens.difference_update({'|'})

    for mod_token in mod_tokens.union(neg_mod_tokens):
        if mod_token not in dgcog.index2.all_modifiers:
            settings.add_typo_mod(mod_token)

    # print(mod_tokens, neg_mod_tokens, name_query_tokens, neg_name_tokens)

    matches = defaultdict(MonsterMatch)
    if name_query_tokens or neg_name_tokens:
        matched_mons = find_monster.process_name_tokens(name_query_tokens,
                                                       neg_name_tokens,
                                                       dgcog,
                                                       matches)
        if not matched_mons:
            # No monsters match the given name tokens
            return None, {}, set()
        matched_mons = find_monster.get_monster_evos(dgcog.database, matched_mons, matches)
    else:
        # There are no name tokens in the query
        matched_mons = {*dgcog.database.get_all_monsters()}
        monster_score = defaultdict(int)

    # Expand search to the evo tree
    matched_mons = find_monster.process_modifiers(mod_tokens, neg_mod_tokens, matched_mons, matches,
                                                 dgcog.index2.modifiers)
    if not matched_mons:
        # no modifiers match any monster in the evo tree
        return None, {}, set()

    # print({k: v for k, v in sorted(matches.items(), key=lambda kv: kv[1].score, reverse=True)
    #        if k in matched_mons})

    # Return most likely candidate based on query.
    mon = find_monster.get_most_eligable_monster(matched_mons, dgcog, tokenized_query, matches)

    return mon, matches, matched_mons


find_monster = FindMonster()
