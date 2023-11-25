{
    'name': 'Show on partner credit debit payments and unreconciled entries and credit_limit',
    'category': 'Accounting/Accounting',
    'version': '14.0.0.2',
    'author':'Nexterp Romania',
    'description': ''' Show on partner credit debit payments and unreconciled entries
    in tab invoicing, show existing partner fields  debit, credit, has_unreconciled_entries
    
    addend also total_bills
    
    and added total_payments 

    install also partner_statement from oca to view reports on partner invoices..
    
    0.2  added credit limit. You can not invoice a partner if will pass the credit limit.
    will give error also at sale order at writing a status of ['sent','done','sale']
    
    
    !!!not woking in website sale gives error; must be put as error at payment acquiere
    
''',
    'depends': ['account',
                'purchase', # only to put total_bills in same vendor bills button
                'sale', # just for credit_limit to give error also on sale_order
                ],
    'data': [
        'views/res_partner.xml',
    ],
    

    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
}
