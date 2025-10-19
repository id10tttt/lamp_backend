# Copyright 2014-2021 Akretion France (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2016-2021 Sodexis (http://sodexis.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    # Link rental service -> rented HW product
    rented_product_id = fields.Many2one(
        "product.product",
        string="Related Rented Product",
        domain=[("type", "in", ("product", "consu"))],
    )
    # Link rented HW product -> rental service
    rental_service_ids = fields.One2many(
        "product.product", "rented_product_id", string="Related Rental Services"
    )

    @api.model
    def _prepare_rental_product(self):
        day_uom_id = self.env.ref("uom.product_uom_day").id
        vals = {
            "type": "service",
            "sale_ok": True,
            "purchase_ok": False,
            "uom_id": day_uom_id,
            # "uom_po_id": day_uom_id,
            "list_price": self.rental,
            "name": '租赁服务: {}'.format(self.name),
            "default_code": self.default_code,
            "rented_product_id": self.id,
            "must_have_dates": True,
            "categ_id": self.categ_id.id,
            "invoice_policy": "order",
        }
        return vals

    @api.model
    def create(self, values):
        res = super().create(values)
        if not self.env.context.get('auto_create_rental'):
            res.create_rental_product_auto()
        return res

    def create_rental_product_auto(self):
        for product_id in self:
            if product_id.rental_service_tmpl_ids:
                continue
            product_id.with_context(auto_create_rental=True).create(product_id._prepare_rental_product())

    @api.constrains("rented_product_id", "must_have_dates", "type", "uom_id")
    def _check_rental(self):
        day_uom = self.env.ref("uom.product_uom_day")
        for product in self:
            if product.rented_product_id:
                if product.type != "service":
                    raise ValidationError(
                        _("The rental product '{}' must be of type 'Service'.").format(
                            product.name
                        )
                    )
                if not product.must_have_dates:
                    raise ValidationError(
                        _(
                            "The rental product '{}' must have the option "
                            "'Must Have Start and End Dates' checked."
                        ).format(product.name)
                    )
                # In the future, we would like to support all time UoMs
                # but it is more complex and requires additionnal developments
                if product.uom_id != day_uom:
                    raise ValidationError(
                        _(
                            "The unit of measure of the rental product '{}' must "
                            "be 'Day'."
                        ).format(product.name)
                    )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    rented_product_tmpl_id = fields.Many2one(
        "product.template",
        compute="_compute_rented_product_tmpl_id",
        string="Rented Product",
        inverse="_inverse_rented_product_tmpl_id",
        store=True,
    )
    rental_service_tmpl_ids = fields.One2many(
        "product.template", "rented_product_tmpl_id", string="Rental Services"
    )

    def write(self, vals):
        res = super().write(vals)
        if self.product_variant_ids and 'name' in vals and self.product_variant_ids.rental_service_ids and not self.env.context.get('auto_update_rental'):
            self.product_variant_ids.rental_service_ids.with_context(auto_update_rental=True).write({
                'name': '租赁服务: {}'.format(self.name)
            })
        return res

    def create_rental_product_auto(self):
        return self.product_variant_ids.create_rental_product_auto()

    @api.depends("product_variant_ids", "product_variant_ids.rented_product_id")
    def _compute_rented_product_tmpl_id(self):
        unique_variants = self.filtered(
            lambda template: len(template.product_variant_ids) == 1
        )
        for template in unique_variants:
            template.rented_product_tmpl_id = (
                template.product_variant_ids.rented_product_id.product_tmpl_id.id
            )
        for template in self - unique_variants:
            template.rented_product_tmpl_id = False

    def _inverse_rented_product_tmpl_id(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.rented_product_id = (
                    template.rented_product_tmpl_id.product_variant_ids[0].id
                )
