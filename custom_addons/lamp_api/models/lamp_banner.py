# -*- coding: utf-8 -*-
from odoo import models, fields


class LampBanner(models.Model):
    _name = 'lamp.banner'
    _description = 'Banner'

    product_id = fields.Many2one('product.product', string='链接商品(可选)')
    title = fields.Char(string='名称', required=True)
    image = fields.Image('图片', copy=False, attachment=True)
    active = fields.Boolean('显示', default=True)
    remark = fields.Text(string='备注')
