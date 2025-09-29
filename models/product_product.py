# -*- coding: utf-8 -*-
# Part of insightful-erp Technologies.

from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    zid_id = fields.Char(string="zid id")
    zid_price = fields.Float(string="zid price")
    sh_zid_arabic_name = fields.Char(string="zid Arabic Name")
    sh_zid_categ_ids = fields.Many2many(
        'sh.zid.product.category', related='product_tmpl_id.sh_zid_categ_ids', string="Zid Category")

    # TO CALCULATE SALE PRICE USING EXTRA PRICE FROM ZID
    def _compute_product_price_extra(self):
        for product in self:
            if product.zid_id:
                product.price_extra = product.zid_price-product.product_tmpl_id.list_price
            else:
                product.price_extra = sum(
                    product.product_template_attribute_value_ids.mapped('price_extra'))
