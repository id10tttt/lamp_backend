# -*- coding: utf-8 -*-
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def parse_sale_order(self, order_ids):
        resp_data = []
        for order_id in order_ids:
            order_data = {
                'id': order_id.id,
                'name': order_id.name,
                'partner_id': order_id.partner_id.id,
                'partner_name': order_id.partner_id.name,
                'start_date': str(order_id.default_start_date),
                'end_date': str(order_id.default_end_date),
                'picker': order_id.picker,
                'state': order_id.state,
                'status_value': dict(order_id._fields['status']._description_selection(order_id.env)).get(
                    order_id.status),
                'status': order_id.status,
                'payment_status': order_id.payment_status,
                'stock_status': order_id.stock_status,
                'picker_phone': order_id.picker_phone,
                'pick_time': str(order_id.pick_time),
                'warehouse_id': order_id.warehouse_id.id,
                'warehouse_name': order_id.warehouse_id.name,
                'amount_total': order_id.amount_total,
                'order_line': [{
                    'product_image': sol.product_id.get_product_product_attachment_url(sol.product_id),
                    'product_id': sol.product_id.id,
                    'product_name': sol.product_id.name,
                    'name': sol.name,
                    'product_uom_qty': sol.product_uom_qty,
                    'price_unit': sol.price_unit,
                    'start_date': str(sol.start_date),
                    'end_date': str(sol.end_date),
                    'price_total': sol.price_total,
                } for sol in order_id.order_line.filtered(lambda x: not x.is_downpayment)]
            }

            resp_data.append(order_data)
        return resp_data

    def get_current_order_price_total(self):
        pass
