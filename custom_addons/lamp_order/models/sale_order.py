# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import float_compare
from datetime import timedelta


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    defer = fields.Boolean('Defer', default=False, copy=False, tracking=True)
    picker = fields.Char('Picker')
    picker_phone = fields.Char('Picker Phone')
    pick_time = fields.Datetime('Pick Time')
    actual_pick_time = fields.Datetime('Actual Pick time')

    full_reduction = fields.Char('Full Reduction')
    coupon = fields.Char('Coupon')
    reserve = fields.Float('Reserve', digits=(16, 2))
    order_amount = fields.Float('Order Amount', digits=(16, 2))
    arrival_time = fields.Datetime('Arrival Time')
    stock_status = fields.Selection([], string='Stock Status')
    payment_status = fields.Selection([], string='Payment Status')
    payment_time = fields.Datetime('Payment Time')
    status = fields.Selection([], string='Status')

    pay_state = fields.Boolean('Pay State')
    return_time = fields.Datetime('Return Time')
    actual_return_time = fields.Datetime('Actual Return time')

    deposit = fields.Float('Deposit', digits=(16, 2))
    dock = fields.Float('Dock', digits=(16, 2))
    labor_cost = fields.Float('Labor Cost', digits=(16, 2))

    active_address = fields.Char('Active address')
    billing_days = fields.Integer('Billing days')

    balance_amount = fields.Float('Balance', digits=(16, 2))

    picker_id_card = fields.Image('Picker ID Card', copy=False, attachment=True)
    picker_selfie = fields.Boolean('Picker Selfie')
    stock_preparation = fields.Boolean('Stock preparation', default=False)
    changed = fields.Boolean('Change')

    pickup_code = fields.Char('Pickup Code')
    check_pickup_code = fields.Boolean('Check Pickup Code')

    is_vip = fields.Boolean('IS VIP')
    vip_discount = fields.Float('VIP Discount', digits=(16, 2))
    actual_pay = fields.Float('Actual Pay', digits=(16, 2))

    insurance_state = fields.Boolean('Insurance State')


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def get_date_range_available_qty(self, move_date, order_line):
        stock_move_ids = self.env['stock.move'].sudo().search([
            ('date', '=', move_date),
            ('product_id', '=', order_line.product_id.rented_product_id.id),
        ])

        stock_in = stock_move_ids.filtered(lambda sm: sm.picking_type_id.code == 'incoming')
        stock_out = stock_move_ids.filtered(lambda sm: sm.picking_type_id.code == 'outgoing')

        stock_in_qty = sum(x.product_uom_qty for x in stock_in)
        stock_out_qty = sum(x.product_uom_qty for x in stock_out)

        return stock_in_qty, stock_out_qty

    @api.onchange("product_id", "rental_qty")
    def rental_product_available_qty(self):
        self.ensure_one()
        line_id = self
        res = {}
        if self.product_id and self.product_id.rented_product_id:
            product_uom = self.product_id.rented_product_id.uom_id
            warehouse = self.order_id.warehouse_id
            rental_in_location = warehouse.rental_in_location_id

            rented_product_ctx = self.with_context(
                location=rental_in_location.id
            ).product_id.rented_product_id

            in_location_available_qty = (
                    rented_product_ctx.qty_available
                    - rented_product_ctx.outgoing_qty
            )

            compare_qty = float_compare(
                in_location_available_qty,
                self.rental_qty,
                precision_rounding=product_uom.rounding,
            )

            if compare_qty == -1:
                current_date = self.start_date
                current_qty = in_location_available_qty
                end_date = self.end_date
                qty_msg = '日期: {}, 可用库存: {}\n'.format(
                    current_date, in_location_available_qty
                )
                while current_date <= end_date:
                    current_date += timedelta(days=1)
                    stock_in_qty, stock_out_qty = self.get_date_range_available_qty(current_date, line_id)
                    current_qty = current_qty + stock_in_qty - stock_out_qty
                    qty_msg += '日期: {}, 可用库存: {}\n'.format(
                        current_date, current_qty
                    )

                res["warning"] = {
                    "title": '库存不足',
                    "message": "您想要租赁 {rental_qty} {uom}, 但是在位置: {location}, "
                               "您当前可用为: {available_qty} {uom}, 请确保当前库存可用，或者已经被返回!\n"
                               "库存信息: \n{qty_msg}".format(
                        rental_qty=self.rental_qty,
                        uom=product_uom.name,
                        available_qty=in_location_available_qty,
                        location=rental_in_location.name,
                        qty_msg=qty_msg
                    )
                }

        return res
