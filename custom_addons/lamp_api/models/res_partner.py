# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # @api.constrains('mobile')
    # def check_partner_mobile_unique(self):
    #     for record_id in self:
    #         if not record_id.mobile:
    #             continue
    #
    #         exist_records = self.search([
    #             ('mobile', '=', record_id.mobile),
    #             ('id', '!=', record_id.id)
    #         ])
    #         _logger.info('exist_records: {}, {}'.format(exist_records, record_id))
    #         if exist_records:
    #             raise ValidationError('存在重复的手机号!')
