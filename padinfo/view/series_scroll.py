from typing import List, TYPE_CHECKING, Optional

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedField
from discordmenu.embed.text import BoldText
from tsutils.emoji import char_to_emoji
from tsutils.menu.components.config import UserConfig
from tsutils.menu.pad_view import PadView, PadViewState
from tsutils.query_settings.query_settings import QuerySettings
from tsutils.tsubaki.monster_header import MonsterHeader

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel
    from dbcog.database_context import DbContext


class SeriesScrollViewState(PadViewState):
    MAX_ITEMS_PER_PANE = 11

    def __init__(self, original_author_id, menu_type, raw_query, query, qs: QuerySettings,
                 series_id,
                 paginated_monsters: List[List["MonsterModel"]], current_page, rarity: int,
                 all_rarities: List[int],
                 title, message,
                 current_index: int = None,
                 max_len_so_far: int = None,
                 reaction_list=None, extra_state=None,
                 child_message_id=None):
        super().__init__(original_author_id, menu_type, raw_query, query, qs,
                         extra_state=extra_state)
        self.current_index = current_index
        self.all_rarities = all_rarities
        self.paginated_monsters = paginated_monsters
        self.current_page = current_page or 0
        self.series_id = series_id
        self.rarity = rarity
        self.idle_message = message
        self.child_message_id = child_message_id
        self.title = title
        self.reaction_list = reaction_list
        self._max_len_so_far = max(max_len_so_far or len(self.monster_list), len(self.monster_list))

    @property
    def monster_list(self) -> List["MonsterModel"]:
        return self.paginated_monsters[self.current_page]

    @property
    def max_len_so_far(self) -> int:
        self._max_len_so_far = max(len(self.monster_list), self._max_len_so_far)
        return self._max_len_so_far

    @property
    def current_monster_id(self) -> int:
        return self.monster_list[self.current_index].monster_id

    @property
    def pages_in_rarity(self) -> int:
        return len(self.paginated_monsters)

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': SeriesScrollView.VIEW_TYPE,
            'series_id': self.series_id,
            'current_page': self.current_page,
            'pages_in_rarity': self.pages_in_rarity,
            'title': self.title,
            'rarity': self.rarity,
            'all_rarities': self.all_rarities,
            'reaction_list': self.reaction_list,
            'child_message_id': self.child_message_id,
            'idle_message': self.idle_message,
            'max_len_so_far': self.max_len_so_far,
            'current_index': self.current_index,
        })
        return ret

    def get_serialized_child_extra_ims(self, emoji_names, menu_type):
        extra_ims = {
            'is_child': True,
            'reaction_list': emoji_names,
            'menu_type': menu_type,
            'resolved_monster_id': self.current_monster_id,
            'qs': self.qs.serialize(),
            'idle_message': self.idle_message
        }
        return extra_ims

    @classmethod
    async def deserialize(cls, dbcog, user_config: UserConfig, ims: dict):
        if ims.get('unsupported_transition'):
            return None
        series_id = ims['series_id']
        rarity = ims['rarity']
        all_rarities = ims['all_rarities']
        qs = QuerySettings.deserialize(ims.get('qs'))
        paginated_monsters = await SeriesScrollViewState.do_query(dbcog, series_id, rarity, qs.server)
        current_page = ims['current_page']
        title = ims['title']

        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        reaction_list = ims.get('reaction_list')
        child_message_id = ims.get('child_message_id')
        current_index = ims.get('current_index')
        current_monster_list = paginated_monsters[current_page]
        max_len_so_far = max(ims['max_len_so_far'] or len(current_monster_list), len(current_monster_list))
        idle_message = ims.get('idle_message')

        return cls(original_author_id, menu_type, raw_query, query, qs, series_id,
                   paginated_monsters, current_page, rarity,
                   all_rarities,
                   title, idle_message,
                   current_index=current_index,
                   max_len_so_far=max_len_so_far,
                   reaction_list=reaction_list,
                   extra_state=ims,
                   child_message_id=child_message_id)

    @staticmethod
    async def do_query(dbcog, series_id, rarity, server):
        db_context: "DbContext" = dbcog.database
        all_series_monsters = db_context.get_monsters_by_series(series_id, server=server)
        base_monsters_of_rarity = list(filter(
            lambda m: db_context.graph.monster_is_base(m) and m.rarity == rarity, all_series_monsters))
        paginated_monsters = [base_monsters_of_rarity[i:i + SeriesScrollViewState.MAX_ITEMS_PER_PANE]
                              for i in range(
                0, len(base_monsters_of_rarity), SeriesScrollViewState.MAX_ITEMS_PER_PANE)]
        return paginated_monsters

    @staticmethod
    def query_all_rarities(dbcog, series_id, server):
        db_context: "DbContext" = dbcog.database
        return sorted({m.rarity for m in db_context.get_all_monsters(server) if
                       m.series_id == series_id and db_context.graph.monster_is_base(m)})

    @staticmethod
    async def query_from_ims(dbcog, ims) -> List[List["MonsterModel"]]:
        series_id = ims['series_id']
        rarity = ims['rarity']
        qs = QuerySettings.deserialize(ims['qs'])
        paginated_monsters = await SeriesScrollViewState.do_query(dbcog, series_id, rarity, qs.server)
        return paginated_monsters

    async def decrement_page(self, dbcog):
        if self.current_page > 0:
            self.current_page = self.current_page - 1
            self.current_index = None
        else:
            # if there are multiple rarities, decrementing first page will change rarity
            if len(self.all_rarities) > 1:
                rarity_index = self.all_rarities.index(self.rarity)
                self.rarity = self.all_rarities[rarity_index - 1]
                self.paginated_monsters = await SeriesScrollViewState.do_query(
                    dbcog, self.series_id, self.rarity, self.qs.server)
                self.current_index = None
            self.current_page = len(self.paginated_monsters) - 1

        if len(self.paginated_monsters) > 1:
            self.current_index = None

    async def increment_page(self, dbcog):
        if self.current_page < len(self.paginated_monsters) - 1:
            self.current_page = self.current_page + 1
            self.current_index = None
        else:
            # if there are multiple rarities, incrementing last page will change rarity
            if len(self.all_rarities) > 1:
                rarity_index = self.all_rarities.index(self.rarity)
                self.rarity = self.all_rarities[(rarity_index + 1) % len(self.all_rarities)]
                self.paginated_monsters = await SeriesScrollViewState.do_query(
                    dbcog, self.series_id, self.rarity, self.qs.server)
                self.current_index = None
            self.current_page = 0

        if len(self.paginated_monsters) > 1:
            self.current_index = None

    async def decrement_index(self, dbcog):
        if self.current_index is None:
            self.current_index = len(self.monster_list) - 1
            return
        if self.current_index > 0:
            self.current_index = self.current_index - 1
            return
        await self.decrement_page(dbcog)
        self.current_index = len(self.monster_list) - 1

    async def increment_index(self, dbcog):
        if self.current_index is None:
            self.current_index = 0
            return
        if self.current_index < len(self.monster_list) - 1:
            self.current_index = self.current_index + 1
            return
        await self.increment_page(dbcog)
        self.current_index = 0

    def set_index(self, new_index: int):
        # don't want to go out of range, which will forget current index, break next, and break prev
        if new_index < len(self.monster_list):
            self.current_index = new_index


class SeriesScrollView(PadView):
    VIEW_TYPE = 'SeriesScroll'

    @classmethod
    def embed_title(cls, state: SeriesScrollViewState) -> Optional[str]:
        return state.title

    @classmethod
    def embed_fields(cls, state: SeriesScrollViewState) -> List[EmbedField]:
        return [
            EmbedField(BoldText('Current rarity: {}'.format(state.rarity)),
                       Box(*SeriesScrollView._monster_list(
                           state.monster_list,
                           state.current_index,
                           state.qs))),
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
    def _monster_list(monsters, current_index, qs: QuerySettings):
        if not len(monsters):
            return []
        return [
            MonsterHeader.box_with_emoji(
                mon,
                link=SeriesScrollView._is_linked(i, current_index),
                prefix=char_to_emoji(str(i)),
                qs=qs
            )
            for i, mon in enumerate(monsters)
        ]

    @staticmethod
    def _is_linked(i, current_index):
        if current_index is None:
            return True
        return i != current_index
