from typing import TYPE_CHECKING, List

from discordmenu.embed.base import Box
from discordmenu.embed.components import EmbedMain, EmbedField
from discordmenu.embed.view import EmbedView
from tsutils import char_to_emoji

from padinfo.common.config import UserConfig
from padinfo.view.components.base import pad_info_footer_with_state
from padinfo.view.components.monster.header import MonsterHeader
from padinfo.view.components.view_state_base import ViewStateBase

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel
    from dadguide.database_context import DbContext


class SeriesScrollViewState(ViewStateBase):
    MAX_ITEMS_PER_PANE = 11

    def __init__(self, original_author_id, menu_type, raw_query, query, color, series_id, current_min_index,
                 monster_list: List["MonsterModel"], full_monster_list: List["MonsterModel"], rarity: int,
                 all_rarities: List[int],
                 title, message,
                 max_len_so_far: int = None,
                 reaction_list=None, extra_state=None,
                 child_message_id=None):
        super().__init__(original_author_id, menu_type, raw_query,
                         extra_state=extra_state)
        self.all_rarities = all_rarities
        self.current_min_index = current_min_index
        self.series_id = series_id
        self.rarity = rarity
        self.message = message
        self.child_message_id = child_message_id
        self.title = title
        self.monster_list = monster_list
        self.full_monster_list = full_monster_list
        self.reaction_list = reaction_list
        self.color = color
        self.query = query
        self.max_len_so_far = max(max_len_so_far or len(monster_list), len(self.monster_list))

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': SeriesScrollView.VIEW_TYPE,
            'series_id': self.series_id,
            'current_min_index': self.current_min_index,
            'title': self.title,
            'full_monster_list': [str(m.monster_no) for m in self.full_monster_list],
            'rarity': self.rarity,
            'all_rarities': self.all_rarities,
            'reaction_list': self.reaction_list,
            'child_message_id': self.child_message_id,
            'message': self.message,
            'max_len_so_far': self.max_len_so_far
        })
        return ret

    @staticmethod
    async def deserialize(dgcog, user_config: UserConfig, ims: dict):
        print(ims)
        if ims.get('unsupported_transition'):
            return None
        series_id = ims['series_id']
        rarity = ims['rarity']
        all_rarities = ims['all_rarities']
        full_monster_list = SeriesScrollViewState.query(dgcog, series_id, rarity)
        current_min_index = ims.get('current_min_index') or {str(rarity): 0}
        current_min_index_num, current_max_index = SeriesScrollViewState.get_current_indices(dgcog, ims)
        monster_list = full_monster_list[current_min_index_num:current_max_index]
        title = ims['title']

        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        reaction_list = ims.get('reaction_list')
        child_message_id = ims.get('child_message_id')
        message = ims.get('message')
        max_len_so_far = max(ims['max_len_so_far'] or len(monster_list), len(monster_list))

        return SeriesScrollViewState(original_author_id, menu_type, raw_query, query, user_config.color, series_id,
                                     current_min_index, monster_list, full_monster_list, rarity,
                                     all_rarities,
                                     title, message,
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
        return base_monsters_of_rarity

    @staticmethod
    def query_all_rarities(dgcog, series_id):
        db_context: "DbContext" = dgcog.database
        return sorted({m.rarity for m in db_context.get_all_monsters() if
                       m.series_id == series_id and db_context.graph.monster_is_base(m)})

    @staticmethod
    def get_current_indices(dgcog, ims):
        # even though some of these definitions are redundant, we need to reuse this code
        # in the menu itself to define the prev & next lazy-scroll buttons
        # so it makes sense to separate out this method
        series_id = ims['series_id']
        rarity = ims['rarity']
        full_monster_list = SeriesScrollViewState.query(dgcog, series_id, rarity)
        current_min_index = ims.get('current_min_index') or {str(rarity): 0}
        current_min_index_num: int = current_min_index.get(str(rarity)) or 0
        current_max_index_num: int = current_min_index_num + SeriesScrollViewState.MAX_ITEMS_PER_PANE
        current_max_index = min(len(full_monster_list), current_max_index_num)
        return current_min_index_num, current_max_index


class SeriesScrollView:
    VIEW_TYPE = 'SeriesScroll'

    @staticmethod
    def embed(state: SeriesScrollViewState):
        fields = [
            EmbedField(SeriesScrollView._rarity_text(state.rarity),
                       Box(*SeriesScrollView._monster_list(
                           state.monster_list)) if state.monster_list else Box(
                           'No monsters of this rarity to display')),
            EmbedField('**All rarities**',
                       Box(SeriesScrollView._all_rarity_text(state.all_rarities, state.rarity))
                       ),
        ]

        return EmbedView(
            EmbedMain(
                title=state.title,
                color=state.color,
            ),
            embed_footer=pad_info_footer_with_state(state),
            embed_fields=fields)

    @staticmethod
    def _rarity_text(this_rarity):
        return 'Current rarity: {}'.format(
            str(this_rarity)
        )

    @staticmethod
    def _all_rarity_text(all_rarities, this_rarity):
        return ', '.join([str(r) if r != this_rarity else '**{}**'.format(str(r)) for r in all_rarities])

    @staticmethod
    def _monster_list(monsters):
        if not len(monsters):
            return []
        return [
            MonsterHeader.short_with_emoji(mon, link=True, prefix=char_to_emoji(i))
            for i, mon in enumerate(monsters)
        ]
