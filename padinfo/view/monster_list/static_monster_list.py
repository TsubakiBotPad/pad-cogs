from typing import TYPE_CHECKING, List

from padinfo.view.monster_list.monster_list import MonsterListViewState

if TYPE_CHECKING:
    from dadguide.models.monster_model import MonsterModel
    from dadguide.database_context import DbContext


class StaticMonsterListViewState(MonsterListViewState):
    VIEW_STATE_TYPE = "StaticMonsterList"

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'full_monster_list': [m.monster_id for page in self.paginated_monsters for m in page],
        })
        return ret

    @classmethod
    async def query(cls, dgcog, monster_list):
        db_context: "DbContext" = dgcog.database
        monster_list = [db_context.graph.get_monster(int(m)) for m in monster_list]
        paginated_monsters = [monster_list[i:i + cls.MAX_ITEMS_PER_PANE]
                              for i in range(0, len(monster_list), MonsterListViewState.MAX_ITEMS_PER_PANE)]
        return paginated_monsters

    @classmethod
    async def query_from_ims(cls, dgcog, ims) -> List[List["MonsterModel"]]:
        monster_list = ims['full_monster_list']
        return await cls.query(dgcog, monster_list)
