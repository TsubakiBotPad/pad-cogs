from dungeon.grouped_skillls import GroupedSkills
from collections import OrderedDict
import discord

class ProcessedMonster(object):

    def __init__(self, name: str, hp, atk, defense, turns, level):
        self.name = name
        self.hp = hp
        self.atk = atk
        self.defense = defense
        self.defense = hp
        self.turns = turns
        self.level = level
        self.groups = []

    def add_group(self, group: GroupedSkills):
        self.groups.append(group)

    async def make_embed(self):
        top_level = []
        field_value_dict = OrderedDict()
        desc = ""
        for g in self.groups:
            await g.give_string(top_level, field_value_dict)
        for s in top_level:
            desc += s
        embed = discord.Embed(title="Behavior for: {} at Level: {}".format(self.name, self.level),
                              description="HP:{} ATK:{} DEF:{} TURN:{}{}".format(f'{self.hp:,}', f'{self.atk:,}', f'{self.defense:,}',
                                                                                 f'{self.turns:,}', desc))
        for k, v in field_value_dict.items():
            content = v
            content2 = ""
            if len(v) > 1024:
                half_len = len(v) / 2
                content = ""
                half = False
                for e in v.split("\n"):
                    if len(content) > half_len and "S:" in e:
                        half = True
                    if half:
                        content2 += "\n" + e
                    else:
                        content += "\n" + e
            embed.add_field(name=k, value=content, inline=False)
            if len(content2) != 0:
                embed.add_field(name="\u200b", value=content2, inline=False)

            # embed.add_field(name=k, value=content, inline=False)
        return embed