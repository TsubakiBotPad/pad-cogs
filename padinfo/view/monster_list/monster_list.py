from typing import TYPE_CHECKING, List, Optional

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.text import BoldText
from discordmenu.embed.view import EmbedView
from tsutils.emoji import char_to_emoji
from tsutils.menu.components.config import UserConfig
from tsutils.menu.components.footers import embed_footer_with_state
from tsutils.menu.view.view_state_base import ViewStateBase
from tsutils.query_settings import QuerySettings
from tsutils.tsubaki.monster_header import MonsterHeader

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class MonsterListViewState(ViewStateBase):
    VIEW_STATE_TYPE: str
    MAX_ITEMS_PER_PANE = 11

    def __init__(self, original_author_id, menu_type, query, color,
                 monster_list: List["MonsterModel"], query_settings: QuerySettings,
                 title, message,
                 *,
                 current_page: int = 0,
                 current_index: int = None,
                 child_menu_type: str = None,
                 child_reaction_list: Optional[List] = None,
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
        self.idle_message = message
        self.child_message_id = child_message_id
        self.child_menu_type = child_menu_type
        self.child_reaction_list = child_reaction_list
        self.title = title
        self.paginated_monsters = paginated_monsters
        self.reaction_list = reaction_list
        self.color = color
        self.query = query
        self.query_settings = query_settings

    @property
    def current_monster_id(self) -> Optional[int]:
        if self.current_index is None:
            return None
        return self.monster_list[self.current_index].monster_id

    @property
    def monster_list(self) -> List["MonsterModel"]:
        return self.paginated_monsters[self.current_page]

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': MonsterListView.VIEW_TYPE,
            'title': self.title,
            'monster_list': [m.monster_id for m in self.monster_list],
            'query_settings': self.query_settings.serialize(),
            'current_page': self.current_page,
            'reaction_list': self.reaction_list,
            'child_message_id': self.child_message_id,
            'idle_message': self.idle_message,
            'current_index': self.current_index,
            'child_menu_type': self.child_menu_type,
            'child_reaction_list': self.child_reaction_list,
        })
        return ret

    def get_serialized_child_extra_ims(self):
        extra_ims = {
            'is_child': True,
            'reaction_list': self.child_reaction_list,
            'menu_type': self.child_menu_type,
            'resolved_monster_id': self.current_monster_id,
            'query_settings': self.query_settings.serialize(),
            'idle_message': self.idle_message,
        }
        return extra_ims

    @classmethod
    async def deserialize(cls, dbcog, user_config: UserConfig, ims: dict):
        if ims.get('unsupported_transition'):
            return None
        title = ims['title']

        monster_list = await cls.query_from_ims(dbcog, ims)
        current_page = ims['current_page']
        current_index = ims.get('current_index')

        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        query_settings = QuerySettings.deserialize(ims.get('query_settings'))
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        reaction_list = ims.get('reaction_list')
        child_message_id = ims.get('child_message_id')
        child_menu_type = ims.get('child_menu_type')
        child_reaction_list = ims.get('child_reaction_list')
        idle_message = ims.get('idle_message')
        return cls(original_author_id, menu_type, query, user_config.color,
                   monster_list, query_settings,
                   title, idle_message,
                   current_page=current_page,
                   current_index=current_index,
                   child_menu_type=child_menu_type,
                   child_reaction_list=child_reaction_list,
                   reaction_list=reaction_list,
                   extra_state=ims,
                   child_message_id=child_message_id
                   )

    @classmethod
    async def query_from_ims(cls, dbcog, ims) -> List["MonsterModel"]:
        ...

    @staticmethod
    def paginate(monster_list: List["MonsterModel"]) -> List[List["MonsterModel"]]:
        paginated_monsters = [monster_list[i:i + MonsterListViewState.MAX_ITEMS_PER_PANE]
                              for i in range(0, len(monster_list), MonsterListViewState.MAX_ITEMS_PER_PANE)]
        return paginated_monsters

    @classmethod
    async def query_paginated_from_ims(cls, dbcog, ims) -> List[List["MonsterModel"]]:
        return cls.paginate(await cls.query_from_ims(dbcog, ims))

    def increment_page(self):
        if self.current_page < len(self.paginated_monsters) - 1:
            self.current_page = self.current_page + 1
            self.current_index = None
            return
        self.current_page = 0
        if len(self.paginated_monsters) > 1:
            self.current_index = None

    def decrement_page(self):
        if self.current_page > 0:
            self.current_page = self.current_page - 1
            self.current_index = None
            return
        self.current_page = len(self.paginated_monsters) - 1
        if len(self.paginated_monsters) > 1:
            self.current_index = None

    async def increment_index(self, _dbcog):
        max_index = len(self.paginated_monsters[self.current_page]) - 1
        if self.current_index is None:
            self.current_index = 0
            return
        if self.current_index < max_index:
            self.current_index = self.current_index + 1
            return
        if self.current_index == max_index and self.current_page < len(self.paginated_monsters) - 1:
            self.current_page = self.current_page + 1
            self.current_index = 0
            return
        if self.current_index == max_index:
            self.current_page = 0
            self.current_index = 0

    async def decrement_index(self, _dbcog):
        max_index = len(self.paginated_monsters[self.current_page]) - 1
        if self.current_index is None:
            self.current_index = max_index
            return
        if self.current_index > 0:
            self.current_index = self.current_index - 1
            return
        if self.current_index == 0 and self.current_page > 0:
            self.current_page = self.current_page - 1
            self.current_index = MonsterListViewState.MAX_ITEMS_PER_PANE - 1
            return
        if self.current_index == 0:
            # respond with left but then set the current index to the max thing possible
            self.current_page = len(self.paginated_monsters) - 1
            self.current_index = len(self.paginated_monsters[-1]) - 1

    def set_index(self, new_index):
        self.current_index = new_index


class MonsterListView:
    VIEW_TYPE = 'MonsterList'

    @classmethod
    def monster_list(cls, monsters: List["MonsterModel"], current_monster_id: int, query_settings: QuerySettings):
        if not len(monsters):
            return []
        return [MonsterHeader.box_with_emoji(
            mon, link=True, prefix=cls.get_emoji(i, current_monster_id),
            query_settings=query_settings) for i, mon in enumerate(monsters)]

    @classmethod
    def get_emoji(cls, i: int, _current_monster_id: int):
        return char_to_emoji(str(i))

    @classmethod
    def embed(cls, state: MonsterListViewState):
        fields = [
            EmbedField(state.title,
                       Box(*cls.monster_list(state.monster_list, state.current_monster_id, state.query_settings))),
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
