# Copyright 2014-2021 Akretion France (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2016-2021 Sodexis (http://sodexis.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.addons.stock.models.stock_rule import ProcurementException
from collections import defaultdict, OrderedDict

import logging

_logger = logging.getLogger(__name__)


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        """Inherit to write the end date of the rental on the return move"""
        res = super()._push_prepare_move_copy_values(move_to_copy, new_date)
        location_id = res.get("location_id", False)
        if (
            location_id
            and location_id == move_to_copy.warehouse_id.rental_out_location_id.id
            and move_to_copy.sale_line_id
            and move_to_copy.sale_line_id.rental_type == "new_rental"
        ):
            rental_end_date = move_to_copy.sale_line_id.end_date
            res["date"] = fields.Datetime.to_datetime(rental_end_date)
        return res

    @api.model
    def run(self, procurements, raise_user_error=True):
        """Fulfil `procurements` with the help of stock rules.

        Procurements are needs of products at a certain location. To fulfil
        these needs, we need to create some sort of documents (`stock.move`
        by default, but extensions of `_run_` methods allow to create every
        type of documents).

        :param procurements: the description of the procurement
        :type procurements: list of `~odoo.addons.stock.models.stock_rule.ProcurementGroup.Procurement`
        :param raise_user_error: will raise either an UserError or a ProcurementException
        :type raise_user_error: boolan, optional
        :raises UserError: if `raise_user_error` is True and a procurement isn't fulfillable
        :raises ProcurementException: if `raise_user_error` is False and a procurement isn't fulfillable
        """

        def raise_exception(procurement_errors):
            if raise_user_error:
                dummy, errors = zip(*procurement_errors)
                raise UserError('\n'.join(errors))
            else:
                raise ProcurementException(procurement_errors)

        actions_to_run = defaultdict(list)
        procurement_errors = []
        for procurement in procurements:
            procurement.values.setdefault('company_id', procurement.location_id.company_id)
            procurement.values.setdefault('priority', '0')
            procurement.values.setdefault('date_planned',
                                          procurement.values.get('date_planned', False) or fields.Datetime.now())
            if self._skip_procurement(procurement):
                continue
            rule = self._get_rule(procurement.product_id, procurement.location_id, procurement.values)
            _logger.info(f'rule: {rule}')
            if not rule:
                error = _(
                    'No rule has been found to replenish "%(product)s" in "%(location)s".\nVerify the routes configuration on the product.',
                    product=procurement.product_id.display_name, location=procurement.location_id.display_name)
                procurement_errors.append((procurement, error))
            else:
                action = 'pull' if rule.action == 'pull_push' else rule.action
                actions_to_run[action].append((procurement, rule))

        if procurement_errors:
            raise_exception(procurement_errors)

        for action, procurements in actions_to_run.items():
            if hasattr(self.env['stock.rule'], '_run_%s' % action):
                try:
                    getattr(self.env['stock.rule'], '_run_%s' % action)(procurements)
                except ProcurementException as e:
                    procurement_errors += e.procurement_exceptions
            else:
                _logger.error("The method _run_%s doesn't exist on the procurement rules" % action)

        if procurement_errors:
            raise_exception(procurement_errors)
        return True
