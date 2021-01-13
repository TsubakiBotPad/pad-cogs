import difflib
from collections import defaultdict
from typing import Set


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

    def _monster_has_token(self, monster, token, monsterscore, monster_mods):
        if len(token) < 6:
            if token in monster_mods:
                monsterscore[monster] += 1
                return True
        else:
            dlm = difflib.get_close_matches(token, monster_mods, n=1, cutoff=.8)
            if dlm:
                monsterscore[monster] += max(calc_ratio(token, p) for p in dlm)
                return True
        return False

    def interpret_query(self, raw_query: str, valid_multi_word_tokens, all_modifiers) -> (Set[str], Set[str]):
        tokenized_query = raw_query.split()
        tokenized_query = self._merge_multi_word_tokens(tokenized_query, valid_multi_word_tokens)

        mods = set()
        nmods = set()
        name = set()
        longmods = [p for p in all_modifiers if len(p) > 8]
        for i, token in enumerate(tokenized_query):
            negated = token.startswith("-")
            token = token.lstrip('-')
            if token in all_modifiers or difflib.get_close_matches(token, longmods, n=1, cutoff=.8):
                if negated:
                    nmods.add(token)
                else:
                    mods.add(token)
            else:
                name.add(token)
                name.update(tokenized_query[i + 1:])
                break

        return mods, nmods, name

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

    def process_modifiers(self, mod_tokens, nmod_tokens, monsterscore, potential_evos, monster_mods):
        for t in mod_tokens:
            potential_evos = {m for m in potential_evos if
                              self._monster_has_token(m, t, monsterscore, monster_mods[m])}
            if not potential_evos:
                return None
        for t in nmod_tokens:
            potential_evos = {m for m in potential_evos if
                              not self._monster_has_token(m, t, monsterscore, monster_mods[m])}
            if not potential_evos:
                return None

        return potential_evos

    def get_monster_evos(self, database, monster_gen, monster_score):
        monster_evos = set()
        for m in sorted(monster_gen, key=lambda m: monster_score[m], reverse=True):
            for evo in database.graph.get_alt_monsters(m):
                monster_evos.add(evo)
                if monster_score[evo] < monster_score[m]:
                    monster_score[evo] = monster_score[m] - .003

        return monster_evos


find_monster = FindMonster()
