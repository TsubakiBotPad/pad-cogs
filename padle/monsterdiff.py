from typing import TYPE_CHECKING

from tsutils.tsubaki.custom_emoji import get_attribute_emoji_by_enum, get_awakening_emoji, get_emoji, get_rarity_emoji, \
    get_type_emoji

if TYPE_CHECKING:
    from dbcog.dbcog import MonsterModel


class MonsterDiff:

    def __init__(self, monster: "MonsterModel", guess_monster: "MonsterModel"):
        self.monster = monster
        self.guess_monster = guess_monster
        self.awakenings_diff = self.get_awakenings_diff(monster, guess_monster)
        self.rarity_diff = self.get_rarity_diff(monster, guess_monster)
        self.attr_diff = self.get_attr_diff(monster, guess_monster)
        self.mp_diff = self.get_mp_diff(monster, guess_monster)
        self.type_diff = self.get_type_diff(monster, guess_monster)

    def get_diff_score(self):
        score = 0
        for v in self.awakenings_diff:
            score += v
        for v in self.attr_diff:
            score += v
        for v in self.type_diff:
            score += v
        score += 1 if self.rarity_diff == 0 else 0
        score += 1 if self.mp_diff == 0 else 0
        return score

    def get_attr_diff(self, monster, guess_monster):
        attr1 = guess_monster.attr1.name.lower()
        attr2 = guess_monster.attr2.name.lower()
        attr_feedback = [1 if attr1 == monster.attr1.name.lower() else 0,
                         1 if attr2 == monster.attr2.name.lower() else 0]
        if (attr1 == monster.attr2.name.lower() and
                attr2 != monster.attr2.name.lower() and attr1 != monster.attr1.name.lower()):
            attr_feedback[0] = 0.5
        if (attr2 == monster.attr1.name.lower() and
                attr2 != monster.attr2.name.lower() and attr1 != monster.attr1.name.lower()):
            attr_feedback[1] = 0.5
        return attr_feedback

    def get_awakenings_diff(self, monster, guess_monster):
        guess_awo_count = len(guess_monster.awakenings) - guess_monster.superawakening_count
        monster_awo_count = len(monster.awakenings) - monster.superawakening_count
        unused = monster.awakenings[:monster_awo_count]
        feedback = []
        for index, guess_awakening in enumerate(guess_monster.awakenings[:guess_awo_count]):
            if (index < monster_awo_count and
                    monster.awakenings[index].awoken_skill_id == guess_awakening.awoken_skill_id):
                feedback.append(1)
                unused.remove(guess_awakening)
            else:
                feedback.append(0)
        for index, guess_awakening in enumerate(guess_monster.awakenings[:guess_awo_count]):
            if guess_awakening in unused and feedback[index] != 1:
                feedback[index] = 0.5
                unused.remove(guess_awakening)
        return feedback

    def get_rarity_diff(self, monster, guess_monster):
        if monster.rarity == guess_monster.rarity:
            return 0
        elif guess_monster.rarity > monster.rarity:
            return -1
        else:
            return 1

    def get_mp_diff(self, monster, guess_monster):
        if monster.sell_mp == guess_monster.sell_mp:
            return 0
        elif guess_monster.sell_mp > monster.sell_mp:
            return -1
        else:
            return 1

    def get_type_diff(self, monster, guess_monster):
        diff = []
        for type in guess_monster.types:
            if type in monster.types:
                diff.append(1)
            else:
                diff.append(0)
        return diff

    def get_name_line_feedback_text(self) -> str:
        line = []
        attr1 = self.guess_monster.attr1.name.lower()
        attr2 = self.guess_monster.attr2.name.lower()
        attr_feedback = []
        for num in self.attr_diff:
            if num == 0:
                attr_feedback.append(get_emoji('red_cross_custom'))
            elif num == 0.5:
                attr_feedback.append(get_emoji('yellow_square_custom'))
            else:
                attr_feedback.append(get_emoji('green_check_custom'))
        line.append(get_attribute_emoji_by_enum(self.guess_monster.attr1))
        line.append(attr_feedback[0] + " / ")
        line.append(get_attribute_emoji_by_enum(self.guess_monster.attr2))
        line.append(attr_feedback[1] + " ")
        line.append("[" + str(self.guess_monster.monster_id) + "] ")
        line.append(self.guess_monster.name_en)
        return "".join(line)

    def get_other_info_feedback_text(self) -> str:
        line = [get_rarity_emoji(self.guess_monster.rarity)]
        if self.rarity_diff == 0:
            line.append(get_emoji('green_check_custom') + " | ")
        elif self.rarity_diff == -1:
            line.append("\N{DOWNWARDS BLACK ARROW}\N{VARIATION SELECTOR-16} | ")
        else:
            line.append("\N{UPWARDS BLACK ARROW}\N{VARIATION SELECTOR-16} | ")
        for type in self.guess_monster.types:
            line.append(get_type_emoji(type))
            if type in self.monster.types:
                line.append(get_emoji('green_check_custom') + " ")
            else:
                line.append(get_emoji('red_cross_custom') + " ")
        line.append(" | Sell MP: ")
        line.append('{:,}'.format(self.guess_monster.sell_mp))
        if self.mp_diff == 0:
            line.append(get_emoji('green_check_custom'))
        elif self.mp_diff == -1:
            line.append("\N{DOWNWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}")
        else:
            line.append("\N{UPWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}")

        return "".join(line)

    def get_awakenings_feedback_text(self) -> str:
        awakes = []
        feedback = []
        guess_awo_count = len(self.guess_monster.awakenings) - self.guess_monster.superawakening_count
        for index, guess_awake in enumerate(self.guess_monster.awakenings[:guess_awo_count]):
            awakes.append(get_awakening_emoji(guess_awake.awoken_skill_id, guess_awake.name))
            val = self.awakenings_diff[index]
            if val == 0:
                feedback.append(get_emoji('red_cross_custom'))
            elif val == 0.5:
                feedback.append(get_emoji('yellow_square_custom'))
            else:
                feedback.append(get_emoji('green_check_custom'))
        return "\n".join(["".join(awakes), "".join(feedback)])
