from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers.monster import monster_router

app = FastAPI(
    title="Tsubotki API",
    description="Tsubotki API",
    version="0.0.1",
)

origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(monster_router, prefix="/monster", tags=["monster"], )
