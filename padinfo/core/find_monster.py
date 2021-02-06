import json
import re
from collections import defaultdict
from typing import Set, List, Tuple, Optional, TYPE_CHECKING

from Levenshtein import jaro_winkler
from tsutils import rmdiacritics

from padinfo.core.historic_lookups import historic_lookups, historic_lookups_file_path, historic_lookups_id3, \
    historic_lookups_file_path_id3
from padinfo.core.padinfo_settings import settings

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel
    from dadguide.old_monster_index import NamedMonster

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
        s = 0
        multi_word_tokens_sorted = sorted(valid_multi_word_tokens,
                                          key=lambda x: (len(x), len(''.join(x))),
                                          reverse=True)
        for c1, token in enumerate(tokens):
            if s:
                s -= 1
                continue
            for mwt in multi_word_tokens_sorted:
                if len(mwt) > len(tokens) - c1:
                    continue
                for c2, t in enumerate(mwt):
                    if (tokens[c1 + c2] != t and len(t) < 5) \
                            or calc_ratio_modifier(tokens[c1 + c2], t) < self.TOKEN_JW_DISTANCE:
                        break
                else:
                    s = len(mwt) - 1
                    result.append("".join(mwt))
                    break
            else:
                result.append(token)
        return result

    def _monster_has_token(self, monster, token, monsterscore, monster_mods):
        if len(token) < 6:
            if token in monster_mods:
                monsterscore[monster] += 1
                return True
        else:
            closest = max(calc_ratio_modifier(m, token) for m in monster_mods)
            if closest > self.TOKEN_JW_DISTANCE:
                monsterscore[monster] += closest
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
                if i:
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

    def process_name_tokens(self, name_query_tokens, neg_name_tokens, index2):
        monstergen = None
        monsterscore = defaultdict(int)

        for t in name_query_tokens:
            valid = self.get_valid_monsters_from_name_token(t, index2, monsterscore)
            if monstergen is not None:
                monstergen.intersection_update(valid)
            else:
                monstergen = valid

        for t in neg_name_tokens:
            invalid = self.get_valid_monsters_from_name_token(t, index2, monsterscore, mult=-10)
            if monstergen is not None:
                monstergen.difference_update(invalid)
            else:
                monstergen = set()

        return monstergen, monsterscore

    def get_valid_monsters_from_name_token(self, t, index2, monsterscore, mult=1):
        valid = set()
        ms = sorted([nt for nt in index2.all_name_tokens if calc_ratio_name(t, nt, index2) > self.TOKEN_JW_DISTANCE],
                    key=lambda nt: calc_ratio_name(t, nt, index2), reverse=True)
        ms += [token for token in index2.all_name_tokens if token.startswith(t)]
        if not ms:
            return None
        for match in ms:
            score = calc_ratio_name(t, match, index2)
            for m in index2.manual[match]:
                if m not in valid:
                    monsterscore[m] += (score + .001) * mult
                    valid.add(m)
            for m in index2.name_tokens[match]:
                if m not in valid:
                    monsterscore[m] += score * mult
                    valid.add(m)
            for m in index2.fluff_tokens[match]:
                if m not in valid:
                    monsterscore[m] += score * mult / 2
                    valid.add(m)

        return valid

    def process_modifiers(self, mod_tokens, neg_mod_tokens, monsterscore, potential_evos, monster_mods):
        for t in mod_tokens:
            potential_evos = {m for m in potential_evos if
                              self._monster_has_token(m, t, monsterscore, monster_mods[m])}
            if not potential_evos:
                return None
        for t in neg_mod_tokens:
            potential_evos = {m for m in potential_evos if
                              not self._monster_has_token(m, t, monsterscore, monster_mods[m])}
            if not potential_evos:
                return None

        return potential_evos

    def get_most_eligable_monster(self, monsters, dgcog, tokenized_query=None, monster_score=None):
        if monster_score is None:
            monster_score = defaultdict(int)
        if tokenized_query is None:
            tokenized_query = []
        return max(monsters,
                   key=lambda m: (monster_score[m],
                                  not m.is_equip,
                                  # Match na on id overlap
                                  bool(m.monster_id > 10000 and re.search(r"\d{4}", " ".join(tokenized_query))),
                                  SERIES_TYPE_PRIORITY.get(m.series.series_type),
                                  m.on_na if m.series.series_type == "collab" else 0,
                                  dgcog.database.graph.monster_is_rem_evo(m),
                                  not all(t.value in [0, 12, 14, 15] for t in m.types),
                                  not any(t.value in [0, 12, 14, 15] for t in m.types),
                                  -dgcog.database.graph.get_base_id(m),
                                  m.rarity,
                                  m.monster_no_na))

    def get_monster_evos(self, database, monster_gen, monster_score):
        monster_evos = set()
        for m in sorted(monster_gen, key=lambda m: monster_score[m], reverse=True):
            for evo in database.graph.get_alt_monsters(m):
                monster_evos.add(evo)
                if monster_score[evo] < monster_score[m]:
                    monster_score[evo] = monster_score[m] - .003

        return monster_evos


