# -*- coding: utf-8 -*-
import time
from os import access

from odoo import http
from ..controllers.response_code import ResponseCode
from odoo.http import request
from odoo.tools import ormcache
import requests
import decimal
import random
from calendar import timegm
from odoo.tools import config
import hashlib
import redis
import datetime
import json
import traceback
import jwt
from functools import wraps
import logging
from .rsa_utils import RSAUtils

from ..exceptions import (
    UnauthorizedInvalidToken
)

_logger = logging.getLogger(__name__)

ACCESS_TOKEN_DB = 2
DEFAULT_TOKEN_EXPIRE = 60 * 60 * 24 * 7
VALID_PAYLOAD_TIMESTAMP = 60 * 2 * 1000
PICKING_CACHE_EXPIRE = 60 * 60 * 24 * 7
ACCESS_TOKEN_REDIS_PREFIX = 'user:login:access:token'
ACCESS_TOKEN_REDIS_EXPIRE_PREFIX = 'user:login:access:token:expire'

LAMP_AUDIENCE = config.get('lamp_audience', 'efje234alzuc{')
LAMP_ISSUER = config.get('lamp_issuer', '4rued2owerc562roc!')
LAMP_JWT_SECRET = config.get('lamp_wt_secret', 'muTtratnax6ewrewrt<olologcit|c7')

STOCK_PICKING_CACHE_DB = 3
SHOPPING_CART_DB = 2
STOCK_PICKING_CACHE_PREFIX = 'USER:STOCK:PICKING:CACHE'
SHOPPING_CART_PREFIX = 'USER:SHOPPING:CART:CACHE'


def decimal_float_number(number, rounding='0.00'):
    decimal.getcontext().rounding = "ROUND_HALF_UP"
    res = decimal.Decimal(str(number)).quantize(decimal.Decimal(rounding))
    return float(res)


def get_redis_client(db):
    return redis.Redis(host=config.get('redis_host'), db=db, password=config.get('redis_password'),
                       port=config.get('redis_port'))


def get_sign_msg(mobile, timestamp, code):
    sign_str = '{},{},{}'.format(mobile, timestamp, code)
    sha256 = hashlib.sha256(sign_str.encode()).hexdigest()
    return sha256


def jwt_encode(payload, expire):
    """Encode and sign a JWT payload so it can be decoded and validated with
    _decode().

    The aud and iss claims are set to this validator's values.
    The exp claim is set according to the expire parameter.
    """
    payload = dict(
        payload,
        exp=timegm(datetime.datetime.utcnow().utctimetuple()) + expire,
        aud=LAMP_AUDIENCE,
        iss=LAMP_ISSUER,
    )
    return jwt.encode(payload, key=LAMP_JWT_SECRET, algorithm="HS256")


def jwt_decode(token, secret=LAMP_JWT_SECRET):
    """Validate and decode a JWT token, return the payload."""
    key = secret
    algorithm = "HS256"

    try:
        payload = jwt.decode(
            token,
            key=key,
            algorithms=[algorithm],
            options=dict(
                require=["exp", "aud", "iss"],
                verify_exp=True,
                verify_aud=True,
                verify_iss=True,
            ),
            audience=LAMP_AUDIENCE,
            issuer=LAMP_ISSUER,
        )
    except Exception as e:
        _logger.info("Invalid token: %s", e)
        raise UnauthorizedInvalidToken(description=str(e))
    return payload


def get_random_char(randon_num=6):
    random_list = random.sample('ABCDEFGHIJLMNOPQRSTUVWXYZ1234567890', randon_num)
    return ''.join(str(x) for x in random_list)


def get_random_login_code():
    random_list = random.sample('1234567890', 6)
    return ''.join(str(x) for x in random_list)


def generate_pick_code():
    random_list = random.sample('1234567890', 4)
    return ''.join(str(x) for x in random_list)


def get_datetime_format():
    req_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    return req_time


def get_lamp_order_number(prefix='RENTAL', randon_num=6):
    order_name = '{}/{}{}'.format(prefix, str(get_datetime_format()), get_random_char(randon_num=randon_num))
    return order_name


def get_wxa_access_token(appid, secret):
    req_url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}'.format(
        appid, secret
    )
    res = requests.get(req_url)
    result = res.json()
    return result


