# -*- coding: utf-8 -*-
# Part of insightful-erp Technologies.
from odoo import fields, models
from datetime import datetime


class ZidQueue(models.Model):
    _name = 'sh.zid.queue'
    _description = 'Helps you to add incoming req in queue'
    _order = 'id desc'

    queue_type = fields.Selection(
        [('customer', 'Customer'), ('product', 'Product'), ('sale_order', 'Salr Order')], string='Queue Type')
    sh_queue_name = fields.Char("Name")
    sh_customer_id = fields.Char("Customers")
    sh_product_id = fields.Char("Product")
    sh_order_id = fields.Char("Order")
    sh_note = fields.Text("Note")
    queue_sync_date = fields.Datetime("Sync Date-Time")
    sh_current_config = fields.Many2one('zid.config', string='Config')
    sh_current_state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Done'), ('error', 'Error')], string="State")

    def _draft(self):
        self.write({
            'sh_current_state': 'draft',
            'queue_sync_date': datetime.now(),
            'sh_note': ''
        })

    def _done(self):
        self.write({
            'sh_current_state': 'done',
            'queue_sync_date': datetime.now(),
            'sh_note': ''
        })

    def _error(self, error):
        self.write({
            'sh_current_state': 'error',
            'queue_sync_date': datetime.now(),
            'sh_note': error
        })

    def import_zid_manually(self):
        active_queue_ids = self.env['sh.zid.queue'].browse(self.env.context.get('active_ids'))
        customer_ids = active_queue_ids.filtered(lambda l: l.sh_customer_id != False)
        product_ids = active_queue_ids.filtered(lambda l: l.sh_product_id != False)
        order_ids = active_queue_ids.filtered(lambda l: l.sh_order_id != False)
        if customer_ids:
            for data in customer_ids:
                data.sh_current_config.import_customers(data.sh_customer_id)
        if product_ids:
            for data in product_ids:
                data.sh_current_config.import_products(data.sh_product_id)
        if order_ids:
            for data in order_ids:
                data.sh_current_config.import_orders(data.sh_order_id)
