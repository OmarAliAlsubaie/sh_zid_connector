# -*- coding: utf-8 -*-
# Part of insightful-erp Technologies.

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    zid_id = fields.Integer(string="zid id")
    sh_zid_arabic_name = fields.Char(string="zid Arabic Name")
