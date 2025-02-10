# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
from .base import BaseController
import logging
from odoo.osv import expression
from ..tools.tools_common import (
    get_random_login_code, get_access_token_from_redis, verify_auth_token_only, get_lamp_order_number,
    DEFAULT_TOKEN_EXPIRE, jwt_encode, LAMP_ISSUER, LAMP_AUDIENCE, verify_auth_token, save_access_token_to_redis)

_logger = logging.getLogger(__name__)

MAX_MOBILE_SMS_LIMIT = 20


class SaleOrder(http.Controller, BaseController):
    @http.route('/api/v1/lamp/sale/order/my', auth='public', methods=['GET'], csrf=False, cors="*", type='http')
    @verify_auth_token_only()
    def my_order_list(self, lang='en_US', **kwargs):
        try:
            request.env.context = dict(request.env.context, lang=lang)
            page = kwargs.get('page', 1)
            limit = kwargs.get('limit', 80)
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

        order_ids = request.env['sale.order'].sudo().search([
            ('partner_id', '=', request.partner_id)
        ])
        if not order_ids:
            return self.response_json_success(data=[], message='成功')

        order_data = order_ids.parse_sale_order(order_ids)

        return self.response_json_success(data=order_data, message='成功')

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

    def create_loyalty_record(self, sale_order_rec):
        vals = {'order_no': sale_order_rec.name,
                'points': sale_order_rec.amount_total,
                'order_date': sale_order_rec.date_order,
                'partner_id': sale_order_rec.partner_id.id,
                'referral_partner_id': sale_order_rec.partner_id.id
                }
        earned_reward_rec = request.env['website.earn.loyalty'].sudo().create(vals)
        _logger.info('创建积分记录! {}'.format(earned_reward_rec))

    def create_redeem_loyalty_record(self, sale_order_rec, points_amount):
        values = {'order_no': sale_order_rec.name,
                  'points': points_amount,
                  'order_date': sale_order_rec.date_order,
                  'partner_id': sale_order_rec.partner_id.id,
                  'points_amount': points_amount,
                  }
        redeem_id = request.env['website.redeem.loyalty'].sudo().create(values)
        _logger.info('使用积分! {}'.format(redeem_id))

    @http.route('/api/v1/lamp/sale/order', auth='public', methods=['POST'], csrf=False, cors="*", type='json')
    @verify_auth_token_only()
    def create_sale_order(self, lang='en_US', **kwargs):
        try:
            request.env.context = dict(request.env.context, lang=lang)
            payload_data = json.loads(request.httprequest.data)
            _logger.info('payload_data: {}'.format(payload_data))
            start_date = payload_data.get('state_date')
            end_date = payload_data.get('state_date')
            picker = payload_data.get('picker')
            picker_phone = payload_data.get('picker_phone')
            pick_time = payload_data.get('pick_time')
            warehouse_id = payload_data.get('warehouse_id')
            redeem_points = payload_data.get('redeem_points', 0)
            redeem_points = int(redeem_points) if redeem_points else 0

            order_line = payload_data.get('order_line')
            coupon_ids = payload_data.get('coupon_ids')
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        if (not all([start_date, end_date, order_line, picker, picker_phone, pick_time]) or
                not isinstance(order_line, list)):
            return self.response_http_json_error(400, message='订单数据异常!')

        partner_id = request.env['res.partner'].sudo().search([
            ('id', '=', request.partner_id)
        ])
        if redeem_points > 0 and redeem_points > partner_id.remaining_points:
            return self.response_http_json_error(400, message='积分不足!')

        warehouse_id = request.env['stock.warehouse'].sudo().search([
            ('id', '=', warehouse_id)
        ])
        if not warehouse_id:
            return self.response_http_json_error(400, message='仓库信息异常!')

        if coupon_ids:
            filter_domain = [('id', 'in', coupon_ids),
                             ('partner_id', '=', request.partner_id)]
            order_domain = ['|', ('order_id', '=', False), ('order_id.state', '!=', 'cancel')]

            filter_domain = expression.AND([filter_domain, order_domain])
            coupon_ids = request.env['coupon.coupon'].sudo().search(filter_domain)
            if len(coupon_ids) != len(set(coupon_ids)):
                return self.response_http_json_error(400, message='优惠券信息异常!')

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
            'order_line': order_line_data,
        })

        try:
            sale_order_rec = request.env['sale.order'].sudo().create(order_data)
            for coupon_id in coupon_ids:
                request.env['sale.coupon.apply.code'].with_context(active_id=sale_order_rec.id).sudo().create({
                    'coupon_code': coupon_id.code
                }).process_coupon()

            # 保存积分
            self.create_loyalty_record(sale_order_rec)
            if redeem_points:
                # 使用积分
                self.create_redeem_loyalty_record(sale_order_rec, redeem_points)
        except Exception as e:
            request.env.cr.rollback()
            _logger.info('创建记录出现了错误! {}'.format(e))

            return self.response_http_json_error(400, message='出现了错误: {}'.format(e))

        resp_data = {
            'id': sale_order_rec.id,
            'name': sale_order_rec.name
        }
        return self.response_http_json_success(data=resp_data, message='成功')

    @http.route('/api/v1/lamp/sale/order/amount', auth='public', methods=['POST'], csrf=False, cors="*", type='json')
    @verify_auth_token_only()
    def get_sale_order_price_amount(self, lang='en_US', **kwargs):
        try:
            request.env.context = dict(request.env.context, lang=lang)

            payload_data = json.loads(request.httprequest.data)
            _logger.info('payload_data: {}'.format(payload_data))

            start_date = payload_data.get('state_date')
            end_date = payload_data.get('state_date')
            picker = payload_data.get('picker')
            picker_phone = payload_data.get('picker_phone')
            pick_time = payload_data.get('pick_time')
            coupon_ids = payload_data.get('coupon_ids')
            warehouse_id = payload_data.get('warehouse_id')
            redeem_points = payload_data.get('redeem_points', 0)
            redeem_points = int(redeem_points) if redeem_points else 0

            order_line = payload_data.get('order_line')
            note = payload_data.get('note')

        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        if (not all([start_date, end_date, order_line, picker, picker_phone, pick_time]) or
                not isinstance(order_line, list)):
            return self.response_http_json_error(400, message='订单数据异常!')

        partner_id = request.env['res.partner'].sudo().search([
            ('id', '=', request.partner_id)
        ])
        if redeem_points > 0 and redeem_points > partner_id.remaining_points:
            return self.response_http_json_error(400, message='积分不足!')

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
            'note': note,
            'warehouse_id': warehouse_id.id
        }

        order_line_data = self.parse_sale_order_line(order_line, start_date, end_date)
        if not order_line_data or len(order_line_data) != len(order_line):
            return self.response_http_json_error(400, message='解析订单出现了错误!')

        order_data.update({
            'order_line': order_line_data
        })

        amount_total = 0

        if coupon_ids:
            filter_domain = [('id', 'in', coupon_ids),
                             ('partner_id', '=', request.partner_id)]
            order_domain = ['|', ('order_id', '=', False), ('order_id.state', '!=', 'cancel')]

            filter_domain = expression.AND([filter_domain, order_domain])
            coupon_ids = request.env['coupon.coupon'].sudo().search(filter_domain)
            if len(coupon_ids) != len(set(coupon_ids)):
                return self.response_http_json_error(400, message='优惠券信息异常!')

        coupon_amount = 0
        # TODO: 计算费用
        try:
            sale_order_rec = request.env['sale.order'].sudo().create(order_data)
            for coupon_id in coupon_ids:
                request.env['sale.coupon.apply.code'].with_context(active_id=sale_order_rec.id).sudo().create({
                    'coupon_code': coupon_id.code
                }).process_coupon()

            amount_total = sale_order_rec.amount_total
            coupon_amount = sale_order_rec.reward_amount
            raise
        except Exception as e:
            request.env.cr.rollback()

        resp_data = {
            'amount_total': amount_total,
            'redeem_amount': redeem_points / 100,
            'coupon_amount': coupon_amount,
        }
        return self.response_http_json_success(data=resp_data, message='成功')
