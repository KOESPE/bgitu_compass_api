import asyncio
import datetime

import re

from pprint import pprint

import openpyxl
from openpyxl.cell import MergedCell
from openpyxl.worksheet.worksheet import Worksheet

from config import EXCEL_DIRECTORY
from data import WEEKDAY_INDEX, STRANGE_PHRASES
from database.base import manage_subjects, manage_groups, db_init, insert_schedule, db_reset_schedules, db_drop_tables
from modules.excel_parser.excel_parser_functions import make_dict_day, find_classroom, extract_numbers, \
    standardize_names
from modules.schedule_managment.weekly_updates import weekly_management_schedule


async def initialize_excel_schedules(full_reset=False,
                                     reset_schedules=False,
                                     reset_schedules_and_subjects=False):
    """
    Инициализация расписания из excel файлов в db.groups.rawSchedule

    :param full_reset: drop tables + init tables
    :param reset_schedules: Delete Lessons
    :return:
    """
    is_force_update = True  # Флаг обновления group.forceUpdateVersion

    if full_reset:
        await db_drop_tables()
        await db_init()

    if reset_schedules:
        await db_reset_schedules()

    if reset_schedules_and_subjects:
        await db_reset_schedules(and_subjects=True)
        is_force_update = True

    excel_files = [file for file in EXCEL_DIRECTORY.iterdir() if '.xlsx' in file.name]

    for file in excel_files:
        is_magistracy = True if 'маг' in file.name else False  # Добавление надписи (маг.) в конце названия группы

        wb = openpyxl.load_workbook(file)
        sheet = wb.worksheets[0]

        # MAGISTRACY PARSER ————————————————————————————————————
        if is_magistracy:
            print("\n\n\n\n\nМАГААААААААААААААААААААААААААААаа!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\n\n\n")
            building_row = 0
            group_name = ''
            is_subgroups = False

            # Ищем название группы
            for row in range(1, 20):  # 20 — просто число с запасом
                value: str = parse_cell(sheet, row, col=2)
                print(value)
                if value is not None:
                    match = re.search(r"группа\s+(\w+-\d+)", value)
                    if match:
                        group_name = match.group(1)

                    if 'корпус' in value:
                        building_row = row
                        break
            if group_name == '':
                value = parse_cell(sheet, row=building_row, col=4)
                split_string = value.casefold().split(' ')
                group_index = split_string.index("группа")
                group_name = split_string[group_index + 1]
                is_subgroups = True
                building_row += 1  # В таком случае "корпус" растянут на 2 клетки
            print('building_row: ', building_row)

            groups_id = []
            if is_subgroups:
                groups_id.append(await manage_groups(f'{group_name}(А)(маг.)'))
                groups_id.append(await manage_groups(f'{group_name}(Б)(маг.)'))
            else:
                groups_id.append(await manage_groups(f'{group_name}(маг.)'))

            groups_range_in_file = 2 if is_subgroups else 1  # Есть в одном файле группы А и Б, их нужно итерировать
            for additional_index in range(groups_range_in_file):
                schedule_week = {
                    "first_week": {},
                    "second_week": {}
                }
                schedule_per_day_first_week = []
                schedule_per_day_second_week = []

                weekday_last = 'пятница'
                # Перебираем ячейки
                lesson_step = 2 if is_subgroups else 1  # У строителей с группами две ячейки на урок
                for group_row in range(building_row, sheet.max_row + 1, lesson_step):
                    # идем по строчкам вниз и берем сразу на первую и вторую неделю если not is_subgroups
                    weekday_now = parse_cell(sheet, row=group_row, col=1)
                    print('group_row: ', group_row, ' weekday: ', weekday_now)
                    if weekday_now not in ['пятница', 'суббота']:  # Еще не дошли до учебных дней
                        continue
                    if weekday_now == '' or weekday_now is None:
                        break
                    if weekday_now != weekday_last:  # Смена дней
                        # ТУТ ПОМЕНЯЛОСЬ МЕСТАМИ НАМЕРЕНО!!!!!!!!!!!!!!!(приколы второго семестра)
                        schedule_week['second_week'][
                            WEEKDAY_INDEX[weekday_last.lower()]] = schedule_per_day_first_week
                        schedule_week['first_week'][
                            WEEKDAY_INDEX[weekday_last.lower()]] = schedule_per_day_second_week

                        weekday_last = weekday_now
                        schedule_per_day_first_week = []  # Данные на один день на первую неделю
                        schedule_per_day_second_week = []

                    if is_subgroups:
                        lesson_first_week = parse_day(sheet, row=group_row, col=4 + additional_index)
                        lesson_second_week = lesson_first_week
                    else:
                        lesson_first_week = parse_day(sheet, row=group_row, col=4)
                        lesson_second_week = parse_day(sheet, row=group_row, col=5)

                    if lesson_first_week is not None:
                        subject_id = await manage_subjects(lesson_first_week.get('subjectName'), groups_id[additional_index])
                        day_template = make_dict_day(data=lesson_first_week, subject_id=subject_id)
                        schedule_per_day_first_week.append(day_template)

                    if lesson_second_week is not None:
                        subject_id = await manage_subjects(lesson_second_week.get('subjectName'), groups_id[additional_index])
                        day_template = make_dict_day(data=lesson_second_week, subject_id=subject_id)
                        schedule_per_day_second_week.append(day_template)
                # Закончили парсить группу и заносим последние данные
                schedule_week['second_week'][
                    WEEKDAY_INDEX[weekday_last.lower()]] = schedule_per_day_first_week
                schedule_week['first_week'][
                    WEEKDAY_INDEX[weekday_last.lower()]] = schedule_per_day_second_week
                await insert_schedule(groups_id[additional_index], schedule_week, is_force_update)

        else:  # БАК и СПО
            # Parsing all groups one by one
            all_group_columns = sheet.max_column
            for group_column in range(4, all_group_columns + 1):
                group_name = parse_cell(sheet=sheet, row=3, col=group_column)
                if group_name is not None:  # Sometimes we are still getting empty cells despite sheet.max_column
                    group_name = group_name.upper()
                    group_name = group_name.replace(' ', '')  # Unnecessary spaces
                    group_name = group_name.replace('/', '-')  # Да, и такие "нововведения" бывают

                    if group_name.lower() == 'а' or group_name.lower() == 'б':  # Handling subgroups
                        """
                        There is can be magic line break that I can`t handle with .replace \r\n \r \n
                        # " ИСП(спо)-109-2
                        # 1"	
                        """
                        group_name = (parse_cell(sheet, row=2, col=group_column).split())[0] + f'({group_name})'
                    if 'спо' in group_name.lower():
                        group_name = group_name.replace('спо', 'СПО')

                    group_id = await manage_groups(group_name)

                    # Finally got the name of the group, let's fetch schedule
                    schedule_week = {
                        "first_week": {},
                        "second_week": {}
                    }

                    # Данные на один день на первую неделю
                    schedule_per_day_first_week = []
                    schedule_per_day_second_week = []

                    weekday_last = parse_cell(sheet, row=4, col=1)  # Запоминаем последний день недели

                    for group_row in range(4, sheet.max_row + 1, 2):  # Идем вниз по столбцу

                        weekday_now = parse_cell(sheet, row=group_row, col=1)

                        # Если вместо "понедельник" в weekday_last получаем, например "вторник" (и не None)
                        # значит день закончился и пора записать его в словарь с ключем в виде цифры (1,2...)
                        if weekday_now != weekday_last:  # добавил and weekday_now is not None
                            # ТУТ ПОМЕНЯЛОСЬ МЕСТАМИ НАМЕРЕНО!!!!!!!!!!!!!!!(приколы второго семестра)
                            schedule_week['second_week'][
                                WEEKDAY_INDEX[weekday_last.lower()]] = schedule_per_day_first_week
                            schedule_week['first_week'][
                                WEEKDAY_INDEX[weekday_last.lower()]] = schedule_per_day_second_week

                            if not((weekday_now is None) or (weekday_now == '')):  # Закончилась учебная неделя группы
                                weekday_last = weekday_now
                                schedule_per_day_first_week = []  # Данные на один день на первую неделю
                                schedule_per_day_second_week = []

                        # Занятие на четной и нечетной неделе
                        lesson_first_week = parse_day(sheet, row=group_row, col=group_column)
                        lesson_second_week = parse_day(sheet, row=group_row + 1, col=group_column)

                        if lesson_first_week is not None:
                            subject_id = await manage_subjects(lesson_first_week.get('subjectName'), group_id)
                            day_template = make_dict_day(data=lesson_first_week, subject_id=subject_id)
                            schedule_per_day_first_week.append(day_template)

                        if lesson_second_week is not None:
                            subject_id = await manage_subjects(lesson_second_week.get('subjectName'), group_id)
                            day_template = make_dict_day(data=lesson_second_week, subject_id=subject_id)
                            schedule_per_day_second_week.append(day_template)

                    # Закончили парсить группу
                    schedule_week['second_week'][
                        WEEKDAY_INDEX[weekday_last.lower()]] = schedule_per_day_first_week
                    schedule_week['first_week'][
                        WEEKDAY_INDEX[weekday_last.lower()]] = schedule_per_day_second_week
                    await insert_schedule(group_id, schedule_week, is_force_update)

                else:  # Группы в файле закончились
                    break
    if full_reset or reset_schedules or reset_schedules_and_subjects:
        await weekly_management_schedule()


