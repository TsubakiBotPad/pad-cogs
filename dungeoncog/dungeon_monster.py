from typing import List

from dungeoncog.grouped_skillls import GroupedSkills


class DungeonMonster(object):
    """
    A class that symbolizes an encounter in a dungeon. Why is it not a model? Good question.
    """

    def __init__(self, hp, atk, defense, turns, level, monster, error=None):
        self.hp = hp
        self.atk = atk
        self.defense = defense
        self.turns = turns
        self.level = level
        self.groups: List[GroupedSkills] = []
        self.am_invade = False
        self.monster = monster

        self.error = error

    def add_group(self, group: GroupedSkills):
        self.groups.append(group)

    async def collect_skills(self):
        skills = []
        for g in self.groups:
            skills.extend(await g.collect_skills())
        return skills
