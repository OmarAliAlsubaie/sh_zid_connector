# -*- coding: utf-8 -*-
# Part of insightful-erp Technologies.

from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    zid_type = fields.Char(string="zid Type")
    zid_code = fields.Char(string="zid Code")
