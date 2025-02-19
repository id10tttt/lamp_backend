# -*- coding: utf-8 -*-
import math
from datetime import datetime
from odoo import http, fields
from odoo.http import request
import json
from .base import BaseController
import logging
from odoo.osv import expression
from odoo.exceptions import ValidationError, UserError
from ..tools.tools_common import verify_auth_token_only, get_lamp_order_number, delete_shopping_cart_data

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
            status = kwargs.get('status')
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

        filter_domain = [('partner_id', '=', request.partner_id)]

        if status:
            if status == 'to_confirm':
                status_domain = [('status', '=', '10')]
                filter_domain = expression.AND([filter_domain, status_domain])
            elif status == 'to_pay':
                status_domain = [
                    ('status', '=', '20'),
                    ('payment_status', '=', 10)
                ]
                filter_domain = expression.AND([filter_domain, status_domain])
            elif status == 'to_delivery':
                status_domain = [
                    ('status', '=', '30'),
                    ('stock_status', '=', '10')
                ]
                filter_domain = expression.AND([filter_domain, status_domain])
            elif status == 'to_return':
                status_domain = [
                    ('status', '=', '30'),
                    ('stock_status', '=', '20')
                ]
                filter_domain = expression.AND([filter_domain, status_domain])
            elif status == 'completed':
                status_domain = [
                    ('status', '=', '40'),
                ]
                filter_domain = expression.AND([filter_domain, status_domain])

        order_ids = request.env['sale.order'].sudo().search([
            filter_domain
        ], limit=limit, offset=offset, order='id desc')
        if not order_ids:
            return self.response_json_success(data=[], message='成功')

        order_data = order_ids.parse_sale_order(order_ids)

        return self.response_json_success(data=order_data, message='成功')

    def get_end_and_start_days(self, start_date, end_date):
        date_formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]

        def parse_date(date_str):
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            return None

        if isinstance(start_date, str):
            start_date = parse_date(start_date)
        if isinstance(end_date, str):
            end_date = parse_date(end_date)

        if isinstance(start_date, datetime):
            start_date = start_date.date()

        if isinstance(end_date, datetime):
            end_date = end_date.date()

        if start_date and end_date:
            return (end_date - start_date).days + 1

        return 1

    def parse_sale_order_line(self, order_line, start_date, end_date):
        empty_cart_task = []
        all_product_ids = [x.get('product_id') for x in order_line]
        product_ids = request.env['product.product'].sudo().search([
            ('id', 'in', all_product_ids)
        ])
        order_line_data = []
        for line_data in order_line:
            empty_cart_task.append(line_data.get('product_id'))
            product_id = product_ids.filtered(lambda p: p.id == line_data.get('product_id'))
            if not product_id:
                continue

            # 对应租赁服务
            rental_service_ids = product_id.rental_service_ids
            product_id = rental_service_ids[0] if rental_service_ids else product_id

            order_line_data.append((0, 0, {
                'rental_type': 'new_rental',
                'product_id': product_id.id,
                'name': '租赁: {}'.format(product_id.name),
                'product_uom_qty': line_data.get('product_uom_qty') * self.get_end_and_start_days(start_date, end_date),
                'price_unit': product_id.list_price,
                'start_date': start_date if start_date else False,
                'end_date': end_date if end_date else False,
                'rental_qty': line_data.get('product_uom_qty')
            }))

        return order_line_data, empty_cart_task

    def create_loyalty_record(self, sale_order_rec):
        if sale_order_rec.amount_total <= 0:
            return
        vals = {
            'order_no': sale_order_rec.name,
            'order_id': sale_order_rec.id,
            'points': math.floor(sale_order_rec.amount_total),
            'order_date': sale_order_rec.date_order,
            'partner_id': sale_order_rec.partner_id.id,
            'referral_partner_id': sale_order_rec.partner_id.id
        }
        earned_reward_rec = request.env['website.earn.loyalty'].sudo().create(vals)
        _logger.info('创建积分记录! {}'.format(earned_reward_rec))

    def apply_redeem_points(self, sale_order_rec, points_amount):
        redeem_amount = abs(points_amount / 100)
        # 免费的订单
        if sale_order_rec.amount_total - redeem_amount < 0:
            redeem_amount = sale_order_rec.amount_total

        sale_order_rec.write({
            'redeem_amount': -redeem_amount,
            'order_line': [(0, 0, {
                'product_id': request.env.ref('lamp_order.loyalty_points').id,
                'product_uom_qty': 1,
                'name': '折扣：积分兑换',
                'price_unit': -redeem_amount
            })]
        })

    def create_redeem_loyalty_record(self, sale_order_rec, points_amount):
        if points_amount <= 0:
            return

        values = {
            'order_no': sale_order_rec.name,
            'order_id': sale_order_rec.id,
            'points': points_amount,
            'order_date': sale_order_rec.date_order,
            'partner_id': sale_order_rec.partner_id.id,
            'points_amount': points_amount,
        }
        redeem_id = request.env['website.redeem.loyalty'].sudo().create(values)
        _logger.info('使用积分! {}'.format(redeem_id))

    def prepare_sale_order(self, payload_data, raise_exceptions=True):
        try:
            _logger.info('payload_data: {}'.format(payload_data))
            start_date = payload_data.get('start_date')
            if not start_date:
                start_date = fields.Date.today()
            end_date = payload_data.get('end_date')
            if not end_date:
                end_date = fields.Date.today()
            picker_partner_id = payload_data.get('picker_partner_id')
            picker_partner_id = int(picker_partner_id) if picker_partner_id else False
            # picker = payload_data.get('picker')
            # picker_phone = payload_data.get('picker_phone')
            pick_time = payload_data.get('pick_time')
            warehouse_id = payload_data.get('warehouse_id')
            redeem_points = payload_data.get('redeem_points', 0)
            redeem_points = int(redeem_points) if redeem_points else 0

            order_line = payload_data.get('order_line')
            coupon_ids = payload_data.get('coupon_ids')
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            raise ValidationError('出现错误!{}'.format(e))

        picker_partner_id = request.env['res.partner'].sudo().search([
            ('id', '=', picker_partner_id),
            ('parent_id', '=', request.partner_id)
        ])

        if (not all([start_date, end_date, order_line, picker_partner_id]) or
                not isinstance(order_line, list)):
            if raise_exceptions:
                raise ValidationError('订单数据异常! 缺少必要的字段')

        partner_id = request.env['res.partner'].sudo().search([
            ('id', '=', request.partner_id)
        ])
        if redeem_points > 0 and redeem_points > partner_id.remaining_points:
            raise ValidationError('积分不足')

        warehouse_id = request.env['stock.warehouse'].sudo().search([
            ('id', '=', warehouse_id)
        ])
        if not warehouse_id:
            raise ValidationError('仓库信息异常')

        if coupon_ids:
            filter_domain = [('id', 'in', coupon_ids),
                             ('partner_id', '=', request.partner_id)]
            order_domain = ['|', ('order_id', '=', False), ('order_id.state', '!=', 'cancel')]

            filter_domain = expression.AND([filter_domain, order_domain])
            coupon_ids = request.env['coupon.coupon'].sudo().search(filter_domain)
            if len(coupon_ids) != len(set(coupon_ids)):
                raise ValidationError('优惠券信息异常!')

        order_data = {
            'name': get_lamp_order_number(),
            'partner_id': request.partner_id,
            'default_start_date': start_date if start_date else False,
            'default_end_date': end_date if end_date else False,
            'picker_partner_id': picker_partner_id.id,
            'picker': picker_partner_id.name,
            'picker_phone': picker_partner_id.mobile,
            # 'pick_time': pick_time,
            'state': 'draft',
            'stock_status': '10',
            'status': '10',
            'payment_status': '10',
            'note': payload_data.get('note'),
            'warehouse_id': warehouse_id.id
        }

        order_line_data, empty_cart_task = self.parse_sale_order_line(order_line, start_date, end_date)
        if not order_line_data or len(order_line_data) != len(order_line):
            raise ValidationError('解析订单出现了错误')

        order_data.update({
            'order_line': order_line_data,
        })

        return order_data, coupon_ids, empty_cart_task

    def delete_shop_cart_after_order_created(self, product_id, warehouse_id):
        redis_key = '{}:{}'.format(product_id, warehouse_id)
        delete_shopping_cart_data(request.partner_id, redis_key)

    @http.route('/api/v1/lamp/sale/order', auth='public', methods=['POST'], csrf=False, cors="*", type='json')
    @verify_auth_token_only()
    def create_sale_order(self, lang='en_US', **kwargs):
        try:
            request.env.context = dict(request.env.context, lang=lang)
            payload_data = json.loads(request.httprequest.data)

            redeem_points = payload_data.get('redeem_points', 0)
            warehouse_id = int(payload_data.get('warehouse_id'))
            redeem_points = int(redeem_points) if redeem_points else 0
            order_data, coupon_ids, empty_cart_task = self.prepare_sale_order(payload_data)

        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        try:
            sale_order_rec = request.env['sale.order'].sudo().create(order_data)
            for coupon_id in coupon_ids:
                request.env['sale.coupon.apply.code'].with_context(active_id=sale_order_rec.id).sudo().create({
                    'coupon_code': coupon_id.code
                }).process_coupon()

            # 删除购物车
            for task_id in empty_cart_task:
                self.delete_shop_cart_after_order_created(task_id, warehouse_id)

            if redeem_points:
                self.apply_redeem_points(sale_order_rec, redeem_points)

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

            order_data, coupon_ids, empty_cart_task = self.prepare_sale_order(payload_data, raise_exceptions=False)

        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        amount_total = 0
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
            _logger.info('订单信息! {}, {}, {}'.format(sale_order_rec, amount_total, coupon_amount))
            raise
        except UserError as e:
            request.env.cr.rollback()
            return self.response_http_json_error(400, message='出现了错误: {}'.format(e))

        except Exception as e:
            _logger.error('出现了错误! {}'.format(e), exc_info=True)
            request.env.cr.rollback()

        resp_data = {
            'amount_total': amount_total,
            'loyalty_points': math.floor(amount_total),
            'coupon_amount': coupon_amount,
        }
        return self.response_http_json_success(data=resp_data, message='成功')

    @http.route('/api/v1/lamp/sale/order/confirm', auth='public', methods=['POST'], csrf=False, cors="*", type='json')
    @verify_auth_token_only()
    def sale_order_confirm(self, lang='en_US', **kwargs):
        try:
            request.env.context = dict(request.env.context, lang=lang)
            payload_data = json.loads(request.httprequest.data)

            order_id = int(payload_data.get('order_id'))
        except Exception as e:
            return self.response_http_json_error(400, message='出现了错误: {}'.format(e))

        if not order_id:
            return self.response_http_json_error(400, message='订单信息异常!')

        order_id = request.env['sale.order'].sudo().search([
            ('partner_id', '=', request.partner_id),
            ('id', '=', order_id)
        ])

        if not order_id:
            return self.response_http_json_error(400, message='订单信息异常!')

        if order_id.status != '10':
            return self.response_http_json_error(400, message='当前订单状态，不允许执行确认操作!')

        try:
            order_id.write({
                'status': '20'
            })
        except Exception as e:
            request.env.cr.rollback()
            return self.response_http_json_error(400, message='出现了错误: {}'.format(e))

        resp_data = {
            'id': order_id.id
        }

        return self.response_http_json_success(data=resp_data, message='确认成功')
