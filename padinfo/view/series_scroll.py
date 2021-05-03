from typing import TYPE_CHECKING, List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.text import BoldText
from discordmenu.embed.view import EmbedView
from tsutils import char_to_emoji, embed_footer_with_state

from padinfo.common.config import UserConfig
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.view_state_base import ViewStateBase

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel
    from dadguide.database_context import DbContext


class SeriesScrollViewState(ViewStateBase):
    MAX_ITEMS_PER_PANE = 11

    def __init__(self, original_author_id, menu_type, raw_query, query, color, series_id, current_page,
                 monster_list: List["MonsterModel"], rarity: int, pages_in_rarity: int,
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
        self.current_page = current_page or 0
        self.series_id = series_id
        self.rarity = rarity
        self.message = message
        self.child_message_id = child_message_id
        self.title = title
        self.monster_list = monster_list
        self.reaction_list = reaction_list
        self.color = color
        self.query = query
        self.max_len_so_far = max(max_len_so_far or len(monster_list), len(self.monster_list))

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
            'message': self.message,
            'max_len_so_far': self.max_len_so_far,
            'current_index': self.current_index,
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        # print(ims)
        if ims.get('unsupported_transition'):
            return None
        series_id = ims['series_id']
        rarity = ims['rarity']
        all_rarities = ims['all_rarities']
        paginated_monsters = SeriesScrollViewState.query(dgcog, series_id, rarity)
        current_page = ims['current_page']
        monster_list = paginated_monsters[current_page]
        title = ims['title']

        pages_in_rarity = len(paginated_monsters)
        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        reaction_list = ims.get('reaction_list')
        child_message_id = ims.get('child_message_id')
        message = ims.get('message')
        max_len_so_far = max(ims['max_len_so_far'] or len(monster_list), len(monster_list))
        current_index = ims.get('current_index')

        return SeriesScrollViewState(original_author_id, menu_type, raw_query, query, user_config.color, series_id,
                                     current_page, monster_list, rarity, pages_in_rarity,
                                     all_rarities,
                                     title, message,
                                     current_index=current_index,
                                     max_len_so_far=max_len_so_far,
                                     reaction_list=reaction_list,
                                     extra_state=ims,
                                     child_message_id=child_message_id)

    @staticmethod
    def query(dgcog, series_id, rarity):
        db_context: "DbContext" = dgcog.database
        all_series_monsters = db_context.get_monsters_by_series(series_id)
        base_monsters_of_rarity = list(filter(
            lambda m: db_context.graph.monster_is_base(m) and m.rarity == rarity, all_series_monsters))
        paginated_monsters = [base_monsters_of_rarity[i:i + SeriesScrollViewState.MAX_ITEMS_PER_PANE]
                              for i in range(
                0, len(base_monsters_of_rarity), SeriesScrollViewState.MAX_ITEMS_PER_PANE)]
        return paginated_monsters

    @staticmethod
    def query_all_rarities(dgcog, series_id):
        db_context: "DbContext" = dgcog.database
        return sorted({m.rarity for m in db_context.get_all_monsters() if
                       m.series_id == series_id and db_context.graph.monster_is_base(m)})

    @staticmethod
    def query_from_ims(dgcog, ims) -> List[List["MonsterModel"]]:
        series_id = ims['series_id']
        rarity = ims['rarity']
        paginated_monsters = SeriesScrollViewState.query(dgcog, series_id, rarity)
        return paginated_monsters


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
