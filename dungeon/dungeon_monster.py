import logging
import json
from typing import List

from dungeon.grouped_skillls import GroupedSkills
from collections import OrderedDict
import discord


def indent(level):
    ret = ""
    for l in range(level):
        ret += "\u200b \u200b \u200b \u200b \u200b "
    return ret


def embed_helper(level, names, values, line):
    current_index = len(names) - 1
    indents = indent(level)
    if len(names[current_index]) + len(line) + len(indents) <= 255 and len(names[current_index]) == 0:
        names[current_index] += "\n{}{}".format(indents, line)
    elif len(values[current_index]) + len(line) + len(indents) <= 1023:
        values[current_index] += "\n{}{}".format(indents, line)
    else:
        names.append("")
        values.append("")
        embed_helper(level, names, values, line)


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


class DungeonMonster(object):

    def __init__(self, name: str, hp, atk, defense, turns, level, error=None):
        self.name = name
        self.hp = hp
        self.atk = atk
        self.defense = defense
        self.defense = hp
        self.turns = turns
        self.level = level
        self.groups: List[GroupedSkills] = []
        self.am_invade = False

        self.error = error

    def add_group(self, group: GroupedSkills):
        self.groups.append(group)

    def make_embed(self, verbose: bool = False, spawn: "list[int]" = None, floor: "list[int]" = None,
                   technical: int = None, has_invade=False):
        # top_level = []
        # field_value_dict = OrderedDict()

        embeds = []

        desc = ""
        if spawn is not None:
            embed = discord.Embed(
                title="Enemy:{} at Level: {} Spawn:{}/{} Floor:{}/{}".format(self.name, self.level, spawn[0], spawn[1],
                                                                             floor[0], floor[1]),
                description="HP:{} ATK:{} DEF:{} TURN:{}{}".format(f'{self.hp:,}', f'{self.atk:,}', f'{self.defense:,}',
                                                                   f'{self.turns:,}', desc)
            )
        else:
            embed = discord.Embed(
                title="Enemy:{} at Level: {}".format(self.name, self.level),
                description="HP:{} ATK:{} DEF:{} TURN:{}{}".format(f'{self.hp:,}', f'{self.atk:,}', f'{self.defense:,}',
                                                                   f'{self.turns:,}', desc)
            )
        embeds.append(embed)
        embeds.append(embed.copy())
        lines = []
        for group in self.groups:
            group.give_string2(lines, 0, verbose)
        names = [""]
        values = [""]
        fields = 0
        current_embed = 0
        length = len(embed.title) + len(embed.description)
        first = None
        for l in lines:
            for comp in l[1]:
                embed_helper(l[0], names, values, comp)
        if len(values[len(values) - 1]) == 0:
            values[len(values) - 1] = '\u200b'
        for index in range(len(names)):
            name = names[index]
            value = values[index]
            if len(name) > 0:
                temp_length = length + len(name) + len(value)
                if temp_length > 6000:
                    current_embed += 1
                    length = len(embed.title) + len(embed.description)
                embeds[current_embed].add_field(name=name, value=value, inline=False)
                length += len(name) + len(value)
                fields += 1
            # embed.add_field(name=k, value=content, inline=False)
        return embeds

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
        return [embed, discord.Embed(title="test", desc="test")]

    """def make_menu2_stuff(self, verbose: bool = False, spawn: "list[int]" = None, floor: "list[int]" = None,
                   technical: int = None, has_invade=False, color=None):
        # top_level = []
        # field_value_dict = OrderedDict()

        embeds = []

        desc = ""
        if spawn is not None:
            embed = discord.Embed(
                title="Enemy:{} at Level: {} Spawn:{}/{} Floor:{}/{}".format(self.name, self.level, spawn[0], spawn[1],
                                                                             floor[0], floor[1]),
                description="HP:{} ATK:{} DEF:{} TURN:{}{}".format(f'{self.hp:,}', f'{self.atk:,}', f'{self.defense:,}',
                                                                   f'{self.turns:,}', desc),
                color=color
            )
        else:
            embed = discord.Embed(
                title="Enemy:{} at Level: {}".format(self.name, self.level),
                description="HP:{} ATK:{} DEF:{} TURN:{}{}".format(f'{self.hp:,}', f'{self.atk:,}', f'{self.defense:,}',
                                                                   f'{self.turns:,}', desc),
                color=color
            )
        embeds.append(embed)
        embeds.append(discord.Embed(title="test", desc="test"))
        lines = []
        for group in self.groups:
            group.give_string2(lines, 0, verbose)
        names = [""]
        values = [""]
        fields = 0
        first = None
        for l in lines:
            for comp in l[1]:
                embed_helper(l[0], names, values, comp)
        if len(values[len(values) - 1]) == 0:
            values[len(values) - 1] = '\u200b'
        for index in range(len(names)):
            name = names[index]
            value = values[index]
            if len(name) > 0:
                embed.add_field(name=name, value=value, inline=False)
                fields += 1
            # embed.add_field(name=k, value=content, inline=False)
        return embeds"""

    async def collect_skills(self):
        skills = []
        for g in self.groups:
            skills.extend(await g.collect_skills())
        return skills
