import logging
import re
from typing import List

import discord

from dungeon.grouped_skillls import GroupedSkills
from dungeon.models.EnemySkill import EnemySkill
class ProcessedSkill(object):
    def __init__(self, name: str, effect: str, processed: List[str], condition: str = None, parent: GroupedSkills = None):
        self.name = name
        self.effect = effect
        self.processed = processed
        self.condition = condition
        self.parent = parent
        self.type = self.find_type()
        self.is_passive_preempt = len(self.process_type()) != 0

    def find_type(self):
        up = self.parent
        while up is not None:
            if up.type is not None:
                return up.type
            up = up.parent
        return None

    def process_type(self):
        if "Passive" in self.type or "Preemptive" in self.type:
            return "({})".format(self.type)
        return ""

    def give_string(self, indent: str = "", verbose: bool = False):
        components = [[], None, None] # skills (condensed), effect, condition
        # if no skills/not processed just return (N/A) as the skill
        if len(self.processed) == 0:
            components[0].append("(N/A)")
            return components
        components[0] = [self.process_type()]
        components[0].extend(self.processed)
        if verbose:
            components[1] = "**E: {}**".format(self.effect)
        if self.condition is not None:
            components[2] = "**Cond: {}**".format(self.condition)
        return components
