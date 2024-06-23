import datetime
import random
import string

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import aiohttp as aiohttp
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from api.accounts import generate_token
from models.api import payloads
from config import DEFAULT_TIMEZONE, HOSTNAME_PORT
from data import FACULTIES, BIRTHDAY_MONTH_INDEX
from database.base import insert_user, get_session_fastapi
from models.database.models import Users, Accounts
from locals import loc


users_router = APIRouter(tags=['Пользователи'])

security = HTTPBearer()

"""


ИСПОЛЬЗУЕТСЯ ТОЛЬКО В СТАРЫХ ВЕРСИЯХ ПРИЛОЖЕНИЯ
осталось для обратной совместимости

"""

def generate_refresh_token():  # Временно за бессмысленностью нормальных токенов
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(64))


@users_router.post('/auth')  # OUTDATED
async def add_user(credentials: payloads.UserAuth, session: AsyncSession = Depends(get_session_fastapi)):
    # async def add_user(login: str, password: str):
    """
    accessToken, tokenExpireAt, refreshToken, name, surname, studentId, groupId, group_id, groupName
    """

    login = credentials.login
    password = credentials.password
    password = password.replace(' ', '')

    async with aiohttp.ClientSession() as session:
        auth_req = await session.post(url='https://eos.bgitu.ru/api/tokenauth',
                                      json={'userName': login,
                                            'password': password})
        auth_resp = await auth_req.json()
        if auth_resp.get('state') == -1:
            # Отключил по причине: можно получить спамблок
            # await tg_notif_auth_error(login, password, 'Неправильный логин или пароль')
            raise HTTPException(detail=loc('errors', 'wrong_credentials'), status_code=401)

        access_token = auth_resp.get('data').get('accessToken')
        print('access_token: ', access_token)
        student_id = abs(int(auth_resp.get('data').get('data').get('id')))
        print('student_id: ', student_id)

        user_data_req = await session.get(url=f'https://eos.bgitu.ru/api/UserInfo/Student?studentID={student_id}',
                                          cookies={'authToken': access_token})
        student_data = await user_data_req.json()

        if student_data.get('msg') != 'Информация о студенте':
            raise HTTPException(detail='Вы не являетесь студентом', status_code=401)

        student_data = student_data['data']
        print('student_data: ', student_data)
        name = student_data['name']
        surname = student_data['surname']
        middle_name = student_data['middleName']
        avatarUrl = 'https://eos.bgitu.ru' + student_data['photoLink']
        group_name = student_data['group']['item1'].upper()
        course = str(student_data['course'])
        department = student_data['kaf']['kafName']
        faculty = student_data['facul']['faculName']
        gradebook = student_data['numRecordBook']

        email = student_data['email']
        birthday_date = student_data['birthday']
        birthday_format = '%d %m %Y г.'
        for month in BIRTHDAY_MONTH_INDEX.keys():
            if month in birthday_date:
                birthday_date = birthday_date.replace(month, str(BIRTHDAY_MONTH_INDEX[month]))
        birthday_date = datetime.datetime.strptime(birthday_date, birthday_format).date()

        req = await session.get(url=f'{HOSTNAME_PORT}/groups?groupName={group_name}')
        group_id = (await req.json()).get('groupId')

        # Все супер
        if isinstance(group_id, int):
            group_id = int(group_id)
            refresh_token = generate_refresh_token()
            expires_in = auth_resp['data']['expiresIn']
            print('expires_in: ', expires_in)
            token_expire_at = (datetime.datetime.now(DEFAULT_TIMEZONE) +
                               datetime.timedelta(minutes=int(expires_in))).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            result = await insert_user(student_id, group_id, course, department, faculty,
                                       login, password, access_token, token_expire_at, refresh_token,
                                       name, surname, middle_name,
                                       birthday_date, gradebook, email, avatarUrl)
            return JSONResponse({'accessToken': access_token,
                                 'tokenExpireAt': token_expire_at,
                                 'refreshToken': refresh_token,
                                 'studentId': student_id},
                                status_code=200)
        else:
            # Проверям, что ошибка точно в отсутствии группы
            if student_data['faculty'].upper() in FACULTIES:
                raise HTTPException(detail=loc('errors', 'auth.app_not_available'),
                                    status_code=401)
            else:
                raise HTTPException(detail=loc('errors', 'auth.unknown_error'),
                                    status_code=400)


