# -*- coding: utf-8 -*-
# Part of insightful-erp Technologies.

from odoo import fields, models, _
from datetime import datetime
from odoo.exceptions import UserError

PAGE_COUNTER = 1
import_10_times = 1



class ZidConfig(models.Model):
    _inherit = 'zid.config'

    # For Customer Import
    auto_import_customer = fields.Boolean("Auto Import Customer")
    auto_export_customer = fields.Boolean("Auto Export Customer")
    import_customer = fields.Boolean("Import Customer", default=True)
    export_customer = fields.Boolean("Export Customer")
    last_sync_customer = fields.Datetime("Last Sync Customer")
    manage_log_customer = fields.Boolean(default=True)

    def get_customers(self):
        try:
            if not self.check_internet_connection():
                raise UserError(_("No internet connection. Please check your connection and try again."))
     
            if not self.import_customer:
                return
            if not (self.authorization and self.access_token):
                return
            global PAGE_COUNTER
            global import_10_times
            params = {
                'page': '%s' % (PAGE_COUNTER),
                'per_page': '50',
            }
            success, res_json = self._get_req('customers', params)
            if not success:
                self.zid_log(res_json, 'customer', state='error')
                return
            # ========================================================
            # Get All customer from zid
            # ========================================================
            if 'error' in res_json:
                self.zid_log(res_json['error'], 'customer', state='error')
                return

            # if not 'error' in res_json:
            created = 0 
            # if res_json.get('customers') and len(res_json.get('customers')) >= 50 and import_10_times <= 10:
            if res_json.get('customers'):
                for person in res_json['customers']:
                    zid_id = person.get('id')
                    if 'name' in person:
                        final_name = person['name']
                    else:
                        final_name = 'No Name'
                    find_in_queue = False

                    # ========================================================
                    # Import customer from zid to queue
                    # ========================================================

                    find_in_queue = self.env['sh.zid.queue'].search([
                        ('sh_customer_id', '=', zid_id),
                        ('queue_type', '=', 'customer')
                    ])
                    if not find_in_queue:
                        created += 1
                        self.create_queue('customer', zid_id, final_name)
                    else:
                        created += 1
                        find_in_queue._draft()
                PAGE_COUNTER += 1
                import_10_times += 1
                self.get_customers()
            else:
                PAGE_COUNTER = 1
                import_10_times = 1

            # ========================================================
            # Manage log to display to message about import to user
            # ========================================================
            self.last_sync_customer = datetime.now()
            count_created=0
            if created >=1:
                count_created=created
                self.zid_log(f'{created} customer Added to the Queue', 'customer')
            elif count_created ==created:
                pass
            else:
                self.zid_log('No Customer Found', 'customer')
            
        except Exception as e:
            self.zid_log(e, 'customer', state='error')

    # Import one by one customer from queue to res.partner
    def manage_import_customer(self):
        get_con = self.env['sh.zid.queue'].search([
            ('queue_type', '=', 'customer'),
            ('sh_current_state', '=', 'draft')
        ], order="id asc", limit=50)
        if get_con:
            counter = 0
            for data in get_con:
                counter += 1
                data.sh_current_config.import_customers(data.sh_customer_id)
            if counter:
                get_con[0].sh_current_config.zid_log(f"Cron : Imported Successfully {counter} Customer", 'customer')
    
    
    
    
    def import_customers(self, import_values):
        
        if not self.check_internet_connection():
            raise UserError(_("No internet connection. Please check your connection and try again."))
     
        
        if not (self.authorization and self.access_token):
            queue = self.env['sh.zid.queue'].search(
                [('sh_customer_id', '=', import_values)], limit=1)
            queue.sh_note = "Plz Genearte Token Before Importing"
            if self.manage_log_customer:
                self.zid_log("No Token Found, genearte token again", 'customer', 'error')
            raise UserError(_("Plz Genearte Token Before Importing"))
        try:
            one_count = 0
            success, res_json = self._get_req('customer_by_id', zid_id=import_values)
            if not success:
                self.zid_log(res_json, 'customer', state='error')
                return
            # ========================================================
            # Get all fields value from zid of customer
            # ========================================================
            if res_json.get('status') == 'error':
                return res_json.get('message')
            customer = res_json.get('customer')
            zid_id = customer.get('id')
            email = False
            mobile = False
            active = True
            city = False
            country_id = False
            if customer.get('name'):
                name = customer.get('name')
            else:
                name = 'No Name'
            if customer.get('email'):
                email = customer.get('email')
            if customer.get('mobile'):
                mobile = customer.get('mobile')
            if customer.get('is_active'):
                active = customer.get('is_active')
            if customer.get('city'):
                address = customer.get('city')
                city = address['en_name']
                country_id = self.env['res.country'].search(
                    [('code', '=', address['country_code'])]).id
            already_imported = self.env['res.partner'].search([('zid_id', '=', zid_id)])
            vals = {
                'zid_id': zid_id,
                'name': name,
                'email': email,
                'mobile': mobile,
                'active': active,
                'city': city if city else False,
                'country_id': country_id if country_id else False,
            }
            # ========================================================
            # Crate customer if not exist otherwise update
            # ========================================================
            if already_imported:
                one_count += 1
                already_imported.write(vals)
            else:
                one_count += 1
                vals.update({
                    'company_type': 'person',
                })
                self.env['res.partner'].create(vals)
            if one_count > 0:
                find_queue = self.env['sh.zid.queue'].search([
                    ('sh_customer_id', '=', import_values),
                    ('queue_type', '=', 'customer')
                ])
                if find_queue:
                    find_queue._done()
            else:
                return res_json.get('message')
        # ========================================================
        # Manage log to display message to user
        # ========================================================
        except Exception as e:
            queue = self.env['sh.zid.queue'].search(
                [('sh_customer_id', '=', import_values)], limit=1)
            queue.sh_note = e
            self.zid_log(e, 'customer', 'error')
