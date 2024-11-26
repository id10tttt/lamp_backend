# -*- coding: utf-8 -*-

import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer
from typing import Annotated
from datetime import datetime, timedelta, timezone
import logging

_logger = logging.getLogger(__name__)

# 秘钥和算法
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

LAMP_AUDIENCE = 'your-audience'
LAMP_ISSUER = 'your-issuer'


# 创建 Token 的函数
def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=30)):
    expire = datetime.now(timezone.utc) + expires_delta
    payload = dict(
        data.copy(),
        exp=expire,
        aud=LAMP_AUDIENCE,
        iss=LAMP_ISSUER,
    )
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# 解析和验证 Token 的函数
def decode_access_token(token: str):
    try:
        payload = jwt.decode(
            token,
            key=SECRET_KEY,
            algorithms=[ALGORITHM],
            options=dict(
                require=["exp", "aud", "iss"],
                verify_exp=True,
                verify_aud=True,
                verify_iss=True,
            ),
            audience=LAMP_AUDIENCE,
            issuer=LAMP_ISSUER,
        )
        _logger.info('payload: {}'.format(payload))
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
