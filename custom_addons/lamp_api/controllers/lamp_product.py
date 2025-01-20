# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.osv import expression
from .base import BaseController
import logging

_logger = logging.getLogger(__name__)

MAX_MOBILE_SMS_LIMIT = 20



class ProductProduct(http.Controller, BaseController):
    @http.route('/api/v1/lamp/product', auth='public', methods=['GET'], csrf=False, cors="*", type='http')
    def get_product_list(self, lang='en_US', **kwargs):
        try:
            request.env.context = dict(request.env.context, lang=lang)
            page = kwargs.get('page', 1)
            limit = kwargs.get('limit', 80)
            warehouse_id = kwargs.get('warehouse_id')
            categ_id = kwargs.get('categ_id')
            product_name = kwargs.get('name')
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

        if not warehouse_id:
            return self.response_json_error(400, message='请先指定仓库!')

        warehouse_id = request.env['stock.warehouse'].sudo().search([
            ('id', '=', warehouse_id)
        ])

        if not warehouse_id:
            return self.response_json_error(400, message='请先指定仓库!')

        # rental_in_location_id = warehouse_id.rental_in_location_id
        # rental_out_location_id = warehouse_id.rental_out_location_id

        filter_domain = [('location_id.warehouse_id', '=', warehouse_id.id)]
        if categ_id:
            categ_domain = ['|',
                            ('product_id.categ_id', '=', int(categ_id)),
                            ('product_id.categ_id.parent_id', '=', int(categ_id))]

            filter_domain = expression.AND([filter_domain, categ_domain])

        # 根据库存，查找物料
        quant_ids = request.env['stock.quant'].sudo().search(filter_domain)

        filter_domain = [('id', 'in', quant_ids.product_id.ids)]
        
        if product_name:
            name_domain = [('name', 'ilike', product_name)]
            filter_domain = expression.AND([filter_domain, name_domain])

        product_ids = request.env['product.product'].sudo().search(filter_domain, limit=limit, offset=offset)

        product_data = request.env['product.product'].parse_product_data(product_ids)

        return self.response_json_success(data=product_data, message='成功')

    @http.route('/api/v1/lamp/product/detail', auth='public', methods=['GET'], csrf=False, cors="*", type='http')
    def get_product_detail(self, lang='en_US', **kwargs):
        try:
            request.env.context = dict(request.env.context, lang=lang)
            product_id = kwargs.get('product_id')
            _logger.info('payload_data: {}'.format(product_id))
        except Exception as e:
            _logger.info('出现了错误: {}'.format(e))
            return self.response_json_error(400, message='出现错误!{}'.format(e))

        product_id = request.env['product.product'].sudo().search([
            ('id', '=', product_id)
        ])

        if not product_id:
            return self.response_json_error(400, message='数据异常')

        product_data = product_id.parse_product_data(product_id)

        return self.response_json_success(data=product_data, message='成功')
