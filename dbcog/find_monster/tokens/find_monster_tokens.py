from abc import ABC, abstractmethod
from collections import namedtuple
from fnmatch import fnmatch
from typing import Iterable, List, Mapping, NamedTuple, Optional, Set, TYPE_CHECKING, Tuple, Type, TypeVar, Union

import regex as re
from Levenshtein import jaro, jaro_winkler
from itertools import chain
from tsutils.helper_classes import DummyObject
from tsutils.tsubaki.monster_header import MonsterHeader

from dbcog.find_monster.token_mappings import AWAKENING_TOKENS, AWOKEN_SKILL_MAP, BOOL_MONSTER_ATTRIBUTE_ALIASES, \
    BOOL_MONSTER_ATTRIBUTE_NAMES, \
    NUMERIC_MONSTER_ATTRIBUTE_ALIASES, \
    NUMERIC_MONSTER_ATTRIBUTE_NAMES, \
    PLUS_AWOKENSKILL_MAP, STRING_MONSTER_ATTRIBUTE_ALIASES, STRING_MONSTER_ATTRIBUTE_NAMES
from dbcog.models.enum_types import Attribute, AwokenSkills
from dbcog.models.monster_model import MonsterModel
from dbcog.monster_index import MonsterIndex

if TYPE_CHECKING:
    from dbcog import DBCog

T = TypeVar("T")
MODIFIER_JW_DISTANCE = .95
TOKEN_JW_DISTANCE = .8
EPSILON = .001


class MonsterMatch:
    def __init__(self):
        # The total score of the monster
        self.score: float = 0

        # Match data for all name tokens
        self.name: Set[TokenMatch] = set()

        # Match data for all modifier tokens
        self.mod: Set[TokenMatch] = set()

    def __repr__(self):
        return str((self.score, [t[0] for t in self.name], [t[0] for t in self.mod]))


MatchMap = Mapping[MonsterModel, MonsterMatch]


class MonsterInfo(NamedTuple):
    # The best matching monster
    matched_monster: Optional[MonsterModel]

    # How the user tokens matched each monster
    monster_matches: MatchMap

    # All monsters that were not rejected by the query
    valid_monsters: Set[MonsterModel]


class MatchData(NamedTuple):
    # The actual matching token
    token: "QueryToken"

    # Type of name token
    name_type: Optional[str] = None

    # Subquery result
    subquery_result: Optional[MonsterModel] = None

    # Whether a attribute token matched the subattribute
    subattr_match: Optional[bool] = None

    # Which or result was chosen
    or_index: Optional[Tuple[int, str]] = None

    # Is negatable
    can_negate: bool = True

    # From Evolution
    from_evo: int = None

    def __repr__(self):
        ret = []
        if self.name_type is not None:
            ret.append(f"({self.name_type})")
        if self.subquery_result is not None:
            ret.append(f"[Subquery: {MonsterHeader.text_with_emoji(self.subquery_result)}]")
        if self.subattr_match is not None:
            ret.append("[Subattr]")
        if self.or_index is not None:
            ret.append(f"[Matched `{self.or_index[1]}`]")
        if self.from_evo is not None:
            ret.append(f"[From evo {self.from_evo}]")
        return " ".join(ret)

    def __or__(self, other) -> "MatchData":
        if other is None:
            return self
        kwargs = {}
        for field in self._fields:
            kwargs[field] = getattr(self, field)
            if kwargs[field] is None:
                kwargs[field] = getattr(other, field)
        return MatchData(**kwargs)


class TokenMatch(NamedTuple):
    # User token string
    token: str

    # Monster token string
    matched: str

    # Extra match data
    match_data: MatchData


def regexlist(tokens):
    return '(?:' + '|'.join(re.escape(t) for t in chain(tokens, ['$^'])) + ")"


