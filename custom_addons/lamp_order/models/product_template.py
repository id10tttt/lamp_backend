# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    rental = fields.Float('Rental', digits=(16, 2), required=True)
    device_code = fields.Char('Device code', translate=True)
    delay_price = fields.Float('Delay Price', digits=(16, 2), required=True)
    coupon = fields.Boolean('Coupon', default=False)
    package_type = fields.Char('Package Type', translate=True)

    net_weight = fields.Float('Net Weight')
    gross_weight = fields.Float('Gross Weight')

    logo_size = fields.Char('Logo Size', translate=True)
    product_size = fields.Char('Product Size', translate=True)
    packaging_size = fields.Char('Packaging Size', translate=True)
    monthly_subscription = fields.Float('Monthly Subscription')

    vip_price = fields.Float('VIP Price', digits=(16, 2))
    vip_monthly_price = fields.Float('VIP Monthly Price', digits=(16, 2))

    product_template_image_ids = fields.One2many('product.image', 'product_tmpl_id', string="Extra Product Media",
                                                 copy=True)

    put_on_shelves = fields.Boolean('Put On Shelves', default=True, copy=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)