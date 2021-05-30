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
            'monster_server': self.paginated_monsters[0].server_priority if self.paginated_monsters else "COMBINED",
        })
        return ret

    @classmethod
    async def query(cls, dgcog, monster_list, server) -> List["MonsterModel"]:
        db_context: "DbContext" = dgcog.database
        monster_list = [db_context.graph.get_monster(int(m), server=server) for m in monster_list]
        return monster_list

    @classmethod
    async def query_from_ims(cls, dgcog, ims) -> List["MonsterModel"]:
        monster_ids = ims['full_monster_list']
        server = ims['monster_server']
        monster_list = await cls.query(dgcog, monster_ids, server)
        return monster_list
