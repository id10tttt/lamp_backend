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



class ProductProduct(http.Controller, BaseController):
    @http.route('/api/v1/lamp/product', auth='public', methods=['POST'], csrf=False, cors="*", type='http')
    def get_product_list(self, **kwargs):
        try:
            payload_data = json.loads(request.httprequest.data)
            _logger.info('payload_data: {}'.format(payload_data))
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_json_error(400, message='出现错误!{}'.format(e))

        page = payload_data.get('page', 1)
        limit = payload_data.get('limit', 80)

        try:
            page = int(page)
            page = page if page > 0 else 1
            offset = (page - 1) * limit
        except Exception as e:
            return self.response_json_error(400, message='数据类型错误')

        product_ids = request.env['product.product'].sudo().search([], offset=offset, limit=limit)

        product_data = product_ids.parse_product_data(product_ids)

        return self.response_json_success(data=product_data, message='成功')

    @http.route('/api/v1/lamp/product/detail', auth='public', methods=['POST'], csrf=False, cors="*", type='http')
    def get_product_detail(self, **kwargs):
        try:
            payload_data = json.loads(request.httprequest.data)
            _logger.info('payload_data: {}'.format(payload_data))
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_json_error(400, message='出现错误!{}'.format(e))

        product_id = payload_data.get('product_id')

        product_id = request.env['product.product'].sudo().search([
            ('id', '=', product_id)
        ])

        if not product_id:
            return self.response_json_error(400, message='数据异常')

        product_data = product_id.parse_product_data(product_id)

        return self.response_json_success(data=product_data, message='成功')
