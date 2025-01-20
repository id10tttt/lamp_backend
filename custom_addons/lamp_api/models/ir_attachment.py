# -*- coding: utf-8 -*-
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

IGNORE_ACCESS_RIGHT_CHECK = ['product.template', 'product.product']


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        res = super()._search(args, offset=offset, limit=limit, order=order, count=count,
                              access_rights_uid=access_rights_uid)
        _logger.info('args: {}, {}'.format(args, res))

        return res
