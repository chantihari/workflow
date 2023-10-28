from frappe.utils.nestedset import NestedSet

class Company(NestedSet):
	def validate(self):
		self.chart_of_accounts='Standard with Numbers'
		self.default_currency = 'USD'
