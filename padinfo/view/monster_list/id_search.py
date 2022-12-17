from typing import List, Optional, TYPE_CHECKING

from tsutils.query_settings.enums import EvoGrouping
from tsutils.query_settings.query_settings import QuerySettings

from padinfo.view.monster_list.monster_list import MonsterListViewState, MonsterListQueriedProps

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class IdSearchViewState(MonsterListViewState):
    VIEW_STATE_TYPE = "IdSearch"

    @classmethod
    async def do_query(cls, dbcog, query, original_author_id, query_settings: QuerySettings) \
            -> Optional[MonsterListQueriedProps]:
        found_monsters, extra_info = await dbcog.find_monsters(query, original_author_id)

        if not found_monsters:
            return None

        # print(query_settings.serialize())
        if query_settings.evogrouping == EvoGrouping.splitevos:
            return found_monsters
        used = set()
        monster_list = []
        for mon in found_monsters:
            base_id = dbcog.database.graph.get_base_id(mon)
            if base_id not in used:
                used.add(base_id)
                monster_list.append(mon)

        return MonsterListQueriedProps(monster_list, extra_info)

    @classmethod
    async def query_from_ims(cls, dbcog, ims) -> MonsterListQueriedProps:
        queried_props = await cls.do_query(dbcog, ims['raw_query'], ims['original_author_id'],
                                           QuerySettings.deserialize(ims['query_settings']))
        return queried_props
