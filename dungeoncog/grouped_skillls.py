class GroupedSkills(object):
    """This is a container class that holds the top level condition and its processed children"""

    def __init__(self, condition: str, skill_type, parent=None):
        self.nested_groups = []
        self.skills = []
        self.condition = condition
        self.type = skill_type
        self.parent = parent

    def add_group(self, group):
        self.nested_groups.append(group)

    def add_skill(self, skill):
        self.skills.append(skill)

    def give_string2(self, lines, level=0, verbose: bool = False):
        """
        When called it stores the necessary text of it's child skills in lines.
        @param lines: a list to store lines of text in the following format [number of indents needed, actual line of text]
        @param level: how many indents do we need (essentially is this a nested group or not)
        @param verbose: display skill effect text or not
        """
        condition = self.condition
        if condition is not None:
            lines.append([level, ["**Condition: {}:**".format(condition)]])
            level += 1
        for g in self.nested_groups:
            g.give_string2(lines, level, verbose)
        for s in self.skills:
            skill_string_components = s.give_string(verbose=verbose)
            skill_string_components[0] = "".join(skill_string_components[0])
            skill_string_components[0] = "**{}**".format(skill_string_components[0])
            skill_string_components = [x for x in skill_string_components if x is not None]
            lines.append([level, skill_string_components])

    async def collect_skills(self):
        skill_copy = self.skills.copy()
        for g in self.nested_groups:
            skill_copy.extend(await g.collect_skills())
        return skill_copy
