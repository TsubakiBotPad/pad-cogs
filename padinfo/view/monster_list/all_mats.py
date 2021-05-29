from typing import TYPE_CHECKING, List, Optional

from padinfo.view.materials import MaterialsViewState
from padinfo.view.monster_list.monster_list import MonsterListViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class AllMatsViewState(MonsterListViewState):
    VIEW_STATE_TYPE = "AllMats"

    @classmethod
    async def query(cls, dgcog, monster: "MonsterModel") -> Optional[List["MonsterModel"]]:
        _, usedin, _, gemusedin, _, _, _, _ = await MaterialsViewState.query(dgcog, monster)
        if usedin is None and gemusedin is None:
            return None
        monster_list = usedin or gemusedin
        return monster_list

    @classmethod
    async def query_from_ims(cls, dgcog, ims) -> List["MonsterModel"]:
        monster = await dgcog.find_monster(ims['raw_query'], ims['original_author_id'])
        monster_list = await cls.query(dgcog, monster)
        return monster_list
