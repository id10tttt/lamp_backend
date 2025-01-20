# -*- coding: utf-8 -*-
from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_product_image_attachment_url(self, product_id):
        attachment_id = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', product_id._name),
            ('res_id', '=', product_id.id),
            ('res_field', '=', 'image_1920')
        ])
        if not attachment_id:
            return ''

        attachment_url = self.get_ir_attachment_public_url(attachment_id[0])

        return attachment_url

    def parse_product_data(self, product_ids):
        product_data = []
        for product_id in product_ids:
            product_data.append({
                'product_id': product_id.id,
                'categ_id': product_id.categ_id.id,
                'categ_name': product_id.categ_id.name,
                'name': product_id.name,
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
                'monthly_subscription': product_id.monthly_subscription,
                'vip_price': product_id.vip_price,
                'vip_monthly_price': product_id.vip_monthly_price,
                'product_image': self.get_product_image_attachment_url(product_id)
            })
        return product_data
