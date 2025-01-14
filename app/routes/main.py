# -*- coding: utf-8 -*-

from fastapi import APIRouter
from .res_users import user_router


router = APIRouter()
router.include_router(user_router)