class QueryToken(ABC):
    def __init__(self, value: str, *, negated: bool = False, exact: bool = False):
        self.value = value
        self.negated = negated
        self.exact = exact or negated

    @abstractmethod
    async def matches(self, monster: MonsterModel, index: MonsterIndex) -> Tuple[float, Optional[TokenMatch]]:
        ...

    def __eq__(self, other):
        if isinstance(other, QueryToken):
            return self.value == self.value
        elif isinstance(other, str):
            return self.value == other

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        token = ("-" if self.negated else "") + (repr(self.value) if self.exact else self.value)
        return f"{self.__class__.__name__}<{token}>"


class RegularToken(QueryToken):
    async def matches(self, monster, index):
        if len(self.value) < 6:
            matched_token = self.value
        else:
            matched_token = max(index.modifiers[monster], key=lambda m: calc_ratio_modifier(self, m))

        ratio = calc_ratio_modifier(matched_token, self.value)
        if matched_token not in index.modifiers[monster] or ratio <= MODIFIER_JW_DISTANCE:
            return 0.0, None

        return ratio, TokenMatch(self.value, matched_token, MatchData(self))


class SpecialToken(QueryToken):
    RE_MATCH: str

    def __init__(self, value, *, negated=False, exact=False, dbcog: "DBCog"):
        self.dbcog = dbcog
        super().__init__(value, negated=negated, exact=exact)

    async def special_matches(self, monster: MonsterModel) -> Tuple[Union[bool, float], MatchData]:
        return True, MatchData(self)

    async def matches(self, monster, index: MonsterIndex):
        mult, data = await self.special_matches(monster)
        if self.value in index.modifiers[monster] and mult <= 1:
            # If the full value is actually a modifier
            return 1.0, TokenMatch(self.value, self.value, MatchData(self))
        if monster in index.name_tokens[self.value].union(index.manual[self.value]) and mult <= 1:
            # If the full value is actually a name token
            return 1.0, TokenMatch(self.value, self.value, MatchData(self))
        return mult, TokenMatch(self.value, '', data)

    async def prepare(self):
        return self


class MultipleAwakeningToken(SpecialToken):
    RE_MATCH = rf"(\d+)-(sa-)?-?({regexlist(AWAKENING_TOKENS)})"

    def __init__(self, fullvalue, *, negated=False, exact=False, dbcog):
        count, sa, awo = re.fullmatch(self.RE_MATCH, fullvalue).groups()
        self.minimum_count = int(count)
        self.allows_super_awakenings = bool(sa)
        self.awo = awo
        super().__init__(fullvalue, negated=negated, exact=exact, dbcog=dbcog)

    async def special_matches(self, monster):
        monster_total_awakenings_matching_token = 0
        for awakening in monster.awakenings:
            if awakening.is_super and not self.allows_super_awakenings:
                return False, MatchData(self)

            # Keep track of whether we matched this cycle for SA check at the end
            matched = True
            for awoken_skill in (self.dbcog.database.awoken_skill_map[aws.value]
                                 for aws, tokens in AWOKEN_SKILL_MAP.items()
                                 if self.awo in tokens):
                if (equivalence := PLUS_AWOKENSKILL_MAP.get(AwokenSkills(awakening.awoken_skill_id))) \
                        and equivalence.awoken_skill.value == awoken_skill.awoken_skill_id:
                    monster_total_awakenings_matching_token += equivalence.value
                    break
                elif awoken_skill == awakening:
                    monster_total_awakenings_matching_token += 1
                    break
            else:
                matched = False

            if monster_total_awakenings_matching_token >= self.minimum_count:
                return True, MatchData(self)

            # If we already matched an SA and didn't return True, fail immediately.
            # We only allow one SA to count towards the total for each MultipleAwakeningToken
            if awakening.is_super and matched:
                return False, MatchData(self)
        return False, MatchData(self)


