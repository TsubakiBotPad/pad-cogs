from typing import TYPE_CHECKING, List

from padinfo.view.monster_list.monster_list import MonsterListViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class IdSearchViewState(MonsterListViewState):
    VIEW_STATE_TYPE = "IdSearch"

    @classmethod
    async def query(cls, dgcog, query, original_author_id):
        found_monsters = await dgcog.find_monsters(query, original_author_id)

        if not found_monsters:
            return None

        used = set()
        monster_list = []
        for mon in found_monsters:
            base_id = dgcog.database.graph.get_base_id(mon)
            if base_id not in used:
                used.add(base_id)
                monster_list.append(mon)

        return cls.paginate(monster_list)

    @classmethod
    async def query_from_ims(cls, dgcog, ims) -> List[List["MonsterModel"]]:
        return await cls.query(dgcog, ims['raw_query'], ims['original_author_id'])
