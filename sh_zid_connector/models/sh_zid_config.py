# -*- coding: utf-8 -*-
# Part of insightful-erp Technologies.

from odoo import models, fields
from urllib.parse import urlencode
import requests
from datetime import datetime
import base64
import socket


OAUTH_URL = 'https://oauth.zid.sa/oauth/authorize?'
TOKEN_URL = 'https://oauth.zid.sa/oauth/token'
REDIR_URL = 'zid/auth'
ZID_API = {
    'delivery_options': 'https://api.zid.sa/v1/managers/store/delivery-options',
    'payment_methods': 'https://api.zid.sa/v1/managers/store/payment-methods',
    'orders': 'https://api.zid.sa/v1/managers/store/orders',
    'order_by_id': 'https://api.zid.sa/v1/managers/store/orders/%s/view',
    'customers': 'https://api.zid.sa/v1/managers/store/customers',
    'customer_by_id': 'https://api.zid.sa/v1/managers/store/customers/%s',
    'profile': 'https://api.zid.sa/v1/managers/account/profile',
    'product_by_id': 'https://api.zid.sa/v1/products/%s',
    'products': 'https://api.zid.sa/v1/products'
}


class ZidConfig(models.Model):
    _name = 'zid.config'
    _description = 'ZidConfig'

    _rec_name = 'name'
    _order = 'name ASC'

    # ===================================== FIELDS ===================================== #

    name = fields.Char(string='Name', required=True, copy=False)
    active = fields.Boolean(default=True)
    auth_active = fields.Boolean(default=False)
    client_id = fields.Char(required=True, copy=False)
    client_secret = fields.Char(required=True, copy=False)
    zid_redirect_url = fields.Char("Redirect Url", copy=False)
    access_token = fields.Char(copy=False)
    authorization = fields.Char(copy=False)
    refresh_token = fields.Char(copy=False)
    state = fields.Selection(
        [('draft', 'Draft'), ('success', 'Success')], default="draft")
    log_historys = fields.One2many(
        'sh.zid.base.log', 'base_config_id', string="Log History")
    zid_store_id = fields.Char('Zid Store ID')

    # ===================================== METHODS ===================================== #

    def open_auth(self):
        self.ensure_one()
        all_other_conf = self.search([]) - self
        all_other_conf.write({'auth_active': False})
        self.auth_active = True
        return {
            "type": "ir.actions.act_url",
            "url": self.get_auth_url(),
            "target": "new",
        }

    def get_base(self):
        return self.env['ir.config_parameter'].sudo().get_param('web.base.url').rstrip('/')

    def get_auth_url(self):
        self.ensure_one()
        params = {
            'client_id': self.client_id,
            'redirect_uri': '%s' % (self.zid_redirect_url),
            'response_type': 'code'
        }
        return "%s%s" % (OAUTH_URL, urlencode(params))

    def get_callback_url(self):
        self.ensure_one()
        return '%s' % (self.zid_redirect_url)

    def make_auth_request(self, code):
        self.ensure_one()
        auth_request = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.get_callback_url(),
            'code': code,
        }
        response = requests.post(url=TOKEN_URL, data=auth_request)
        data = response.json()
        self.write({
            'access_token': data['access_token'],
            'authorization': data['authorization'],
            'refresh_token': data['refresh_token'],
            'auth_active': False,
            'state': 'success',
        })

    # ==============================================================================

    # -----------------------------
    #  Get headers
    # -----------------------------

    def _get_headers(self, stor_id_in_header=False):
        headers = {
            'Content-Type': "application/json",
            'Authorization': f"Bearer {self.authorization}",
            'X-MANAGER-TOKEN': self.access_token,
            'Accept-Language': "en",
        }
        if stor_id_in_header:
            store_id = self.zid_store_id
            if not store_id:
                store_id = self._get_store_id()
            headers.update({
                'ROLE': "Customer",
                'STORE-ID': store_id,
            })
        return headers

    # -----------------------------
    #  Get request img
    # -----------------------------

    def _get_req_img(self, url):
        response = requests.get(url=url, headers=self._get_headers(True))
        if response.status_code != 200:
            return ''
        return base64.b64encode(response.content)

    # -----------------------------
    #  Get request
    # -----------------------------

    def _get_req(self, _type, params=False, zid_id=False, stor_id_in_header=False):
        if not params:
            params = {}
        endpoint = ZID_API[_type]
        if zid_id:
            endpoint = ZID_API[_type] % zid_id
        headers = self._get_headers(stor_id_in_header)
        response = requests.get(url=endpoint, headers=headers, params=params)
        if response.status_code != 200:
            return False, f'Failed to get the api response !\n{response.text}'
        return True, response.json()

    # ------------------------------------------
    #  Get the store ID
    # ------------------------------------------

    def _get_store_id(self):
        success, store_res_json = self._get_req('profile')
        if not success:
            return ''
        if 'user' in store_res_json.keys():
            user = store_res_json['user']
            if 'store' in user.keys():
                store = user['store']
                if 'id' in store.keys():
                    self.zid_store_id = str(store['id'])
                    return str(store['id'])
        return ''

    # ----------------------
    #  Create Log method
    # ----------------------

    def zid_log(self, message, field_type='sale_order', state='success', operation='import'):

      

        is_manage_log = False
        if field_type == 'sale_order' and self.manage_log_order:
            is_manage_log = True
        elif field_type == 'product' and self.manage_log_product:
            is_manage_log = True
        elif field_type == 'customer' and self.manage_log_customer:
            is_manage_log = True
        elif field_type == 'basic_thing' and self.manage_log_basic:
            is_manage_log = True
     
      

        if is_manage_log:
            self.env['sh.zid.base.log'].create({
                "base_config_id": self.id,
                "name": self.name,
                "datetime": datetime.now(),
                "operation": operation,
                "state": state,
                "field_type": field_type,
                "error": message,
            })

        

    def check_internet_connection(self):
        try:
            # Connect to the Google DNS server
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            return True
        except OSError:
            return False
    # ----------------------
    #  Create Queue method
    # ----------------------

    def create_queue(self, queue_type, zid_id, name):
        vals = {
            'queue_type': queue_type,
            'queue_sync_date': datetime.now(),
            'sh_current_state': 'draft',
            'sh_queue_name': name,
            'sh_current_config': self.id,
        }
        if queue_type == 'sale_order':
            vals.update({'sh_order_id': zid_id})
        elif queue_type == 'product':
            vals.update({'sh_product_id': zid_id})
        elif queue_type == 'customer':
            vals.update({'sh_customer_id': zid_id})
        self.env['sh.zid.queue'].create(vals)

    # -----------------------------
    #  Create/Update Queue method
    # -----------------------------

    def is_create_or_write(self, **queue):
        '''If the record does not exist then create else write.'''
        if not queue['rec']:
            self.create_queue('product', queue['zid_id'], queue['final_name'])
        else:
            queue['rec']._draft()
