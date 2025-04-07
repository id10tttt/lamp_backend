# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _order = 'id desc'

    _sql_constraints = [
        ('remaining_points_check',
         'CHECK(remaining_points < 0)',
         "可用积分不能小于0"),
        ('unique_email', 'unique(email)', '邮箱必须唯一!')
    ]

    legal_entity_front = fields.Image('Legal Entity Front', copy=False, attachment=True)
    legal_entity_back = fields.Image('Legal Entity Back', copy=False, attachment=True)

    money = fields.Float('Money', digits=(16, 2), copy=False)
    odoo_create = fields.Boolean('Odoo Create', default=True, copy=False)

    user_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
        ('user', 'User')
    ], default='customer', ondelete='set null')

    default_delivery = fields.Boolean(string='默认取货地址', default=False, copy=False)
    delivery_email = fields.Char('配送邮箱')
    earned_loyalty_ids = fields.One2many('website.earn.loyalty', 'partner_id', string="Earned Loyalty")
    redeem_loyalty_ids = fields.One2many('website.redeem.loyalty', 'partner_id', string="Redeem Loyalty")
    remaining_points = fields.Integer(string="Available Points", compute='compute_total_earned', store=True, default=0)

    hash_password = fields.Char('密码')
    warehouse_id = fields.Many2one('stock.warehouse', string='仓库')

    @api.depends('earned_loyalty_ids', 'redeem_loyalty_ids')
    def compute_total_earned(self):
        for each in self:
            total_earned = sum(each.earned_loyalty_ids.mapped("points"))
            total_redeem = sum(each.redeem_loyalty_ids.mapped("points"))
            each.remaining_points = total_earned - total_redeem

    def get_ir_attachment_public_url(self, attachment_id):
        if not attachment_id.access_token:
            attachment_id.generate_access_token()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return '{}/web/content/{}?access_token={}'.format(base_url, attachment_id.id,
                                                          attachment_id.access_token)

    def get_pres_partner_attachment_url(self, partner_id):
        attachment_id = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', partner_id._name),
            ('res_id', '=', partner_id.id),
            ('res_field', '=', 'image_128')
        ])

        if not attachment_id:
            return ''

        attachment_url = self.get_ir_attachment_public_url(attachment_id[0])

        return attachment_url
