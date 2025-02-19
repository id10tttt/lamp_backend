# -*- coding: utf-8 -*-
from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def change_sale_order_status(self, picking_ids):
        for picking_id in picking_ids:
            group_id = picking_id.group_id
            if not group_id:
                continue

            sale_id = group_id.sale_id
            if not sale_id:
                continue

            if picking_id.picking_type_id.code == 'outgoing':
                sale_id.write({
                    'status': '30',
                    'stock_status': '20',
                })
            elif picking_id.picking_type_id.code == 'incoming':
                sale_id.write({
                    'status': '40',
                    'stock_status': '30',
                })

    def button_validate(self):
        picking_ids = self
        res = super().button_validate()

        self.change_sale_order_status(picking_ids)
        return res
