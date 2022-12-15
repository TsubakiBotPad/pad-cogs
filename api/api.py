from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from api.routers.monster import monster_router

app = FastAPI(
    title="Tsubotki API",
    description="Tsubotki API",
    version="0.0.1",
)

origins = [
    "http://localhost",
    "http://localhost:3000",
    "https://www.tsubakibot.com",
    "https://teambuilder.tsubakibot.com",
    "http://teambuilder.tsubakibot.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(monster_router, prefix="/monster", tags=["monster"], )


def use_route_names_as_operation_ids(app: FastAPI) -> None:
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name  # in this case, 'read_items'


use_route_names_as_operation_ids(app)
