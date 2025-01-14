# -*- coding: utf-8 -*-
from odoo import models, fields


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