# -*- coding: utf-8 -*-
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def parse_sale_order(self, order_ids):
        order_data = []
        for order_id in order_ids:
            order_data = {
                'name': order_id.name,
                'partner_id': order_id.partner_id.id,
                'partner_name': order_id.partner_id.name,
                'start_date': str(order_id.default_start_date),
                'end_date': str(order_id.default_end_date),
                'picker': order_id.picker,
                'picker_phone': order_id.picker_phone,
                'pick_time': str(order_id.pick_time),
                'warehouse_id': order_id.warehouse_id.id,
                'warehouse_name': order_id.warehouse_id.name,
                'order_line': [{
                    'product_id': sol.product_id.id,
                    'product_name': sol.product_id.name,
                    'name': sol.name,
                    'product_uom_qty': sol.product_uom_qty,
                    'price_unit': sol.price_unit,
                    'start_date': str(sol.start_date),
                    'end_date': str(sol.end_date),
                } for sol in order_id.order_line]
            }

        return order_data

    def get_current_order_price_total(self):
        pass