def get_wxa_user_openid(access_token, js_code):
    req_url = 'https://api.weixin.qq.com/wxa/getpluginopenpid?access_token={}'.format(access_token)
    payload_data = {
        'code': js_code
    }
    res = requests.post(req_url, data=payload_data)
    result = res.json()
    return result


@ormcache('access_token')
def get_wxa_user(access_token):
    wx_user = request.env['wxa.user'].sudo().search([
        ('user_uuid', '=', access_token),
        ('forbidden_user', '=', False)
    ])
    return wx_user


def check_access_token(access_token):
    try:
        decode_token = jwt_decode(access_token)
        uid = decode_token.get('uid')
        email = decode_token.get('email')

        redis_access_token = get_access_token_from_redis(email)

        # 单点登录
        if not redis_access_token:
            return False, 'Token异常/已过期'

        if redis_access_token.decode() != access_token:
            return False, 'Token异常/已过期, 不能同时登录，请重新登录!'

    except UnauthorizedInvalidToken as e:
        _logger.error('出现了错误: {}'.format(e))
        return False, e.description

    if decode_token.get('aud') != LAMP_AUDIENCE or decode_token.get('iss') != LAMP_ISSUER:
        return False, '签名验证失败!'

    partner_id = request.env['res.partner'].sudo().search([
        ('id', '=', uid)
    ])
    if not partner_id or len(partner_id) != 1:
        return False, '失败'

    if email != partner_id.email:
        return False, '签名验证失败!'

    http.request.partner_id = partner_id.id
    http.request.partner_mobile = partner_id.mobile
    return True, '成功!'


def response_text_message(message='fail'):
    return request.make_response(message, headers=[('Content-Type', 'text/html')])


def response_wechat_message(success=True, message='失败'):
    result = {
        'code': 'SUCCESS' if success else 'FAIL',
        'message': message
    }
    return request.make_response(
        headers={'Content-Type': 'json'},
        data=json.dumps(result)
    )


def response_json_success(data=None, message='成功'):
    result = ResponseCode.CODE_200
    if data is not None:
        result['data'] = data
    else:
        result['data'] = []

    if message:
        result['message'] = message
    # return result
    return request.make_response(
        headers={'Content-Type': 'json'},
        data=json.dumps(result)
    )


def response_json_error(code, data=None, message=None):
    custom_code = 'CODE_{}'.format(code)
    if hasattr(ResponseCode, custom_code):
        result = getattr(ResponseCode, custom_code)
    else:
        result = ResponseCode.CODE_403
    if message:
        result['message'] = message
    if data:
        result['data'] = data
    else:
        result['data'] = []
    return request.make_response(
        headers={'Content-Type': 'json'},
        data=json.dumps(result)
    )


def response_http_json_error(code, data=None, message=None):
    custom_code = 'CODE_{}'.format(code)
    if hasattr(ResponseCode, custom_code):
        result = getattr(ResponseCode, custom_code)
    else:
        result = ResponseCode.CODE_403
    if message:
        result['message'] = message
    if data:
        result['data'] = data
    else:
        result['data'] = []
    return result


def decrypt_payload_data(http_request):
    payload_data = json.loads(http_request.httprequest.data)
    try:
        if 'data' in payload_data:
            encrypt_msg = payload_data.get('data')
            decrypt_payload = RSAUtils().decrypt_rsa_message(encrypt_msg)
            _logger.info('decrypt_payload: {}'.format(decrypt_payload))
            decrypt_payload_json = json.loads(decrypt_payload)
            # _logger.info('decrypt_payload_json: {}'.format(decrypt_payload_json))
            if 'timestamp' not in decrypt_payload_json:
                return False
            now_timestamp = int(time.time() * 1000)
            payload_timestamp = decrypt_payload_json.get('timestamp')
            # _logger.info('当前时间: {}, 参数: {}'.format(now_timestamp, payload_timestamp))
            if now_timestamp - int(payload_timestamp) >= VALID_PAYLOAD_TIMESTAMP:
                return False

            # _logger.info('解析: {}'.format(decrypt_payload))
            http_request.httprequest.data = decrypt_payload
        else:
            return False
    except Exception as e:
        _logger.error('验证出现错误: {}, {}'.format(e, traceback.format_exc()))
        return False
    return True


