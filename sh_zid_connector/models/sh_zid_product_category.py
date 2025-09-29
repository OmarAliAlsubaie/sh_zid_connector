# -*- coding: utf-8 -*-
# Part of insightful-erp Technologies.
from odoo import api, fields, models, _
from odoo.tools.translate import html_translate


class ZidProductCategory(models.Model):
    _name = "sh.zid.product.category"
    _description = "Zid Product Category"
    _parent_store = True
    _order = "sequence, name, id"

    def _sh_default_sequence(self):
        cat = self.search([], limit=1, order="sequence DESC")
        if cat:
            return cat.sequence + 5
        return 1

    name = fields.Char(required=True, translate=True, string="Name")
    parent_id = fields.Many2one(
        'sh.zid.product.category', string='Parent Category', index=True, ondelete="cascade")
    parent_path = fields.Char('Parent Path', index=True, unaccent=False)
    child_id = fields.One2many(
        'sh.zid.product.category', 'parent_id', string='Children Categories')
    zid_id = fields.Char(translate=True, string="Zid Id")
    zid_slug = fields.Char(translate=True, string="Zid Slug")
    parents_and_self = fields.Many2many(
        'sh.zid.product.category', compute='_compute_parents_and_self')
    sequence = fields.Integer(
        help="Gives the sequence order when displaying a list of product categories.", index=True, default=_sh_default_sequence)
    website_description = fields.Html(
        'Category Description', sanitize_attributes=False, translate=html_translate, sanitize_form=False)
    product_tmpl_ids = fields.Many2many(
        'product.template')

    @api.constrains('parent_id')
    def sh_check_parent_id(self):
        if not self._check_recursion():
            raise ValueError(_('Error ! You cannot create recursive categories.'))

    def sh_name_get(self):
        res = []
        for category in self:
            res.append(
                (category.id, " / ".join(category.parents_and_self.mapped('name'))))
        return res

    def _compute_sh_parents_and_self(self):
        for category in self:
            if category.parent_path:
                category.parents_and_self = self.env['sh.zid.product.category'].browse(
                    [int(p) for p in category.parent_path.split('/')[:-1]])
            else:
                category.parents_and_self = category
