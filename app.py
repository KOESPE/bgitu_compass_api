import asyncio
import datetime
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import PlainTextResponse
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

"""
    scheduler = AsyncIOScheduler()
    if len(scheduler.get_jobs()) == 0:  # Думал сперва хранить таски через SQLAlchemyJobStore
        scheduler.add_job(weekly_management_schedule, trigger='cron', day_of_week=6, hour=1,
                          id='schedule_weekly_updates')
    scheduler.start()
    
    или в новой версии (не стоит):
        data_store = SQLAlchemyDataStore(engine=engine)
        async with AsyncScheduler() as scheduler:
            if len(await scheduler.get_schedules()) == 0:
                await scheduler.add_schedule(weekly_management_schedule,
                                             CronTrigger(day_of_week=6, hour=1),
                                             id="schedule_weekly_updates")
                await scheduler.start_in_background()
    """


async def lifespan():
    await db_init()

    # yield


app = FastAPI(
    title='BGITU Compass API',
    version='1',
    on_startup=[lifespan],
    docs_url='/supersecretdocs', redoc_url=None
)

app.mount("/static", StaticFiles(directory="public", html=False))

app.include_router(general_router)
app.include_router(administration_router)
app.include_router(updates_router)
app.include_router(users_router)
app.include_router(schedules_router)
app.include_router(accounts_router)
app.include_router(profiles_router)

# origins = [
#     "http://localhost",
#     "http://localhost:8000",
#     "http://bgitu-compass.ru",
#     "http://5.42.76.162/"
# ]

app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"],
                   )
