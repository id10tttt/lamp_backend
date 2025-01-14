# -*- coding: utf-8 -*-
from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def parse_product_data(self, product_ids):
        product_data = []
        for product_id in product_ids:
            product_data.append({
                'product_id': product_id.id,
                'categ_id': product_id.categ_id.id,
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
            })
        return product_data
