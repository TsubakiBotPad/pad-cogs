from typing import List

from dungeoncog.grouped_skillls import GroupedSkills


class ProcessedSkill(object):
    """
    This is a representation of a processed enemy skill. It contains the name, effect,
    processed (emoji) version of the effect, condition requriements, parents, type (passive, preempt)
    The class also contains a function called give_string. When called it returns the necessary strings needed to
    display it in dungeon_info2
    """

    def __init__(self, name: str, effect: str, processed: List[str], condition: str = None,
                 parent: GroupedSkills = None):
        self.name = name
        self.effect = effect
        self.processed = processed
        self.condition = condition
        self.parent = parent
        self.type = self.find_type()
        self.is_passive_preempt = len(self.process_type()) != 0

    def find_type(self):
        """Helper function to determine whether the skill is a preempt/passive from the parent group"""
        parent = self.parent
        while parent is not None:
            if parent.type is not None:
                return parent.type
            parent = parent.parent
        return None

    def process_type(self):
        if "Passive" in self.type or "Preemptive" in self.type:
            return "({}".format(self.type)
        return ""

    def give_string(self, indent: str = "", verbose: bool = False):
        """When called returns the strings of a skill in the following format: [emoji, effect, condition]"""
        components = [[], None, None]  # skills (condensed), effect, condition
        # if no skills/not processed just return (N/A) as the skill
        if len(self.processed) == 0:
            components[0].append("(N/A)")
            return components
        # For the emoji text we append the skill type to the beginning eg. (Emoji Effect) -> (Passive) (Emoji Effect)
        components[0] = [self.process_type()]
        components[0].extend(self.processed)
        # If verbose information is requested (ie display Effect text) we provide it
        if verbose:
            components[1] = "E: {}".format(self.effect)
        if self.condition is not None:
            components[2] = "Cond: {}".format(self.condition)
        return components
