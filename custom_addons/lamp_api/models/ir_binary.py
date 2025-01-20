# -*- coding: utf-8 -*-
from odoo import models

IGNORE_ACCESS_RIGHT_CHECK = ['product.template', 'product.product']


class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _find_record_check_access(self, record, access_token):
        if record._name in IGNORE_ACCESS_RIGHT_CHECK:
            return record
        return super()._find_record_check_access(record, access_token)
