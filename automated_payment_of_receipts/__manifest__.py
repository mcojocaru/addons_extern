{
    'name': 'auto payment of receipts ',
    'category': 'account',
    'version': '14.0.0.1',
    'author':'',
    'description': ''' 
now at a receipt you have to make the payment, but the receipt is a bill that has been paid in same day usualy with cache or with card

this module will add 2 new buttons

confirm paid by cache and by bank that will make also the payment in fist journal of that type that is found ( like pressing the Confirm and than the register payments)

used at simple accounting by cbs ( no enterprise module) no use of account.bank.statement
''',
    'depends': [
                'account', 
                ],
    'data': [
        'views/account_move.xml',
    ],

    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
}