async def findMonsterCustom(dgcog, ctx, config, query):
    if await config.user(ctx.author).beta_id3():
        m = await findMonster3(dgcog, query)
        if m:
            return m, "", ""
        else:
            return None, "Monster not found", ""
    else:
        return await findMonster1(dgcog, query)


async def findMonsterCustom2(dgcog, beta_id3, query):
    if beta_id3:
        m = await findMonster3(dgcog, query)
        if m:
            return m, "", ""
        else:
            return None, "Monster not found", ""
    else:
        return await findMonster1(dgcog, query)


async def findMonster1(dgcog, query):
    query = rmdiacritics(query)
    nm, err, debug_info = await _findMonster(dgcog, query)

    monster_no = nm.monster_id if nm else -1
    historic_lookups[query] = monster_no
    json.dump(historic_lookups, open(historic_lookups_file_path, "w+"))

    m = dgcog.get_monster(nm.monster_id) if nm else None

    return m, err, debug_info


async def _findMonster(dgcog, query) -> Tuple[Optional["NamedMonster"], Optional[str], Optional[str]]:
    await dgcog.wait_until_ready()
    try:
        return dgcog.index.find_monster(query)
    except:
        prefix = (await dgcog.bot.get_valid_prefixes())[0]
        return (None,
                f"Sorry, id1 doesn't support this query and we are no longer"
                f" developing id1 features. Please use `{prefix}id3 {query}`! You can"
                f" opt into using the beta all the time by running `{prefix}idset beta y`!",
                None)


async def findMonster3(dgcog, query):
    m = await _findMonster3(dgcog, query)

    monster_no = m.monster_id if m else -1
    historic_lookups_id3[query] = monster_no
    json.dump(historic_lookups_id3, open(historic_lookups_file_path_id3, "w+"))

    return m


async def _findMonster3(dgcog, query) -> Optional["MonsterModel"]:
    await dgcog.wait_until_ready()

    query = rmdiacritics(query).lower().replace(",", "")
    tokenized_query = query.split()
    mw_tokenized_query = find_monster.merge_multi_word_tokens(tokenized_query, dgcog.index2.multi_word_tokens)

    return max(
        await find_monster_search(tokenized_query, dgcog),
        await find_monster_search(mw_tokenized_query, dgcog)
        if tokenized_query != mw_tokenized_query else (0.0, None),
        key=lambda t: t[0]
    )[1]


async def find_monster_search(tokenized_query, dgcog) -> Tuple[int, Optional["MonsterModel"]]:
    mod_tokens, neg_mod_tokens, name_query_tokens, neg_name_tokens = \
        find_monster.interpret_query(tokenized_query, dgcog.index2)

    name_query_tokens.difference_update({'|'})

    for t in mod_tokens.union(neg_mod_tokens):
        if t not in dgcog.index2.all_modifiers:
            settings.add_typo_mod(t)

    # print(mod_tokens, neg_mod_tokens, name_query_tokens, neg_name_tokens)

    if name_query_tokens:
        monster_gen, monster_score = find_monster.process_name_tokens(name_query_tokens, neg_name_tokens, dgcog.index2)
        if not monster_gen:
            # No monsters match the given name tokens
            return 0, None
        monster_gen = find_monster.get_monster_evos(dgcog.database, monster_gen, monster_score)
    else:
        # There are no name tokens in the query
        monster_gen = {*dgcog.database.get_all_monsters()}
        monster_score = defaultdict(int)

    # Expand search to the evo tree
    monster_gen = find_monster.process_modifiers(mod_tokens, neg_mod_tokens, monster_score, monster_gen,
                                                 dgcog.index2.modifiers)
    if not monster_gen:
        # no modifiers match any monster in the evo tree
        return 0, None

    # print({k: v for k, v in sorted(monster_score.items(), key=lambda kv: kv[1], reverse=True) if k in monster_gen})

    # Return most likely candidate based on query.
    mon = find_monster.get_most_eligable_monster(monster_gen, dgcog, tokenized_query, monster_score)

    return monster_score[mon], mon


find_monster = FindMonster()
