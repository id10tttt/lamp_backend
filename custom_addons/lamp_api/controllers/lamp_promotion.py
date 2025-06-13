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


class LampPromotion(http.Controller, BaseController):

    def get_promotion_attachment_url(self, promotion_id):
        attachment_id = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', promotion_id._name),
            ('res_id', '=', promotion_id.id),
            ('res_field', '=', 'image')
        ])
        if not attachment_id:
            return ''

        attachment_url = self.get_ir_attachment_public_url(attachment_id[0])

        return attachment_url

    @http.route('/api/v1/lamp/promotion', auth='public', methods=['GET'], csrf=False, cors="*", type='http')
    def get_all_promotion(self, lang='en_US', **kwargs):
        try:
            page = kwargs.get('page', 1)
            limit = kwargs.get('limit', 80)
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e), exc_info=True)
            return self.response_json_error(400, message='出现错误!{}'.format(e))

        try:
            page = int(page)
            limit = int(limit)
            page = page if page > 0 else 1
            offset = (page - 1) * limit
        except Exception as e:
            return self.response_json_error(400, message='数据类型错误')

        filter_domain = []
        promotion_ids = request.env['lamp.promotion'].sudo().search(filter_domain, limit=limit, offset=offset)

        promotion_data = [{
            'id': promotion_id.id,
            'title': promotion_id.name,
            'description': promotion_id.description,
            'image': self.get_promotion_attachment_url(promotion_id),
            'product_id': promotion_id.product_id.id,
            'product_name': promotion_id.product_id.name
        } for promotion_id in promotion_ids]

        return self.response_json_success(data=promotion_data, message='成功')
