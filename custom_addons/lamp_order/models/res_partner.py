# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    legal_entity_front = fields.Image('Legal Entity Front', copy=False, attachment=True)
    legal_entity_back = fields.Image('Legal Entity Back', copy=False, attachment=True)

    money = fields.Float('Money', digits=(16, 2), copy=False)
    odoo_create = fields.Boolean('Odoo Create', defaule=True, copy=False)

    user_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
        ('user', 'User')
    ], default='customer', ondelete='set null')