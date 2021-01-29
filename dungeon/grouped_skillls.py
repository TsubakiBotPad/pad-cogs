import logging
from collections import OrderedDict
def indent(level):
    ret = ""
    for l in range(level):
        ret += "\u200b \u200b \u200b \u200b \u200b "
    return ret

"""def indent2(level):
    ret = ""
    for l in range(level - 1):
        ret += "* "
    return ">>> " + ret"""
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

    async def give_string(self, top, dict: OrderedDict, nest_level=0, verbose: bool = False):
        # blocked = False
        condition = self.condition
        set = False
        output = ""
        if condition is not None:
            if nest_level != 0:
                output += "\n**{}Condition: {}**".format(indent(nest_level), condition)
            else:
                set = True
            nest_level += 1
        for g in self.nested_groups:
            o = await g.give_string(top, dict, nest_level, verbose=verbose)
            if o is not None:
                output += o
        for s in self.skills:
            if ">>>" not in output:
                output += "\n" + s.give_string(indent(nest_level), verbose=verbose)
            else:
                output += "\n" + s.give_string(indent(nest_level), verbose=verbose)
        if set:
            # print(condition)
            dict.update({"**Condition: {}**".format(condition): output})
        elif nest_level == 0:
            top += output
        else:
            return output
    async def collect_skills(self):
        skill_copy = self.skills.copy()
        for g in self.nested_groups:
            skill_copy.extend(await g.collect_skills())
        return skill_copy


    # return output