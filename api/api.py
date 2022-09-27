from fastapi import FastAPI
from .botref import get_bot

app = FastAPI()


@app.get("/monster/{monster_id}")
async def get_monster(monster_id):
    dbcog = get_bot().get_cog("DBCog")
    monster = await dbcog.find_monster(monster_id)
    return monster
