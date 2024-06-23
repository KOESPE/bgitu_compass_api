import re


def make_dict_day(data, subject_id):
    template = dict(subjectId=subject_id,
                    building=data.get('building'),
                    startAt=str(data.get('startAt')),
                    endAt=str(data.get('endAt')),
                    classroom=data.get('classroom'),
                    teacher=data.get('teacher'),
                    isLecture=data.get('isLecture'))
    return template


def find_classroom(value_list: list):
    """
    [[classrooms], [classroom_indexes]]
    @param value_list
    """
    # смотрим, сколько цифр можно сделать интом
    # если два/одно число, то возвращаем это число строкой
    # если ноль, то просто берем последний элемент в строке, таким образом точно получаем кабинет
    isdigit_counter = 0
    classrooms = []
    classroom_indexes = []

    for value in value_list:
        # бывает 123 / 456, а ситуацию 123/456 обработает алгоритм дальше
        if value == '/':
            slash_index = value_list.index(value)
            classrooms.append(value_list[slash_index - 1] + '/' + value_list[slash_index + 1])
            classroom_indexes.append(slash_index - 1)
            return [classrooms, classroom_indexes]

    for value in value_list:
        if value.isdigit():
            isdigit_counter += 1
            classroom_indexes.append(value_list.index(value))
            classrooms.append(value)

    if isdigit_counter > 0:
        return [classrooms, classroom_indexes]
    else:  # Возврщается последнее
        return [[value_list[-1]], [value_list.index(value_list[-1])]]


def extract_numbers(str_list: list):
    """
    Returns 'classrooms' and 'str_list_no_classrooms'
    """
    # Регулярное выражение для поиска чисел
    str_list_saved = str_list.copy()
    number_regex = r"\d+"
    numbers = []

    for element in str_list:
        # Проверка на пустые элементы
        if not element:
            continue

        # Если элемент содержит дробь, добавляем его как есть
        if "/" in element or ":" in element or ";" in element.upper():
            numbers.append(element)

        # Если элемент не содержит дробь, просто добавляем его в список
        else:
            if (re.match(number_regex, element) and element not in ['1C', '1С']) or element.upper() == 'ДОТ':
                numbers.append(element)

    for num in numbers:
        str_list_saved.remove(num)

    # Объединение элементов, не являющихся дробью (, '314', '/211', )
    if numbers and not all(x.count("/") for x in numbers):
        fixed_numbers = "/".join(numbers)
        fixed_numbers = fixed_numbers.replace("//", "/")
        numbers = [fixed_numbers]

    # Заплатка на получение classroom вида "1С/ДОТ"
    # if len(numbers) > 0:
    #     if 'ДОТ' in numbers[0]:
    #         numbers = ['ДОТ']

    return {'classrooms': numbers,
            'str_list_no_classrooms': str_list_saved}


def standardize_names(s):
    s = s.replace(',', '')

    s = s.strip()
    # Замена точек и пробелов на символ ';'
    s = re.sub(r'[. ]', ';', s)
    while ';' in s:
        s = s.replace(';;', ' ').replace(';', ' ')

    s = s.strip()
    buff = list(s)
    buff[-2] = '.'
    s = ''.join(buff)

    # Если последний символ не точка, добавить точку
    if s[-1] != '.':
        s += '.'
    return s
