from abc import ABC, abstractmethod
from fnmatch import fnmatch
from typing import Iterable, NamedTuple, Optional, Set, TYPE_CHECKING, Tuple, Type, TypeVar, Union

import regex as re
from tsutils.helper_classes import DummyObject
from tsutils.tsubaki.monster_header import MonsterHeader

from dbcog.models.enum_types import Attribute, AwokenSkills
from dbcog.models.monster_model import MonsterModel
from dbcog.token_mappings import AWAKENING_TOKENS, AWOKEN_SKILL_MAP, BOOL_MONSTER_ATTRIBUTE_ALIASES, \
    BOOL_MONSTER_ATTRIBUTE_NAMES, \
    NUMERIC_MONSTER_ATTRIBUTE_ALIASES, \
    NUMERIC_MONSTER_ATTRIBUTE_NAMES, \
    PLUS_AWOKENSKILL_MAP, STRING_MONSTER_ATTRIBUTE_ALIASES, STRING_MONSTER_ATTRIBUTE_NAMES

if TYPE_CHECKING:
    from dbcog import DBCog

T = TypeVar("T")


class MatchData(NamedTuple):
    subquery_result: Optional[MonsterModel] = None
    subattr_match: Optional[bool] = None

    def __repr__(self):
        ret = []
        if self.subquery_result is not None:
            ret.append(f"[Subquery: {MonsterHeader.text_with_emoji(self.subquery_result)}]")
        if self.subattr_match:
            ret.append("[Subattr]")
        return " ".join(ret)


def regexlist(tokens):
    return '(?:' + '|'.join(re.escape(t) for t in tokens) + ")"


class Token:
    def __init__(self, value: str, *, negated: bool = False, exact: bool = False):
        self.value = self.full_value = value
        self.negated = negated
        self.exact = exact

    async def matches(self, monster: MonsterModel) -> Tuple[Union[bool, float], MatchData]:
        return True, MatchData()

    def __eq__(self, other):
        if isinstance(other, Token):
            return self.__dict__ == other.__dict__
        elif isinstance(other, str):
            return self.value == other

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        token = ("-" if self.negated else "") + (repr(self.full_value) if self.exact else self.full_value)
        return f"{self.__class__.__name__}<{token}>"


class SpecialToken(Token):
    RE_MATCH: str

    def __init__(self, value='', *, negated=False, exact=False, dbcog: "DBCog"):
        self.dbcog = dbcog
        super().__init__(value, negated=negated, exact=exact)

    async def prepare(self: T) -> T:
        return self

    async def matches(self, monster: MonsterModel):
        return False, MatchData()


class MultipleAwakeningToken(SpecialToken):
    RE_MATCH = rf"(\d+)-(sa-)?-?({regexlist(AWAKENING_TOKENS)})"

    def __init__(self, fullvalue, *, negated=False, exact=False, dbcog):
        count, sa, value = re.fullmatch(self.RE_MATCH, fullvalue).groups()
        self.minimum_count = int(count)
        self.allows_super_awakenings = bool(sa)
        super().__init__(value, negated=negated, exact=exact, dbcog=dbcog)
        self.full_value = fullvalue

    async def matches(self, monster):
        monster_total_awakenings_matching_token = 0
        for awakening in monster.awakenings:
            if awakening.is_super and not self.allows_super_awakenings:
                return False, MatchData()

            # Keep track of whether we matched this cycle for SA check at the end
            matched = True

            for awoken_skill in (self.dbcog.database.awoken_skill_map[aws.value]
                                 for aws, tokens in AWOKEN_SKILL_MAP.items()
                                 if self.value in tokens):
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
        super().__init__(negated=negated, exact=exact, dbcog=dbcog)
        self.full_value = fullvalue

    async def matches(self, monster):
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
        super().__init__(negated=negated, exact=exact, dbcog=dbcog)
        self.full_value = fullvalue

    async def matches(self, monster):
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
        super().__init__(negated=negated, exact=exact, dbcog=dbcog)
        self.full_value = fullvalue

    async def matches(self, monster):
        for class_attrs in self.monster_class_attributes:
            val: MonsterModel = monster
            for class_attr in class_attrs:
                val: str = getattr(val, class_attr, None)
            if val is None:
                continue
            if val == self.bool_value:
                return True, MatchData()
        return False, MatchData()


class SubqueryToken(ABC, SpecialToken):
    def __init__(self, fullvalue, subquery, *, negated=False, exact=False, dbcog):
        self.subquery = subquery
        self.match_data = None
        self.valid_monsters = None
        self.max_score = None

        super().__init__(negated=negated, exact=exact, dbcog=dbcog)
        self.full_value = fullvalue

    async def prepare(self):
        m_info, _ = await self.dbcog.find_monster_debug(self.subquery)
        self.match_data = m_info.monster_matches
        self.valid_monsters = m_info.valid_monsters
        self.max_score = max((self.match_data[mon].score for mon in self.valid_monsters), default=0)
        return self

    @abstractmethod
    def get_matching_monsters(self, monster: MonsterModel) -> Iterable[MonsterModel]:
        ...

    async def matches(self, monster):
        mats = self.valid_monsters.intersection(self.get_matching_monsters(monster))
        if not mats:
            return False, MatchData()
        matched, score = max(((mat, self.match_data.get(mat, DummyObject(score=0)).score) for mat in mats),
                             key=lambda x: x[1])
        return score / self.max_score, MatchData(subquery_result=matched)


class HasMaterial(SubqueryToken):
    RE_MATCH = r"hasmat:([\"']?)(.+)\1"

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

        super().__init__(negated=negated, exact=exact, dbcog=dbcog)
        self.full_value = fullvalue

    async def matches(self, monster):
        if monster.attr1 == self.attr:
            return True, MatchData()
        if monster.attr2 == self.attr:
            return .999, MatchData(subattr_match=True)
        return False, MatchData()


SPECIAL_TOKEN_TYPES: Set[Type[SpecialToken]] = {
    MultipleAwakeningToken,
    MonsterAttributeNumeric,
    MonsterAttributeString,
    MonsterAttributeBool,
    HasMaterial,
    SeriesOf,
    AttributeToken,
}
