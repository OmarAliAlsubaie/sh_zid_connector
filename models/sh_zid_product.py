# -*- coding: utf-8 -*-
# Part of insightful-erp Technologies.

from odoo import fields, models,_
from datetime import datetime
from odoo.exceptions import UserError

PAGE_COUNTER = 1

class ZidConfig(models.Model):
    _inherit = 'zid.config'

    # For Product Import
    auto_import_product = fields.Boolean("Auto Import Product")
    auto_export_product = fields.Boolean("Auto Export Product")
    import_product = fields.Boolean("Import Product", default=True)
    export_product = fields.Boolean("Export Product")
    last_sync_product = fields.Datetime("Last Sync Product")
    manage_log_product = fields.Boolean(default=True)
    sync_image = fields.Boolean(
        "Sync Image", help="It will reduce performance", default=True)
    sh_import_based_on_date = fields.Boolean()
    sh_from_date = fields.Datetime()
    sh_to_date = fields.Datetime()
    sh_default_category = fields.Many2one(
        'product.category', string="Default Category", required=True)
    sh_default_warehouse = fields.Many2one('stock.warehouse', required=True, string='Default Warehouse')
    sh_not_update_product = fields.Boolean(
        "Not Update Any Product", default=False)
    next_product_url = fields.Char("Next Product Url")

    # ------------------------------------------
    #  Sync Products
    # ------------------------------------------

    def sync_product(self, product, created):
        zid_id = product.get('id')
        if 'name' in product:
            final_name = product['name']
        else:
            final_name = 'No Name'
        find_in_queue = False
        domain = [('sh_product_id', '=', zid_id),
                  ('queue_type', '=', 'product')]
        find_in_queue = self.env['sh.zid.queue'].search(domain)

        find_in_product_template = self.env['product.template'].search(
            ['|', ('default_code', '=', product.get('sku')),
                ('zid_id', '=', zid_id)])
        if not find_in_product_template:
            product_variant_id = self.env['product.product'].search([
                '|',
                ('default_code', '=', product['sku']),
                ('zid_id', '=', zid_id)
            ], limit=1)
            if product_variant_id:
                find_in_product_template = product_variant_id.product_tmpl_id
        if self.sh_not_update_product:
            if not find_in_product_template:
                self.is_create_or_write(
                    rec=find_in_queue, zid_id=zid_id, final_name=final_name)
                created += 1
        else:
            self.is_create_or_write(
                rec=find_in_queue, zid_id=zid_id, final_name=final_name)
            created += 1
        self.last_sync_product = datetime.now()
        return created

    def get_products(self):
        if not self.check_internet_connection():
                raise UserError(_("No internet connection. Please check your connection and try again."))
     
        self.ensure_one()
        if not self.import_product:
            return
        if not (self.authorization and self.access_token):
            return
        global PAGE_COUNTER
        querystring = {
            "page_size": "100",
            "page": f"{PAGE_COUNTER}"
        }
        success, res_json = self._get_req('products', querystring, stor_id_in_header=True)
        if not success:
            self.zid_log(res_json['error'], 'product', res_json)
            return
        if 'error' in res_json:
            self.zid_log(res_json['error'], 'product', 'error')
            return
        created = 0
        products = res_json['results']
        if not products:
            PAGE_COUNTER = 1
            return
        for product in products:
            # find_in_product_template = False
            # ===========================================================
            # Import product in between from date and to date in queue
            # ===========================================================
            if product.get('created_at') and self.sh_import_based_on_date:
                if datetime.fromisoformat(product.get('created_at')[:-1]) > self.sh_from_date and datetime.fromisoformat(product.get('created_at')[:-1]) < self.sh_to_date:
                    created = self.sync_product(product, created)
            # ========================================================
            # Import all product in queue
            # ========================================================
            else:
                created = self.sync_product(product, created)
        # ========================================================
        # Create entry on log to display message to user
        # ========================================================
        if created:
            self.zid_log(f'{created} Product Added to the Queue', 'product')
        else:
            self.zid_log('No Product Found', 'product')

        if res_json.get("next"):
            self.next_product_url = res_json.get("next")
            PAGE_COUNTER += 1
            self.get_products()
        else:
            PAGE_COUNTER = 1
            self.next_product_url = False

    # -------------------------------
    #  Cron: Import products
    # -------------------------------

    def manage_import_product(self):
        domain = [('queue_type', '=', 'product'),
                  ('sh_current_state', '=', 'draft')]
        get_con = self.env['sh.zid.queue'].search(
            domain, order="id asc", limit=50)
        if get_con:
            counter = 0
            for data in get_con:
                counter += 1
                data.sh_current_config.import_products(data.sh_product_id)
            if counter:
                get_con[0].sh_current_config.zid_log(f"Cron : Imported Successfully {counter} Product", 'product')

    def get_quantity(self, product, quantity):
        # ================================================================
        # create or update record on stock.quant from quantity of zid
        # ================================================================
        if isinstance(product, str):
            product_record = self.env['product.product'].search(
                [('zid_id', '=', product)], limit=1)
        else:
            product_record = self.env['product.product'].search(
                [('product_tmpl_id', '=', product.id)], limit=1)
        if product_record:
            find_quant = self.env['stock.quant'].search(
                [('product_id', '=', product_record.id)], limit=1)
            final_quantity = float(quantity)
            if final_quantity >= 0:
                qty_vals = {
                    'product_id': product_record.id,
                    'product_tmpl_id': product_record.product_tmpl_id.id,
                    'location_id': self.sh_default_warehouse.lot_stock_id.id,
                    'quantity': final_quantity,
                }
                if find_quant:
                    find_quant.write(qty_vals)
                else:
                    self.env['stock.quant'].sudo().create(qty_vals)

    def import_products(self, import_values):
        queue = self.env['sh.zid.queue'].search([('sh_product_id', '=', import_values)], limit=1)
        if not (self.authorization and self.access_token):
            # ========================================================
            # note on queue if any error generate
            # ========================================================
            queue._error("Plz Genearte Token Before Importing")
            self.zid_log('No Token Found, genearte token again', 'product', 'error')
            return
        try:
            one_count = 0
            success, res_json = self._get_req('product_by_id', zid_id=import_values, stor_id_in_header=True)
            if not success:
                queue._error(res_json)
                return
            if 'error' in res_json:
                queue._error(f"Error: {res_json['error']} !")
                return
            # ========================================================
            # Get all field value from zid
            # ========================================================
            zid_id = res_json.get('id')
            name = f'Name not found for zid ID: {zid_id} !'
            if res_json.get('name'):
                name = res_json.get('name')
            sku = False
            list_price = 0.0
            quantity_onhand = 0.0
            list_to_keep_attr = []
            list_to_keep_attr_value = []
            category_list = []
            description = ''
            if res_json.get('sku'):
                sku = res_json.get('sku')
            if res_json.get('sale_price'):
                list_price = res_json.get('sale_price')
            elif res_json.get('price'):
                list_price = res_json.get('price')
            if res_json.get('quantity'):
                quantity_onhand = res_json.get('quantity')
            if res_json.get('description'):
                description = res_json.get('description')
            if res_json.get('categories'):
                categories = res_json.get('categories')
                for category in categories:
                    category_imported = self.env['sh.zid.product.category'].search(
                        [('zid_id', '=', category['id'])], limit=1)
                    if category['name']:
                        category_vals = {
                            'zid_id': category['id'],
                            'name': category['name'],
                            'website_description': category['description'],
                            'zid_slug': category['slug'],
                        }
                        if category_imported:
                            category_imported.write(category_vals)
                        else:
                            category_imported = self.env['sh.zid.product.category'].create(
                                category_vals)
                        category_list.append((4, category_imported.id))
            encoded = ''
            if self.sync_image and 'images' in res_json and res_json['images']:
                images = res_json['images']
                image_url = images[0]['image']['large']
                encoded = self._get_req_img(image_url)

            already_imported = self.env['product.template'].search([
                '|',
                ('default_code', '=', sku),
                ('zid_id', '=', zid_id)
            ])
            vals = {
                'zid_id': zid_id,
                'name': name,
                'default_code': sku,
                'list_price': list_price,
                'description': description if res_json.get('description') else 0.0,
                'categ_id': self.sh_default_category.id,
                'sh_zid_categ_ids': category_list,
                'image_1920': encoded if 'images' in res_json and res_json.get('images') else '',
                'weight': res_json['weight']['value'] if res_json.get('weight') else 0.0,
                'sh_zid_arabic_name': res_json.get('slug') if res_json.get('slug') else '',
            }
            # ============================
            # Create or Update Product
            # ============================
            vals.update({
                    'type': 'consu',
                    'is_storable':True,
                    'tracking':'none'
                })
            if already_imported:
                one_count += 1
                already_imported.write(vals)
                if not res_json.get('variants'):
                    self.get_quantity(already_imported, quantity_onhand)
            else:
                one_count += 1
              
                already_imported = self.env['product.template'].create(
                    vals)
                if not res_json.get('variants'):
                    self.get_quantity(already_imported, quantity_onhand)
            # ============================
            # Getting Variant
            # ============================
            if res_json.get('variants'):
                variant_count = 0
                attr_vals_list = []
                pro_attr_line_obj = self.env['product.template.attribute.line']
                pro_attr_value_obj = self.env['product.attribute.value']
                pro_attr_obj = self.env['product.attribute']
                attr_ids_list = []
                dic_attr_id_value_ids_list = {}
                # ========================================================
                # Crate or update Attribute and its value
                # ========================================================
                for attribute in res_json.get('options'):
                    if already_imported:
                        attr_name = attribute['name']
                        search_attr_name = False
                        search_attr_name = pro_attr_obj.search(
                            [('name', '=', attr_name)], limit=1)
                        if not search_attr_name:
                            search_attr_name = pro_attr_obj.create(
                                {'name': attr_name})
                        attr_ids_list.append(search_attr_name.id)
                        dic_attr_id_value_ids_list[search_attr_name.id] = [
                        ]
                        value_name_list = attribute.get("choices", [])
                        list_value_ids = []
                        for value_name in value_name_list:
                            search_attr_value = False
                            search_attr_value = pro_attr_value_obj.search([
                                ('name', '=', value_name),
                                ('attribute_id', '=', search_attr_name.id)
                            ], limit=1)
                            if not search_attr_value:
                                search_attr_value = pro_attr_value_obj.create({
                                    'name': value_name,
                                    'attribute_id': search_attr_name.id
                                })
                            list_value_ids.append(search_attr_value.id)
                        dic_attr_id_value_ids_list[search_attr_name.id] = list_value_ids
                        product_var_obj = self.env[
                            'product.product']
                        domain = [('product_tmpl_id', '=', already_imported.id)]
                        for value_id in list_value_ids:
                            domain.append(('product_template_attribute_value_ids.product_attribute_value_id.id',
                                            '=', value_id))
                        product_varient = product_var_obj.search(
                            domain, limit=1)
                        if not product_varient:
                            search_attr_line = pro_attr_line_obj.search(
                                [
                                    ('attribute_id', '=', search_attr_name.id),
                                    ('product_tmpl_id', '=',
                                        already_imported.id),
                                ], limit=1)
                            if search_attr_line:
                                past_values_list = []
                                past_values_list = search_attr_line.value_ids.ids
                                past_values_list = past_values_list + list_value_ids
                                search_attr_line.write({
                                    'value_ids':
                                    [(6, 0,
                                        past_values_list
                                        )]
                                })
                            else:
                                pro_attr_line_obj.create({
                                    'attribute_id': search_attr_name.id,
                                    'value_ids': [(6, 0, list_value_ids)],
                                    'product_tmpl_id': already_imported.id,
                                })

                        # Variant Created from attribute
                        # =====================================

                        already_imported._create_variant_ids()

                        # To Keep Attribute Value List
                        # =====================================
                        if list_value_ids:
                            for item in list_value_ids:
                                if item not in list_to_keep_attr_value:
                                    list_to_keep_attr_value.append(item)

                        # To Keep Attribute List

                        # =====================================
                        if attr_ids_list:
                            for item in attr_ids_list:
                                if item not in list_to_keep_attr:
                                    list_to_keep_attr.append(item)
                    else:
                        variant_count += 1
                        domain = [('name', '=', attribute['name'])]
                        get_attr = self.env['product.attribute'].search(
                            domain, limit=1)
                        if get_attr:
                            attr_line_vals = {
                                'attribute_id': get_attr.id
                            }
                            value_list = []
                            value_name = []
                            for xyz in get_attr.value_ids:
                                for res in attribute['values']:
                                    if xyz.name == res:
                                        value_name.append(xyz.name)
                            new_list = []
                            for res in attribute['values']:
                                if res not in value_name:
                                    a_dict = {
                                        'name': res
                                    }
                                    new_list.append((0, 0, a_dict))
                            get_attr.write({'value_ids': new_list})
                            for xyz in get_attr.value_ids:
                                for res in attribute['values']:
                                    if xyz.name == res:
                                        value_list.append(xyz.id)
                            attr_line_vals['value_ids'] = value_list
                        else:
                            attribute_vals = {
                                'name': attribute['name']
                            }
                            valeu = []
                            attr_list = []
                            for res in attribute['values']:
                                a_line_vals = {
                                    'name': res
                                }
                                valeu.append(res)
                                attr_list.append((0, 0, a_line_vals))
                            attribute_vals['value_ids'] = attr_list
                            create_attribute = self.env['product.attribute'].create(
                                attribute_vals)
                            attr_line_vals = {
                                'attribute_id': create_attribute.id,
                                'value_ids': create_attribute.value_ids.ids
                            }
                        attr_vals_list.append((0, 0, attr_line_vals))

                # ========================================================
                # Update Product variant with it's all values from zid
                # ========================================================
                for rec in res_json.get('variants'):
                    if variant_count == 0:
                        vals['list_price'] = rec['price']
                        vals['default_code'] = rec['sku']
                    elif attr_vals_list:
                        vals['attribute_line_ids'] = attr_vals_list
                # product_value = ''
                if already_imported:
                    # product_value = already_imported
                    already_imported.write(vals)
                variant = 0
                for rec in res_json.get('variants'):
                    # ------- Link the product variant ids -------
                    value_list = []
                    if rec.get('attributes'):
                        for _attribute in rec['attributes']:
                            if _attribute.get('value'):
                                _value = _attribute['value']
                                if isinstance(_value, str):
                                    value_list.append(_value)
                                elif isinstance(_value, dict) and _value.get('ar'):
                                    value_list.append(_value['ar'])
                    for value in already_imported.product_variant_ids:
                        if value.product_template_variant_value_ids:
                            if value_list and len(value_list) == 1:
                                for variant_value in value.product_template_variant_value_ids:
                                    if variant_value.name == value_list[0]:
                                        value.sudo().write({
                                            'zid_id': rec.get('id'),
                                            'default_code': rec.get('sku')
                                        })
                    # ====================
                    arabic_name = ''
                    zid_price = 0.0
                    for value in already_imported.product_variant_ids:
                        check = ''
                        check1 = ''
                        check = res_json.get('name') + " - "
                        check1 = res_json.get('name') + " - "
                        for data in value.product_template_attribute_value_ids:
                            check += data.name + " - "
                        for data in reversed(value.product_template_attribute_value_ids):
                            check1 += data.name + " - "
                        if check or check1:
                            check = check[:-2].strip()
                            check1 = check1[:-2].strip()
                            if check == rec['name'] or check1 == rec['name']:
                                variant_vals = {}
                                encoded = ''
                                # ========================================================
                                # Import Image of variant if exist
                                # ========================================================
                                if self.sync_image and 'images' in rec and rec['images']:
                                    image_url = rec['images'][0]['image']['large']
                                    encoded = self._get_req_img(image_url)
                                if 'sale_price' in rec and rec['sale_price']:
                                    zid_price = rec['sale_price']
                                elif 'price' in rec and rec['price']:
                                    zid_price = rec['price']
                                if 'slug' in rec and rec.get('slug'):
                                    arabic_name = rec.get('slug').split('ar-')
                                    arabic_name = arabic_name[0]
                                variant_vals = {
                                    'default_code': rec['sku'],
                                    'zid_id': rec['id'],
                                    'zid_price': zid_price,
                                    'weight': rec['weight']['value'] if rec.get('weight') else 0.0,
                                    'image_1920': encoded if 'images' in rec and rec.get('images') else False,
                                    'sh_zid_arabic_name': arabic_name if rec.get('slug') else '',
                                }
                                if variant_vals:
                                    variant += 1
                                    value.write(variant_vals)
                    # ========================================================
                    # Crate or update Stock.quant with zid quantity
                    # ========================================================
                    if rec['quantity']:
                        quantity = rec['quantity']
                    else:
                        quantity = 0.0
                    self.get_quantity(rec['id'], quantity)
            # ========================================================
            # Crate or update Stock.quant with zid quantity
            # ========================================================
            if one_count > 0:
                find_queue = self.env['sh.zid.queue'].search([
                    ('sh_product_id', '=', import_values),
                    ('queue_type', '=', 'product')
                ])
                if find_queue:
                    # find_queue.unlink()
                    attrs = already_imported.attribute_line_ids.mapped(
                        'attribute_id').filtered(
                            lambda r: r.id not in
                            list_to_keep_attr)
                    for attr in attrs:
                        line = already_imported.attribute_line_ids.search([
                            ('attribute_id', '=', attr.id),
                            ('product_tmpl_id', '=', already_imported.id),
                        ], limit=1)
                        if line:
                            line.unlink()
                    find_queue._done()

                # Remove Unnecessary Attribute Line.
                # ===============================================

                # Remove Unnecessary Attribute Value From Line.
                # ===============================================
                attr_values = already_imported.attribute_line_ids.mapped(
                    'value_ids').filtered(lambda r: r.id not in list_to_keep_attr_value)
                for attr_value in attr_values:
                    line = already_imported.attribute_line_ids.search([
                        ('value_ids', 'in', attr_value.ids),
                        ('product_tmpl_id', '=', already_imported.id),
                    ], limit=1)
                    if line:
                        line.write({
                            'value_ids':
                            [(3, attr_value.id, 0)],
                        })
                # Remove Unnecessary Attribute Value From Line.
                # ===============================================
                # already_imported._create_variant_ids()
                list_to_keep_attr = []
                list_to_keep_attr_value = []
        except Exception as e:
            queue = self.env['sh.zid.queue'].search(
                [('sh_product_id', '=', import_values)], limit=1)
            queue._error(str(e))
            self.zid_log(e, 'product', 'error')
