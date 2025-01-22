# -*- coding: utf-8 -*-
from ..tools.tools_common import verify_auth_token_only, save_shopping_cart_to_redis, \
    get_shopping_cart_from_redis, empty_shopping_cart, \
    delete_shopping_cart_data
from odoo import http, fields
from odoo.http import request
from .base import BaseController
import json
import logging
from uuid import uuid4

_logger = logging.getLogger(__name__)


class ShoppingCart(BaseController, http.Controller):

    @http.route('/api/v1/lamp/cart', auth='public', methods=['GET'], csrf=False, cors="*", type='http')
    @verify_auth_token_only()
    def get_shop_cart_list(self, lang='en_US', **kwargs):
        shopping_cart_data = get_shopping_cart_from_redis(request.partner_id)

        if not shopping_cart_data:
            return self.response_json_success()

        all_uuid = shopping_cart_data.keys()
        resp_data = []
        for current_uuid in all_uuid:
            tmp_data = {
                'uuid': current_uuid
            }
            tmp_data.update(**shopping_cart_data.get(current_uuid))
            resp_data.append(tmp_data)
        _logger.info('resp_data: {}'.format(resp_data))
        return self.response_json_success(data=resp_data)

    @http.route('/api/v1/lamp/cart/update', auth='public', methods=['POST'], csrf=False, cors="*", type='json')
    @verify_auth_token_only()
    def update_shop_cart_info(self, lang='en_US', **kwargs):
        payload_data = json.loads(request.httprequest.data)

        cart_data = payload_data.get('cart_data')

        try:
            all_product_id = [int(x.get('product_id')) for x in cart_data]
            all_warehouse_id = [int(x.get('warehouse_id')) for x in cart_data]
        except Exception as e:
            return self.response_http_json_error(400, message='出现了错误: {}'.format(e))

        product_ids = request.env['product.product'].sudo().search([('id', 'in', all_product_id)])

        warehouse_ids = request.env['stock.warehouse'].sudo().search([
            ('id', 'in', all_warehouse_id)
        ])

        if not all([warehouse_ids, product_ids]):
            return self.response_http_json_error(code=400, message='存在无效数据!')

        for cart_line in cart_data:
            product_id = cart_line.get('product_id')
            warehouse_id = cart_line.get('warehouse_id')

            product_id = product_ids.filtered(lambda pt: pt.id == product_id)
            warehouse_id = warehouse_ids.filtered(lambda w: w.id == warehouse_id)
            qty = cart_line.get('qty')

            uuid_value = str(uuid4())
            card_data = {
                'product_id': product_id.id,
                'product_image': product_id.get_product_product_attachment_url(product_id),
                'product_name': product_id.name,
                'warehouse_id': warehouse_id.id,
                'warehouse_name': warehouse_id.name,
                'qty': qty,
            }
            product_data = product_id._parse_product_data(product_id)
            card_data.update(**product_data)
            save_shopping_cart_to_redis(request.partner_id, uuid_value, json.dumps(card_data))

        return self.response_http_json_success()

    @http.route('/api/v1/lamp/cart/add', auth='public', methods=['POST'], csrf=False, cors="*", type='json')
    @verify_auth_token_only()
    def add_shop_cart_info(self, lang='en_US', **kwargs):
        payload_data = json.loads(request.httprequest.data)

        product_id = payload_data.get('product_id')
        qty = payload_data.get('qty')
        uuid = payload_data.get('uuid')
        warehouse_id = payload_data.get('warehouse_id')

        try:
            product_id = int(product_id)
        except Exception as e:
            return self.response_http_json_error(400, message='出现了错误: {}'.format(e))

        product_id = request.env['product.product'].sudo().search([('id', '=', product_id)])

        warehouse_id = request.env['stock.warehouse'].sudo().search([
            ('id', '=', warehouse_id)
        ])
        if not all([product_id, warehouse_id]):
            return self.response_http_json_error(code=400, message='存在无效数据!')

        cart_data = {
            'product_id': product_id.id,
            'product_name': product_id.name,
            'warehouse_id': warehouse_id.id,
            'warehouse_name': warehouse_id.name,
            'qty': qty,
        }
        if uuid:
            uuid_value = uuid
        else:
            uuid_value = str(uuid4())

        save_shopping_cart_to_redis(request.partner_id, uuid_value, json.dumps(cart_data))

        return self.response_http_json_success(data={
            'uuid': uuid_value
        })

    @http.route('/api/v1/lamp/cart/delete', auth='public', methods=['DELETE'], csrf=False, cors="*", type='json')
    @verify_auth_token_only()
    def delete_shop_cart(self, lang='en_US', **kwargs):
        payload_data = json.loads(request.httprequest.data)
        uuid = payload_data.get('uuid')
        if isinstance(uuid, list):
            delete_shopping_cart_data(request.partner_id, *uuid)

        if isinstance(uuid, str):
            delete_shopping_cart_data(request.partner_id, uuid)

        return self.response_http_json_success()

    @http.route('/api/v1/lamp/cart/delete/all', auth='public', methods=['DELETE'], csrf=False, cors="*", type='json')
    @verify_auth_token_only()
    def delete_all_shop_cart(self, lang='en_US', **kwargs):

        empty_shopping_cart(request.partner_id)

        return self.response_http_json_success()