class MonsterAttributeNumeric(SpecialToken):
    RE_MATCH = rf"({regexlist(NUMERIC_MONSTER_ATTRIBUTE_NAMES)}):([<>=]+)?(\d+)([kmb])?"

    def __init__(self, fullvalue, *, negated=False, exact=False, dbcog):
        c_attr, ineq, value, mult = re.fullmatch(self.RE_MATCH, fullvalue.lower()).groups()
        self.monster_class_attributes = {ats for ats, aliases in NUMERIC_MONSTER_ATTRIBUTE_ALIASES.items()
                                         if c_attr in aliases}.pop()
        self.operator = ineq or "="
        self.rhs = int(value) * (1e9 if mult == 'b' else 1e6 if mult == 'm' else 1e3 if mult == 'k' else 1)
        super().__init__(fullvalue, negated=negated, exact=exact, dbcog=dbcog)

    async def special_matches(self, monster):
        for class_attrs in self.monster_class_attributes:
            val: MonsterModel = monster
            for class_attr in class_attrs:
                val: int = getattr(val, class_attr, None)
            if val is None:
                continue
            # Test each character of the equality operator because I don't want to use the eval function here
            if "<" in self.operator and val < self.rhs:
                return True, MatchData(self)
            if ">" in self.operator and val > self.rhs:
                return True, MatchData(self)
            if "=" in self.operator and val == self.rhs:
                return True, MatchData(self)
        return False, MatchData(self)


class MonsterAttributeString(SpecialToken):
    RE_MATCH = rf"({regexlist(STRING_MONSTER_ATTRIBUTE_NAMES)}):([=rg]?)([\"']?)(.+)\3"

    def __init__(self, fullvalue, *, negated=False, exact=False, dbcog):
        c_attr, match, _, string = re.fullmatch(self.RE_MATCH, fullvalue.lower()).groups()
        self.monster_class_attributes = {ats for ats, aliases in STRING_MONSTER_ATTRIBUTE_ALIASES.items()
                                         if c_attr in aliases}.pop()
        self.match = match
        self.string = string
        super().__init__(fullvalue, negated=negated, exact=exact, dbcog=dbcog)

    async def special_matches(self, monster):
        max_score = 0
        for class_attrs in self.monster_class_attributes:
            val: MonsterModel = monster
            for class_attr in class_attrs:
                val: str = getattr(val, class_attr, None)
            if val is None:
                continue
            val: str = val.lower()
            if self.match == "=" and val == self.string:  # Exact match
                return True, MatchData(self)
            elif self.match == "r" and bool(re.search(self.string, val)):  # Regex match
                return True, MatchData(self)
            elif self.match == "g" and fnmatch(val, '*' + self.string + '*'):  # Glob match
                return True, MatchData(self)
            elif self.string in val:
                return True, MatchData(self)
            max_score = max(max_score, jaro(self.string, val))
        if max_score >= TOKEN_JW_DISTANCE:
            return max_score, MatchData(self)
        return False, MatchData(self)


class MonsterAttributeBool(SpecialToken):
    RE_MATCH = rf"({regexlist(BOOL_MONSTER_ATTRIBUTE_NAMES)}):(.+)"

    def __init__(self, fullvalue, *, negated=False, exact=False, dbcog):
        c_attr, raw_bool_value = re.fullmatch(self.RE_MATCH, fullvalue.lower()).groups()
        self.monster_class_attributes = {ats for ats, aliases in BOOL_MONSTER_ATTRIBUTE_ALIASES.items()
                                         if c_attr in aliases}.pop()
        self.bool_value = raw_bool_value not in ('0', 'false', 'no')
        super().__init__(fullvalue, negated=negated, exact=exact, dbcog=dbcog)

    async def special_matches(self, monster):
        for class_attrs in self.monster_class_attributes:
            val: MonsterModel = monster
            for class_attr in class_attrs:
                val: str = getattr(val, class_attr, None)
            if val is None:
                continue
            if val == self.bool_value:
                return True, MatchData(self)
        return False, MatchData(self)


