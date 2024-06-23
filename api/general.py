from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from fastapi import Depends
from fastapi.security import HTTPBearer

from fastapi.templating import Jinja2Templates

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse

from config import PUBLIC_DIRECTORY
from models.api import responses
from models.database.models import Groups, Subjects
from database.base import get_session_fastapi, search_group, get_session_fastapi_bot

general_router = APIRouter()
security = HTTPBearer()
templates = Jinja2Templates(directory=PUBLIC_DIRECTORY)


@general_router.get('/groups', tags=['Schedules'],
                    responses={
                        200: {"model": List[responses.Groups]}
                    })
async def get_groups(
        group_name: Optional[str] = Query(None, alias="groupName", description="Точное совпадение"),
        group_id: Optional[int] = Query(None, alias="groupId"),
        search_query: Optional[str] = Query(None, alias="searchQuery",
                                            description="Поисковой запрос, регистр не важен"),
        session: AsyncSession = Depends(get_session_fastapi),
):
    """
    Без аргументов — все группы
    """
    if search_query is not None:
        return JSONResponse(await search_group(search_query), status_code=200)

    query = select(Groups.id, Groups.name)
    if group_name:
        query = query.where(Groups.name == group_name.upper())
    elif group_id:
        query = query.where(Groups.id == group_id)

    result = await session.execute(query)
    groups_list = [dict(r._mapping) for r in result]

    if not groups_list and (group_name or group_id):
        raise HTTPException(status_code=404, detail="Group not found")

    return JSONResponse(groups_list, status_code=200)


@general_router.get('/subjects', tags=['Schedules'],
                    responses={
                        200: {"model": List[responses.Subjects]}
                    })
async def get_subjects(groupId: int, session: AsyncSession = Depends(get_session_fastapi)):
    query = select(Subjects.id, Subjects.name).where(Subjects.groupId == groupId)
    result = await session.execute(query)
    subjects_list = [dict(r._mapping) for r in result]
    return JSONResponse(subjects_list, status_code=200)


# Joke
@general_router.get("/", response_class=HTMLResponse)
async def main_page():
    """
    RickRoll если кто-то захочет исследовать api
    """
    return RedirectResponse('https://youtu.be/-cctf5hP900?si=Qm9q8RzFWVyGCKrH&t=466')


@general_router.get('/getGroupIDByTGID',
                    responses={
                        200: {"model": responses.GetDataByTGID},
                        404: {"description": "User not found"}
                    })
async def get_group_id_by_telegram_id(telegramID: int,
                                      session: AsyncSession = Depends(get_session_fastapi_bot)):
    query = text("SELECT users.group_id, users.group_name FROM users WHERE users.id = :val")
    result = await session.execute(query, {'val': telegramID})
    row = result.fetchone()

    if row:
        return JSONResponse({
            'group_id': row.group_id,
            'group_name': row.group_name
        }, status_code=200)
    else:
        raise HTTPException(status_code=404, detail="User not found")
