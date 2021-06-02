from typing import TYPE_CHECKING, List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.text import BoldText
from discordmenu.embed.view import EmbedView
from tsutils import char_to_emoji, embed_footer_with_state
from tsutils.enums import Server
from tsutils.query_settings import QuerySettings

from padinfo.common.config import UserConfig
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.view_state_base import ViewStateBase

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class MonsterListViewState(ViewStateBase):
    MAX_ITEMS_PER_PANE = 11

    def __init__(self, original_author_id, menu_type, query, color,
                 monster_list: List["MonsterModel"], qsettings: QuerySettings,
                 title, message,
                 *,
                 current_page: int = 0,
                 current_index: int = None,
                 reaction_list=None,
                 extra_state=None,
                 child_message_id=None
                 ):
        super().__init__(original_author_id, menu_type, query,
                         extra_state=extra_state)
        paginated_monsters = self.paginate(monster_list)
        self.current_index = current_index
        self.current_page = current_page
        self.page_count = len(paginated_monsters)
        self.message = message
        self.child_message_id = child_message_id
        self.title = title
        self.paginated_monsters = paginated_monsters
        self.monster_list = paginated_monsters[current_page]
        self.reaction_list = reaction_list
        self.color = color
        self.query = query
        self.qsettings = qsettings

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': MonsterListView.VIEW_TYPE,
            'title': self.title,
            'monster_list': [m.monster_id for m in self.monster_list],
            'qsettings': self.qsettings.serialize(),
            'current_page': self.current_page,
            'reaction_list': self.reaction_list,
            'child_message_id': self.child_message_id,
            'message': self.message,
            'current_index': self.current_index,
        })
        return ret

    @classmethod
    async def deserialize(cls, dgcog, user_config: UserConfig, ims: dict):
        if ims.get('unsupported_transition'):
            return None
        title = ims['title']

        monster_list = await cls.query_from_ims(dgcog, ims)
        current_page = ims['current_page']
        current_index = ims.get('current_index')

        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        qsettings = QuerySettings.deserialize(ims.get('qsettings'))
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        reaction_list = ims.get('reaction_list')
        child_message_id = ims.get('child_message_id')
        message = ims.get('message')
        return MonsterListViewState(original_author_id, menu_type, query, user_config.color,
                                    monster_list, qsettings,
                                    title, message,
                                    current_page=current_page,
                                    current_index=current_index,
                                    reaction_list=reaction_list,
                                    extra_state=ims,
                                    child_message_id=child_message_id
                                    )

    @classmethod
    async def query_from_ims(cls, dgcog, ims) -> List["MonsterModel"]:
        ...

    @staticmethod
    def paginate(monster_list: List["MonsterModel"]) -> List[List["MonsterModel"]]:
        paginated_monsters = [monster_list[i:i + MonsterListViewState.MAX_ITEMS_PER_PANE]
                              for i in range(0, len(monster_list), MonsterListViewState.MAX_ITEMS_PER_PANE)]
        return paginated_monsters

    @classmethod
    async def query_paginated_from_ims(cls, dgcog, ims) -> List[List["MonsterModel"]]:
        return cls.paginate(await cls.query_from_ims(dgcog, ims))


def _monster_list(monsters):
    if not len(monsters):
        return []
    return [
        MonsterHeader.short_with_emoji(mon, link=True, prefix=char_to_emoji(i))
        for i, mon in enumerate(monsters)
    ]


class MonsterListView:
    VIEW_TYPE = 'MonsterList'

    @staticmethod
    def embed(state: MonsterListViewState):
        fields = [
            EmbedField(state.title,
                       Box(*_monster_list(state.monster_list))),
            EmbedField(BoldText('Page'),
                       Box('{} of {}'.format(state.current_page + 1, state.page_count)),
                       inline=True
                       )
        ]

        return EmbedView(
            EmbedMain(
                color=state.color,
            ),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields)
