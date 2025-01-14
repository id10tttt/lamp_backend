# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    rental = fields.Float('Rental', digits=(16, 2))
    device_code = fields.Char('Device code')
    delay_price = fields.Float('Delay Price', digits=(16, 2))
    coupon = fields.Boolean('Coupon', default=False)
    package_type = fields.Char('Package Type')

    net_weight = fields.Float('Net Weight')
    gross_weight = fields.Float('Gross Weight')

    logo_size = fields.Char('Logo Size')
    product_size = fields.Char('Product Size')
    packaging_size = fields.Char('Packaging Size')
    monthly_subscription = fields.Float('Monthly Subscription')

    vip_price = fields.Float('VIP Price', digits=(16, 2))
    vip_monthly_price = fields.Float('VIP Monthly Price', digits=(16, 2))
