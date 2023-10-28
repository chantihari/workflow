from __future__ import unicode_literals

from frappe import _


def get_data(data):
    if data:
        return {
                'fieldname': 'sales_invoice',
                'internal_links': {
                    'Sales Order': ['items', 'sales_order']
                },
                'transactions': [
                    {
                        'label': _('Reference'),
                        'items': ['Sales Order']
                    },
                ]
        }
    
    
