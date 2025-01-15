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
    @http.route('/api/v1/lamp/product', auth='public', methods=['GET'], csrf=False, cors="*", type='http')
    def get_product_list(self, **kwargs):
        try:
            page = kwargs.get('page', 1)
            limit = kwargs.get('limit', 80)
            warehouse_id = kwargs.get('warehouse_id')
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_json_error(400, message='出现错误!{}'.format(e))

        try:
            page = int(page)
            limit = int(limit)
            page = page if page > 0 else 1
            offset = (page - 1) * limit
        except Exception as e:
            return self.response_json_error(400, message='数据类型错误')

        if not warehouse_id:
            return self.response_json_error(400, message='请先指定仓库!')

        warehouse_id = request.env['stock.warehouse'].sudo().search([
            ('id', '=', warehouse_id)
        ])

        if not warehouse_id:
            return self.response_json_error(400, message='请先指定仓库!')

        # rental_in_location_id = warehouse_id.rental_in_location_id
        # rental_out_location_id = warehouse_id.rental_out_location_id

        # 根据库存，查找物料
        quant_ids = request.env['stock.quant'].sudo().search([
            ('location_id.warehouse_id', '=', warehouse_id.id)
        ])

        product_ids = request.env['product.product'].sudo().search([
            ('id', 'in', quant_ids.product_id.ids)
        ], limit=limit, offset=offset)

        product_data = request.env['product.product'].parse_product_data(product_ids)

        return self.response_json_success(data=product_data, message='成功')

    @http.route('/api/v1/lamp/product/detail', auth='public', methods=['GET'], csrf=False, cors="*", type='http')
    def get_product_detail(self, **kwargs):
        try:
            product_id = kwargs.get('product_id')
            _logger.info('payload_data: {}'.format(product_id))
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_json_error(400, message='出现错误!{}'.format(e))

        product_id = request.env['product.product'].sudo().search([
            ('id', '=', product_id)
        ])

        if not product_id:
            return self.response_json_error(400, message='数据异常')

        product_data = product_id.parse_product_data(product_id)

        return self.response_json_success(data=product_data, message='成功')
