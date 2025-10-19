# -*- coding: utf-8 -*-
from odoo import models, fields, tools
import logging
from odoo.fields import Domain
from odoo.exceptions import UserError
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

        # 当前仓库真实库存（done状态的结果）
        today_quants = self.env['stock.quant'].sudo().search_read(domain=[
            ('location_id', '=', warehouse_id.rental_in_location_id.id)
        ], fields=['product_id', 'quantity'])

        # 所有调拨单（使用 scheduled_date）
        move_domain = [
            '|',
            ('location_id', 'in', all_location_ids),
            ('location_dest_id', 'in', all_location_ids),
            ('date', '>=', all_days[0]),
            ('date', '<=', all_days[-1]),
            ('state', 'in', ['confirmed', 'assigned', 'done']),
        ]
        stock_moves = self.env['stock.move'].sudo().search(move_domain)

        all_report_data = []

        for quant in today_quants:
            product_id = quant['product_id'][0]
            real_qty = quant['quantity']  # 当前实际库存

            # ===== 1️⃣ 历史库存（仅统计 done 状态）=====
            qty_before = real_qty
            for d in reversed(before_today):
                moves = stock_moves.filtered(
                    lambda sm: sm.date.date() == d and sm.product_id.id == product_id
                )
                done_in = moves.filtered(
                    lambda sm: sm.location_dest_id == warehouse_id.rental_in_location_id and sm.state == 'done')
                done_out = moves.filtered(
                    lambda sm: sm.location_id == warehouse_id.rental_in_location_id and sm.state == 'done')

                repair_wait = moves.filtered(
                    lambda sm: sm.location_id == warehouse_id.rental_in_location_id and
                               sm.location_dest_id == warehouse_id.rental_in_location_id and
                               sm.state in ['confirmed', 'assigned'])

                qty_before = qty_before - sum(done_in.mapped('product_uom_qty')) + sum(
                    done_out.mapped('product_uom_qty')) - sum(repair_wait.mapped('product_uom_qty'))


                all_report_data.append({
                    'date': d,
                    'warehouse_id': warehouse_id.id,
                    'product_id': product_id,
                    'product_qty': qty_before
                })

            # ===== 2️⃣ 今日库存（真实库存 + 今日待完成调拨）=====
            today_moves = stock_moves.filtered(
                lambda sm: sm.date.date() == today and sm.product_id.id == product_id
            )

            _logger.info(f'today_moves: {today_moves} {today_moves.move_line_ids}')
            in_wait = today_moves.filtered(
                lambda sm: sm.location_dest_id == warehouse_id.rental_in_location_id and sm.state in ['confirmed',
                                                                                                      'assigned'])
            out_wait = today_moves.filtered(
                lambda sm: sm.location_id == warehouse_id.rental_in_location_id and sm.state in ['confirmed',
                                                                                                 'assigned'])

            repair_wait = today_moves.filtered(
                lambda sm: sm.location_id == warehouse_id.rental_in_location_id and
                           sm.location_dest_id == warehouse_id.rental_in_location_id and
                           sm.state in ['confirmed', 'assigned'])

            today_estimate = real_qty + sum(in_wait.mapped('product_uom_qty')) - sum(
                out_wait.mapped('product_uom_qty')) - sum(repair_wait.mapped('product_uom_qty'))

            # 保存“今日预估库存”
            all_report_data.append({
                'date': today,
                'warehouse_id': warehouse_id.id,
                'product_id': product_id,
                'product_qty': today_estimate
            })

            # ===== 3️⃣ 未来库存（基于今日预估逐日推算）=====
            qty_future = today_estimate
            for d in after_today:
                moves = stock_moves.filtered(
                    lambda sm: sm.date.date() == d and sm.product_id.id == product_id
                )
                incoming = moves.filtered(
                    lambda sm: sm.location_dest_id == warehouse_id.rental_in_location_id and sm.state in ['confirmed',
                                                                                                          'assigned'])
                outgoing = moves.filtered(
                    lambda sm: sm.location_id == warehouse_id.rental_in_location_id and sm.state in ['confirmed',
                                                                                                     'assigned'])

                repair_wait = moves.filtered(
                    lambda sm: sm.location_id == warehouse_id.rental_in_location_id and
                               sm.location_dest_id == warehouse_id.rental_in_location_id and
                               sm.state in ['confirmed', 'assigned'])

                qty_future = qty_future + sum(incoming.mapped('product_uom_qty')) - sum(
                    outgoing.mapped('product_uom_qty')) - sum(repair_wait.mapped('product_uom_qty'))
                all_report_data.append({
                    'date': d,
                    'warehouse_id': warehouse_id.id,
                    'product_id': product_id,
                    'product_qty': qty_future
                })

        if all_report_data:
            all_report_data = sorted(all_report_data, key=lambda x: x['date'])

        _logger.info('📦 Stock report data: %s', all_report_data)
        return all_report_data
