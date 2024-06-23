import re
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.base import get_session_fastapi
from locals import loc
from models.api import responses
from models.database.models import Lessons, Subjects, Groups

schedules_router = APIRouter(tags=['Schedules'])


@schedules_router.get('/lessons')
async def get_lessons(groupId: int, startAt: date, endAt: date, session: AsyncSession = Depends(get_session_fastapi)):
    query = select(Lessons.id, Lessons.subjectId, Lessons.lessonDate, Lessons.weekday,
                   Lessons.startAt, Lessons.endAt, Lessons.building, Lessons.classroom,
                   Lessons.isLecture, Lessons.teacher).join(Subjects) \
        .filter(Subjects.groupId == groupId).filter(Lessons.lessonDate.between(startAt, endAt))
    result = await session.execute(query)
    lessons_list = [dict(r._mapping) for r in result]
    return lessons_list


@schedules_router.get('/scheduleVersion')
async def get_schedule_version(request: Request, groupId: int,
                               session: AsyncSession = Depends(get_session_fastapi)):
    """
    В headers есть "DataVersion"
    В новой версии приложения ответ в json теперь, а в старой — int
    """
    version = request.headers.get("DataVersion")
    if version is not None:
        query = await session.execute(
            select(Groups.scheduleVersion, Groups.forceUpdateVersion).where(Groups.id == groupId))
        schedule_version = [dict(r._mapping) for r in query]
        return schedule_version[0]
    else:
        query = await session.execute(select(Groups.scheduleVersion).where(Groups.id == groupId))
        schedule_version = query.scalar()
        return int(schedule_version)


@schedules_router.get('/teacherSearch')
async def find_teacher(search_query: Optional[str] = Query(None, alias="searchQuery", description="Поисковой запрос, регистр не важен"),
                       teacher: Optional[str] = Query(None, description="Точное совпадение"),
                       date_from: Optional[date] = Query(None, alias="dateFrom"),
                       date_to: Optional[date] = Query(None, alias="dateTo"),
                       session: AsyncSession = Depends(get_session_fastapi)):
    if teacher:
        if not is_valid_russian(teacher):
            raise HTTPException(detail='No results', status_code=404)

        db_search_query = await session.execute(select(
            Lessons.classroom,
            Lessons.isLecture,
            Lessons.startAt,
            Lessons.endAt,
            Lessons.building,
            Lessons.lessonDate,
            Lessons.weekday,
        ).filter(
            Lessons.lessonDate.between(date_from, date_to),
            Lessons.teacher.like('%' + teacher.title() + '%'),  # .like оставляем на тот случай, если в паре два препода
        ).group_by(
            Lessons.classroom,
            Lessons.isLecture,
            Lessons.startAt,
            Lessons.endAt,
            Lessons.building,
            Lessons.lessonDate,
            Lessons.weekday,
        ).order_by(
            Lessons.lessonDate,
            Lessons.startAt
        ))

        search_results = db_search_query.fetchall()
        teachers_list = [responses.TeacherLocationPerLesson(classroom=resp.classroom,
                                                            building=resp.building,
                                                            isLecture=resp.isLecture,
                                                            lessonDate=resp.lessonDate,
                                                            startAt=resp.startAt,
                                                            endAt=resp.endAt,
                                                            weekday=resp.weekday) for resp in search_results]
        return teachers_list
    elif search_query:
        if not is_valid_russian(search_query):
            raise HTTPException(detail='No results', status_code=404)

        db_search_query = await session.execute(
            select(Lessons.teacher).distinct().filter(
                Lessons.teacher.like('%' + search_query.title() + '%')
            ).order_by(Lessons.teacher))
        teachers = [teacher.teacher for teacher in db_search_query.fetchall()]

        return teachers
    else:
        raise HTTPException(detail=loc('errors', 'no_action'), status_code=400)


def is_valid_russian(text: str) -> bool:
    return bool(re.match(r'^[\w\s\.]+$', text))
