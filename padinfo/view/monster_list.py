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


class MonsterListViewState(ViewStateBase):
    MAX_ITEMS_PER_PANE = 11
    MAX_INTERNAL_STORE_SIZE = 100

    def __init__(self, original_author_id, menu_type, raw_query, query, color,
                 paginated_monsters: List[List["MonsterModel"]], page_count, current_page,
                 title, message, subtitle: str = None,
                 current_index: int = None,
                 max_len_so_far: int = None,
                 reaction_list=None,
                 extra_state=None,
                 child_message_id=None
                 ):
        super().__init__(original_author_id, menu_type, raw_query,
                         extra_state=extra_state)
        self.subtitle = subtitle
        self.current_index = current_index
        self.current_page = current_page
        self.page_count = page_count
        self.message = message
        self.child_message_id = child_message_id
        self.title = title
        self.paginated_monsters = paginated_monsters
        self.monster_list = paginated_monsters[current_page]
        self.reaction_list = reaction_list
        self.color = color
        self.query = query
        self.max_len_so_far = max(
            max_len_so_far or len(paginated_monsters[current_page]),
            len(paginated_monsters[current_page]))

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'pane_type': MonsterListView.VIEW_TYPE,
            'title': self.title,
            'subtitle': self.subtitle,
            'monster_list': [m.monster_id for m in self.monster_list],
            'full_monster_list': [m.monster_id for page in self.paginated_monsters for m in page],
            'current_page': self.current_page,
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
        title = ims['title']
        subtitle = ims['subtitle']

        paginated_monsters = MonsterListViewState.query_from_ims(dgcog, ims)
        page_count = len(paginated_monsters)
        current_page = ims['current_page']
        monster_list = paginated_monsters[current_page]
        current_index = ims.get('current_index')
        max_len_so_far = max(ims['max_len_so_far'] or len(monster_list), len(monster_list))

        raw_query = ims['raw_query']
        query = ims.get('query') or raw_query
        original_author_id = ims['original_author_id']
        menu_type = ims['menu_type']
        reaction_list = ims.get('reaction_list')
        child_message_id = ims.get('child_message_id')
        message = ims.get('message')
        return MonsterListViewState(original_author_id, menu_type, raw_query, query, user_config.color,
                                    paginated_monsters,
                                    page_count, current_page,
                                    title, message,
                                    subtitle=subtitle,
                                    current_index=current_index,
                                    max_len_so_far=max_len_so_far,
                                    reaction_list=reaction_list,
                                    extra_state=ims,
                                    child_message_id=child_message_id
                                    )

    @staticmethod
    def query(dgcog, monster_list):
        db_context: "DbContext" = dgcog.database
        monster_list = [db_context.graph.get_monster(int(m)) for m in monster_list]
        paginated_monsters = [monster_list[i:i + MonsterListViewState.MAX_ITEMS_PER_PANE]
                              for i in range(0, len(monster_list), MonsterListViewState.MAX_ITEMS_PER_PANE)]
        return paginated_monsters

    @staticmethod
    def query_from_ims(dgcog, ims) -> List[List["MonsterModel"]]:
        monster_list = ims['full_monster_list']
        return MonsterListViewState.query(dgcog, monster_list)

    @staticmethod
    def paginate(monster_list: List["MonsterModel"]) -> List[List["MonsterModel"]]:
        paginated_monsters = [monster_list[i:i + MonsterListViewState.MAX_ITEMS_PER_PANE]
                              for i in range(0, len(monster_list), MonsterListViewState.MAX_ITEMS_PER_PANE)]
        return paginated_monsters


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
                       Box(state.subtitle, *_monster_list(state.monster_list))),
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
