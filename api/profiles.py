import datetime
import random
import string
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, Body
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse

from models.api import payloads

profiles_router = APIRouter()

@profiles_router.post('/updateBio')
async def update_bio(data: payloads.Profile):
    ...

