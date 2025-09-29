{
    "name": "ZID Odoo Integration | ZID Odoo API",
    "author": "insightful-erp ",
    "website": "https://www.insightful-erp.com",
    "support": "support@insightful-erp.com",
    "version": "18.0.2.0.0",
    "license": "OPL-1",
    "category": "Extra Tools",
    "summary": "ZID Odoo API - Seamless integration between ZID e-commerce platform and Odoo ERP. Import customers, products, and sales orders automatically with advanced synchronization features.",
    "description": """
ZID Odoo API - Complete Integration Solution

Seamlessly connect your ZID e-commerce platform with Odoo ERP system. This powerful connector enables automatic synchronization of:

• Customers - Import customer data from ZID to Odoo with complete contact information
• Products - Sync product catalogs including images, descriptions, and pricing
• Sales Orders - Automatically import orders with full order details and status tracking
• Order Stages - Maintain order workflow synchronization between platforms

Key Features:
• Automated synchronization with configurable cron jobs
• Manual import options for selective data transfer
• Complete order lifecycle management
• Real-time logging and error tracking
• Multi-language support
• Professional ZID Partner account integration

Perfect for businesses looking to streamline their e-commerce and ERP operations with ZID platform integration.
""",
    'depends': ['base', 'contacts', 'product', 'sale_management', 'delivery', 'account', 'stock'],
    'data': [
        # security
        'security/sh_zid_api_groups.xml',
        'security/ir.model.access.csv',
        # data
        'data/sh_zid_order_stage_data.xml',
        'data/ir_cron_data.xml',
        'data/sh_zid_queue_actions.xml',
        # wizard
        'wizard/sh_zid_import_order_views.xml',
        # views
        'views/product_product_views.xml',
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/sh_auto_sale_workflow_views.xml',
        'views/sh_zid_config_views.xml',
        'views/sh_zid_base_log_views.xml',
        'views/sh_zid_queue_views.xml',
        'views/sh_zid_order_stage_views.xml',
        'views/sh_zid_product_category_views.xml',
        'views/sh_zid_customer_views.xml',
        'views/sh_zid_product_views.xml',
        'views/sh_zid_orders_views.xml',
        # views: Menues
        'views/sh_zid_menues.xml',
    ],
    "application": True,
    "auto_install": False,
    "installable": True,
    "images": ["static/description/background.png"],
    "price": "131.86",
    "currency": "EUR"
}
