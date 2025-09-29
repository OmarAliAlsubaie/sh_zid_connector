# -*- coding: utf-8 -*-
# Part of insightful-erp Technologies.
from odoo import fields, models


class ZidOrderStage(models.Model):
    _name = "sh.zid.order.stage"
    _description = "Zid Order Stage"
    _order = "sequence, name, id"

    def _sh_default_sequence_order(self):
        cat = self.search([], limit=1, order="sequence DESC")
        if cat:
            return cat.sequence + 5
        return 1

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(
        help="Gives the sequence order when displaying a list of product categories.", index=True, default=_sh_default_sequence_order)
