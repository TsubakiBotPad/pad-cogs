from typing import TYPE_CHECKING, List

from padinfo.view.evos import EvosViewState
from padinfo.view.monster_list.monster_list import MonsterListViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel


class EvoListViewState(MonsterListViewState):
    VIEW_STATE_TYPE = "EvoList"

    @classmethod
    async def query(cls, dgcog, monster):
        monster_list, _ = await EvosViewState.query(dgcog, monster)

        if not monster_list:
            return None

        return cls.paginate(monster_list)

    @classmethod
    async def query_from_ims(cls, dgcog, ims) -> List[List["MonsterModel"]]:
        monster = await dgcog.find_monster(ims['raw_query'], ims['original_author_id'])
        return await cls.query(dgcog, monster)