def verify_auth_token_only():
    def decorator(func):
        @wraps(func)
        def decorated_function(request, *args, **kwargs):
            access_token = http.request.httprequest.headers.get('Authorization')
            request_method = http.request.httprequest.method
            _logger.info('request_method: {}'.format(request_method))
            if not access_token:
                err_msg = 'access token 异常，无效数据'
                _logger.error(err_msg)
                if request_method in ['get', 'GET']:
                    return response_json_error(403, message=err_msg)
                return response_http_json_error(403, message=err_msg)

            if access_token.startswith('Bearer '):
                access_token = access_token[7:]

            if not access_token:
                err_msg = 'access token 异常，无效数据'
                _logger.error(err_msg)
                if request_method in ['get', 'GET']:
                    return response_json_error(403, message=err_msg)
                return response_http_json_error(403, message=err_msg)

            verify_token, verify_msg = check_access_token(access_token)
            if not verify_token:
                err_msg = 'access token 异常<{}>，认证失败'.format(verify_msg)
                _logger.error(err_msg)
                if request_method in ['get', 'GET']:
                    return response_json_error(403, message=err_msg)
                return response_http_json_error(403, message=err_msg)
            return func(request, *args, **kwargs)

        return decorated_function

    return decorator


def verify_auth_token():
    def decorator(func):
        @wraps(func)
        def decorated_function(request, *args, **kwargs):
            access_token = http.request.httprequest.headers.get('Authorization')
            if not access_token:
                err_msg = 'access token 异常，无效数据'
                _logger.error(err_msg)
                return response_http_json_error(403, message=err_msg)

            if access_token.startswith('Bearer '):
                access_token = access_token[7:]

            if not access_token:
                err_msg = 'access token 异常，无效数据'
                _logger.error(err_msg)
                return response_http_json_error(403, message=err_msg)

            verify_token, verify_msg = check_access_token(access_token)
            if not verify_token:
                err_msg = 'access token 异常<{}>，认证失败'.format(verify_msg)
                _logger.error(err_msg)
                return response_http_json_error(403, message=err_msg)
            decrypt_msg = decrypt_payload_data(http.request)
            if not decrypt_msg:
                err_msg = '密文解析失败，请检查数据'
                _logger.error(err_msg)
                return response_http_json_error(400, message=err_msg)
            return func(request, *args, **kwargs)

        return decorated_function

    return decorator


def check_http_payload_valid():
    def decorator(func):
        @wraps(func)
        def decorated_function(request, *args, **kwargs):
            try:
                json.loads(http.request.httprequest.data)
            except Exception as e:
                err_msg = '数据异常!'
                _logger.error(err_msg)
                return response_http_json_error(403, message=err_msg)
            return func(request, *args, **kwargs)

        return decorated_function

    return decorator


# 保存access token
def save_access_token_to_redis(uid, access_token):
    redis_client = get_redis_client(db=ACCESS_TOKEN_DB)
    redis_client.set('{}:{}'.format(ACCESS_TOKEN_REDIS_PREFIX, uid), access_token, ex=DEFAULT_TOKEN_EXPIRE)
    redis_client.close()


def delete_access_token_redis(uid):
    redis_client = get_redis_client(db=ACCESS_TOKEN_DB)
    redis_client.unlink('{}:{}'.format(ACCESS_TOKEN_REDIS_PREFIX, uid))
    redis_client.close()


def get_access_token_from_redis(uid):
    redis_client = get_redis_client(db=ACCESS_TOKEN_DB)
    access_token = redis_client.get('{}:{}'.format(ACCESS_TOKEN_REDIS_PREFIX, uid))
    redis_client.close()
    return access_token


# 保存 expiry access token
def save_expiry_access_token_to_redis(mobile, access_token):
    if access_token.startswith('Bearer '):
        access_token = access_token[7:]
    redis_client = get_redis_client(db=ACCESS_TOKEN_DB)
    redis_client.set('{}:{}:{}'.format(ACCESS_TOKEN_REDIS_EXPIRE_PREFIX, mobile, time.time()), access_token,
                     ex=DEFAULT_TOKEN_EXPIRE)
    redis_client.close()


