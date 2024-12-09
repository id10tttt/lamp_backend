{
    "name": "Lamp Order",
    "summary": "Lamp Order",
    "author": "1di0t",
    "license": "AGPL-3",
    'depends': ['base', 'web', 'product', 'stock', 'sale'],
    "data": [
        "views/sale_order_view.xml",
        "views/res_partner_view.xml",
        "views/stock_warehouse_view.xml",
        "views/product_template_view.xml",
    ],
    "installable": True,
    "auto_install": False,
}
