import logging
from collections import OrderedDict
def indent(level):
    ret = ""
    for l in range(level):
        ret += "\u200b \u200b \u200b \u200b \u200b "
    return ret

class GroupedSkills(object):
    """This is a container class that holds the top level condition, and its processed children"""
    def __init__(self, condition: str, type, parent= None):
        self.nested_groups = []
        self.skills = []
        self.condition = condition
        self.type = type
        self.parent = parent
    def add_group(self, group):
        self.nested_groups.append(group)
    def add_skill(self, skill):
        self.skills.append(skill)

    def give_string2(self, lines, level=0, verbose: bool = False):
        condition = self.condition
        if condition is not None:
            lines.append([level, ["**Condition: {}**".format(condition)]])
            level += 1
        for g in self.nested_groups:
            g.give_string2(lines, level, verbose)
        for s in self.skills:
            skill_string_components = s.give_string(verbose=verbose)
            skill_string_components[0] = "".join(skill_string_components[0])
            skill_string_components[0] = "**{}**".format(skill_string_components[0])
            skill_string_components = [x for x in skill_string_components if x is not None]
            # lines.append([level, '\n'.join(skill_string_components)])
            lines.append([level, skill_string_components])

    async def collect_skills(self):
        skill_copy = self.skills.copy()
        for g in self.nested_groups:
            skill_copy.extend(await g.collect_skills())
        return skill_copy


    # return output