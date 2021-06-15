import random
from typing import List

import discord

from dungeon.grouped_skillls import GroupedSkills

egg_text = [
    "But nobody came...",
    "Come again later",
    "Tsubaki loves you",
    "Remember 100 turn Hera stalling?",
    "Odin x Mermaid are the OG heroes",
    "Never forget 10 minute stamina",
    "Another 3*...",
    "Nice!",
    "Maybe one day DBZ will come",
    "Special thanks to the PADX team and tactical_retreat!"
]


def indent(level):
    """
    Helper function that indents text for the embed
    """
    ret = ""
    for l in range(level):
        if l == 0:
            ret += "> "
        else:
            ret += "\u200b \u200b \u200b \u200b \u200b "
    return ret


def embed_helper(level, names, values, line):
    """
    Adds a line in such a way to maximize discord embed limits.

    We first try to add it to the most recent name part of the name/value pair.
    If that fails we try to add it to the corresponding value. If that fails,
    we create another name/value pair.
    @param level: how many indents the line needs
    @param names: an existing list (a list of strings that will be placed in "name fields"
    @param values: an existing list (a list of strings that will be placed in the value part of the name/value field
    @param line: the line of text we want to add
    """

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


class DungeonMonster(object):
    """
    A class that symbolizes an encounter in a dungeon. Why is it not a model? Good question.
    """

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
        """
            When called this generates an embed that displays the encounter (what is seen in dungeon_info).
            @param verbose: whether or not to display effect text
            @param spawn: used to show what spawn this is on a floor [spawn, max] -> "spawn/max"
            @param floor: used to show what floor this is [current floor, number of floors]
        """

        embeds = []

        desc = ""

        # We create two pages as monsters at max will only ever require two pages of embeds
        if spawn is not None:
            embed = discord.Embed(
                title="Enemy:{} at Level: {} Spawn:{}/{} Floor:{}/{} Page:".format(self.name, self.level, spawn[0],
                                                                                   spawn[1],
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

        if technical == 0:
            embeds[0].title += " 1/1"
            embeds[1].title += " 2/1"
            return embeds
        embeds[0].title += " 1/"
        embeds[1].title += " 2/"
        # We collect text from the skills and groups of skills
        lines = []
        for group in self.groups:
            group.give_string2(lines, 0, verbose)

        # We add the lines using embed_helper
        names = [""]
        values = [""]
        fields = 0
        current_embed = 0
        length = len(embed.title) + len(embed.description) + 1
        first = None
        for l in lines:
            for comp in l[1]:
                embed_helper(l[0], names, values, comp)

        # We add the name/value pairs to the actual embed. If needed we go to the second page
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

        if current_embed == 0:
            embeds[0].title += '1'
            embeds[1].title += '1'

            # for fun
            random_index = random.randint(0, len(egg_text) - 1)
            embeds[1].add_field(name=egg_text[random_index], value="Come back when you see 1/2 for page!")
        else:
            embeds[0].title += '2'
            embeds[1].title += '2'
        return embeds

    async def make_preempt_embed(self, spawn: "list[int]" = None, floor: "list[int]" = None, technical: int = None):
        """
        Currently unused: when called it creates an embed that only contains embed information.
        """
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

    async def collect_skills(self):
        skills = []
        for g in self.groups:
            skills.extend(await g.collect_skills())
        return skills
