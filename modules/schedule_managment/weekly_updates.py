import asyncio
import datetime

from database.base import get_raw_schedules, insert_lesson, is_schedule_filled, clean_schedules, up_schedule_version
from models.database.models import Lessons


async def weekly_management_schedule():
    """
    Из постоянного raw_schedule из бд в json —> db.Lesson
    """
    await clean_schedules()
    all_schedules = await get_raw_schedules()  # select(Groups.id, Groups.rawSchedule)
    for group in all_schedules:

        json_schedule: dict = group.rawSchedule
        today_date = datetime.date.today()
        for week in range(-2, 4):
            current_date = today_date + datetime.timedelta(weeks=week)
            monday_date = current_date - datetime.timedelta(days=(today_date.weekday()) % 7)
            if not await is_schedule_filled(group_id=group[0], monday_date=monday_date):
                await up_schedule_version(group.id)  # Чтобы приложение обновило расписание

                current_week_number = int(current_date.strftime("%V"))
                monday_date = datetime.datetime.strptime(f'{current_date.year} {current_week_number} 1',
                                                         '%Y %W %w').date()  # %w - weekday, %W - week_number
                if current_week_number % 2 == 0:
                    week_type = 'first_week'
                else:
                    week_type = 'second_week'
                for day in json_schedule[week_type]:  # Пройдемся по всем дням недели
                    lesson_date = monday_date + datetime.timedelta(days=int(day)-1)
                    for lesson in json_schedule[week_type][day]:
                        new_lesson = Lessons(subjectId=lesson.get("subjectId"),
                                             lessonDate=lesson_date,
                                             weekday=int(day),
                                             startAt=datetime.datetime.strptime(lesson.get("startAt"), '%H:%M:%S').time(),
                                             endAt=datetime.datetime.strptime(lesson.get("endAt"), '%H:%M:%S').time(),
                                             building=str(lesson.get("building")),
                                             classroom=lesson.get("classroom"),
                                             isLecture=lesson.get("isLecture"),
                                             teacher=lesson.get("teacher")
                                             )
                        await insert_lesson(new_lesson)


if __name__ == '__main__':
    asyncio.run(weekly_management_schedule())
