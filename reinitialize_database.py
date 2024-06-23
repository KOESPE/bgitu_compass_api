import asyncio

from modules.excel_parser.timetable_excel import initialize_excel_schedules

if __name__ == '__main__':
    print('Если вы продолжите, то будет DROP всех таблиц и инициализация моделей таблиц')
    print('Введите "YES" чтобы продолжить')
    if input() == 'YES':
        asyncio.run(initialize_excel_schedules(full_reset=True))