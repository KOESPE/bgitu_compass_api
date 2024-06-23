from datetime import date, time
from typing import Optional, List

from pydantic import BaseModel, HttpUrl, Field


class Credentials(BaseModel):
    accessToken: str
    refreshToken: str
    expirationDate: str


class RegisterGuest(BaseModel):
    userId: int
    groupId: int
    groupName: str
    credentials: Credentials


class RegisterEosUser(BaseModel):
    userId: int
    eosUserId: int
    groupId: Optional[int] = None
    groupName: Optional[str] = None
    credentials: Credentials


class AccountData(BaseModel):
    userId: int
    eosUserId: Optional[int] = None
    groupId: Optional[int] = None
    groupName: Optional[str] = None
    fullName: Optional[str] = None
    avatarUrl: Optional[HttpUrl] = None
    role: str
    permissions: list
    additionalData: dict


class UpdateUUID(BaseModel):
    user_id: int


class TeacherLocationPerLesson(BaseModel):
    classroom: str
    building: str
    isLecture: bool
    lessonDate: date
    startAt: time
    endAt: time
    weekday: int