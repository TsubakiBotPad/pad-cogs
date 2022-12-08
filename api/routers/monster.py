from typing import Union

from fastapi import APIRouter, Query

from api.botref import get_bot
from api.responses.monster import MonsterResponse, MonsterWithEvosResponse

monster_router = APIRouter()


@monster_router.get("/{monster_id}", response_model=MonsterResponse)
async def get(monster_id):
    dbcog = get_bot().get_cog("DBCog")
    monster = await dbcog.find_monster(monster_id)
    return MonsterResponse.from_model(monster)


@monster_router.get("/team-builder/", response_model=MonsterWithEvosResponse)
async def team_builder_query(q: Union[str, None] = Query(default=None, min_length=1)):
    dbcog = get_bot().get_cog("DBCog")
    monster = await dbcog.find_monster(q)
    alt_monsters = dbcog.database.graph.get_alt_monsters(monster)
    return MonsterWithEvosResponse.from_model(monster, alt_monsters)
