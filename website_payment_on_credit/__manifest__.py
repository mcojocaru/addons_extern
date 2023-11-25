{
    'name': 'website payment on credit ',
    'category': 'Website',
    'version': '14.0.1.0.0',
    'author':'Nexterp Romania',
    'description': ''' 
    If the partner has Credit Limit at partner in Sale&Purcase Tab, can show payment_on_credit  option as payment method on site,
    For partners that do not have credit_limit is not showing this type of payment.
    If is over the limit will show a warning and the payment method can not be used (is disabled) .
    It knows when is over the limit from trying to set a sale_order to sent and if raise error will show that error ( form partner_current_debit_credit_payments)
     
    
    When this payment method is selected, the order will be validated automatically ( like at a online payment)
    
    v 0.2 now ok payment also from invoice ( portal) but no check is done there, no error - because does not mather 
    v 1.0.0 without some logs
''',
    'depends': ['payment',
                'website_sale',
                'partner_current_debit_credit_payments',  # to know when the partner is over credit limit  
                'account_payment',
                ],
    'data': [
       'views/payment_transfer_templates.xml',
        'views/payment.xml',
        'views/templates.xml',
        
        'views/account_portal_templates.xml',
        
        'data/payment_acquirer_data.xml',
     ],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
}
