from typing import List, Optional, TYPE_CHECKING

from tsutils.menu.components.config import UserConfig
from tsutils.query_settings.query_settings import QuerySettings

from padinfo.view.monster_list.monster_list import MonsterListView, MonsterListViewState, MonsterListQueriedProps

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel
    from dbcog.database_context import DbContext


class ScrollViewState(MonsterListViewState):
    VIEW_STATE_TYPE = "Scroll"

    def __init__(self, original_author_id, menu_type, query,
                 queried_props: MonsterListQueriedProps, query_settings: QuerySettings,
                 title, message, current_monster_id: int,
                 *,
                 current_page: int = 0,
                 current_index: int = None,
                 child_menu_type: str = None,
                 child_reaction_list: Optional[List] = None,
                 reaction_list=None,
                 extra_state=None,
                 child_message_id=None
                 ):
        super().__init__(original_author_id, menu_type, query, queried_props, query_settings, title, message,
                         current_page=current_page, current_index=current_index, child_menu_type=child_menu_type,
                         child_reaction_list=child_reaction_list, reaction_list=reaction_list,
                         extra_state=extra_state, child_message_id=child_message_id)

        self._current_monster_id = current_monster_id

    @property
    def current_monster_id(self) -> int:
        return self._current_monster_id

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'current_monster_id': self._current_monster_id
        })
        return ret

    @classmethod
    async def deserialize(cls, dbcog, user_config: UserConfig, ims: dict):
        if ims.get('unsupported_transition'):
            return None
        title = ims['title']

        queried_props = await cls.query_from_ims(dbcog, ims)
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
        return ScrollViewState(original_author_id, menu_type, query,
                               queried_props, query_settings,
                               title, idle_message, ims['current_monster_id'],
                               current_page=current_page,
                               current_index=current_index,
                               child_menu_type=child_menu_type,
                               child_reaction_list=child_reaction_list,
                               reaction_list=reaction_list,
                               extra_state=ims,
                               child_message_id=child_message_id
                               )

    @classmethod
    async def do_query(cls, dbcog, monster) -> Optional[MonsterListQueriedProps]:
        prev_monster = dbcog.database.graph.numeric_prev_monster(monster)
        next_monster = dbcog.database.graph.numeric_next_monster(monster)

        monster_list = []

        if prev_monster is not None:
            monster_list.append(prev_monster)
        if next_monster is not None:
            monster_list.append(next_monster)

        return MonsterListQueriedProps(monster_list)

    async def decrement_index(self, dbcog):
        db_context: "DbContext" = dbcog.database
        monster = db_context.graph.get_monster(self.current_monster_id, server=self.query_settings.server)

        prev_monster: "MonsterModel" = dbcog.database.graph.numeric_prev_monster(monster)
        if prev_monster is None:
            # TODO: raise an error here so that the "omg yikes" sign shows up once that's based on an error again
            return
        monster_list = await self.do_query(dbcog, prev_monster)

        self._current_monster_id = prev_monster.monster_id
        self.paginated_monsters = [monster_list]

    async def increment_index(self, dbcog):
        db_context: "DbContext" = dbcog.database
        monster = db_context.graph.get_monster(self.current_monster_id, server=self.query_settings.server)
        next_monster = dbcog.database.graph.numeric_next_monster(monster)
        if next_monster is None:
            # TODO: raise an error here so that the "omg yikes" sign shows up once that's based on an error again
            return
        monster_list = await self.do_query(dbcog, next_monster)

        self._current_monster_id = next_monster.monster_id
        self.paginated_monsters = [monster_list]

    @classmethod
    async def query_from_ims(cls, dbcog, ims) -> MonsterListQueriedProps:
        monster = await dbcog.find_monster(ims['raw_query'], ims['original_author_id'])
        queried_props = await cls.do_query(dbcog, monster)
        return queried_props


class ScrollView(MonsterListView):
    emojis = ['\N{BLACK LEFT-POINTING TRIANGLE}', '\N{BLACK RIGHT-POINTING TRIANGLE}']

    @classmethod
    def get_emoji(cls, i: int, current_monster_id: int):
        if current_monster_id == 1:
            return cls.emojis[1]
        return cls.emojis[i]
