# -*- coding: utf-8 -*-
# Part of insightful-erp Technologies.

from odoo import fields, models, _
from datetime import datetime
from odoo.exceptions import UserError
from odoo import SUPERUSER_ID

PAGE_NO = 1


class ZidConfig(models.Model):
    _inherit = 'zid.config'

    auto_import_order = fields.Boolean("Auto Import Order",)
    auto_export_order = fields.Boolean("Auto Export Order")
    import_order = fields.Boolean("Import Order", default=True)
    export_order = fields.Boolean("Export Order")
    last_sync_order = fields.Datetime("Last Sync Order")
    manage_log_order = fields.Boolean("Manage Log History", default=True)
    manage_log_basic = fields.Boolean(
        "Manage Log History (Basic Things)", default=True)
    sh_import_based_on_date_order = fields.Boolean("Import based on date")
    sh_from_date_order = fields.Datetime("From Date")
    sh_to_date_order = fields.Datetime("To Date")
    sh_zid_id_appear_in_order = fields.Boolean(
        "Zid sequence to appear in sale order ")
    next_order_url = fields.Char("Next Order Url")
    discount_product = fields.Many2one(
        'product.template', string="Discount Product", help="Used in sale order line when the Discount/Coupon is present in the Zid SO")
    sh_zid_stage_ids = fields.Many2many(
        'sh.zid.order.stage', string="Select Stage")
    delivery_warehosue = fields.Many2one(
        'stock.warehouse', string="Delivery Warehouse")

    # ===================================== For Import Orders ===================================== #

    def shipping_method(self, options):
        '''Create and write shipping methods and their relevant product.
        return: (int) number of shipping methods created'''
        created_shipping = 0
        for option in options:
            cost_price = 0.0
            product_alreay_imported = False
            if option['name']:
                option_name = option['name']
                product_alreay_imported = self.env['product.template'].search(
                    [('name', '=', option_name)], limit=1)
                if not product_alreay_imported:
                    product_alreay_imported = self.env['product.template'].create(
                        {'name': option_name, })
                shipping_method_already_import = self.env['delivery.carrier'].search(
                    [('zid_name', '=', option['name'])], limit=1)
            if option.get('cost'):
                cost_price = option['cost']
            deliver_option_vals = {
                'name': option_name,
                'product_id': product_alreay_imported.product_variant_id.id,
                'delivery_type': 'fixed',
                'fixed_price': cost_price,
                'zid_name': option_name,
            }
            if not shipping_method_already_import:
                self.env['delivery.carrier'].create(deliver_option_vals)
            else:
                shipping_method_already_import.write(deliver_option_vals)
            created_shipping += 1
        return created_shipping

    # --------------------------------------
    #  Import shipping method from zid
    # --------------------------------------

    def _process_zid_delivery_options(self):
        success, res_json_d = self._get_req('delivery_options')
        if not success:
            return
        if 'error' in res_json_d:
            return
        created_shipping = 0
        if 'delivery_options' in res_json_d:
            options = res_json_d['delivery_options']
            created_shipping += self.shipping_method(options)
        if 'system_delivery_options' in res_json_d:
            options = res_json_d['system_delivery_options']
            created_shipping += self.shipping_method(options)
        if created_shipping:
            self.zid_log(f'{created_shipping} Shipping Method Imported', 'basic_thing')

    # ------------------------------------------
    #  Import Payment Method(Journal) from zid
    # ------------------------------------------

    def _process_zid_payment_methods(self):
        success, res_json_p = self._get_req('payment_methods')
        if not success:
            return
        if 'error' in res_json_p:
            return
        created = 0
        default_account = False
        if 'payload' not in res_json_p:
            return
        payments = res_json_p.get('payload')
        for payment in payments:
            if payment['name']:
                payment_name = payment['name']
            if payment['type']:
                zid_type = payment['type']
            if payment['code']:
                zid_code = payment['code']
            default_account = self.env['account.account'].search(
                [('account_type', '=', 'Income')], limit=1).id
            payment_vals = {
                'name': payment_name,
                'zid_type': zid_type,
                'zid_code': zid_code,
                'type': 'sale',
                'code': zid_code,
                'default_account_id': default_account,
            }
            if payment['name'] and zid_code:
                journal_already_import = self.env['account.journal'].search(
                    [('zid_code', '=', zid_code)], limit=1)
            if not journal_already_import:
                self.env['account.journal'].create(
                    payment_vals)
            else:
                journal_already_import.write(payment_vals)
            created += 1
        if created:
            self.zid_log(f'{created} Payment journal Imported', 'basic_thing')

    # ------------------------------------------
    #  Button: Get Baisic Things
    # ------------------------------------------

    def get_basic_thing(self):
        if not self.authorization or not self.access_token:
            return
        try:
            # Import shipping method from zid
            self._process_zid_delivery_options()
            # Import Payment Method(Journal) from zid
            self._process_zid_payment_methods()
        # Manage log to display message to user
        except Exception as e:
            self.zid_log(f'Error: {e}', 'basic_thing', state='error')

    # # ------------------------------------------
    # #  Button: Get Baisic Things
    # # ------------------------------------------

    # def get_orders(self):
    #     ''' Get Orders From zid '''
    #     if self.import_order:
    #         if self.authorization and self.access_token:
    #             global PAGE_NO
    #             if self.next_order_url:
    #                 get_orders_url = self.next_order_url
    #             else:
    #                 get_orders_url = "https://api.zid.sa/v1/managers/store/orders"
    #             headers = {
    #                 'Content-Type': "application/json",
    #                 'Authorization': "Bearer %s" % self.authorization,
    #                 'X-MANAGER-TOKEN': self.access_token,
    #                 'Accept-Language': "en"
    #             }
    #             querystring = {"per_page": "50"}

    #             response = requests.get(
    #                 url=get_orders_url, headers=headers, params=querystring)
    #             res_json = response.json()
    #             if 'error' in res_json:
    #                 self.zid_log(res_json['error'], state='error')
    #                 return
    #             created = 0
    #             for order in res_json['orders']:
    #                 # ==================================================================
    #                 # Import order in between from date and to date from zid to queue
    #                 # ==================================================================
    #                 if order.get('created_at') and self.sh_import_based_on_date_order:

    #                     if datetime.strptime(order.get('created_at'), '%Y-%m-%d %H:%M:%S') > self.sh_from_date_order and datetime.strptime(order.get('created_at'), '%Y-%m-%d %H:%M:%S') < self.sh_to_date_order:
    #                         zid_id = order.get('id')
    #                         if 'code' in order:
    #                             code = order.get('code')
    #                         else:
    #                             code = ''
    #                         find_in_queue = False
    #                         domain = [('sh_order_id', '=', zid_id),
    #                                     ('queue_type', '=', 'sale_order')]
    #                         find_in_queue = self.env['sh.zid.queue'].search(
    #                             domain)
    #                         find_in_sale_order = self.env['sale.order'].search(
    #                             [('zid_id', '=', zid_id)])
    #                         if not find_in_sale_order:
    #                             if not find_in_queue:
    #                                 created += 1
    #                                 self.create_queue('sale_order', zid_id, code)
    #                             else:
    #                                 created += 1
    #                                 find_in_queue._draft()
    #                 else:
    #                     # ==================================================================
    #                     # Import order all from zid to queue
    #                     # ==================================================================
    #                     zid_id = order.get('id')
    #                     if 'code' in order:
    #                         code = order.get('code')
    #                     else:
    #                         code = ''
    #                     find_in_queue = False
    #                     domain = [('sh_order_id', '=', zid_id),
    #                                 ('queue_type', '=', 'sale_order')]
    #                     find_in_queue = self.env['sh.zid.queue'].search(
    #                         domain)
    #                     find_in_sale_order = self.env['sale.order'].search(
    #                         [('zid_id', '=', zid_id)])
    #                     if not find_in_sale_order:
    #                         if not find_in_queue:
    #                             created += 1
    #                             self.create_queue('sale_order', zid_id, code)
    #                         else:
    #                             created += 1
    #                             find_in_queue._draft()
    #             # ==================================================================
    #             # Manage log to display message to users
    #             # ==================================================================
    #             self.last_sync_order = datetime.now()
    #             if created:
    #                 self.zid_log(f'{created} Orders Added to the Queue')
    #             else:
    #                 self.zid_log('No Order Found')
    #             if res_json.get("next", False):
    #                 next_url = res_json.get("next")
    #                 if next_url:
    #                     self.next_order_url = next_url
    #                     self.get_orders()
    #                 else:
    #                     self.next_order_url = False
    #             else:
    #                 self.next_order_url = False

    def manage_import_order(self):
        '''Import one by one order from queue to sale.order '''
        domain = [('queue_type', '=', 'sale_order'),
                  ('sh_current_state', '=', 'draft')]
        get_con = self.env['sh.zid.queue'].search(
            domain, order="id asc", limit=10)
        if get_con:
            counter = 0
            # =================================================================
            # Import one by one order From queue and display Message in log
            # =================================================================
            for data in get_con:
                counter += 1
                data.sh_current_config.import_orders(data.sh_order_id)
            if counter:
                get_con[0].sh_current_config.zid_log(f"Cron : Imported Successfully {counter} Orders")

    def import_orders(self, import_values):
        '''Import one order at a time get order value using zid order id'''
        if not self.authorization or not self.access_token:
            queue = self.env['sh.zid.queue'].search(
                [('sh_order_id', '=', import_values)], limit=1)
            queue._error("Plz Genearte Token Before Importing")
            self.zid_log('No Token Found, genearte token again', 'customer', state='error')
            raise UserError(_("Plz Genearte Token Before Importing"))
        queue = self.env['sh.zid.queue'].search(
            [('sh_order_id', '=', import_values)], limit=1)
        stop = False
        try:
            one_count = 0
            success, res_json = self._get_req('order_by_id', zid_id=import_values)
            if not success:
                queue._error(res_json)
                return
            # ==================================================================
            # Get all fields value of sale order from zid
            # ==================================================================
            if 'error' in res_json:
                queue._error(f"Error: {res_json['error']} !")
                return
            if not res_json.get('order'):
                queue._error('Not get the order data !')
                return
            order_lines = []
            taxes_list = []
            state = 'draft'
            customer = False
            order_total = 0.0
            workflow_id = False
            currency_code = False
            sh_zid_payment_journal = False
            order = res_json.get('order')
            zid_id = order.get('id')
            # if order.get('code'):
            #     code = order.get('code')

            if order.get('currency_code'):
                currency_code = order.get('currency_code')
            
            
            if order.get('customer'):
                customer = self.env['res.partner'].search(
                    [('zid_id', '=', order.get('customer')['id'])], limit=1)
                if not customer:
                    customer_zid_id = order.get('customer')['id']
                    message = self.import_customers(customer_zid_id)
                    if message:
                        if message.get('type') == 'error':
                            queue._error(message.get("description"))
                            return False
                    customer = self.env['res.partner'].search(
                        [('zid_id', '=', order.get('customer')['id'])], limit=1)
            
            if order.get('order_total'):
                order_total = order.get('order_total')
            # =======================================================================
            # Prepare order_line with product, description, quantity, price, tax
            # =======================================================================
            
            if order.get('products'):
                quantity = 0.0
                price = 0.0
                total = 0.0
                taxes_list = []
                products = order.get('products')
                for product in products:
                    product_id = self.env['product.template'].search(
                        [('default_code', 'ilike', product['sku'])], limit=1)
                    product_variant_id = False
                    if product_id:
                        product_variant_id = product_id.product_variant_id
                    else:
                        product_variant_id = self.env['product.product'].search([('default_code', 'ilike', product['sku'])], limit=1)

                        if not product_variant_id and product.get('id'):
                            self.import_products(product.get('id'))
                            product_variant_id = self.env['product.product'].search([
                                ('default_code', 'ilike', product['sku'])
                            ], limit=1)
                        else:
                            vals = {
                                'name': product['name'],
                                'zid_id': zid_id,
                                'default_code': product['sku'],
                                'categ_id': self.sh_default_category.id,
                                'weight': res_json['weight']['value'] if res_json.get('weight') else 0.0,
                                'sh_zid_arabic_name': res_json.get('slug') if res_json.get('slug') else '',
                            }
                          
                            already_imported = self.env['product.template'].create(vals)
                    if not product_variant_id:
                        error = f"Product '{product['name']}' does not have sku or not found in odoo with sku '{product['sku']}' !"
                        queue._error(error)

                        self.zid_log(error, state='error')
                        stop = True
                        return
                    if 'quantity' in product:
                        quantity = product['quantity']
                    if 'price' in product:
                        price = product['price']
                    if 'total' in product:
                        total = product['total']
                    if product['is_taxable']:
                        if product['tax_percentage'] > 0:
                            tax_percentage = self.env['account.tax'].search(
                                [('amount', '=', (product['tax_percentage']*100)), ('type_tax_use', '=', 'sale')], limit=1)
                            if not tax_percentage:
                                tax_vals = {
                                    'name': 'Tax' + str(product['tax_percentage'])+'%',
                                    'amount': float(product['tax_percentage']*100),
                                    'type_tax_use': 'sale',
                                }
                                tax_percentage = self.env['account.tax'].create(
                                    tax_vals)
                            taxes_list.append(tax_percentage.id)
                    if not stop:
                        order_lines.append([0, 0, {
                            'product_id': product_variant_id.id,
                            # 'name': product_id.name,
                            'name': product_variant_id.name,
                            'product_uom_qty': quantity,
                            'price_unit': price,
                            'tax_id': [(6, 0, taxes_list)],
                            'price_subtotal':total,
                        }])
            
            # Check for dicosunt and shipping
            shipping_charge = 0.0
            discount = 0.0
            if order.get('payment'):
                for invoice_details in order['payment']['invoice']:
                    if invoice_details['code'] == 'shipping':
                        shipping_charge += float(
                            invoice_details['value'])
                    if invoice_details['code'] == 'free_shipping_coupon':
                        shipping_charge += float(
                            invoice_details['value'])
                    if invoice_details['code'] == 'shipping_discount':
                                shipping_charge += float(invoice_details['value'])
                    if invoice_details['code'] == 'coupon':
                        discount += float(invoice_details['value'])
            # ==================================================================
            # Add shipping method on order_line if exist
            # ==================================================================
            
            if self.discount_product:
                if discount < 0.0:
                    order_lines.append([0, 0, {
                        'product_id': self.discount_product.product_variant_id.id,
                        'name': self.discount_product.product_variant_id.name,
                        'product_uom_qty': 1.0,
                        'price_unit': discount + ((discount * 15)/100),
                        'tax_id': [(6, 0, taxes_list)],
                    }])
            if shipping_charge > 0.0 and taxes_list:
                shipping_charge = shipping_charge + \
                    ((shipping_charge * 15)/100)
            
            if order.get('shipping'):
                if order.get('shipping')['method']:
                    shipping_method = order.get('shipping')['method']['name']
                    shipping_method_already_import = self.env['delivery.carrier'].search(
                        [('zid_name', '=', shipping_method)], limit=1)
                    if not shipping_method_already_import:
                        product_alreay_imported = False
                        if not shipping_method_already_import:
                            if shipping_method:
                                product_alreay_imported = self.env['product.template'].search(
                                    [('name', '=', shipping_method)], limit=1)
                                if not product_alreay_imported:
                                    vals = {
                                        'name': shipping_method,
                                    }
                                    product_alreay_imported = self.env['product.template'].create(
                                        vals)
                            deliver_option_vals = {
                                'name': shipping_method,
                                'product_id': product_alreay_imported.product_variant_id.id,
                                'delivery_type': 'fixed',
                                'zid_name': shipping_method,
                            }
                            shipping_method_already_import = self.env['delivery.carrier'].create(
                                deliver_option_vals)
                    order_lines.append([0, 0, {
                        'product_id': shipping_method_already_import.product_id.product_variant_id.id,
                        'name': shipping_method_already_import.product_id.product_variant_id.name,
                        'product_uom_qty': 1.0,
                        'price_unit': shipping_charge,
                        'is_delivery': True,
                        'tax_id': [(6, 0, taxes_list)],
                    }])
            # ==================================================================
            # Get payment method(Journal) from zid
            # ==================================================================
            if not stop:
                if order.get('payment'):
                    if order.get('payment')['method']:
                        sh_zid_payment_journal = self.env['account.journal'].search(
                            [('zid_code', '=', order.get('payment')['method']['code'])], limit=1)
                domain = [('zid_id', '=', zid_id)]
                already_imported = self.env['sale.order'].search(
                    domain)
                

                if currency_code:
                    pricelist_id = self.env['product.pricelist'].search(
                        [('currency_id.name', '=', currency_code)], limit=1).id
                if order.get('order_status'):
                    workflow_id = self.env['sh.auto.sale.workflow'].search(
                        [('zid_order_state', '=', order.get('order_status')['code'])], limit=1).id
                vals = {
                    'zid_id': zid_id,
                    'state': state,
                    'partner_id': customer.id,
                    'order_line': order_lines,
                    'user_id': SUPERUSER_ID,
                    'amount_total': order_total,
                    'workflow_id': workflow_id,
                    'pricelist_id': pricelist_id if pricelist_id else customer.property_product_pricelist.id,
                    'sh_zid_payment_journal': sh_zid_payment_journal.id if order.get('payment') and order.get('payment')['method'] and sh_zid_payment_journal else False,
                }
                if self.delivery_warehosue:
                    vals['warehouse_id'] = self.delivery_warehosue.id
                if self.sh_zid_id_appear_in_order:
                    vals['name'] = zid_id
                date_order = False
                if order.get('issue_date'):
                    date_order=order.get('issue_date').split(' ')[0]
                    date_time=datetime.strptime(date_order,'%d-%m-%Y')
                    date_order=datetime.combine(date_time, datetime.min.time())
                    vals['date_order']=date_order
                    vals['zid_so_date'] = date_order
                # =====================================================================
                # Crate or update order with order_line and auto sale order work flow
                # =====================================================================
                if already_imported:
                    # TODO: Add the inverse condition in the starting of the code,
                    # if state not draft, return from their.
                    if already_imported.state == 'draft':
                        for line in already_imported.order_line:
                            line.unlink()
                        already_imported.write(vals)
                        if date_order:
                            already_imported.write({'date_order': date_order})
                    # one_count += 1
                else:
                    # one_count += 1
                    new_sale_order = self.env['sale.order'].create(vals)
                    
                    if order.get('order_status')['code'] != 'new':
                        new_sale_order.action_confirm()
                    if date_order:
                        new_sale_order.write({'date_order': date_order})

                one_count += 1
                if one_count > 0:
                    find_queue = self.env['sh.zid.queue'].search([
                        ('sh_order_id', '=', import_values),
                        ('queue_type', '=', 'sale_order')
                    ])
                    if find_queue:
                        find_queue._done()
                    

        # ==================================================================
        # Manage log to display message to user
        # ==================================================================
        except Exception as e:
            queue._error(str(e))
            self.zid_log(e, state='error')

    def manage_import_order_from_zid(self):
        zid_config = self.env['zid.config'].search([], limit=1)
        if not zid_config:
            return
        if not zid_config.auto_import_order:
            return
        global PAGE_NO
        querystring = {
            "per_page": "50",
            "page": f"{PAGE_NO}",
            "date_from": f"{zid_config.last_sync_order.date()}"
        }
        success, res_json = self._get_req('orders', querystring)
        if not success:
            return
        if 'error' in res_json:
            zid_config.zid_log(res_json['error'], state='error')
            return
        created = 0
        stage_name_list = []
        if zid_config.sh_zid_stage_ids:
            stage_name_list = zid_config.sh_zid_stage_ids.mapped('name')
        orders = res_json['orders']
        if not orders:
            PAGE_NO = 1
        for order in orders:
            # ==================================================================
            # Import order from zid to queue
            # ==================================================================
            if not order.get('order_status'):
                continue
            if not order['order_status'].get('code'):
                continue
            if not order['order_status']['code'] in stage_name_list:
                continue
            zid_id = order.get('id')
            code = ''
            if 'code' in order:
                code = order.get('code')
            find_in_queue = False
            find_in_queue = self.env['sh.zid.queue'].search([
                ('sh_order_id', '=', zid_id),
                ('queue_type', '=', 'sale_order')
            ])
            find_in_sale_order = self.env['sale.order'].search(
                [('zid_id', '=', zid_id)])
            if not find_in_sale_order:
                if not find_in_queue:
                    created += 1
                    zid_config.create_queue('sale_order', zid_id, code)
                else:
                    created += 1
                    find_in_queue._draft()
    # ==================================================================
    # Manage log to display message to users
    # ==================================================================
        zid_config.last_sync_order = datetime.now()
        if created:
            zid_config.zid_log(f'{created} Orders Added to the Queue')
        else:
            zid_config.zid_log('No Order Found')
        PAGE_NO += 1
        zid_config.manage_import_order_from_zid()
