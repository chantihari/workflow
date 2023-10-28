from __future__ import unicode_literals

from frappe import _


def get_data(data):
	if data:
	    return {
	            'fieldname': 'lead',
	            'transactions': [
	                {
	                    'label': _('Reference'),
	                    'items': ['Contract']
	                },
	            ]
	    }
	

