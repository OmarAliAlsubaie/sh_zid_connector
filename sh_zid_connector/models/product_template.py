# -*- coding: utf-8 -*-
# Part of insightful-erp Technologies.

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    zid_id = fields.Char(string="zid id")
    sh_zid_arabic_name = fields.Char(string="zid Arabic Name")
    sh_zid_categ_ids = fields.Many2many(
        'sh.zid.product.category', string="Zid Category")
