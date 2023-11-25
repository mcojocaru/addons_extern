{
    'name': 'After delivery automated posted invoice, payment ',
    'category': 'Stock',
    'version': '14.0.0.4',
    'author':'Nexterp Romania',
    'description': ''' 
    simplifing the odoo flux less clicks more thinks automaticaly.
    utomated posted invoice, payment after delivery
    1. at picking, the button validate now is validating without backorder, another button exist for original validate with posibility of backorder
    2. at validate the transfer is calling the button 'create invoice' from sale_order  that creating a invoice without downpayment and is validating it
    3  the resulting invoice from step2 is stored in picking in field created_invoice_id (visible in tab Aditional Info) and exist posibility to print it
    4. If the sale has a payment transaction will put in on the invoice ( will make the caputre transaction) 
    5. the print of invoice exist also on barcode interface
    6. at difference between sale order and delivery will put on sale_order and invoice fields paid_more paid_less and difference_between_order_and_deliverd
    7. exist also another filed string resolved difference 
    8. view of new field in invoice and sale_order
    !! If is a difference between the sale order & payment and the delivered quantity:
       ! if the payment is on delivery will modify this value with the value of delivered goods
       ! it the payment is bank will capture the transaction that exists
       !     and you must give them back the money as a wrong payment and if is too few to tell them to pay the invoice
       !?  another version would be to create a advance invoice, than to reverse it and to make the payment or to make somehow to put in on a future sale
 v0.3 #20211027   modified with try because the the payment_action_capure at sale order for bt pay is giving error Payment must be in approved state
 v0.4 skip_create_invoice_after_transfer   in context at validation of pickings and will not create invoices      
''',
    'depends': ['stock',
                'sale',
                'barcodes',
                'payment', 
                'stock_barcode', # just to show print invoice in stock_barcode application 
                'delivery',
            #    'cbs_solutions_customization', # for format of invoice with payment
                ],
    'data': [
        'views/stock_picking.xml',
        'views/assets.xml',
        'views/sale_order.xml',
        'views/account_move.xml',
    ],
    'qweb': [
        "static/src/xml/qweb_templates.xml", # just to show print invoice in stock_barcode application
    ],    

    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
}
