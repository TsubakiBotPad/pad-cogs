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
    from dadguide.database_context import DbContext


class SeriesScrollViewState(ViewStateBase):
    MAX_ITEMS_PER_PANE = 11

    def __init__(self, original_author_id, menu_type, raw_query, query, color, series_id,
                 paginated_monsters: List[List["MonsterModel"]], current_page, rarity: int, pages_in_rarity: int,
                 query_settings: QuerySettings,
                 all_rarities: List[int],
                 title, message,
                 current_index: int = None,
                 max_len_so_far: int = None,
                 reaction_list=None, extra_state=None,
                 child_message_id=None):
        super().__init__(original_author_id, menu_type, raw_query,
                         extra_state=extra_state)
        self.pages_in_rarity = pages_in_rarity
        self.current_index = current_index
        self.all_rarities = all_rarities
        self.paginated_monsters = paginated_monsters
        self.current_page = current_page or 0
        self.series_id = series_id
        self.rarity = rarity
        self.query_settings = query_settings
        self.message = message
        self.child_message_id = child_message_id
        self.title = title
        self.reaction_list = reaction_list
        self.color = color
        self.query = query
        self.monster_list = paginated_monsters[current_page]
        self.max_len_so_far = max(max_len_so_far or len(self.monster_list), len(self.monster_list))

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': SeriesScrollView.VIEW_TYPE,
            'series_id': self.series_id,
            'query_settings': self.query_settings.serialize(),
            'current_page': self.current_page,
            'pages_in_rarity': self.pages_in_rarity,
            'title': self.title,
            'rarity': self.rarity,
            'all_rarities': self.all_rarities,
            'reaction_list': self.reaction_list,
            'child_message_id': self.child_message_id,
            'message': self.message,
            'max_len_so_far': self.max_len_so_far,
            'current_index': self.current_index,
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        if ims.get('unsupported_transition'):
            return None
        series_id = ims['series_id']
        rarity = ims['rarity']
        all_rarities = ims['all_rarities']
        query_settings = QuerySettings.deserialize(ims.get('query_settings'))
        paginated_monsters = await SeriesScrollViewState.do_query(dgcog, series_id, rarity, query_settings.server)
        current_page = ims['current_page']
        title = ims['title']

        pages_in_rarity = len(paginated_monsters)
        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        reaction_list = ims.get('reaction_list')
        child_message_id = ims.get('child_message_id')
        message = ims.get('message')
        monster_list = paginated_monsters[current_page]
        max_len_so_far = max(ims['max_len_so_far'] or len(monster_list), len(monster_list))
        current_index = ims.get('current_index')

        return SeriesScrollViewState(original_author_id, menu_type, raw_query, query, user_config.color, series_id,
                                     paginated_monsters, current_page, rarity, pages_in_rarity, query_settings,
                                     all_rarities,
                                     title, message,
                                     current_index=current_index,
                                     max_len_so_far=max_len_so_far,
                                     reaction_list=reaction_list,
                                     extra_state=ims,
                                     child_message_id=child_message_id)

    @staticmethod
    async def do_query(dgcog, series_id, rarity, server):
        db_context: "DbContext" = dgcog.database
        all_series_monsters = db_context.get_monsters_by_series(series_id, server=server)
        base_monsters_of_rarity = list(filter(
            lambda m: db_context.graph.monster_is_base(m) and m.rarity == rarity, all_series_monsters))
        paginated_monsters = [base_monsters_of_rarity[i:i + SeriesScrollViewState.MAX_ITEMS_PER_PANE]
                              for i in range(
                0, len(base_monsters_of_rarity), SeriesScrollViewState.MAX_ITEMS_PER_PANE)]
        return paginated_monsters

    @staticmethod
    def query_all_rarities(dgcog, series_id, server):
        db_context: "DbContext" = dgcog.database
        return sorted({m.rarity for m in db_context.get_all_monsters(server) if
                       m.series_id == series_id and db_context.graph.monster_is_base(m)})

    @staticmethod
    async def query_from_ims(dgcog, ims) -> List[List["MonsterModel"]]:
        series_id = ims['series_id']
        rarity = ims['rarity']
        query_settings = QuerySettings.deserialize(ims['query_settings'])
        paginated_monsters = await SeriesScrollViewState.do_query(dgcog, series_id, rarity, query_settings.server)
        return paginated_monsters

    async def decrement_page(self, dgcog, ims: dict):
        if self.current_page > 0:
            self.current_page = self.current_page - 1
            self.current_index = None
        else:
            # if there are multiple rarities, decrementing first page will change rarity
            if len(self.all_rarities) > 1:
                rarity_index = self.all_rarities.index(self.rarity)
                self.rarity = self.all_rarities[rarity_index - 1]
                self.paginated_monsters = await SeriesScrollViewState.do_query(dgcog, self.series_id, self.rarity,
                                                                               self.query_settings.server)
                self.pages_in_rarity = len(self.paginated_monsters)
                self.current_index = None
            self.current_page = len(self.paginated_monsters) - 1

        self.monster_list = self.paginated_monsters[self.current_page]
        self.max_len_so_far = len(self.monster_list)
        if len(self.paginated_monsters) > 1:
            self.current_index = None

    async def increment_page(self, dgcog, ims: dict):
        if self.current_page < len(self.paginated_monsters) - 1:
            self.current_page = self.current_page + 1
            self.current_index = None
        else:
            # if there are multiple rarities, incrementing last page will change rarity
            if len(self.all_rarities) > 1:
                rarity_index = self.all_rarities.index(self.rarity)
                self.rarity = self.all_rarities[(rarity_index + 1) % len(self.all_rarities)]
                self.paginated_monsters = await SeriesScrollViewState.do_query(dgcog, self.series_id, self.rarity,
                                                                               self.query_settings.server)
                self.pages_in_rarity = len(self.paginated_monsters)
                self.current_index = None
            self.current_page = 0

        self.monster_list = self.paginated_monsters[self.current_page]
        self.max_len_so_far = len(self.monster_list)
        if len(self.paginated_monsters) > 1:
            self.current_index = None

    async def decrement_index(self, dgcog, ims: dict):
        if self.current_index is None:
            self.current_index = len(self.monster_list) - 1
            return
        if self.current_index > 0:
            self.current_index = self.current_index - 1
            return
        await self.decrement_page(dgcog, ims)
        self.current_index = len(self.monster_list) - 1

    async def increment_index(self, dgcog, ims: dict):
        if self.current_index is None:
            self.current_index = 0
            return
        if self.current_index < len(self.monster_list) - 1:
            self.current_index = self.current_index + 1
            return
        await self.increment_page(dgcog, ims)
        self.current_index = 0


