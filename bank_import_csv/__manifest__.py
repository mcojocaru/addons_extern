{
    'name': 'Import CSV Romania Banca Transilvania as payments',
    'category': 'Accounting/Accounting',
    'version': '14.0.0.1',
    'author':'Nexterp Romania',
    'description': ''' import banca transilvania csv format bank
    we are going to import the statement as  account.payments  and not as account.bank.statement.line
    the complexity of workig is 10 times bigger in having 2 models for payments instead of one with 2 more fields
    
    no more invoice in_payment, no more 2 recociliation, no more same info in pyament and bank account.bank.statement.line
    no more hiden menus for statements ..
    
    future:
    1. on customer to exist also payments; and a difference between invoices and payments. to view also not_payd invoices.
    2. also to reconcile the payments with invoices
    3. in payment list also to review = that that have as client not found clinet


used at simple accounting by cbs ( no enterprise module) no use of account.bank.statement
''',
    'depends': ['account'],
    'data': [
        'wizard/account_payment_import_bank.xml',
        'wizard/result_wizard.xml',
        
        'views/account_payment.xml',
        'views/assets.xml',
        'security/ir.model.access.csv',
        'data/default_partner_at_unknown_payments.xml'
    ],
    
    'qweb': [ "static/src/xml/button_after_create_payment.xml",],
    'external_dependencies': {
        'python': [
            'distlib',
        ]
    },
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
}
