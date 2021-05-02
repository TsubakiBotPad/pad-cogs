import re

from dadguide.models.monster_model import MonsterModel
from dadguide.token_mappings import AWAKENING_TOKENS, inverse_map, AWOKEN_MAP, AWAKENING_EQUIVALENCES


def regexlist(tokens):
    return '(?:' + '|'.join(re.escape(t) for t in tokens) + ")"


class Token:
    def __init__(self, value, *, negated=False, exact=False):
        self.value = self.full_value = value
        self.negated = negated
        self.exact = exact

    def matches(self, other: MonsterModel) -> bool:
        return True

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
    RE_MATCH = r""

    def __init__(self, value, *, negated=False, exact=False, database):
        self.database = database
        super().__init__(value, negated=negated, exact=exact)

    def matches(self, other: MonsterModel) -> bool:
        return False


class MultipleAwakeningToken(SpecialToken):
    RE_MATCH = rf"(\d+)-(sa-)?-?({regexlist(AWAKENING_TOKENS)})"

    def __init__(self, fullvalue, *, negated=False, exact=False, database):
        count, sa, value = re.fullmatch(self.RE_MATCH, fullvalue).groups()
        self.count = int(count)
        self.sa = bool(sa)
        super().__init__(value, negated=negated, exact=exact, database=database)
        self.full_value = fullvalue

    def matches(self, other):
        c = 0
        for idx, maw in enumerate(other.awakenings):
            if maw.is_super and self.sa:
                return False
            
            matched = True
            for aw in inverse_map(AWOKEN_MAP)[self.value]:
                aw = self.database.awoken_skill_map[aw.value]
                if (eq := AWAKENING_EQUIVALENCES.get(maw.awoken_skill_id)) and eq[1] == aw.awoken_skill_id:
                    c += eq[0]
                    break
                elif maw == aw:
                    c += 1
                    break
            else:
                matched = False

            if c >= self.count:
                return True
            if maw.is_super and matched:
                return False
        return False



SPECIAL_TOKEN_TYPES = [
    MultipleAwakeningToken,
]
