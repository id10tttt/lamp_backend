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



class ProductCategory(http.Controller, BaseController):
    @http.route('/api/v1/lamp/product/category', auth='public', methods=['GET'], csrf=False, cors="*", type='json')
    def get_product_category_list(self, lang='en_US', **kwargs):
        try:
            warehouse_id = kwargs.get('warehouse_id')
        except Exception as e:
            _logger.info('解析数据出错! {}'.format(e), exc_info=True)

        request.env.context = dict(request.env.context, lang=lang)

        categ_ids = request.env['product.category'].sudo().search([
            ('parent_id', '=', False),
            ('id', '!=', 1)
        ])

        categ_data = []
        for categ_id in categ_ids:
            categ_data.append({
                'categ_id': categ_id.id,
                'categ_name': categ_id.name,
                'child_ids': [{
                    'categ_id': child_id.id,
                    'categ_name': child_id.name,
                    'parent_id': child_id.parent_id.id,
                    'parent_name': child_id.parent_id.name,
                } for child_id in categ_id.child_id]
            })

        return self.response_http_json_success(data=categ_data, message='成功')