def get_expiry_access_token_from_redis(mobile):
    redis_client = get_redis_client(db=ACCESS_TOKEN_DB)
    expiry_keys = redis_client.keys('{}:{}:*'.format(ACCESS_TOKEN_REDIS_EXPIRE_PREFIX, mobile))
    all_data = []
    if expiry_keys:
        for key_id in expiry_keys:
            access_token = redis_client.get(key_id.decode())
            all_data.append(access_token.decode())
    redis_client.close()
    return all_data


def catch_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            return response_http_json_error(400, message='{}'.format(e))

    return wrapper


def save_stock_picking_cache_to_redis(user_id, uuid, card_data):
    redis_client = get_redis_client(db=STOCK_PICKING_CACHE_DB)
    redis_prefix = '{}:{}'.format(STOCK_PICKING_CACHE_PREFIX, user_id)
    _logger.info('开始保存: {}, {}, {}'.format(user_id, uuid, card_data))
    redis_client.hset(redis_prefix, uuid, card_data)

    redis_client.expire(redis_prefix, PICKING_CACHE_EXPIRE)
    redis_client.close()


def delete_stock_picking_cache_data(user_id, *args):
    redis_client = get_redis_client(db=STOCK_PICKING_CACHE_DB)
    redis_prefix = '{}:{}'.format(STOCK_PICKING_CACHE_PREFIX, user_id)
    _logger.info('开始删除 uuid: {}'.format(*args))
    redis_client.hdel(redis_prefix, *args)
    redis_client.close()


def empty_stock_picking_cache(user_id):
    redis_client = get_redis_client(db=STOCK_PICKING_CACHE_DB)
    redis_prefix = '{}:{}'.format(STOCK_PICKING_CACHE_PREFIX, user_id)
    key_type = redis_client.type(redis_prefix)
    if key_type in {b'string', b'hash', b'list', b'set', b'zset', b'stream'}:
        redis_client.delete(redis_prefix)
    else:
        _logger.info('不支持该类型的删除: {}'.format(key_type))
    redis_client.close()


def get_stock_picking_cache_from_redis(user_id):
    redis_client = get_redis_client(db=STOCK_PICKING_CACHE_DB)
    redis_prefix = '{}:{}'.format(STOCK_PICKING_CACHE_PREFIX, user_id)
    cart_data = redis_client.hgetall(redis_prefix)

    cart_data = {k.decode('utf-8'): json.loads(v.decode('utf-8')) for k, v in
                 cart_data.items()}

    redis_client.close()
    return cart_data


def empty_shopping_cart(user_id):
    redis_client = get_redis_client(db=SHOPPING_CART_DB)
    redis_prefix = '{}:{}'.format(SHOPPING_CART_PREFIX, user_id)
    key_type = redis_client.type(redis_prefix)
    if key_type in {b'string', b'hash', b'list', b'set', b'zset', b'stream'}:
        redis_client.delete(redis_prefix)
    else:
        _logger.info('不支持该类型的删除: {}'.format(key_type))
    redis_client.close()


def save_shopping_cart_to_redis(user_id, uuid, card_data):
    redis_client = get_redis_client(db=SHOPPING_CART_DB)
    redis_prefix = '{}:{}'.format(SHOPPING_CART_PREFIX, user_id)
    _logger.info('开始保存: {}, {}, {}'.format(user_id, uuid, card_data))
    redis_client.hset(redis_prefix, uuid, card_data)
    redis_client.close()


def delete_shopping_cart_data(user_id, *args):
    redis_client = get_redis_client(db=SHOPPING_CART_DB)
    redis_prefix = '{}:{}'.format(SHOPPING_CART_PREFIX, user_id)
    _logger.info('开始删除 uuid: {}'.format(*args))
    redis_client.hdel(redis_prefix, *args)
    redis_client.close()


def get_shopping_cart_from_redis(user_id):
    redis_client = get_redis_client(db=SHOPPING_CART_DB)
    redis_prefix = '{}:{}'.format(SHOPPING_CART_PREFIX, user_id)
    cart_data = redis_client.hgetall(redis_prefix)

    cart_data = {k.decode('utf-8'): json.loads(v.decode('utf-8')) for k, v in
                 cart_data.items()}

    redis_client.close()
    return cart_data
