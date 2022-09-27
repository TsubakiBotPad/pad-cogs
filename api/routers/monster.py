from fastapi import APIRouter

from api.botref import get_bot
from api.responses.monster import MonsterResponse

monster_router = APIRouter()


@monster_router.get("/{monster_id}", response_model=MonsterResponse)
async def get(monster_id):
    dbcog = get_bot().get_cog("DBCog")
    monster = await dbcog.find_monster(monster_id)
    return MonsterResponse.from_model(monster)
