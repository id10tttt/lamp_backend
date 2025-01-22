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



class StockWarehouse(http.Controller, BaseController):

    def get_stock_warehouse_attachment_url(self, warehouse_id):
        attachment_id = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', warehouse_id._name),
            ('res_id', '=', warehouse_id.id),
            ('res_field', '=', 'warehouse_image')
        ])
        if not attachment_id:
            return ''

        attachment_url = self.get_ir_attachment_public_url(attachment_id[0])

        return attachment_url

    @http.route('/api/v1/lamp/warehouse', auth='public', methods=['GET'], csrf=False, cors="*", type='json')
    def get_product_list(self, lang='en_US', **kwargs):
        try:
            request.env.context = dict(request.env.context, lang=lang)
            page = kwargs.get('page', 1)
            limit = kwargs.get('limit', 80)
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e), exc_info=True)
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        try:
            page = int(page)
            limit = int(limit)
            page = page if page > 0 else 1
            offset = (page - 1) * limit
        except Exception as e:
            return self.response_http_json_error(400, message='数据类型错误')

        warehouse_ids = request.env['stock.warehouse'].sudo().search([], limit=limit, offset=offset)

        warehouse_data = [{
            'id': warehouse_id.id,
            'name': warehouse_id.name,
            'code': warehouse_id.code,
            'address': warehouse_id.address,
            'province': warehouse_id.province,
            'warehouse_image': self.get_stock_warehouse_attachment_url(warehouse_id),
        } for warehouse_id in warehouse_ids]

        return self.response_http_json_success(data=warehouse_data, message='成功')
