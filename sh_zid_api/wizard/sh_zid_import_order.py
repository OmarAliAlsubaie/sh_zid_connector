# -*- coding: utf-8 -*-
# Part of insightful-erp Technologies.

from odoo import fields, models,_
from datetime import datetime
from odoo.exceptions import UserError
import socket

PAGE_COUNTER = 1


class ZidImportOrder(models.TransientModel):
    _name = 'sh.zid.import.order'
    _description = 'Zid Import Order'

    zid_order_filter = fields.Selection([('all', 'All'), ('import_by_date', 'Import By Date'), (
        'import_by_id', 'Import By Id')], string="Filter Order", required=True)
    sh_zid_stage_ids = fields.Many2many(
        'sh.zid.order.stage', string="Select Stage", required=True)
    sh_from_date_order = fields.Datetime("From Date")
    sh_to_date_order = fields.Datetime("To Date")
    sh_zid_ids = fields.Char(translate=True, string="Enter Zid Ids")
    next_order_url = fields.Char("Next Order Url")

    # -------------------------------------------
    #  Import the order in queue by ID
    # -------------------------------------------

    def _get_zid_order_by_id(self, zid_config, order_id):
        success, res_json = zid_config._get_req('order_by_id', zid_id=order_id)
        if not success:
            return 'error', res_json
        if res_json.get('status') == 'error':
            if res_json.get('message'):
                if res_json['message'].get('description'):
                    return 'error', res_json['message']['description']
                return 'error', res_json['message']
            return 'error', 'Something went wrong !'
        if not res_json.get('order'):
            return 'error', res_json
        order = res_json['order']
        zid_id = order.get('id')
        find_in_queue = False
        domain = [('sh_order_id', '=', zid_id),
                ('queue_type', '=', 'sale_order')]
        find_in_queue = self.env['sh.zid.queue'].search(
            domain)
        find_in_sale_order = self.env['sale.order'].search(
            [('zid_id', '=', zid_id)])
        if find_in_sale_order:
            return 'success', f'already imported.'
        if find_in_queue:
            find_in_queue._draft()
            return 'success', f'reset to draft in the queue.'
        zid_config.create_queue('sale_order', zid_id, order.get('code'))
        return 'success', f'added in the queue.'



   
    def check_internet_connection(self):
        try:
            # Connect to the Google DNS server
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            return True
        except OSError:
            return False
    # -------------------------------------------
    #  Import orders from the zid to queue
    # -------------------------------------------

    def get_orders(self):
         
    
        if not self.check_internet_connection():
            raise UserError(_("No internet connection. Please check your connection and try again."))
     
        self.ensure_one()
        zid_config = self.env['zid.config'].search([
            ('id', '=', self.env.context.get('active_id'))
        ])
        if not zid_config:
            zid_config.zid_log('Something went wrong !', state='error')
            return
        if not zid_config.import_order:
            zid_config.zid_log('Please select the import order checkbox !', state='error')
            return
        if not (zid_config.authorization and zid_config.access_token):
            zid_config.zid_log('Please generaet the credentials first !', state='error')
            return
        global PAGE_COUNTER
        # ---------------- Import By ID ----------------
        if self.zid_order_filter == 'import_by_id':
            if not self.sh_zid_ids:
                zid_config.zid_log('Please enter the zid ids !', state='error')
                return
            zid_id_list = self.sh_zid_ids.split(",")
            if not zid_id_list:
                zid_config.zid_log('Please enter the zid ids !', state='error')
                return
            for zid_order_id in zid_id_list:
                if not zid_order_id:
                    continue
                status, message = self._get_zid_order_by_id(zid_config, zid_order_id)
                message = f'{zid_order_id}: {message}'
                zid_config.zid_log(message, state=status)
            return
        querystring = {
            "per_page": "100",
            "page": "%s" % (PAGE_COUNTER)
        }
        # ---------------- Import By Date -----------------
        if self.sh_from_date_order and self.sh_to_date_order:
            querystring.update({
                "date_from": "%s" % (self.sh_from_date_order.date()),
                "date_to": "%s" % (self.sh_to_date_order.date())
            })

        # ------------------- Get request -------------------
        success, res_json = zid_config._get_req('orders', querystring)
        if not success:
            zid_config.zid_log(res_json, state='error')
            return

        if 'error' in res_json:
            zid_config.zid_log(res_json['error'], state='error')
            return
        orders = False
        if 'orders' in res_json:
            orders = res_json['orders']
        if not orders:
            if PAGE_COUNTER == 1:
                zid_config.zid_log("Can't find any order to import !", state='error')
            PAGE_COUNTER = 1
            return
        created = 0
        for order in orders:
            stage_name_list = []
            if self.sh_zid_stage_ids:
                stage_name_list = self.sh_zid_stage_ids.mapped('name')
            if not order.get('order_status'):
                continue
            if not order['order_status'].get('code'):
                continue
            if order['order_status']['code'] not in stage_name_list:
                continue
            zid_id = order.get('id')
            if not zid_id:
                continue
            find_in_sale_order = self.env['sale.order'].search(
                [('zid_id', '=', zid_id)])
            if find_in_sale_order:
                continue
            find_in_queue = self.env['sh.zid.queue'].search([
                ('sh_order_id', '=', zid_id),
                ('queue_type', '=', 'sale_order')
            ])
            if find_in_queue:
                created += 1
                find_in_queue._draft()
            else:
                created += 1
                zid_config.create_queue('sale_order', zid_id, zid_config.name)

        zid_config.last_sync_order = datetime.now()
        if created:
            zid_config.zid_log(f"{created} orders added in the queue")
        elif PAGE_COUNTER == 1:
            zid_config.zid_log("No Order Found !")
        PAGE_COUNTER += 1
        self.get_orders()