@users_router.get('/studentInfo')
async def get_user_info(credentials: HTTPAuthorizationCredentials = Depends(security),
                        session: AsyncSession = Depends(get_session_fastapi)):
    """
    200: studentId, groupId, refreshToken, telegramId, role, name, surname, middleName, permissions
    404: {'msg': 'Invalid accessToken or user doesn`t exist'}
    """
    access_token = credentials.credentials
    print('STDinfo: access_token: ', access_token)
    query = await session.execute(select(Users.studentId, Users.groupId, Users.course, Users.department, Users.faculty,
                                         Users.name, Users.surname, Users.middleName,
                                         Users.email, Users.gradebook,
                                         Users.role, Users.telegramId, Users.permissions, Users.firebaseToken,
                                         Users.avatarUrl).where(
        Users.accessToken == access_token))
    user_data = [dict(_._mapping) for _ in query]

    # Отдельно потому что json не понимает datetime.date
    query = await session.execute(select(Users.birthday).where(Users.accessToken == access_token))
    birthday = str(query.scalar())

    async with aiohttp.ClientSession() as session:
        req_group_name = await session.get(url=HOSTNAME_PORT + '/groups' + '?groupId=' + str(user_data[0]['groupId']))
        group_name = (await req_group_name.json()).get('groupName')

    if len(user_data) > 0:
        user_data[0]['groupName'] = group_name
        user_data[0]['birthday'] = birthday
        return JSONResponse(user_data[0], status_code=200)
    else:
        raise HTTPException(detail=loc('errors', 'invalid_token'), status_code=404)


@users_router.get('/refreshToken')
async def refresh_token(refreshToken: str, session: AsyncSession = Depends(get_session_fastapi)):
    """
    Этот запрос должен посылаться когда пришло время истечения accessToken.
    Если отправить запрос ранее — вернутся старые данные, как обновлять — так и не понял
    """
    query = await session.execute(select(Users).where(Users.refreshToken == refreshToken))
    user = query.scalar()

    query = await session.execute(select(Accounts).where(Accounts.refreshToken == refreshToken))
    account = query.scalar()

    if user and account is None:
        raise HTTPException(detail=loc('errors', 'invalid_token'), status_code=404)

    # # Авторизуемся и забираем данные
    # async with aiohttp.ClientSession() as session:
    #     auth_req = await session.post(url='https://eos.bgitu.ru/api/tokenauth',
    #                                   json={'userName': user.login,
    #                                         'password': user.password})
    #     auth_resp = await auth_req.json()
    #
    # if auth_resp.get('state') == -1:
    #     raise HTTPException(detail=loc('errors', 'wrong_credentials')+' (еос)', status_code=401)

    access_token = generate_token(token_type='access')
    refresh_token = generate_token(token_type='refresh')
    token_expire_at = (datetime.datetime.now(DEFAULT_TIMEZONE) +
                       datetime.timedelta(weeks=4)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    if user is not None:
        user.accessToken = access_token
        user.tokenExpireAt = token_expire_at
        user.refreshToken = refresh_token

    if account is not None:
        account.accessToken = access_token
        account.tokenExpireAt = token_expire_at
        account.refreshToken = refresh_token

    return JSONResponse({'accessToken': access_token,
                         'tokenExpireAt': token_expire_at,
                         'refreshToken': refresh_token},
                        status_code=200)


@users_router.post('/registerFirebaseToken')
async def register_firebase_token(firebaseToken: str,
                                  credentials: HTTPAuthorizationCredentials = Depends(security),
                                  session: AsyncSession = Depends(get_session_fastapi)):
    access_token = credentials.credentials
    query = await session.execute(select(Users).where(Users.accessToken == access_token))
    user = query.scalar()
    user.firebaseToken = firebaseToken
    await session.commit()



