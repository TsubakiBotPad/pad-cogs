from abc import ABC, abstractmethod
from fnmatch import fnmatch
from typing import Iterable, List, NamedTuple, Optional, Set, TYPE_CHECKING, Tuple, Type, TypeVar, Union

import regex as re
from Levenshtein import jaro_winkler
from tsutils.helper_classes import DummyObject
from tsutils.tsubaki.monster_header import MonsterHeader

from dbcog.models.enum_types import Attribute, AwokenSkills
from dbcog.models.monster_model import MonsterModel
from dbcog.monster_index import MonsterIndex
from dbcog.token_mappings import AWAKENING_TOKENS, AWOKEN_SKILL_MAP, BOOL_MONSTER_ATTRIBUTE_ALIASES, \
    BOOL_MONSTER_ATTRIBUTE_NAMES, \
    NUMERIC_MONSTER_ATTRIBUTE_ALIASES, \
    NUMERIC_MONSTER_ATTRIBUTE_NAMES, \
    PLUS_AWOKENSKILL_MAP, STRING_MONSTER_ATTRIBUTE_ALIASES, STRING_MONSTER_ATTRIBUTE_NAMES

if TYPE_CHECKING:
    from dbcog import DBCog

T = TypeVar("T")
MODIFIER_JW_DISTANCE = .95
TOKEN_JW_DISTANCE = .8
EPSILON = .001


class MatchData(NamedTuple):
    name_type: Optional[str] = None
    subquery_result: Optional[MonsterModel] = None
    subattr_match: Optional[bool] = None
    or_index: Optional[Tuple[int, str]] = None

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
    token: str
    matched: str
    match_data: MatchData


def regexlist(tokens):
    return '(?:' + '|'.join(re.escape(t) for t in tokens) + ")"


class QueryToken(ABC):
    def __init__(self, value: str, *, negated: bool = False, exact: bool = False):
        self.value = value
        self.negated = negated
        self.exact = exact

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

        return ratio, TokenMatch(self.value, matched_token, MatchData())


class SpecialToken(QueryToken):
    RE_MATCH: str

    def __init__(self, value, *, negated=False, exact=False, dbcog: "DBCog"):
        self.dbcog = dbcog
        super().__init__(value, negated=negated, exact=exact)

    async def special_matches(self, monster: MonsterModel) -> Tuple[Union[bool, float], MatchData]:
        return True, MatchData()

    async def matches(self, monster, index):
        mult, data = await self.special_matches(monster)
        if self.value in index.modifiers[monster] and mult <= 1:
            # If the full value is actually a modifier
            return 1.0, TokenMatch(self.value, self.value, MatchData())
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
                return False, MatchData()

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
                return True, MatchData()

            # If we already matched an SA and didn't return True, fail immediately.
            # We only allow one SA to count towards the total for each MultipleAwakeningToken
            if awakening.is_super and matched:
                return False, MatchData()
        return False, MatchData()


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
                return True, MatchData()
            if ">" in self.operator and val > self.rhs:
                return True, MatchData()
            if "=" in self.operator and val == self.rhs:
                return True, MatchData()
        return False, MatchData()


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
        for class_attrs in self.monster_class_attributes:
            val: MonsterModel = monster
            for class_attr in class_attrs:
                val: str = getattr(val, class_attr, None)
            if val is None:
                continue
            val: str = val.lower()
            if self.match == "=" and val == self.string:  # Exact match
                return True, MatchData()
            elif self.match == "r" and bool(re.search(self.string, val)):  # Regex match
                return True, MatchData()
            elif self.match == "g" and fnmatch(val, '*' + self.string + '*'):  # Glob match
                return True, MatchData()
            elif self.string in val:
                return True, MatchData()
        return False, MatchData()


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
                return True, MatchData()
        return False, MatchData()


