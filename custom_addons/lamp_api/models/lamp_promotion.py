# -*- coding: utf-8 -*-
from odoo import models, fields


class LampPromotion(models.Model):
    _name = 'lamp.promotion'
    _description = '近期活动'

    name = fields.Char('标题', required=True)
    description = fields.Char('详细描述', required=True)
    image = fields.Image('图片', copy=False, attachment=True)
    product_id = fields.Many2one('product.product', string='链接商品')
