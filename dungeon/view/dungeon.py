from typing import List

from discord import Embed
from discordmenu.embed.base import Box
from discordmenu.emoji.emoji_cache import emoji_cache
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.view import EmbedView
from tsutils import embed_footer_with_state

from dungeon.SafeDict import SafeDict
from dungeon.enemy_skills_pb2 import MonsterBehavior
from dungeon.processors import process_monster
from padinfo.common.config import UserConfig
from padinfo.view.components.view_state_base import ViewStateBase


class DungeonViewState(ViewStateBase):
    def __init__(self, original_author_id, menu_type, raw_query, color, pm,
                 sub_dungeon_id, num_floors, floor, num_spawns, floor_index, technical, database, page=0, verbose=False,
                 reaction_list: List[str] = None):
        super().__init__(original_author_id, menu_type, raw_query, reaction_list=reaction_list)
        self.pm = pm
        self.sub_dungeon_id = sub_dungeon_id
        self.num_floors = num_floors
        self.floor = floor
        self.floor_index = floor_index
        self.technical = technical
        self.color = color
        self.database = database
        self.num_spawns = num_spawns
        self.page = page
        self.verbose = verbose

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
            'page': self.page
        })
        return ret

    @classmethod
    async def deserialize(cls, dgcog, color, ims: dict, inc_floor: int = 0, inc_index: int = 0,
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
        floor_models = dgcog.database.dungeon.get_floor_from_sub_dungeon(sub_dungeon_id, floor)

        # check if we are on final monster of the floor
        if floor_index >= len(floor_models):
            floor_index = 0

        if floor_index < 0:
            floor_index = len(floor_models) + floor_index

        # check if we reset the floor_index
        if reset_spawn:
            floor_index = 0

        encounter_model = floor_models[floor_index]

        return cls(original_author_id, menu_type, raw_query, color, encounter_model, sub_dungeon_id,
                   num_floors, floor, len(floor_models), floor_index,
                   technical, dgcog.database, verbose=verbose,
                   reaction_list=ims.get('reaction_list'), page=page)


class DungeonView:
    VIEW_TYPE = 'DungeonText'

    @staticmethod
    def embed(state: DungeonViewState):
        fields = []
        mb = MonsterBehavior()
        encounter_model = state.pm
        if (encounter_model.enemy_data is not None) and (encounter_model.enemy_data.behavior is not None):
            mb.ParseFromString(encounter_model.enemy_data.behavior)
        else:
            mb = None
        monster = process_monster(mb, encounter_model, state.database)
        monster_embed: Embed = \
            monster.make_embed(verbose=state.verbose, spawn=[state.floor_index + 1, state.num_spawns],
                               floor=[state.floor, state.num_floors], technical=state.technical)[state.page]
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
            embed_footer=embed_footer_with_state(state)
        )
