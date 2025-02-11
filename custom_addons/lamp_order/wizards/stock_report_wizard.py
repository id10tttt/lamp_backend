# -*- coding: utf-8 -*-
from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class StockQuantReportForecastWizard(models.TransientModel):
    _name = 'stock.quant.forecast.wizard'
    _description = '引导'

    warehouse_id = fields.Many2one('stock.warehouse', string='仓库', required=True)
    start_date = fields.Date('开始日期', required=True)
    end_date = fields.Date('结束日期', required=True)

    def start_quant_forecast(self):
        self.env.cr.execute('''
        delete from stock_quant_forecast_report where date >= '{}' and date <= '{}' and warehouse_id = {}
        '''.format(
            str(self.start_date), str(self.end_date), self.warehouse_id.id
        ))
        report_obj = self.env['stock.quant.forecast.report'].sudo()
        res = report_obj.action_stock_quant_report(
            self.warehouse_id,
            self.start_date,
            self.end_date
        )

        _logger.info('开始计算: {}'.format(res))

        if res:
            report_ids = report_obj.create(res)
            return {
                'name': '租赁库存预测',
                'view_mode': 'tree,pivot,graph',
                'domain': [('id', 'in', report_ids.ids)],
                'res_model': 'stock.quant.forecast.report',
                'type': 'ir.actions.act_window',
                'context': {'create': False, 'edit': False},
            }
