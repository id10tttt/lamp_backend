# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.tools import config
import json
from .base import BaseController
import logging
from ..tools.rsa_utils import RSAUtils
from ..tools.tools_common import (
    verify_auth_token_only, get_access_token_from_redis,
    DEFAULT_TOKEN_EXPIRE, jwt_encode, LAMP_ISSUER, LAMP_AUDIENCE, verify_auth_token, save_access_token_to_redis)

_logger = logging.getLogger(__name__)

MAX_MOBILE_SMS_LIMIT = 20

STATUS_MAP = {
    'to_confirm': '待确认',
    'to_pay': '待付款',
    'to_delivery': '待发货',
    'to_return': '待归还',
    'completed': '已完成',
}


class LampUtils(http.Controller, BaseController):
    @http.route('/api/v1/lamp/utils/common/code', auth='public', methods=['GET'], csrf=False, cors="*", type='http')
    def get_all_common_code(self, lang='en_US', **kwargs):
        resp_code = {
            'status': STATUS_MAP
        }

        return self.response_json_success(data=resp_code, message='成功')
