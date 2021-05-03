import re

from dadguide.models.monster_model import MonsterModel
from dadguide.token_mappings import AWAKENING_TOKENS, AWOKEN_SKILL_MAP, PLUS_AWOKENSKILL_MAP, AwokenSkills


def regexlist(tokens):
    return '(?:' + '|'.join(re.escape(t) for t in tokens) + ")"


class Token:
    def __init__(self, value, *, negated=False, exact=False):
        self.value = self.full_value = value
        self.negated = negated
        self.exact = exact

    def matches(self, monster: MonsterModel) -> bool:
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

    def matches(self, monster: MonsterModel) -> bool:
        return False


class MultipleAwakeningToken(SpecialToken):
    RE_MATCH = rf"(\d+)-(sa-)?-?({regexlist(AWAKENING_TOKENS)})"

    def __init__(self, fullvalue, *, negated=False, exact=False, database):
        count, sa, value = re.fullmatch(self.RE_MATCH, fullvalue).groups()
        self.minimum_count = int(count)
        self.allows_super_awakenings = bool(sa)
        super().__init__(value, negated=negated, exact=exact, database=database)
        self.full_value = fullvalue

    def matches(self, monster):
        monster_total_awakenings_matching_token = 0
        for awakening in monster.awakenings:
            if awakening.is_super and not self.allows_super_awakenings:
                return False
            
            # Keep track of whether we matched this cycle for SA check at the end
            matched = True
            
            for awoken_skill in (self.database.awoken_skill_map[aws.value]
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
                return True

            # If we already matched an SA and didn't return True, fail immediately.
            # We only allow one SA to count towards the total for each MultipleAwakeningToken
            if awakening.is_super and matched:
                return False
        return False



SPECIAL_TOKEN_TYPES = [
    MultipleAwakeningToken,
]
