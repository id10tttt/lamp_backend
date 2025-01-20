# -*- coding: utf-8 -*-
from odoo import models
import odoo
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def check_field_access_rights(self, operation, field_names):
        if isinstance(field_names, list):
            if field_names[0] == 'image_128' and len(field_names) == 1:
                super_user = self.env['res.users'].sudo().browse([odoo.SUPERUSER_ID])
                self.env = self.env(user=super_user)
        return super(ProductProduct, self).check_field_access_rights(operation, field_names)

    def get_product_image(self, image_size='image_128'):
        if not self:
            return ''
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = '{}/web/image?model={}&field={}&id={}'.format(
            base_url, self._name, image_size, self.id)
        return url

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
                'product_image': product_id.get_product_image()
            })
        return product_data
