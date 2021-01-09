import re
from collections import defaultdict

from tsutils import rmdiacritics
from typing import List, Set
import difflib


def calc_ratio(s1, s2):
    return difflib.SequenceMatcher(None, s1, s2).ratio()

def calc_ratio_prefix(token, full_word):
    if full_word == token:
        return 1
    elif full_word.startswith(token):
        return 1 - len(full_word)/100
    return difflib.SequenceMatcher(None, token, full_word).ratio()


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
                    if (tokens[c1 + c2] != t and len(t) < 5) or calc_ratio(tokens[c1 + c2], t) < .8:
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

    def process_name_tokens(self, name_query_tokens, index2):
        monstergen = None
        monsterscore = defaultdict(int)

        for t in name_query_tokens:
            valid = set()

            ms = difflib.get_close_matches(t, index2.name_tokens, n=10000, cutoff=.8)
            ms += [token for token in index2.name_tokens if token.startswith(t)]
            if not ms:
                return None, None
            for match in ms:
                for m in index2.manual[match]:
                    if m not in valid:
                        monsterscore[m] += calc_ratio_prefix(t, match) + .001
                        valid.add(m)
                for m in index2.tokens[match]:
                    if m not in valid:
                        monsterscore[m] += calc_ratio_prefix(t, match)
                        valid.add(m)

            if monstergen is not None:
                monstergen.intersection_update(valid)
            else:
                monstergen = valid

        return monstergen, monsterscore

    def process_prefix_tokens(self, prefix_query_tokens, monsterscore, potential_evos, monster_prefixes):
        for t in prefix_query_tokens:
            potential_evos = {m for m in potential_evos if self._monster_has_token(m, t, monsterscore, monster_prefixes[m])}
            if not potential_evos:
                return None

        return potential_evos

    def get_monster_evos(self, database, monster_gen):
        monster_evos = set()
        for m in monster_gen:
            monster_evos.update(database.graph.get_alt_monsters(m))

        return monster_evos


find_monster = FindMonster()
