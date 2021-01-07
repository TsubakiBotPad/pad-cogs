import re
from collections import defaultdict

from tsutils import rmdiacritics
from typing import List, Set
import difflib

COLOR_MAP = {}

for r in ('r', 'red', 'fire'): COLOR_MAP[r] = 'r'
for b in ('b', 'blue', 'water'): COLOR_MAP[b] = 'b'
for g in ('g', 'green', 'wood'): COLOR_MAP[g] = 'g'
for l in ('l', 'light', 'yellow', 'white'): COLOR_MAP[l] = 'l'
for d in ('d', 'dark', 'purple', 'black'): COLOR_MAP[d] = 'd'
for x in ('x', 'none', 'null', 'nil'): COLOR_MAP[x] = 'x'

COLORS = 'rbgld?x'


def prefix_to_filter(prefix):
    prefix = prefix.lower()

    # light, nil, wood
    if prefix in COLOR_MAP:
        m = COLORS.index(COLOR_MAP[prefix])

        def filter_via_attribute(monster):
            return monster.attr1.value == m

    # light/red, l/r, yellow/fire
    match = re.match(r'^({0})/?({0})$'.format('|'.join(COLOR_MAP)), prefix)
    if match:
        m, s = [COLORS.index(COLOR_MAP[a]) for a in match.groups()]

        def filter_via_attributes(monster):
            return monster.attr1.value == m and monster.attr2.value == s

        return filter_via_attributes


def calc_ratio(s1, s2):
    return difflib.SequenceMatcher(None, s1, s2).ratio()


class FindMonster:
    def _merge_multi_word_tokens(self, tokens, valid_multi_word_tokens):
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
                    if calc_ratio(tokens[c1 + c2], t) < .8:
                        break
                else:
                    s = len(mwt)
                    result.append("".join(mwt))
                    break
            else:
                result.append(token)
        return result

    def _monster_has_token(self, monster, token, monsterscore, prefixes_for_monster):
        if len(token) < 6:
            if token in prefixes_for_monster:
                monsterscore[monster] += 1
                return True
        else:
            dlm = difflib.get_close_matches(token, prefixes_for_monster, n=1, cutoff=.8)
            if dlm:
                monsterscore[monster] += max(calc_ratio(token, p) for p in dlm)
                return True
        return False

    def interpret_query(self, raw_query: str, valid_multi_word_tokens, all_prefixes) -> (Set[str], Set[str]):
        tokenized_query = raw_query.split()
        tokenized_query = self._merge_multi_word_tokens(tokenized_query, valid_multi_word_tokens)

        prefixes = set()
        name = set()
        longer_prefixes = [p for p in all_prefixes if len(p) > 8]
        for i, token in enumerate(tokenized_query):
            if token in all_prefixes or difflib.get_close_matches(token, longer_prefixes, n=1, cutoff=.8):
                prefixes.add(token)
            else:
                name.add(token)
                name.update(tokenized_query[i + 1:])
                break

        return prefixes, name

    def process_name_tokens(self, name_query_tokens, all_monster_name_tokens, all_name_override_tokens,
                            all_name_tokens):
        monstergen = None
        monsterscore = defaultdict(int)

        for t in name_query_tokens:
            valid = set()

            ms = difflib.get_close_matches(t, all_monster_name_tokens, n=10000, cutoff=.8)
            if not ms:
                return None, None, True
            for match in ms:
                for m in all_name_override_tokens[match]:
                    if m not in valid:
                        monsterscore[m] += calc_ratio(t, match) + .001
                        valid.add(m)
                for m in all_name_tokens[match]:
                    if m not in valid:
                        monsterscore[m] += calc_ratio(t, match)
                        valid.add(m)

            if monstergen is not None:
                monstergen.intersection_update(valid)
            else:
                monstergen = valid

        return monstergen, monsterscore, False

    def process_prefix_tokens(self, prefix_query_tokens, monsterscore, potential_evos, monster_prefixes):
        for t in prefix_query_tokens:
            potential_evos = {m for m in potential_evos if self._monster_has_token(m, t, monsterscore, monster_prefixes[m])}
            if not potential_evos:
                return None, True

        return potential_evos, False

    def get_monster_evos(self, database, monster_gen):
        if monster_gen is None:
            # This happens when no name tokens were specified, and we're searching over the entire world
            return {*database.get_all_monsters()}, None

        monster_evos = set()
        for m in monster_gen:
            monster_evos.update(database.graph.get_alt_monsters(m))

        return monster_evos
