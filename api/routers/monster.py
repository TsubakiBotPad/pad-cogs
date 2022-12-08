from typing import Union

from fastapi import APIRouter, Query

from api.botref import get_bot
from api.responses.monster import MonsterResponse, MonsterWithEvosResponse, MonstersResponse

monster_router = APIRouter()


@monster_router.get("/{monster_id}", response_model=MonsterResponse)
async def get(monster_id):
    dbcog = get_bot().get_cog("DBCog")
    monster = await dbcog.find_monster(monster_id)
    return MonsterResponse.from_model(monster)


@monster_router.get("/get-many/", response_model=MonstersResponse)
async def getManyById(q: Union[str, None] = Query(default=None, min_length=1)):
    monster_ids = q.split(",")

    dbcog = get_bot().get_cog("DBCog")
    monsters = []
    for monster_id in monster_ids:
        monster = await dbcog.find_monster(monster_id)
        monsters.append(monster)

    return MonstersResponse.from_model(monsters)


@monster_router.get("/team-builder/", response_model=MonsterWithEvosResponse)
async def team_builder_query(q: Union[str, None] = Query(default=None, min_length=1)):
    dbcog = get_bot().get_cog("DBCog")
    monster = await dbcog.find_monster(q)
    alt_monsters = dbcog.database.graph.get_alt_monsters(monster)
    return MonsterWithEvosResponse.from_model(monster, alt_monsters)
