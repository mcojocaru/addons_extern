{
    'name': 'conditional delivery',
    'category': 'Website',
    'version': '14.0.0.1',
    'author':'Nexterp Romania',
    'description': ''' 
a domain on delivery applied on res_partner, so you can let only deliveries that met a condition.
for example [('name','ilike','a')] put on a delivery will show this delivery only to partners that have the name containing a 
   
''',
    'depends': ['website_sale_delivery', ],
    'data': [
        'views/delivery.xml',
     ],

    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
}
