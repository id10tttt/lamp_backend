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
            return self.response_json_error(code=400, message='没有数据')

        country_data = [{
            'id': country_id.id,
            'name': country_id.name,
            'code': country_id.code,
            'child_ids': self.get_country_state(country_id)
        } for country_id in country_ids]

        return self.response_json_success(data=country_data, message='成功')

    @http.route('/api/v1/lamp/res/address', auth='public', methods=['GET'], csrf=False, cors="*", type='http')
    @verify_auth_token_only()
    def get_my_address_list(self, lang='en_US', **kwargs):
        partner_id = request.env['res.partner'].sudo().search([
            ('id', '=', request.partner_id)
        ])

        if not partner_id:
            return self.response_json_error(code=400, message='没有数据')

        if not partner_id.child_ids:
            return self.response_json_success(data=[], message='成功')

        partner_data = [{
            'id': child_id.id,
            'name': child_id.name,
            'country_id': child_id.country_id.id if child_id.country_id else '',
            'country_name': child_id.country_id.name if child_id.country_id else '',
            'state_id': child_id.state_id.id if child_id.state_id else '',
            'state_name': child_id.state_id.name if child_id.state_id else '',
            'city': child_id.city or '',
            'street': child_id.street or '',
            'street2': child_id.street2 or '',
            'mobile': child_id.mobile or '',
            'email': child_id.delivery_email or '',
            'default_delivery': child_id.default_delivery,
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
            state_id = payload_data.get('state_id')
            state_id = int(state_id) if state_id else False
            name = payload_data.get('name')
            city = payload_data.get('city')
            street = payload_data.get('street')
            street2 = payload_data.get('street2')
            mobile = payload_data.get('mobile')
            email = payload_data.get('email')
            default_delivery = payload_data.get('default_delivery', False)

        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        country_id = request.env['res.country'].sudo().search([
            ('id', '=', country_id)
        ])

        state_id = request.env['res.country.state'].sudo().search([
            ('id', '=', state_id)
        ])

        if not country_id:
            return self.response_http_json_error(400, message='地址信息异常')

        partner_data = {
            'name': name,
            'country_id': country_id.id,
            'state_id': state_id.id if state_id else False,
            'city': city,
            'street': street,
            'street2': street2,
            'mobile': mobile,
            'delivery_email': email,
            'type': 'delivery',
            'parent_id': request.partner_id,
            'default_delivery': default_delivery
        }

        try:
            partner_address_id = request.env['res.partner'].sudo().create(partner_data)

            # 更新状态
            self.change_partner_address_default_state(partner_address_id)

        except Exception as e:
            request.env.cr.rollback()
            return self.response_http_json_error(400, message='地址添加错误! {}'.format(e))

        return self.response_http_json_success(data={
            'id': partner_address_id.id
        }, message='创建成功')

    def change_partner_address_default_state(self, address_id):
        if address_id.default_delivery:
            partner_id_address = address_id.parent_id.child_ids
            partner_id_address = partner_id_address.filtered(lambda p: p.id != address_id.id)
            partner_id_address.write({
                'default_delivery': False
            })

    @http.route('/api/v1/lamp/res/partner/address', auth='public', methods=['PATCH'], csrf=False, cors="*", type='json')
    @verify_auth_token_only()
    def patch_my_address(self, lang='en_US', **kwargs):
        update_key = ['name', 'city', 'street', 'street2', 'mobile', 'email', 'default_delivery']
        try:
            request.env.context = dict(request.env.context, lang=lang)

            payload_data = json.loads(request.httprequest.data)
            _logger.info('payload_data: {}'.format(payload_data))

            address_id = int(payload_data.get('address_id'))
            country_id = None
            state_id = None
            if 'country_id' in payload_data.keys():
                country_id = int(payload_data.get('country_id'))

            if 'state_id' in payload_data.keys():
                state_id = payload_data.get('state_id')
                state_id = int(state_id) if state_id else False

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
            if up_key in payload_data.keys():
                if up_key == 'email':
                    update_value['delivery_email'] = payload_data.get(up_key)
                else:
                    update_value[up_key] = payload_data.get(up_key)

        if not update_value:
            return self.response_http_json_error(400, message='更新数据异常!')

        address_id.write(update_value)

        # 更新状态
        self.change_partner_address_default_state(address_id)
        return self.response_http_json_success(data={
            'id': address_id.id
        }, message='修改成功')

    @http.route('/api/v1/lamp/res/partner/address', auth='public', methods=['DELETE'], csrf=False, cors="*",
                type='json')
    @verify_auth_token_only()
    def delete_my_address(self, lang='en_US', **kwargs):
        try:
            payload_data = json.loads(request.httprequest.data)
            address_id = int(payload_data.get('address_id'))
        except Exception as e:
            return self.response_http_json_error(400, message='出现错误!{}'.format(e))

        address_id = request.env['res.partner'].sudo().search([('id', '=', address_id)])

        if not address_id:
            return self.response_http_json_error(400, message='没有找到该数据!')

        if address_id.parent_id.id != request.partner_id:
            return self.response_http_json_error(400, message='权限错误，不能删除!')

        try:
            address_id.unlink()
        except Exception as e:
            return self.response_http_json_error(400, message='删除出现了错误! {}'.format(e))
        return self.response_http_json_success()
