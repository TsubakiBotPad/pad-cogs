from typing import List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.view import EmbedView

from padinfo.common.config import UserConfig
from padinfo.view.components.base import pad_info_footer_with_state
from padinfo.view.components.view_state_base import ViewStateBase

class DungeonViewState(ViewStateBase):
    def __init__(self, original_author_id, menu_type, raw_query,
                pm_dungeon, floor, floor_index, type,
                 reaction_list: List[str] = None):
        super().__init__(original_author_id, menu_type, raw_query, reaction_list=reaction_list)
        self.pm_dungeon = pm_dungeon
        self.floor = floor
        self.floor_index = floor_index
        self.type = type


    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pm_dungeon': self.pm_dungeon,
            'floor': self.floor,
            'floor_index': self.floor_index,
            'type': self.type
        })
        return ret

    @classmethod
    async def deserialize(cls, dgcog, user_config: UserConfig, ims: dict, inc_floor, inc_index):
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        raw_query = ims.get('raw_query')
        pm_dungeon = ims.get('pm_dungeon')
        floor = ims.get('floor')
        floor_index = ims.get('floor_index')
        type = ims.get('type')

        return cls(original_author_id, menu_type, raw_query, pm_dungeon, floor, floor_index, type, ims.get('reaction_list'))



class DungeonView:
    VIEW_TYPE = 'DungeonText'

    @staticmethod
    def embed(state: DungeonViewState):
        fields=[
            EmbedField("Title", Box(*["1", '2']))
        ]
        return EmbedView(
            EmbedMain(
                color=state.color,
                description=state.message_list[state.index]
            ),
            embed_fields=fields,
            embed_footer=pad_info_footer_with_state(state),
        )