class SubqueryToken(SpecialToken):
    def __init__(self, fullvalue, subquery, *, negated=False, exact=False, dbcog):
        self.subquery = subquery
        self.sub_matches = None
        self.valid_monsters = None
        self.max_score = None

        super().__init__(fullvalue, negated=negated, exact=exact, dbcog=dbcog)

    async def prepare(self):
        m_info, _ = await self.dbcog.find_monster_debug(self.subquery)
        self.sub_matches = m_info.monster_matches
        self.valid_monsters = m_info.valid_monsters
        self.max_score = max((self.sub_matches[mon].score for mon in self.valid_monsters), default=0)

    @abstractmethod
    def get_matching_monsters(self, monster: MonsterModel) -> Iterable[MonsterModel]:
        ...

    async def special_matches(self, monster):
        mons = self.valid_monsters.intersection(self.get_matching_monsters(monster))
        if not mons:
            return False, MatchData()
        matched, score = max(((mon, self.sub_matches.get(mon, DummyObject(score=0)).score) for mon in mons),
                             key=lambda x: x[1])
        return score / self.max_score, MatchData(subquery_result=matched)


class HasMaterial(SubqueryToken):
    RE_MATCH = r"ha[sz]mat:([\"']?)(.+)\1"

    def __init__(self, fullvalue, *, negated=False, exact=False, dbcog):
        _, subquery = re.fullmatch(self.RE_MATCH, fullvalue.lower()).groups()
        super().__init__(fullvalue, subquery, negated=negated, exact=exact, dbcog=dbcog)

    def get_matching_monsters(self, monster):
        return self.dbcog.database.graph.evo_mats(monster)


class SeriesOf(SubqueryToken):
    RE_MATCH = r"seriesof:([\"']?)(.+)\1"

    def __init__(self, fullvalue, *, negated=False, exact=False, dbcog):
        _, subquery = re.fullmatch(self.RE_MATCH, fullvalue.lower()).groups()
        super().__init__(fullvalue, subquery, negated=negated, exact=exact, dbcog=dbcog)

    def get_matching_monsters(self, monster):
        return self.dbcog.database.get_monsters_where(lambda m: m.series_id == monster.series_id,
                                                      server=monster.server_priority,
                                                      cache_key=('series_id', monster.series_id))


class AttributeToken(SpecialToken):
    RE_MATCH = r"[rbgldx]|red|fire|blue|water|green|wood|light|yellow|dark|purple|nil|none|null|white"

    def __init__(self, fullvalue, *, negated=False, exact=False, dbcog):
        if fullvalue in ('r', 'red', 'fire'):
            self.attr = Attribute.Fire
        elif fullvalue in ('b', 'blue', 'water'):
            self.attr = Attribute.Water
        elif fullvalue in ('g', 'green', 'wood'):
            self.attr = Attribute.Wood
        elif fullvalue in ('l', 'light', 'yellow'):
            self.attr = Attribute.Light
        elif fullvalue in ('d', 'dark', 'purple'):
            self.attr = Attribute.Dark
        else:
            self.attr = Attribute.Nil

        super().__init__(fullvalue, negated=negated, exact=exact, dbcog=dbcog)

    async def special_matches(self, monster):
        if monster.attr1 == self.attr:
            return True, MatchData()
        if monster.attr2 == self.attr:
            return .999, MatchData(subattr_match=True)
        return False, MatchData()


class OrToken(SpecialToken):
    RE_MATCH = r"\[.+ .+\]"

    def __init__(self, fullvalue, *, negated=False, exact=False, dbcog):
        self._strings = re.sub(r'"[^"]+"|\'[^\']+\'',
                               lambda m: m.group(0).replace(' ', ''),
                               fullvalue[1:-1]).split()

        self.tokens: Optional[List[QueryToken]] = None

        super().__init__(fullvalue, negated=negated, exact=exact, dbcog=dbcog)

    async def prepare(self):
        self.tokens = [await string_to_token(s, self.dbcog) for s in self._strings]

    async def matches(self, monster, index):
        best_score, best_data = 0.0, None
        for idx, token in enumerate(self.tokens):
            score, data = await token.matches(monster, index)
            # print(token, score, data, monster)
            if score > best_score:
                best_score = score
                best_data = TokenMatch(self.value, '', data.match_data | MatchData(or_index=(idx, token.value)))
        return best_score, best_data


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


SPECIAL_TOKEN_TYPES: Set[Type[SpecialToken]] = {
    MultipleAwakeningToken,
    MonsterAttributeNumeric,
    MonsterAttributeString,
    MonsterAttributeBool,
    HasMaterial,
    SeriesOf,
    AttributeToken,
    OrToken,
}
