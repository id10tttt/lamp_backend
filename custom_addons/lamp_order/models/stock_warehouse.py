# -*- coding: utf-8 -*-
from odoo import models, fields


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    address = fields.Char('Address')
    province = fields.Char('Province')
    warehouse_image = fields.Image('Warehouse Img', copy=False, attachment=True)
    customer_service = fields.Char('客服联系方式')
