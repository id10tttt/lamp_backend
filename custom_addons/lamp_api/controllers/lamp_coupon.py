# -*- coding: utf-8 -*-
import datetime

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


class CouponCoupon(http.Controller, BaseController):

    def get_available_coupon_count(self):
        pass

    @http.route('/api/v1/lamp/coupon/available', auth='public', methods=['GET'], csrf=False, cors="*", type='http')
    def get_all_coupon_list(self, lang='en_US', **kwargs):
        program_ids = request.env['coupon.program'].sudo().search([
            ('active', '=', True)
        ])
        if not program_ids:
            return self.response_json_success(data=[], message='没有优惠券可以用')

        coupon_ids = request.env['coupon.coupon'].sudo().search([
            ('partner_id', '=', False),
            ('expiration_date', '>=', datetime.date.today())
        ])

        if not coupon_ids:
            return self.response_json_success(data=[], message='没有优惠券可以用')

        coupon_data = [{
            'id': program_id.id,
            'name': program_id.name,
            'rule_date_from': str(program_id.rule_date_from),
            'rule_date_to': str(program_id.rule_date_to),
            'total_order_count': program_id.total_order_count,
            'order_count': program_id.order_count,
            'coupon_count': program_id.coupon_count,
            'discount_type': program_id.discount_type,
            'discount_fixed_amount': program_id.discount_fixed_amount,
            'discount_percentage': program_id.discount_percentage,
            'discount_max_amount': program_id.discount_max_amount,
        } for program_id in program_ids]

        return self.response_json_success(data=coupon_data, message='成功')

    @http.route('/api/v1/lamp/coupon/my', auth='public', methods=['GET'], csrf=False, cors="*", type='http')
    @verify_auth_token_only()
    def get_my_coupon_list(self, lang='en_US', **kwargs):
        coupon_ids = request.env['coupon.coupon'].sudo().search([
            ('partner_id', '=', request.partner_id)
        ])

        if not coupon_ids:
            return self.response_json_error(data=[], message='没有优惠券可以用')

        coupon_data = [{
            'id': coupon_id.id,
            'program_id': coupon_id.program_id.id,
            'program_name': coupon_id.program_id.name,
            'expiration_date': str(coupon_id.expiration_date),
        } for coupon_id in coupon_ids]

        return self.response_json_success(data=coupon_data, message='成功')

    @http.route('/api/v1/lamp/coupon/collect', auth='public', methods=['POST'], csrf=False, cors="*", type='json')
    @verify_auth_token_only()
    def collect_coupon(self, lang='en_US', **kwargs):
        try:
            payload_data = json.loads(request.httprequest.data)
            program_id = payload_data.get('program_id')
        except Exception as e:
            return self.response_http_json_success(data=[], message='优惠券数据异常! {}'.format(e))

        coupon_id = request.env['coupon.coupon'].sudo().search([
            ('program_id', '=', program_id),
            ('partner_id', '=', False),
            ('expiration_date', '>=', datetime.date.today())
        ], limit=1)

        if not coupon_id:
            return self.response_http_json_success(data=[], message='没有优惠券可以用')

        coupon_id.write({
            'partner_id': request.partner_id
        })

        coupon_data = {
            'id': coupon_id.id
        }
        return self.response_http_json_success(data=coupon_data, message='领取成功')
