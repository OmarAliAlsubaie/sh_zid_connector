# -*- coding: utf-8 -*-
# Part of insightful-erp Technologies.

from odoo import fields, models


class Logger(models.Model):
    _name = 'sh.zid.base.log'
    _description = 'Helps you to maintain the activity done'
    _order = 'id desc'

    name = fields.Char("Name")
    error = fields.Char("Message")
    datetime = fields.Datetime("Date & Time")
    base_config_id = fields.Many2one('zid.config')
    field_type = fields.Selection([('customer', 'Customer'), ('product', 'Product'), (
        'sale_order', 'Sale Order'), ('basic_thing', 'Basic Thing')], string="Zid")
    state = fields.Selection([('success', 'Success'), ('error', 'Failed')])
    operation = fields.Selection([('import', 'Import'), ('export', 'Export')])
