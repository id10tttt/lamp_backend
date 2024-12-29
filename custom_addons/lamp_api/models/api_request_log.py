# -*- coding: utf-8 -*-
from odoo import models, fields


class ApiRequestLog(models.Model):
    _name = 'api.request.log'
    _description = '接口日志'
    _order = 'id desc'
    _rec_name = 'url'

    url = fields.Char('路由')
    method = fields.Char('Method')
    source_data = fields.Text('请求数据')
    return_msg = fields.Text('接口返回')
    active = fields.Boolean('有效', default=True)
