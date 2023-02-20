import random
from typing import TYPE_CHECKING, List

import discord
from discord import Embed
from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.view import EmbedView
from discordmenu.embed.view_state import ViewState
from tsutils.enums import Server
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.monster_header import MonsterHeader

from dungeoncog.dungeon_monster import DungeonMonster
from dungeoncog.enemy_skills_pb2 import MonsterBehavior
from dungeoncog.processors import process_monster

if TYPE_CHECKING:
    from dbcog.models.encounter_model import EncounterModel


class DungeonViewState(ViewState):
    def __init__(self, original_author_id: int, menu_type: str, qs: QuerySettings, raw_query: str,
                 encounter: "EncounterModel", sub_dungeon_id: int, num_floors: int, floor: int, num_spawns: int,
                 floor_index: int, technical: int, database,
                 page: int = 0, verbose: bool = False):
        super().__init__(original_author_id, menu_type, raw_query)
        self.encounter = encounter
        self.sub_dungeon_id = sub_dungeon_id
        self.num_floors = num_floors
        self.floor = floor
        self.floor_index = floor_index
        self.technical = technical
        self.database = database
        self.num_spawns = num_spawns
        self.page = page
        self.verbose = verbose
        self.query_settings = qs

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'sub_dungeon_id': self.sub_dungeon_id,
            'num_floors': self.num_floors,
            'floor': self.floor,
            'floor_index': self.floor_index,
            'technical': self.technical,
            'pane_type': DungeonView.VIEW_TYPE,
            'verbose': self.verbose,
            'page': self.page,
            'query_settings': self.query_settings.serialize(),
        })
        return ret

    @classmethod
    async def deserialize(cls, dbcog, ims: dict, inc_floor: int = 0, inc_index: int = 0,
                          verbose_toggle: bool = False, page: int = 0, reset_spawn: bool = False):
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        raw_query = ims.get('raw_query')
        sub_dungeon_id = ims.get('sub_dungeon_id')
        num_floors = ims.get('num_floors')
        floor = ims.get('floor') + inc_floor
        floor_index = ims.get('floor_index') + inc_index
        technical = ims.get('technical')
        verbose = ims.get('verbose')
        # check if we are on final floor/final monster of the floor
        if floor > num_floors:
            floor = 1

        if floor < 1:
            floor = num_floors

        # toggle verbose
        if verbose_toggle:
            verbose = not verbose

        # get encounter models for the floor
        floor_models = dbcog.database.dungeon.get_floor_from_sub_dungeon(sub_dungeon_id, floor, server=Server.COMBINED)

        # check if we are on final monster of the floor
        if floor_index >= len(floor_models):
            floor_index = 0

        if floor_index < 0:
            floor_index = len(floor_models) + floor_index

        # check if we reset the floor_index
        if reset_spawn:
            floor_index = 0

        encounter_model = floor_models[floor_index]

        qs = QuerySettings.deserialize(ims.get('qs'))

        return cls(original_author_id, menu_type, qs, raw_query, encounter_model, sub_dungeon_id,
                   num_floors, floor, len(floor_models), floor_index,
                   technical, dbcog.database, verbose=verbose, page=page)


class DungeonView:
    VIEW_TYPE = 'DungeonText'

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

    @staticmethod
    def indent(level):
        """
        Helper function that indents text for the embed
        """
        ret = ""
        for lv in range(level):
            if lv == 0:
                ret += "> "
            else:
                ret += "\u200b \u200b \u200b \u200b \u200b "
        return ret

    @staticmethod
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
        indents = DungeonView.indent(level)
        if len(names[current_index]) + len(line) + len(indents) <= 255 and len(names[current_index]) == 0:
            names[current_index] += "\n{}{}".format(indents, line)
        elif len(values[current_index]) + len(line) + len(indents) <= 1023:
            values[current_index] += "\n{}{}".format(indents, line)
        else:
            names.append("")
            values.append("")
            DungeonView.embed_helper(level, names, values, line)

    @staticmethod
    def embed(state: DungeonViewState):
        fields = []
        mb = MonsterBehavior()
        encounter_model = state.encounter
        if encounter_model.enemy_data is not None and encounter_model.enemy_data.behavior is not None:
            mb.ParseFromString(encounter_model.enemy_data.behavior)
        else:
            mb = None
        monster = process_monster(mb, encounter_model, state.database)

        monster_embed: Embed = DungeonView.make_embed(
            monster, verbose=state.verbose, spawn=[state.floor_index + 1, state.num_spawns],
            floor=[state.floor, state.num_floors], technical=state.technical
        )[state.page]

        hp = f'{monster.hp:,}'
        atk = f'{monster.atk:,}'
        defense = f'{monster.defense:,}'
        turns = f'{monster.turns:,}'
        title = monster_embed.title
        desc = monster_embed.description
        me_fields = monster_embed.fields

        for f in me_fields:
            fields.append(
                EmbedField(f.name, Box(*[f.value]))
            )
        return EmbedView(
            EmbedMain(
                title=title,
                description=desc,
            ),
            embed_fields=fields,
            embed_footer=embed_footer_with_state(state, qs=state.query_settings)
        )

    @staticmethod
    def make_embed_description(dungeon_monster, desc=""):
        return "HP: {} ATK: {} DEF: {} CD: {}{}".format(f'{dungeon_monster.hp:,}',
                                                        f'{dungeon_monster.atk:,}',
                                                        f'{dungeon_monster.defense:,}',
                                                        f'{dungeon_monster.turns:,}', desc)

    @staticmethod
    def make_embed(dungeon_monster: DungeonMonster, verbose: bool = False, spawn: List[int] = None,
                   floor: List[int] = None, technical: int = None) -> List[discord.Embed]:
        """
        When called this generates an embed that displays the encounter (what is seen in dungeon_info).
        @param dungeon_monster: the processed monster to make an embed for
        @param verbose: whether or not to display effect text
        @param spawn: used to show what spawn this is on a floor [spawn, max] -> "spawn/max"
        @param floor: used to show what floor this is [current floor, number of floors]
        @param technical: if the dungeon is a technical dungeon we don't display skills
        """

        embeds = []

        desc = ""

        # We create two pages as monsters at max will only ever require two pages of embeds
        if spawn is not None:
            embed = discord.Embed(
                title="Floor: {}/{} Spawn: {}/{} Page: ".format(
                    floor[0], floor[1],
                    spawn[0], spawn[1]
                ),
                description='{}\n{}'.format(
                    MonsterHeader.text_with_emoji(dungeon_monster.monster),
                    DungeonView.make_embed_description(dungeon_monster, desc))
            )
        else:
            embed = discord.Embed(
                title="Enemy:{} at Level: {}".format(
                    MonsterHeader.text_with_emoji(dungeon_monster.monster),
                    dungeon_monster.level),
                description=DungeonView.make_embed_description(dungeon_monster, desc)
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
        for group in dungeon_monster.groups:
            group.give_string2(lines, 0, verbose)

        # We add the lines using embed_helper
        names = [""]
        values = [""]
        fields = 0
        current_embed = 0
        length = len(embed.title) + len(embed.description) + 1
        first = None
        for line in lines:
            for comp in line[1]:
                DungeonView.embed_helper(line[0], names, values, comp)

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
            random_index = random.randint(0, len(DungeonView.egg_text) - 1)
            embeds[1].add_field(name=DungeonView.egg_text[random_index], value="Come back when you see 1/2 for page!")
        else:
            embeds[0].title += '2'
            embeds[1].title += '2'
        return embeds
