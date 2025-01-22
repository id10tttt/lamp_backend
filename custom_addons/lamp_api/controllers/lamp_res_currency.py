# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.tools import config
import json
from .base import BaseController
import logging
from ..tools.rsa_utils import RSAUtils
from ..tools.tools_common import (
    get_random_login_code, get_access_token_from_redis,
    DEFAULT_TOKEN_EXPIRE, jwt_encode, LAMP_ISSUER, LAMP_AUDIENCE, verify_auth_token, save_access_token_to_redis)

_logger = logging.getLogger(__name__)

MAX_MOBILE_SMS_LIMIT = 20



class ResCurrency(http.Controller, BaseController):
    @http.route('/api/v1/lamp/res/currency', auth='public', methods=['GET'], csrf=False, cors="*", type='json')
    def get_res_currency_list(self, lang='en_US', **kwargs):
        currency_ids = request.env['res.currency'].sudo().search([
            ('active', '=', True)
        ])

        currency_data = [{
            'id': currency_id.id,
            'name': currency_id.name,
            'full_name': currency_id.full_name,
            'symbol': currency_id.symbol,
            'rounding': currency_id.rounding,
            'currency_unit_label': currency_id.currency_unit_label,
            'decimal_places': currency_id.decimal_places,
        } for currency_id in currency_ids]

        return self.response_http_json_success(data=currency_data, message='成功')