class SubqueryToken(SpecialToken):
    label: str

    def __init__(self, fullvalue, subquery, *, negated=False, exact=False, dbcog):
        self.subquery = subquery
        self.sub_matches = None
        self.valid_monsters = None
        self.max_score = None

        super().__init__(fullvalue, negated=negated, exact=exact, dbcog=dbcog)

    async def prepare(self):
        m_info, _ = await self.dbcog.find_monster_debug(self.subquery)
        pruned_m_info = await prune_results_subquery(m_info)
        self.sub_matches = pruned_m_info.monster_matches
        self.valid_monsters = pruned_m_info.valid_monsters
        self.max_score = max((self.sub_matches[mon].score for mon in self.valid_monsters), default=0)

    @abstractmethod
    def get_matching_monsters(self, monster: MonsterModel) -> Iterable[MonsterModel]:
        ...

    async def special_matches(self, monster):
        mons = self.valid_monsters.intersection(self.get_matching_monsters(monster))
        if not mons:
            return False, MatchData(self)
        matched, score = max(((mon, self.sub_matches.get(mon, DummyObject(score=0)).score) for mon in mons),
                             key=lambda x: x[1])
        return normalize_score(score, self.max_score), MatchData(self, subquery_result=matched)


SQT = TypeVar("SQT", bound=Type[SubqueryToken])


def make_tree_based(subquery_token: SQT, name: str, regex: str) -> SQT:
    class _TreeToken(subquery_token):
        RE_MATCH = regex

        def get_matching_monsters(self, monster):
            return chain(*(super(_TreeToken, self).get_matching_monsters(nevo)
                           for nevo in self.dbcog.database.graph.get_all_prev_evolutions(monster)))

    _TreeToken.__name__ = name
    return _TreeToken


class SelfHasMaterial(SubqueryToken):
    label = 'hasmat'
    RE_MATCH = (rf"(?:selfha[sz]mat|ha[sz]matself):([\"']?)(.+)\1")

    def __init__(self, fullvalue, *, negated=False, exact=False, dbcog):
        _, subquery = re.fullmatch(self.RE_MATCH, fullvalue.lower()).groups()
        super().__init__(fullvalue, subquery, negated=negated, exact=exact, dbcog=dbcog)

    def get_matching_monsters(self, monster):
        return self.dbcog.database.graph.evo_mats(self.dbcog.database.graph.evo_gem_monster(monster) or monster)


HasMaterial = make_tree_based(
    SelfHasMaterial,
    "HasMaterial",
    rf"ha[sz]mat:([\"']?)(.+)\1"
)


class SeriesOf(SubqueryToken):
    label = 'seriesof'
    RE_MATCH = r"seriesof:([\"']?)(.+)\1"

    def __init__(self, fullvalue, *, negated=False, exact=False, dbcog):
        _, subquery = re.fullmatch(self.RE_MATCH, fullvalue.lower()).groups()
        super().__init__(fullvalue, subquery, negated=negated, exact=exact, dbcog=dbcog)

    def get_matching_monsters(self, monster):
        return self.dbcog.database.get_monsters_where(lambda m: m.series_id == monster.series_id,
                                                      server=monster.server_priority,
                                                      cache_key=('series_id', monster.series_id))


class SameEvoTree(SubqueryToken):
    label = 'sametree'
    RE_MATCH = r"\((.+)\)"

    def __init__(self, fullvalue, *, negated=False, exact=False, dbcog):
        subquery, = re.fullmatch(self.RE_MATCH, fullvalue.lower()).groups()
        super().__init__(fullvalue, subquery, negated=negated, exact=exact, dbcog=dbcog)

    def get_matching_monsters(self, monster):
        return self.dbcog.database.graph.get_alt_monsters(monster) \
               + list(self.dbcog.database.graph.get_monsters_with_same_id(monster))


