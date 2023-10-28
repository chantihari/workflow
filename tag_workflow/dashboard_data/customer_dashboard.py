from __future__ import unicode_literals

from frappe import _

def get_data(data):
    if data:

        return {
                'heatmap': False,
                'heatmap_message': _('This heatmap is based on <b>Job Order</b>.'),
                'fieldname': 'customer',
                'transactions': [
                    {
                        'label': _('Reference'),
                        'items': ['Sales Invoice']
                    },
                ]
        }
    
