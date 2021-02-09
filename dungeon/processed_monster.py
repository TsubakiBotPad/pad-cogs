from dungeon.grouped_skillls import GroupedSkills
from collections import OrderedDict
import discord


# Called to check if a field/value/description hits character limit
def field_value_split(data: str, limit):
    names = []
    content = [""]
    hit_limit = False
    freshly_added = False
    if len(data) < limit:
        content[0] = data
        return names, content
    current_index = 0
    for e in data.split("\n"):
        if not hit_limit:
            if len(content[current_index]) + len(e) > limit:
                current_index += 1
                names.append(e)
                freshly_added = True
                content.append("")
                hit_limit = True
            else:
                if freshly_added:
                    content[current_index] += e.strip('\n')
                    freshly_added = False
                else:
                    content[current_index] += '\n' + e
        elif len(content[current_index]) + len(e) > 1024:
            current_index += 1
            names.append(e)
            freshly_added = True
            content.append("")
        else:
            if freshly_added:
                content[current_index] += e.strip('\n')
                freshly_added = False
            else:
                content[current_index] += '\n' + e
    return names, content


class ProcessedMonster(object):

    def __init__(self, name: str, hp, atk, defense, turns, level, error=None):
        self.name = name
        self.hp = hp
        self.atk = atk
        self.defense = defense
        self.defense = hp
        self.turns = turns
        self.level = level
        self.groups = []
        self.am_invade = False

        self.error = error

    def add_group(self, group: GroupedSkills):
        self.groups.append(group)

    async def make_embed(self, verbose: bool = False, spawn: "list[int]" = None, floor: "list[int]" = None,
                         technical: int = None, has_invade=False):
        top_level = []
        field_value_dict = OrderedDict()
        desc = ""
        for g in self.groups:
            await g.give_string(top_level, field_value_dict, verbose=verbose)
        for s in top_level:
            desc += s
        names, values = field_value_split(desc, 2048)
        index = 0
        fields = []
        for val in values:
            if index == 0:
                desc = val
            else:
                fields.append({names[index - 1], val})
            index += 1
        if technical == 0:
            desc = ""
        if spawn is not None:
            embed = discord.Embed(
                title="Enemy:{} at Level: {} Spawn:{}/{} Floor:{}/{}".format(self.name, self.level, spawn[0], spawn[1],
                                                                             floor[0], floor[1]),
                description="HP:{} ATK:{} DEF:{} TURN:{}{}".format(f'{self.hp:,}', f'{self.atk:,}', f'{self.defense:,}',
                                                                   f'{self.turns:,}', desc))
        else:
            embed = discord.Embed(
                title="Enemy:{} at Level: {}".format(self.name, self.level),
                description="HP:{} ATK:{} DEF:{} TURN:{}{}".format(f'{self.hp:,}', f'{self.atk:,}', f'{self.defense:,}',
                                                                   f'{self.turns:,}', desc))
        if technical == 0:
            return embed
        for n, v in fields:
            embed.add_field(name=n, value=v, inline=False)

        for k, v in field_value_dict.items():
            names, values = field_value_split(v, 1024)
            index = 0
            for val in values:
                if index == 0:
                    embed.add_field(name=k, value=val, inline=False)
                else:
                    embed.add_field(name=names[index - 1], value=val, inline=False)
                index += 1

            # embed.add_field(name=k, value=content, inline=False)
        return embed

    async def make_preempt_embed(self, spawn: "list[int]" = None, floor: "list[int]" = None, technical: int = None):
        skills = await self.collect_skills()
        desc = ""
        for s in skills:
            if "Passive" in s.type or "Preemptive" in s.type:
                desc += "\n{}".format(s.give_string(verbose=True))
        if technical == 0:
            desc = ""
        if spawn is not None:
            embed = discord.Embed(
                title="Enemy:{} at Level: {} Spawn:{}/{} Floor:{}/{}".format(self.name, self.level, spawn[0], spawn[1],
                                                                             floor[0], floor[1]),
                description="HP:{} ATK:{} DEF:{} TURN:{}{}".format(f'{self.hp:,}', f'{self.atk:,}', f'{self.defense:,}',
                                                                   f'{self.turns:,}', desc))
        else:
            embed = discord.Embed(
                title="Enemy:{} at Level: {}".format(self.name, self.level),
                description="HP:{} ATK:{} DEF:{} TURN:{}{}".format(f'{self.hp:,}', f'{self.atk:,}', f'{self.defense:,}',
                                                                   f'{self.turns:,}', desc))
        return embed

    async def collect_skills(self):
        skills = []
        for g in self.groups:
            skills.extend(await g.collect_skills())
        return skills
