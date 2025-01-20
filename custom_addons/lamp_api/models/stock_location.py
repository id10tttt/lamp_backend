# -*- coding: utf-8 -*-
from odoo import models, fields


class StockLocation(models.Model):
    _inherit = 'stock.location'

    warehouse_id = fields.Many2one('stock.warehouse', compute='_compute_warehouse_id', store=True)
