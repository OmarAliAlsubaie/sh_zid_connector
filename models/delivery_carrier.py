# -*- coding: utf-8 -*-
# Part of insightful-erp Technologies.

from odoo import models, fields


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    zid_name = fields.Char(string="zid Name")