class SingleAttributeToken(SpecialToken):
    RE_MATCH = r"[rbgldx]|red|fire|blue|water|green|wood|light|yellow|dark|purple|nil|none|null|white"

    def __init__(self, fullvalue, *, negated=False, exact=False, dbcog):
        if fullvalue in ('r', 'fire', 'red'):
            self.attr = Attribute.Fire
        elif fullvalue in ('b', 'water', 'blue'):
            self.attr = Attribute.Water
        elif fullvalue in ('g', 'wood', 'green'):
            self.attr = Attribute.Wood
        elif fullvalue in ('l', 'light', 'yellow'):
            self.attr = Attribute.Light
        elif fullvalue in ('d', 'dark', 'purple'):
            self.attr = Attribute.Dark
        else:
            self.attr = Attribute.Nil

        super().__init__(fullvalue, negated=negated, exact=exact, dbcog=dbcog)

    async def special_matches(self, monster):
        if monster.attr1 == self.attr or (monster.attr1 == Attribute.Nil and monster.attr2 == self.attr):
            return True, MatchData(self)
        if monster.attr2 == self.attr:
            # 2ε so it doesn't have mess with manual tokens for seasonals
            return 1 - (2 * EPSILON), MatchData(self, subattr_match=True, can_negate=False)
        if monster.attr3 == self.attr:
            return 1 - (3 * EPSILON), MatchData(self, subattr_match=True, can_negate=False)
        return False, MatchData(self)


class _AnyAttribute:
    def __eq__(self, other):
        return True


class _NotNull:
    def __eq__(self, other):
        return other != Attribute.Nil


class MultiAttributeToken(SpecialToken):
    RE_MATCH = r"(?:[rbgldx\?!]/?){2,3}"

    def __init__(self, fullvalue, *, negated=False, exact=False, dbcog):
        self.attrs = []
        for a in fullvalue.replace('/',''):
            if a == 'r':
                self.attrs.append(Attribute.Fire)
            elif a == 'b':
                self.attrs.append(Attribute.Water)
            elif a == 'g':
                self.attrs.append(Attribute.Wood)
            elif a == 'l':
                self.attrs.append(Attribute.Light)
            elif a == 'd':
                self.attrs.append(Attribute.Dark)
            elif a == 'x':
                self.attrs.append(Attribute.Nil)
            elif a == '?':
                self.attrs.append(_AnyAttribute())
            elif a == '!':
                self.attrs.append(_NotNull())
        super().__init__(fullvalue, negated=negated, exact=exact, dbcog=dbcog)

    async def special_matches(self, monster):
        if len(self.attrs) == 3:
            if self.attrs[0] == monster.attr1 and self.attrs[1] == monster.attr2 and self.attrs[2] == monster.attr3:
                # 123
                return True, MatchData(self)
            if self.attrs[0] == monster.attr1 and self.attrs[1] == monster.attr3 and self.attrs[2] == monster.attr2:
                # 132
                return 1 - (2 * EPSILON), MatchData(self)
        elif len(self.attrs) == 2:
            if self.attrs[0] == monster.attr1 and self.attrs[1] == monster.attr2 and monster.attr3 == Attribute.Nil:
                # 12x
                return True, MatchData(self)
            if self.attrs[0] == monster.attr1 and self.attrs[1] == monster.attr2:
                # 12?
                return 1 - (2 * EPSILON), MatchData(self)
            if self.attrs[0] == monster.attr2 and self.attrs[1] == monster.attr3:
                # ?12
                return 1 - (3 * EPSILON), MatchData(self, subattr_match=True, can_negate=False)
            if self.attrs[0] == monster.attr1 and self.attrs[1] == monster.attr3:
                # 1?2
                return 1 - (4 * EPSILON), MatchData(self)
        return False, MatchData(self)


