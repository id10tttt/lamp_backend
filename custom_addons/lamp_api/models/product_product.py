# -*- coding: utf-8 -*-
from odoo import models
import odoo
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def check_field_access_rights(self, operation, field_names):
        _logger.info('xxxxxxx: {}, {}'.format(operation, field_names))
        if isinstance(field_names, list):
            if field_names[0] in ['image_128', 'write_date', 'name'] and len(field_names) == 1:
                super_user = self.env['res.users'].sudo().browse([odoo.SUPERUSER_ID])
                self.env = self.env(user=super_user)

        # res = super().check_field_access_rights(operation, field_names)
        return super(ProductTemplate, self).check_field_access_rights(operation, field_names)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_ir_attachment_public_url(self, attachment_id):
        if not attachment_id.access_token:
            attachment_id.generate_access_token()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return '{}/web/content/{}?access_token={}'.format(base_url, attachment_id.id,
                                                          attachment_id.access_token)

    def get_product_product_attachment_url(self, product_id):
        product_tmpl_id = product_id.product_tmpl_id
        attachment_id = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', product_tmpl_id._name),
            ('res_id', '=', product_tmpl_id.id),
            ('res_field', '=', 'image_128')
        ])
        _logger.info('attachment_id: {}'.format(attachment_id))
        if not attachment_id:
            return ''

        attachment_url = self.get_ir_attachment_public_url(attachment_id[0])

        return attachment_url

    def parse_product_data(self, product_ids):
        product_data = []
        for product_id in product_ids:
            product_data.append({
                'product_id': product_id.id,
                'categ_id': product_id.categ_id.id,
                'categ_name': product_id.categ_id.name,
                'name': product_id.name,
                'weight': product_id.weight,
                'rental': product_id.rental,
                'device_code': product_id.device_code,
                'product_code': product_id.default_code,
                'delay_price': product_id.delay_price,
                'coupon': product_id.coupon,
                'package_type': product_id.package_type,
                'net_weight': product_id.net_weight,
                'gross_weight': product_id.net_weight,
                'logo_size': product_id.logo_size,
                'product_size': product_id.product_size,
                'monthly_subscription': product_id.monthly_subscription,
                'vip_price': product_id.vip_price,
                'vip_monthly_price': product_id.vip_monthly_price,
                'product_image': product_id.get_product_product_attachment_url(product_id)
            })
        return product_data
