# -*- coding: utf-8 -*-
from odoo import models
import odoo
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_ir_attachment_public_url(self, attachment_id):
        if not attachment_id.access_token:
            attachment_id.generate_access_token()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return '{}/web/content/{}?access_token={}'.format(base_url, attachment_id.id,
                                                          attachment_id.access_token)

    def get_product_product_attachment_url(self, product_id):
        product_tmpl_id = product_id.product_tmpl_id
        attachment_id = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', product_tmpl_id._name),
            ('res_id', '=', product_tmpl_id.id),
            ('res_field', '=', 'image_128')
        ])

        if not attachment_id:
            return ''

        attachment_url = self.get_ir_attachment_public_url(attachment_id[0])

        return attachment_url

    def get_product_template_image_ids(self, product_id):
        product_tmpl_id = product_id.product_tmpl_id
        product_template_image_ids = product_tmpl_id.product_template_image_ids

        attachment_ids = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', product_template_image_ids._name),
            ('res_id', 'in', product_template_image_ids.ids),
            ('res_field', '=', 'image_256')
        ])

        if not attachment_ids:
            return ''

        return [self.get_ir_attachment_public_url(attachment_id) for attachment_id in attachment_ids]

    def _parse_product_data(self, product_id):
        if not product_id:
            return {}
        product_data = {
                'product_id': product_id.id,
                'categ_id': product_id.categ_id.id,
                'categ_name': product_id.categ_id.name,
                'name': product_id.name,
                'list_price': product_id.list_price,
                'currency_id': product_id.currency_id.id,
                'currency': product_id.currency_id.name,
                'weight': product_id.weight,
                'rental': product_id.rental,
                'device_code': product_id.device_code,
                'product_code': product_id.default_code,
                'delay_price': product_id.delay_price,
                'coupon': product_id.coupon,
                'package_type': product_id.package_type,
                'net_weight': product_id.net_weight,
                'gross_weight': product_id.net_weight,
                'logo_size': product_id.logo_size,
                'product_size': product_id.product_size,
                'packaging_size': product_id.packaging_size,
                'monthly_subscription': product_id.monthly_subscription,
                'vip_price': product_id.vip_price,
                'vip_monthly_price': product_id.vip_monthly_price,
                'product_image': product_id.get_product_product_attachment_url(product_id),
                'product_image_list': product_id.get_product_template_image_ids(product_id)
            }
        return product_data

    def parse_product_data(self, product_ids):
        product_data = []
        for product_id in product_ids:
            product_data.append(self._parse_product_data(product_id))
        return product_data
