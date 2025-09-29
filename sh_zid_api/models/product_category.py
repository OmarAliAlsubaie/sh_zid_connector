# -*- coding: utf-8 -*-
# Part of insightful-erp Technologies.

from odoo import models, fields


class ProductCategory(models.Model):
    _inherit = 'product.category'

    zid_id = fields.Integer(string="zid id")