def parse_cell(sheet: Worksheet, row, col, using_merged=True):
    cell = sheet.cell(row=row, column=col)
    if using_merged:
        if isinstance(cell, MergedCell):
            for merged_range in sheet.merged_cells.ranges:
                if cell.coordinate in merged_range:
                    cell = sheet.cell(row=merged_range.min_row, column=merged_range.min_col)
                    break
        else:
            cell = sheet.cell(row, col)
        value = cell.value  # Plain text
    else:
        value = cell.value
    return value


col_weekday = 1
col_time_1_building = 2
col_time_2_building = 3


def parse_day(sheet: Worksheet, row, col):
    """
    Парсинг в пределах одной пары
    :param sheet: Таблица из файла
    :param row: Строка
    :param col: Столбец
    """
    cell = sheet.cell(row=row, column=col)
    if isinstance(cell, MergedCell):
        for merged_range in sheet.merged_cells.ranges:
            if cell.coordinate in merged_range:
                cell = sheet.cell(row=merged_range.min_row, column=merged_range.min_col)
                break
    else:
        cell = sheet.cell(row, col)
    value = cell.value  # Текст ячейки
    print(value)
    if (value is None) or (value == '') or (value == ' '):  # Обработка пустоты
        return None

    # Проверка на второй корпус по цвету текста
    building = 1
    if cell.font.color is not None:
        if cell.font.color.rgb == 'FFFF0000' or cell.font.color.indexed == 10:
            building = 2

    # Проверка на тип занятия по bold
    if cell.font.bold:
        is_lecture = True
    else:
        is_lecture = False

    # Следуя из корпуса получаем время
    if building == 2:
        lesson_time = parse_cell(sheet, row, col_time_2_building)
    else:
        lesson_time = parse_cell(sheet, row, col_time_1_building)

    try:
        lesson_time = lesson_time.split('-')
        start_at = datetime.datetime.strptime(lesson_time[0], '%H.%M').time()
        end_at = datetime.datetime.strptime(lesson_time[1], '%H.%M').time()
    except (ValueError, AttributeError) as e:  # Какая-то некорректная ячейка, не смог отловить в свое время ошибку
        return None

    value: str = value.replace("\n", " ")  # Ненужные переносы

    # Обработка фраз "консп." и временное удаления для корректной работы алгоритмы
    strange_phrase = ''
    if '(' in value and ')' in value:
        strange_phrase = value[value.find('('):value.find(')') + 1]
        value = value.replace(strange_phrase, '')

    # В строчках бывает очень много пробелов
    for i in range(2, 30):
        value = value.replace(' ' * i, ' ')

    # Основа алгоритма — для вытаскивания данных из ячейки
    str_list = value.split(' ')
    str_list = list(filter(None, str_list))  # Убираем '' из списка
    str_list_classrooms = str_list.copy()  # Сохранение оригинала для логики преподавателей
    if len(str_list) == 0:  # В некоторых строчках есть непонятный невидимый символ переноса
        return None

    classrooms_algorithm = extract_numbers(str_list)
    classrooms = classrooms_algorithm['classrooms']
    str_list = classrooms_algorithm['str_list_no_classrooms']

    print('str_list_no_classrooms: ', str_list)
    print('str_list_CLASSROOMS: ', str_list_classrooms)

    print('classrooms: ', classrooms)
    if bool(classrooms):  # Самая обычная ячейка
        if len(classrooms) == 1:
            classroom = classrooms[0]

            """ Обработка спец символов:
            / — разделение на чет/нечет - определяем по клетке
            : или ; - просто второй кабинет, ничего не делаем """
            if '/' in classroom:
                lesson_time = parse_cell(sheet, row, col_time_1_building)
                next_lesson_time = parse_cell(sheet, row + 1, col_time_1_building)
                if lesson_time == next_lesson_time:  # Значит это первая неделя, возвращаем число перед тире
                    classroom = classroom.split('/')[0] + f'({classroom.split("/")[1]})'
                else:
                    classroom = classroom.split('/')[1] + f'({classroom.split("/")[0]})'

            # Странное написание преподавателя — Ситуация вида "СальниковаН.А."
            if str_list_classrooms[-2].replace('/', '').replace(':', '').replace(';', '').isdigit():
                teacher = str_list[-1]
                del str_list[-1:]
            else:
                teacher = str_list[-2] + ' ' + str_list[-1]
                del str_list[-2:]
            # print('after teacher logic: ', str_list)

        else:  # Иногда бывает два кабинета в одной ячейке. !!! В этом случае первое значение — группа А, второе — Б
            # print('\n\n\n\n\n\nДВА ПРЕПОДА ДВА ПРЕПОДА ДВА ПРЕПОДАДВА ПРЕПОДАДВА ПРЕПОДА ДВА ПРЕПОДА ДВА ПРЕПОДА ДВА ПРЕПОДА \n\n\n\n')
            # print('str_list_no_classrooms: ', str_list)
            # print('str_list_classrooms: ', str_list_classrooms)
            # print('classrooms: ', classrooms)

            right_cell_value = parse_cell(sheet, row, col + 1)
            if cell.value == right_cell_value:
                classroom = classrooms[0]

                str_list.remove(classrooms[0])
                str_list.remove(classrooms[1])

                teacher = str_list[-4] + ' ' + str_list[-3]
            else:
                classroom = classrooms[1]

                str_list.remove(classrooms[0])
                str_list.remove(classrooms[1])

                teacher = str_list[-2] + ' ' + str_list[-1]
            del str_list[-4:]
        teacher = standardize_names(teacher)  # Правим написание преподавателя

        subject_name = ' '.join(str_list)
        if classroom.upper() == 'ДОТ':
            building = 'ДОТ'
            classroom = 'ДОТ'

    else:  # Преподаватель отсутствует и строчка из себя представляет название предмета
        subject_name = ' '.join(str_list)
        classroom = ''
        teacher = ''
        is_lecture = False

    if len(strange_phrase) > 0:
        subject_name += ' ' + strange_phrase
    subject_name = ' '.join(str_list)

    return {
        "subjectName": subject_name,
        "building": str(building),
        "startAt": start_at,
        "endAt": end_at,
        "classroom": classroom,
        "teacher": teacher,
        "isLecture": is_lecture
    }

