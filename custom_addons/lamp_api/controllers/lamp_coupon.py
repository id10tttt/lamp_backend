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
    @http.route('/api/v1/lamp/coupon/available', auth='public', methods=['GET'], csrf=False, cors="*", type='http')
    def get_all_coupon_list(self, lang='en_US', **kwargs):
        coupon_ids = request.env['coupon.coupon'].sudo().search([
            ('partner_id', '=', False),
            ('expiration_date', '>=', datetime.date.today())
        ])

        if not coupon_ids:
            return self.response_http_json_success(data=[], message='没有优惠券可以用')

        coupon_data = [{
            'id': coupon_id.id,
            'program_id': coupon_id.program_id.id,
            'program_name': coupon_id.program_id.name,
            'expiration_date': str(coupon_id.expiration_date),
        } for coupon_id in coupon_ids]

        return self.response_http_json_success(data=coupon_data, message='成功')

    @http.route('/api/v1/lamp/coupon/my', auth='public', methods=['GET'], csrf=False, cors="*", type='http')
    @verify_auth_token_only()
    def get_my_coupon_list(self, lang='en_US', **kwargs):
        coupon_ids = request.env['coupon.coupon'].sudo().search([
            ('partner_id', '=', request.partner_id)
        ])

        if not coupon_ids:
            return self.response_http_json_success(data=[], message='没有优惠券可以用')

        coupon_data = [{
            'id': coupon_id.id,
            'program_id': coupon_id.program_id.id,
            'program_name': coupon_id.program_id.name,
            'expiration_date': str(coupon_id.expiration_date),
        } for coupon_id in coupon_ids]

        return self.response_http_json_success(data=coupon_data, message='成功')

    @http.route('/api/v1/lamp/coupon/my', auth='public', methods=['POST'], csrf=False, cors="*", type='http')
    @verify_auth_token_only()
    def collect_coupon(self, lang='en_US', **kwargs):
        try:
            payload_data = json.loads(request.httprequest.data)
            coupon_id = payload_data.get('coupon_id')
        except Exception as e:
            return self.response_http_json_success(data=[], message='优惠券数据异常! {}'.format(e))

        coupon_id = request.env['coupon.coupon'].sudo().search([
            ('id', '=', coupon_id)
        ])

        if not coupon_id:
            return self.response_http_json_success(data=[], message='没有优惠券可以用')

        if coupon_id.expiration_date < datetime.date.today():
            return self.response_http_json_success(data=[], message='优惠券已过期!')

        coupon_id.write({
            'partner_id': request.partner_id
        })

        coupon_data = {
            'id': coupon_id.id
        }
        return self.response_http_json_success(data=coupon_data, message='领取成功')
