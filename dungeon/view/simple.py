from typing import List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.view import EmbedView
from tsutils import embed_footer_with_state

from padinfo.common.config import UserConfig
from padinfo.view.components.view_state_base import ViewStateBase

class SimpleViewState(ViewStateBase):
    def __init__(self, original_author_id, menu_type, raw_query,
                 color, message_list, index,
                 reaction_list: List[str] = None):
        super().__init__(original_author_id, menu_type, raw_query, reaction_list=reaction_list)
        self.message_list = message_list
        self.index = index
        self.color = color

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'message_list': self.message_list,
            'index': self.index
        })
        return ret

    @classmethod
    async def deserialize(cls, dbcog, color, ims: dict, inc):
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        raw_query = ims.get('raw_query')
        print("hi")
        return cls(original_author_id, menu_type, raw_query, color, ims.get('message_list'), ims.get('index') + inc,
                   reaction_list=ims.get('reaction_list'))


class SimpleView:
    VIEW_TYPE = 'SimpleText'

    @staticmethod
    def embed(state: SimpleViewState):
        fields=[
            EmbedField("Title", Box(*["1", '2']))
        ]
        return EmbedView(
            EmbedMain(
                color=state.color,
                description=state.message_list[state.index]
            ),
            embed_fields=fields,
            embed_footer=embed_footer_with_state(state),
        )
