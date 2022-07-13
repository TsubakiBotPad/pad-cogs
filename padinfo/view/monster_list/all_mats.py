from typing import List, Optional, TYPE_CHECKING

from padinfo.view.materials import MaterialsViewState
from padinfo.view.monster_list.monster_list import MonsterListViewState, MonsterListQueriedProps

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel


class AllMatsViewState(MonsterListViewState):
    VIEW_STATE_TYPE = "AllMats"

    @classmethod
    async def do_query(cls, dbcog, monster: "MonsterModel") -> Optional[List["MonsterModel"]]:
        _, usedin, _, gemusedin, _, _, _, _ = await MaterialsViewState.do_query(dbcog, monster)
        if usedin is None and gemusedin is None:
            return None
        monster_list = usedin or gemusedin
        return monster_list

    @classmethod
    async def query_from_ims(cls, dbcog, ims) -> MonsterListQueriedProps:
        monster = await dbcog.find_monster(ims['raw_query'], ims['original_author_id'])
        monster_list = await cls.do_query(dbcog, monster)
        return MonsterListQueriedProps(monster_list)
