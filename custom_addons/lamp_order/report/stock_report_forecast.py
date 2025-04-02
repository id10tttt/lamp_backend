# -*- coding: utf-8 -*-
from odoo import models, fields, tools
import logging
from odoo.osv import expression
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


def generate_all_day_between_start_and_end(start_date, end_date):
    delta = timedelta(days=1)
    dates = []
    if start_date == end_date:
        dates = [start_date]
        return dates
    while start_date <= end_date:
        # add current date to list by converting  it to iso format
        dates.append(start_date)
        # increment start date by timedelta
        start_date += delta
    return dates


class StockQuantForcastReport(models.Model):
    _name = 'stock.quant.forecast.report'
    _description = '库存预测'

    date = fields.Date(string='Date', readonly=True, index=True)
    product_tmpl_id = fields.Many2one('product.template', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True, index=True)
    product_qty = fields.Float(string='Quantity', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', readonly=True)

    def action_stock_quant_report(self, warehouse_id, start_date, end_date):
        today = fields.Date.today()
        all_location_ids = [warehouse_id.rental_in_location_id.id, warehouse_id.rental_out_location_id.id]
        end_date = end_date if end_date > today else today
        all_days = generate_all_day_between_start_and_end(start_date, end_date)

        before_today = [x for x in all_days if x < today]
        after_today = [x for x in all_days if x > today]

        # 当前仓库位置下面的所有库存
        today_quant = self.env['stock.quant'].sudo().search_read(domain=[
            ('location_id', '=', warehouse_id.rental_in_location_id.id)
        ], fields=['product_id', 'quantity'])

        filter_domain = [
            '|',
            ('location_id', 'in', all_location_ids),
            ('location_dest_id', 'in', all_location_ids)
        ]
        date_domain = [
            ('date', '>=', all_days[0]),
            ('date', '<=', all_days[-1]),
            ('state', 'not in', ['cancel', 'done', 'draft'])
        ]
        filter_domain = expression.AND([filter_domain, date_domain])

        range_sm = self.env['stock.move'].sudo().search(filter_domain)

        all_report_data = []

        for product_quant in today_quant:
            product_id = product_quant.get('product_id')[0]
            product_qty = product_quant.get('quantity')
            _logger.info('当前库存: {}, {}'.format(
                product_id, product_qty
            ))
            today_sm = range_sm.filtered(
                lambda sm: sm.date.date() == today and sm.product_id.id == product_id)
            if today_sm:
                sm_in = today_sm.filtered(lambda sm: sm.location_dest_id == warehouse_id.rental_in_location_id)
                sm_out = today_sm.filtered(lambda sm: sm.location_dest_id == warehouse_id.rental_out_location_id)
                product_qty = product_qty + sum(x.product_uom_qty for x in sm_in) - sum(
                    x.product_uom_qty for x in sm_out)

            today_qty = product_qty
            # 前一天
            for current_day in before_today[::-1]:
                current_sm = range_sm.filtered(
                    lambda sm: sm.date.date() == current_day and sm.product_id.id == product_id)
                if not current_sm:
                    tmp = {
                        'date': current_day,
                        'warehouse_id': warehouse_id.id,
                        'product_id': product_id,
                        'product_qty': product_qty
                    }
                else:
                    sm_in = current_sm.filtered(lambda sm: sm.location_dest_id == warehouse_id.rental_in_location_id)
                    sm_out = current_sm.filtered(lambda sm: sm.location_dest_id == warehouse_id.rental_out_location_id)

                    product_qty = product_qty - sum(x.product_uom_qty for x in sm_in) + sum(
                        x.product_uom_qty for x in sm_out)
                    tmp = {
                        'date': current_day,
                        'warehouse_id': warehouse_id.id,
                        'product_id': product_id,
                        'product_qty': product_qty
                    }

                all_report_data.append(tmp)

            product_qty = today_qty
            tmp = {
                'date': today,
                'warehouse_id': warehouse_id.id,
                'product_id': product_id,
                'product_qty': product_qty
            }

            all_report_data.append(tmp)

            # 　后一天
            for current_day in after_today:
                current_sm = range_sm.filtered(
                    lambda sm: sm.date.date() == current_day and sm.product_id.id == product_id)
                if not current_sm:
                    tmp = {
                        'date': current_day,
                        'warehouse_id': warehouse_id.id,
                        'product_id': product_id,
                        'product_qty': product_qty
                    }
                else:
                    sm_in = current_sm.filtered(lambda sm: sm.location_dest_id == warehouse_id.rental_in_location_id)
                    sm_out = current_sm.filtered(lambda sm: sm.location_dest_id == warehouse_id.rental_out_location_id)

                    product_qty = product_qty + sum(x.product_uom_qty for x in sm_in) - sum(
                        x.product_uom_qty for x in sm_out)
                    tmp = {
                        'date': current_day,
                        'warehouse_id': warehouse_id.id,
                        'product_id': product_id,
                        'product_qty': product_qty
                    }

                all_report_data.append(tmp)

        if all_report_data:
            _logger.info('all_report_data: {}'.format(all_report_data))
            all_report_data = sorted(all_report_data, key=lambda x: x.get('date'))

        return all_report_data
