from __future__ import unicode_literals

from frappe import _


def get_data(data):
    if data:
        return {
                'fieldname': 'company',
                'transactions': [
                    {
                        'label': _('Pre Sales'),
                        'items': ['Job Order', 'Quotation']
                    },
                    {
                        'label': _('Orders'),
                        'items': ['Sales Order', 'Sales Invoice']
                    },
                ]
        }
    
