import asyncio
import datetime
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.accounts import accounts_router
from api.administration import administration_router
from api.general import general_router
from api.profiles import profiles_router
from api.schedules import schedules_router
from api.updates import updates_router
from api.users import users_router

from database.base import db_init

logging.basicConfig(level=logging.INFO, filename='py_logs.log')


async def lifespan():
    await db_init()

    # yield


app = FastAPI(
    title='BGITU Compass API',
    version='1',
    on_startup=[lifespan],
    docs_url='/documentation', redoc_url=None
)


app.include_router(general_router)
app.include_router(administration_router)
app.include_router(updates_router)
app.include_router(users_router)
app.include_router(schedules_router)
app.include_router(accounts_router)
app.include_router(profiles_router)


app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"],
                   )
