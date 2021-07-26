from typing import TYPE_CHECKING, List, Optional

from padinfo.view.monster_list.monster_list import MonsterListViewState

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class IdSearchViewState(MonsterListViewState):
    VIEW_STATE_TYPE = "IdSearch"

    @classmethod
    async def do_query(cls, dbcog, query, original_author_id) -> Optional[List["MonsterModel"]]:
        found_monsters = await dbcog.find_monsters(query, original_author_id)

        if not found_monsters:
            return None

        used = set()
        monster_list = []
        for mon in found_monsters:
            base_id = dbcog.database.graph.get_base_id(mon)
            if base_id not in used:
                used.add(base_id)
                monster_list.append(mon)

        return monster_list

    @classmethod
    async def query_from_ims(cls, dbcog, ims) -> List["MonsterModel"]:
        monster_list = await cls.do_query(dbcog, ims['raw_query'], ims['original_author_id'])
        return monster_list
