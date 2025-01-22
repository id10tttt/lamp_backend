# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.tools import config
import json
from .base import BaseController
import logging
from ..tools.rsa_utils import RSAUtils
from ..tools.tools_common import (
    get_random_login_code, get_access_token_from_redis, verify_auth_token_only, get_lamp_order_number,
    DEFAULT_TOKEN_EXPIRE, jwt_encode, LAMP_ISSUER, LAMP_AUDIENCE, verify_auth_token, save_access_token_to_redis)

_logger = logging.getLogger(__name__)

MAX_MOBILE_SMS_LIMIT = 20


class SaleOrder(http.Controller, BaseController):
    @http.route('/api/v1/lamp/sale/order/my', auth='public', methods=['GET'], csrf=False, cors="*", type='json')
    @verify_auth_token_only()
    def my_order_list(self, lang='en_US', **kwargs):
        try:
            request.env.context = dict(request.env.context, lang=lang)
            page = kwargs.get('page', 1)
            limit = kwargs.get('limit', 80)
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        try:
            page = int(page)
            limit = int(limit)
            page = page if page > 0 else 1
            offset = (page - 1) * limit
        except Exception as e:
            return self.response_http_json_error(400, message='数据类型错误')

        order_ids = request.env['sale.order'].sudo().search([
            ('partner_id', '=', request.partner_id)
        ])
        if not order_ids:
            return self.response_http_json_success(data=[], message='成功')

        order_data = order_ids.parse_sale_order(order_ids)

        return self.response_http_json_success(data=order_data, message='成功')

    def parse_sale_order_line(self, order_line, start_date, end_date):
        all_product_ids = [x.get('product_id') for x in order_line]
        product_ids = request.env['product.product'].sudo().search([
            ('id', 'in', all_product_ids)
        ])
        order_line_data = []
        for line_data in order_line:
            product_id = product_ids.filtered(lambda p: p.id == line_data.get('product_id'))
            if not product_id:
                continue

            order_line_data.append((0, 0, {
                'product_id': product_id.id,
                'name': '租赁: {}'.format(product_id.name),
                'product_uom_qty': line_data.get('product_uom_qty'),
                'price_unit': line_data.get('price_unit'),
                'start_date': start_date,
                'end_date': end_date
            }))

        return order_line_data

    @http.route('/api/v1/lamp/sale/order', auth='public', methods=['POST'], csrf=False, cors="*", type='json')
    @verify_auth_token_only()
    def create_sale_order(self, lang='en_US', **kwargs):
        try:
            request.env.context = dict(request.env.context, lang=lang)
            payload_data = json.loads(request.httprequest.data)
            _logger.info('payload_data: {}'.format(payload_data))
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        start_date = payload_data.get('state_date')
        end_date = payload_data.get('state_date')
        picker = payload_data.get('picker')
        picker_phone = payload_data.get('picker_phone')
        pick_time = payload_data.get('pick_time')
        warehouse_id = payload_data.get('warehouse_id')

        order_line = payload_data.get('order_line')

        if (not all([start_date, end_date, order_line, picker, picker_phone, pick_time]) or
                not isinstance(order_line, list)):
            return self.response_http_json_error(400, message='订单数据异常!')

        warehouse_id = request.env['stock.warehouse'].sudo().search([
            ('id', '=', warehouse_id)
        ])
        if not warehouse_id:
            return self.response_http_json_error(400, message='仓库信息异常!')

        order_data = {
            'name': get_lamp_order_number(),
            'partner_id': request.partner_id,
            'default_start_date': start_date,
            'default_end_date': end_date,
            'picker': picker,
            'picker_phone': picker_phone,
            'pick_time': pick_time,
            'state': 'draft',
            'note': payload_data.get('note'),
            'warehouse_id': warehouse_id.id
        }

        order_line_data = self.parse_sale_order_line(order_line, start_date, end_date)
        if not order_line_data or len(order_line_data) != len(order_line):
            return self.response_http_json_error(400, message='解析订单出现了错误!')

        order_data.update({
            'order_line': order_line_data
        })
        order_id = request.env['sale.order'].sudo().create(order_data)

        resp_data = {
            'id': order_id.id,
            'name': order_id.name
        }
        return self.response_http_json_success(data=resp_data, message='成功')

    @http.route('/api/v1/lamp/sale/order/amount', auth='public', methods=['POST'], csrf=False, cors="*", type='json')
    @verify_auth_token_only()
    def get_sale_order_price_amount(self, lang='en_US', **kwargs):
        try:
            request.env.context = dict(request.env.context, lang=lang)

            payload_data = json.loads(request.httprequest.data)
            _logger.info('payload_data: {}'.format(payload_data))
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        start_date = payload_data.get('state_date')
        end_date = payload_data.get('state_date')
        picker = payload_data.get('picker')
        picker_phone = payload_data.get('picker_phone')
        pick_time = payload_data.get('pick_time')
        warehouse_id = payload_data.get('warehouse_id')

        order_line = payload_data.get('order_line')

        if (not all([start_date, end_date, order_line, picker, picker_phone, pick_time]) or
                not isinstance(order_line, list)):
            return self.response_http_json_error(400, message='订单数据异常!')

        warehouse_id = request.env['stock.warehouse'].sudo().search([
            ('id', '=', warehouse_id)
        ])
        if not warehouse_id:
            return self.response_http_json_error(400, message='仓库信息异常!')

        order_data = {
            'name': get_lamp_order_number(),
            'partner_id': request.partner_id,
            'default_start_date': start_date,
            'default_end_date': end_date,
            'picker': picker,
            'picker_phone': picker_phone,
            'pick_time': pick_time,
            'state': 'draft',
            'note': payload_data.get('note'),
            'warehouse_id': warehouse_id.id
        }

        order_line_data = self.parse_sale_order_line(order_line, start_date, end_date)
        if not order_line_data or len(order_line_data) != len(order_line):
            return self.response_http_json_error(400, message='解析订单出现了错误!')

        order_data.update({
            'order_line': order_line_data
        })

        # TODO: 计算费用
        resp_data = {
            'amount_total': 0
        }
        return self.response_http_json_success(data=resp_data, message='成功')
