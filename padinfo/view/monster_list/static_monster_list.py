from typing import List, TYPE_CHECKING

from tsutils.query_settings.query_settings import QuerySettings

from padinfo.view.monster_list.monster_list import MonsterListViewState, MonsterListQueriedProps

if TYPE_CHECKING:
    from dbcog.models.monster_model import MonsterModel
    from dbcog.database_context import DbContext


class StaticMonsterListViewState(MonsterListViewState):
    VIEW_STATE_TYPE = "StaticMonsterList"

    def serialize(self):
        ret = super().serialize()
        ret.update({
            'full_monster_list': [m.monster_id for page in self.paginated_monsters for m in page],
        })
        return ret

    @classmethod
    async def do_query(cls, dbcog, monster_list, server) -> List["MonsterModel"]:
        db_context: "DbContext" = dbcog.database
        monster_list = [db_context.graph.get_monster(int(m), server=server) for m in monster_list]
        return monster_list

    @classmethod
    async def query_from_ims(cls, dbcog, ims) -> MonsterListQueriedProps:
        monster_ids = ims['full_monster_list']
        qs = QuerySettings.deserialize(ims['qs'])
        monster_list = await cls.do_query(dbcog, monster_ids, qs.server)
        return MonsterListQueriedProps(monster_list)
