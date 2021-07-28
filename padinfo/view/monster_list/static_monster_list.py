from typing import TYPE_CHECKING, List

from tsutils.enums import Server
from tsutils.query_settings import QuerySettings

from padinfo.view.monster_list.monster_list import MonsterListViewState

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
    async def query_from_ims(cls, dbcog, ims) -> List["MonsterModel"]:
        monster_ids = ims['full_monster_list']
        query_settings = QuerySettings.deserialize(ims['query_settings'])
        monster_list = await cls.do_query(dbcog, monster_ids, query_settings.server)
        return monster_list
