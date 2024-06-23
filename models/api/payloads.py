from datetime import date
from typing import Optional, List

from fastapi import UploadFile, File, Form
from pydantic import BaseModel, HttpUrl, Field


class RegisterGuest(BaseModel):
    appUUID: str
    groupId: int
    groupName: str


class UserAuth(BaseModel):
    login: str
    password: str


class RegisterEosUser(BaseModel):
    userId: Optional[int] = None
    eosUserId: int
    eosGroupName: str
    fullName: str
    avatarUrl: HttpUrl


class DifferentEosGroupName(BaseModel):
    groupId: int
    groupName: str


class StatisticsBody(BaseModel):
    userId: int
    lastActivity: date
    apiVersion: int
    groupName: str
    data: Optional[dict] = None


class CMTokens(BaseModel):
    tokenType: str
    token: str


class UploadUpdate(BaseModel):
    versionCode: int
    forceUpdateVersions: List[int]
    downloadUrl: str


class DatabaseAction(BaseModel):
    action: str = Field(
        description="The database action to perform",
        pattern=r"^full_reset|reset_schedules|reset_schedules_and_subjects|weekly_management_schedule|just_update_raw_schedules$"
    )


class Profile(BaseModel):
    fullname: Optional[str]
    bio: str
    tg: str
    vk: str