class SeriesScrollView:
    VIEW_TYPE = 'SeriesScroll'

    @staticmethod
    def embed(state: SeriesScrollViewState):
        fields = [
            EmbedField(BoldText('Current rarity: {}'.format(state.rarity)),
                       Box(*SeriesScrollView._monster_list(
                           state.monster_list,
                           state.current_index))),
            EmbedField(BoldText('Rarities'),
                       Box(
                           SeriesScrollView._all_rarity_text(state),
                       ), inline=True
                       ),
            EmbedField(BoldText('Page'),
                       Box('{} of {}'.format(state.current_page + 1, state.pages_in_rarity)),
                       inline=True
                       )
        ]

        return EmbedView(
            EmbedMain(
                title=state.title,
                color=state.color,
            ),
            embed_footer=embed_footer_with_state(state),
            embed_fields=fields)

    @staticmethod
    def _all_rarity_text(state):
        lines = []
        for r in state.all_rarities:
            if r != state.rarity:
                lines.append(str(r))
            else:
                lines.append('**{}**'.format(state.rarity))
        return ', '.join(lines)

    @staticmethod
    def _monster_list(monsters, current_index):
        if not len(monsters):
            return []
        return [
            MonsterHeader.short_with_emoji(
                mon,
                link=SeriesScrollView._is_linked(i, current_index),
                prefix=char_to_emoji(i)
            )
            for i, mon in enumerate(monsters)
        ]

    @staticmethod
    def _is_linked(i, current_index):
        if current_index is None:
            return True
        return i != current_index
