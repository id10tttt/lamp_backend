# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import float_compare
from datetime import timedelta
import random
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def get_random_char(self, randon_num=6):
        random_list = random.sample('ABCDEFGHIJLMNOPQRSTUVWXYZ1234567890', randon_num)
        return ''.join(str(x) for x in random_list)

    defer = fields.Boolean('Defer', default=False, copy=False, tracking=True)
    picker_partner_id = fields.Many2one('res.partner', string='Picker')
    picker = fields.Char('Picker', tracking=True)
    picker_phone = fields.Char('Picker Phone', tracking=True)
    pick_time = fields.Datetime('Pick Time', tracking=True)
    actual_pick_time = fields.Datetime('Actual Pick time', tracking=True)

    full_reduction = fields.Char('Full Reduction')
    coupon = fields.Char('Coupon')
    reserve = fields.Float('Reserve', digits=(16, 2))
    order_amount = fields.Float('Order Amount', digits=(16, 2))
    arrival_time = fields.Datetime('Arrival Time')
    stock_status = fields.Selection([
        ('10', '待出库'),
        ('20', '已出库，待入库'),
        ('30', '已入库'),
    ], string='Stock Status', default='10', tracking=True)
    payment_status = fields.Selection([
        ('10', '未收款'),
        ('20', '已收款'),
        ('30', '已结清'),
    ], string='Payment Status', default='10', tracking=True)
    payment_time = fields.Datetime('Payment Time')
    status = fields.Selection([
        ('10', '待确认'),
        ('20', '已确认'),
        ('30', '租赁中'),
        ('40', '已完成'),
        ('50', '已取消'),
        ('60', '售后中'),
    ], string='Status', default='10', tracking=True)

    pay_state = fields.Boolean('Pay State', tracking=True)
    return_time = fields.Datetime('Return Time')
    actual_return_time = fields.Datetime('Actual Return time')

    deposit = fields.Float('Deposit', digits=(16, 2))
    dock = fields.Float('Dock', digits=(16, 2))
    labor_cost = fields.Float('Labor Cost', digits=(16, 2))

    active_address = fields.Char('Active address')
    billing_days = fields.Integer('Billing days', compute='_compute_billing_days')

    balance_amount = fields.Float('Balance', digits=(16, 2))

    picker_id_card = fields.Image('Picker ID Card', copy=False, attachment=True)
    picker_selfie = fields.Boolean('Picker Selfie')
    stock_preparation = fields.Boolean('Stock preparation', default=False)
    changed = fields.Boolean('Change')

    pickup_code = fields.Char('Pickup Code', default=lambda self: self.get_random_char(), tracking=True)
    check_pickup_code = fields.Boolean('Check Pickup Code')

    is_vip = fields.Boolean('IS VIP')
    vip_discount = fields.Float('VIP Discount', digits=(16, 2))
    actual_pay = fields.Float('Actual Pay', digits=(16, 2))

    insurance_state = fields.Boolean('Insurance State')

    reward_amount = fields.Float("Reward Amount")
    redeem_amount = fields.Float('Redeem Amount')

    default_start_date = fields.Date(string='开始日期', tracking=True)
    default_end_date = fields.Date(string='归还日期', tracking=True)

    @api.depends('default_start_date', 'default_end_date')
    def _compute_billing_days(self):
        for line_id in self:
            if line_id.default_start_date and line_id.default_end_date:
                line_id.billing_days = (line_id.default_end_date - line_id.default_start_date).days + 1
            else:
                line_id.billing_days = 0

    @api.depends('order_line.invoice_lines')
    def _get_invoiced(self):
        # The invoice_ids are obtained thanks to the invoice lines of the SO
        # lines, and we also search for possible refunds created directly from
        # existing invoices. This is necessary since such a refund is not
        # directly linked to the SO.
        for order in self:
            invoices = order.order_line.invoice_lines.move_id.filtered(
                lambda r: r.move_type in ('out_invoice', 'out_refund'))
            order.invoice_ids = invoices
            order.invoice_count = len(invoices)

            if all([invoice.payment_state == 'paid' for invoice in invoices]) and invoices:
                order.payment_status = '30'

    # 确认付款单
    def create_invoice_pay_now(self):
        self.ensure_one()
        if self.payment_status == '30':
            raise ValidationError('订单已经支付!')

        total_amount = self.amount_total
        today = fields.Date.today()
        data = {
            'advance_payment_method': 'fixed',
            'fixed_amount': total_amount
        }

        self.env['sale.advance.payment.inv'].sudo().with_context(active_model='sale.order', active_ids=self.ids,
                                                                 start_date=today, invoice_date_due=today).create(
            data).create_invoices()

        self.invoice_ids.filtered(lambda i: i.state == 'draft').action_post()

    def action_confirm_sale_order(self):
        for order_id in self:
            invoices = order_id.order_line.invoice_lines.move_id.filtered(
                lambda r: r.move_type in ('out_invoice', 'out_refund'))
            if invoices:
                self.write({
                    'status': '20'
                })
                return True
            order_id.create_invoice_pay_now()
        self.write({
            'status': '20'
        })

    def action_confirm(self):
        res = super().action_confirm()

        self.sudo().action_confirm_sale_order()

        return res


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

    def compute_rental_price_total(self):
        line_product_id = self.product_id
        if line_product_id.rented_product_id:
            product_id = line_product_id.rented_product_id
        else:
            product_id = line_product_id
        template_id = product_id.product_tmpl_id

        first_day_price_unit = template_id.rental
        delay_price_unit = template_id.delay_price
        first_day_price = first_day_price_unit * self.number_of_days * self.rental_qty

        delay_price = delay_price_unit * (self.number_of_days - 1) * self.rental_qty

        return first_day_price + delay_price

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'rental_qty')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            if line.rental_type:
                # 价格 = 首日单价 + 次日 * 数量
                price_total = line.compute_rental_price_total()
                _logger.info('price_total: {}'.format(price_total))
                line.update({
                    'price_subtotal': price_total,
                    'price_total': price_total,
                    'price_tax': 0,
                })
            else:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                product=line.product_id, partner=line.order_id.partner_shipping_id)
                line.update({
                    'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                })

    @api.onchange('product_id')
    def change_product_unit_price(self):
        for line_id in self:
            line_product_id = line_id.product_id
            if line_product_id.rented_product_id:
                product_id = line_product_id.rented_product_id
            else:
                product_id = line_product_id

            template_id = product_id.product_tmpl_id
            if not template_id:
                line_id.price_unit = 0
            else:
                line_id.price_unit = template_id.rental

    @api.onchange("product_id", "rental_qty")
    def rental_product_available_qty(self):
        self.ensure_one()
        if not self.start_date:
            return

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
