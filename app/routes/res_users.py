# -*- coding: utf-8 -*-
from fastapi.security import HTTPBearer
from fastapi import APIRouter
from tools.jwt_token import decode_access_token, create_access_token
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import FastAPI, Depends
from typing import Annotated
from fastapi.responses import JSONResponse
from models.res_users import ResUsers
import logging

_logger = logging.getLogger(__name__)


# 使用 HTTPBearer 提取 Token
security = HTTPBearer()

def get_current_user(token: Annotated[HTTPAuthorizationCredentials, Security(security)]):
    _logger.info('token: {}'.format(token))
    token_data = decode_access_token(token.credentials)  # 验证和解析 Token
    return token_data


user_router = APIRouter()


@user_router.post('/login')
def user_login(user_info: ResUsers):
    _logger.info('user info: {}'.format(user_info))

    token = create_access_token(user_info.model_dump())
    return JSONResponse({
        'code': 200,
        'msg': 'success',
        'scheme': 'Bearer',
        'token': token
    })

@user_router.get('/info')
def user_info(user: Annotated[dict, Depends(get_current_user)]):
    return JSONResponse({
        'code': 200,
        'msg': 'success',
        'user': user
    })