def parse_group_mag(sheet: Worksheet, row, col):
    ...



def parse_schedule_file():
    ...

#########################
# OLD OR FOR THE FUTURE #
#########################

    # if '.' in str_list[-1]:  # Самая обычная ячейка
    #     if str_list[-2].isdigit():  # Cитуация вида "СальниковаН.А."
    #         teacher = str_list[-1]
    #     else:
    #         teacher = str_list[-2] + ' ' + str_list[-1]
    #
    #     # Иногда инициалы без пробелов ????????????????????????????????????????????????????????????????????????????
    #     if len(str_list) <= 3:
    #         classrooms_data = find_classroom(str_list[:-1])  # Тут должны остаться только название и кабинет
    #     else:
    #         classrooms_data = find_classroom(str_list[:-2])
    #     # Не трогать названия ниже, используются для логики еще ниже
    #     classroom = classrooms_data[0][0]
    #     classroom_index = classrooms_data[1][0]
    #
    #     subject_name = ' '.join(str_list[:classroom_index])
    #     if classroom.upper() == 'ДОТ':
    #         building = 'ДОТ'
    #
    #     if len(classrooms_data[0]) > 1:  # Иногда бывает два кабинета в одной ячейке
    #         # В этом случае первое значение — группа А, второе — Б
    #         # find_classroom: [['430', '229'], [2, 5]]
    #         right_cell_value = parse_cell(sheet, row, col + 1)
    #
    #         if cell.value == right_cell_value:
    #             classroom = classrooms_data[0][0]
    #             classroom_index = classrooms_data[1][0]
    #             teacher = str_list[classroom_index + 1] + ' ' + str_list[classroom_index + 2]
    #         else:
    #             classroom = classrooms_data[0][1]
    #             classroom_index = classrooms_data[1][1]
    #             teacher = str_list[classroom_index + 1] + ' ' + str_list[classroom_index + 2]
    #     teacher = standardize_names(teacher)
    #
    #     """ Фиксим ужас с спец. символами
    #     : или ; - просто второй кабинет
    #     / разделение на чет/нечет - определяем по клетке
    #     """
    #     # ['Математика', '314/226', 'Камозина', 'О.В.']
    #     # find: [['О.В.'], [3]]
    #
    #     if '/' in classroom:
    #         lesson_time = parse_cell(sheet, row, col_time_1_building)
    #         next_lesson_time = parse_cell(sheet, row + 1, col_time_1_building)
    #         if lesson_time == next_lesson_time:  # Значит это первая неделя, возвращаем число перед тире
    #             classroom = classroom.split('/')[0] + f'({classroom.split("/")[1]})'
    #         else:
    #             classroom = classroom.split('/')[1] + f'({classroom.split("/")[0]})'
    #     if ':' in classroom:
    #         classroom = classroom.replace(':', ';')



    #
    # if weekday_now != weekday_last:
    #     if (weekday_now is None) or (weekday_now == ''):  # Закончилась учебная неделя группы
    #         # Вносим последний день недели
    #         # ТУТ ПОМЕНЯЛОСЬ МЕСТАМИ НАМЕРЕНО!!!!!!!!!!!!!!!(приколы второго семестра)
    #         schedule_week['second_week'][
    #             WEEKDAY_INDEX[weekday_last.lower()]] = schedule_per_day_first_week
    #         schedule_week['first_week'][
    #             WEEKDAY_INDEX[weekday_last.lower()]] = schedule_per_day_second_week
    #     else:
    #         schedule_week['second_week'][
    #             WEEKDAY_INDEX[weekday_last.lower()]] = schedule_per_day_first_week
    #         schedule_week['first_week'][
    #             WEEKDAY_INDEX[weekday_last.lower()]] = schedule_per_day_second_week