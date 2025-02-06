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


class ResPartnerAddress(http.Controller, BaseController):
    def get_country_state(self, country_id):
        state_ids = request.env['res.country.state'].sudo().search([
            ('country_id', '=', country_id.id)
        ])

        if not state_ids:
            return []

        state_data = [{
            'id': state_id.id,
            'name': state_id.name,
            'code': state_id.code,
        } for state_id in state_ids]

        return state_data

    @http.route('/api/v1/lamp/res/country', auth='public', methods=['GET'], csrf=False, cors="*", type='http')
    def get_all_country_list(self, lang='en_US', **kwargs):
        country_ids = request.env['res.country'].sudo().search([])

        if not country_ids:
            return self.response_http_json_error(code=400, message='没有数据')

        country_data = [{
            'id': country_id.id,
            'name': country_id.name,
            'code': country_id.code,
            'child_ids': self.get_country_state(country_id)
        } for country_id in country_ids]

        return self.response_json_success(data=country_data, message='成功')

    @http.route('/api/v1/lamp/res/address', auth='public', methods=['GET'], csrf=False, cors="*", type='http')
    def get_my_address_list(self, lang='en_US', **kwargs):
        partner_id = request.env['res.partner'].sudo().search([
            ('id', '=', request.partner_id)
        ])

        if not partner_id:
            return self.response_http_json_error(code=400, message='没有数据')

        if not partner_id.child_ids:
            return self.response_json_success(data=[], message='成功')

        partner_data = [{
            'id': child_id.id,
            'name': child_id.name,
            'country_id': child_id.country_id.id,
            'country_name': child_id.country_id.name,
            'state_id': child_id.state_id.id,
            'state_name': child_id.state_id.name,
            'city': child_id.city,
            'street': child_id.street,
            'street2': child_id.street2,
            'mobile': child_id.mobile,
            'email': child_id.email,
        } for child_id in partner_id.child_ids]

        return self.response_json_success(data=partner_data, message='成功')

    @http.route('/api/v1/lamp/res/partner/address', auth='public', methods=['POST'], csrf=False, cors="*", type='json')
    @verify_auth_token_only()
    def add_new_address(self, lang='en_US', **kwargs):
        try:
            request.env.context = dict(request.env.context, lang=lang)

            payload_data = json.loads(request.httprequest.data)
            _logger.info('payload_data: {}'.format(payload_data))

            country_id = int(payload_data.get('country_id'))
            state_id = int(payload_data.get('state_id'))
            name = payload_data.get('name')
            city = payload_data.get('city')
            street = payload_data.get('street')
            street2 = payload_data.get('street2')
            mobile = payload_data.get('mobile')
            email = payload_data.get('email')

        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        country_id = request.env['res.country'].sudo().search([
            ('id', '=', country_id)
        ])

        state_id = request.env['res.country.state'].sudo().search([
            ('id', '=', state_id)
        ])

        if not all([country_id, state_id]):
            return self.response_http_json_error(400, message='地址信息异常')

        partner_data = {
            'name': name,
            'country_id': country_id.id,
            'state_id': state_id.id,
            'city': city,
            'street': street,
            'street2': street2,
            'mobile': mobile,
            'email': email,
            'type': 'delivery',
            'parent_id': request.partner_id
        }

        partner_address_id = request.env['res.partner'].sudo().create(partner_data)

        return self.response_http_json_success(data={
            'id': partner_address_id.id
        }, message='创建成功')

    @http.route('/api/v1/lamp/res/partner/address', auth='public', methods=['PATCH'], csrf=False, cors="*", type='json')
    @verify_auth_token_only()
    def patch_my_address(self, lang='en_US', **kwargs):
        update_key = ['name', 'city', 'street', 'street2', 'mobile', 'email']
        try:
            request.env.context = dict(request.env.context, lang=lang)

            payload_data = json.loads(request.httprequest.data)
            _logger.info('payload_data: {}'.format(payload_data))

            address_id = int(payload_data.get('address_id'))
            country_id = int(payload_data.get('country_id'))
            state_id = int(payload_data.get('state_id'))
            name = payload_data.get('name')
            city = payload_data.get('city')
            street = payload_data.get('street')
            street2 = payload_data.get('street2')
            mobile = payload_data.get('mobile')
            email = payload_data.get('email')

        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        address_id = request.env['res.partner'].sudo().search([
            ('id', '=', address_id)
        ])
        update_value = {}
        if not address_id:
            return self.response_http_json_error(400, message='数据异常!')

        if country_id:
            country_id = request.env['res.country'].sudo().search([
                ('id', '=', country_id)
            ])
            if not country_id:
                return self.response_http_json_error(400, message='地址信息异常')
            update_value.update({
                'country_id': country_id
            })

        if state_id:
            state_id = request.env['res.country.state'].sudo().search([
                ('id', '=', state_id)
            ])
            if not state_id:
                return self.response_http_json_error(400, message='地址信息异常')
            state_id = state_id.id
            update_value.update({
                'state_id': state_id
            })

        for up_key in update_key:
            if payload_data.get(up_key):
                update_value[up_key] = payload_data.get(up_key)

        if not update_value:
            return self.response_http_json_error(400, message='更新数据异常!')
    
        address_id.write(**update_value)

        return self.response_http_json_success(data={
            'id': address_id
        }, message='修改成功')

    @http.route('/api/v1/lamp/res/partner/address', auth='public', methods=['DELETE'], csrf=False, cors="*",
                type='json')
    @verify_auth_token_only()
    def delete_my_address(self, lang='en_US', **kwargs):
        payload_data = json.loads(request.httprequest.data)
        address_id = payload_data.get('address_id')

        address_id = request.env['res.partner'].sudo().search([('id', '=', address_id)])

        if not address_id:
            return self.response_http_json_error(400, message='没有找到该数据!')

        if address_id.partner_id.id != request.partner_id:
            return self.response_http_json_error(400, message='权限错误，不能删除!')

        try:
            address_id.unlink()
        except Exception as e:
            return self.response_http_json_error(400, message='删除出现了错误! {}'.format(e))
        return self.response_http_json_success()