class OrToken(SpecialToken):
    RE_MATCH = r"\[.+ .+\]"

    def __init__(self, fullvalue, *, negated=False, exact=False, dbcog):
        self.subqueries = [s.replace('\0', ' ')
                           for s in re.sub(r'"[^"]+"|\'[^\']+\'',
                                           lambda m: m.group(0).replace(' ', '\0')[1:-1],
                                           fullvalue[1:-1]).split()]

        self.tokens: Optional[List[QueryToken]] = None
        self.results = []

        super().__init__(fullvalue, negated=negated, exact=exact, dbcog=dbcog)

    async def prepare(self):
        Subquery = namedtuple("Subquery", 'sub_matches valid_monsters max_score')
        for subquery in self.subqueries:
            m_info, _ = await self.dbcog.find_monster_debug(subquery)
            self.results.append(Subquery(
                m_info.monster_matches,
                m_info.valid_monsters,
                max((m_info.monster_matches[mon].score for mon in m_info.valid_monsters), default=0)
            ))

    async def special_matches(self, monster):
        best_score = 0
        best_data = MatchData(self)
        for c, subquery in enumerate(self.results):
            mons = subquery.valid_monsters
            if monster not in subquery.valid_monsters:
                continue
            score = subquery.sub_matches.get(monster, DummyObject(score=0)).score
            if best_score < normalize_score(score, subquery.max_score):
                best_score = normalize_score(score, subquery.max_score)
                best_data = MatchData(self, or_index=(c, self.subqueries[c]))
        return best_score, best_data


class IDRangeToken(SpecialToken):
    RE_MATCH = r"(\d+?)-(\d*)"

    def __init__(self, fullvalue, *, negated=False, exact=False, dbcog):
        lbound, rbound = re.fullmatch(self.RE_MATCH, fullvalue.lower()).groups()
        self.lower_bound = int(lbound)
        self.upper_bound = int(rbound or 9e9)

        super().__init__(fullvalue, negated=negated, exact=exact, dbcog=dbcog)

    async def special_matches(self, monster):
        return self.lower_bound <= monster.monster_id <= self.upper_bound, MatchData(self)


def calc_ratio_modifier(s1: Union[QueryToken, str], s2: str, prefix_weight: float = .05) -> float:
    """Calculate the modifier distance between two tokens"""
    if isinstance(s1, QueryToken):
        if s1.exact:
            return 1.0 if s1.value == s2 else 0.0
        s1 = s1.value

    return jaro_winkler(s1, s2, prefix_weight)


def calc_ratio_name(token: Union[QueryToken, str], full_word: str, prefix_weight: float, index: MonsterIndex) -> float:
    """Calculate the name distance between two tokens"""
    string = token.value if isinstance(token, QueryToken) else token

    mw = index.mwt_to_len[full_word] != 1
    jw = jaro_winkler(string, full_word, prefix_weight)

    if string != full_word:
        if isinstance(token, QueryToken) and token.exact:
            return 0.0
        if string.isdigit() and full_word.isdigit():
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
        score = score ** 10 * index.mwt_to_len[full_word]

    return score


async def string_to_token(string: str, dbcog: "DBCog") -> QueryToken:
    if (negated := string.startswith('-')):
        string = string.lstrip('-')
    if (exact := bool(re.fullmatch(r'".+"', string))):
        string = string[1:-1]
    for special in SPECIAL_TOKEN_TYPES:
        if re.fullmatch(special.RE_MATCH, string):
            token = special(string, negated=negated, exact=exact, dbcog=dbcog)
            await token.prepare()
            return token
    return RegularToken(string, negated=negated, exact=exact)


async def prune_results_subquery(monster_info: "MonsterInfo") -> "MonsterInfo":
    exacts = set()
    for monster in monster_info.valid_monsters:
        matched = False
        for token in monster_info.monster_matches[monster].name:
            if token.match_data.name_type != "fluff":
                if token.matched == token.token:
                    matched = True
                else:
                    break
        else:
            if matched:
                exacts.add(monster)
    return MonsterInfo(monster_info.matched_monster,
                       monster_info.monster_matches,
                       exacts or monster_info.valid_monsters)


def normalize_score(score: float, max_score: float) -> float:
    if max_score == 0:
        return 1.0
    return score / max_score


SPECIAL_TOKEN_TYPES: Set[Type[SpecialToken]] = {
    MultipleAwakeningToken,
    MonsterAttributeNumeric,
    MonsterAttributeString,
    MonsterAttributeBool,
    SelfHasMaterial,
    HasMaterial,
    SeriesOf,
    SameEvoTree,
    SingleAttributeToken,
    MultiAttributeToken,
    OrToken,
    IDRangeToken,
}
