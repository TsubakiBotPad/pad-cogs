from collections import defaultdict
from typing import NamedTuple, Mapping, Set

from frozendict import frozendict

from dbcog.find_monster.tokens.find_monster_tokens import MatchMap
from dbcog.models.monster_model import MonsterModel


class SubqueryData(NamedTuple):
    # Subquery token type matched
    label: str

    # Subquery given
    subquery: str

    # Immutable Parent-to-Child monster mapping
    map: Mapping[int, int]


class SubqueryMonsters(NamedTuple):
    map: Mapping[int, MonsterModel]


class ExtraInfo(NamedTuple):
    # Subquery Result
    subquery_data: Set[SubqueryData]

    subquery_monsters: Set[SubqueryMonsters]

    # Unused
    return_code: int

    def get_subquery_mon(self, matched_mon_id: int) -> int:
        """Returns the subquery monster ID, preferring the one that restricted the query by the most (i.e. returned the fewest options in the result set)"""
        best_weight = 100000000000  # infinity
        subquery_mon = None
        item: SubqueryData
        for item in list(self.subquery_data):
            if matched_mon_id not in item.map:
                continue
            # we want to show the most restrictive query possible
            if len(item.map) <= best_weight:
                subquery_mon = item.map[matched_mon_id]
        if subquery_mon is None:
            raise KeyError
        return subquery_mon

    def get_monster(self, m_id) -> MonsterModel:
        for item in list(self.subquery_monsters):
            if m_id in item.map:
                return item.map[m_id]
        raise KeyError

    @staticmethod
    def build_extra_info(monster_matches: MatchMap) -> "ExtraInfo":
        subquery_data = defaultdict(dict)
        subquery_mons = defaultdict()
        for monster, match in monster_matches.items():
            for mod_token in match.mod:
                match_data = mod_token.match_data
                if match_data.subquery_result:
                    subquery_data[match_data.token][monster.monster_id] = match_data.subquery_result.monster_id
                    if match_data.subquery_result.monster_id not in subquery_mons:
                        subquery_mons[match_data.subquery_result.monster_id] = match_data.subquery_result
        subquery_data = {SubqueryData(token.label, token.subquery, frozendict(m))
                         for token, m in subquery_data.items()}

        subquery_mons = {SubqueryMonsters(frozendict({token: mon}))
                         for token, mon in subquery_mons.items()}

        return ExtraInfo(subquery_data, subquery_mons, 0)
