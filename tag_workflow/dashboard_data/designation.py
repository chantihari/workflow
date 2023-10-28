from erpnext.setup.doctype.designation.designation import Designation
from tag_workflow.utils.doctype_method import append_number_if_name_exists
import frappe
from frappe import _
class DesignationOverride(Designation):
	def validate(self):
		if self.get('__islocal'):
			self.designation = self.designation_name.split("-")[0]
			if not (self.checkingdesignationandorganization(self.designation,self.organization)):
				frappe.throw(
	                 title='Error',
	                 msg=_('Designation name already exists for this organization')
	             )
			data = self.checkingdesignation_name(self.designation_name)
			self.designation_name = data
			self.name = data


	def checkingdesignationandorganization(self,designation_name,company=None):
		sql = "select designation,organization from `tabDesignation` where designation = '{0}' and organization = '{1}' ".format(designation_name,company)
		if len(frappe.db.sql(sql,as_dict=1)) > 1:
			return False
		return True

	def checkingdesignation_name(self,designation_name):
	    designation_name = designation_name.strip()
	    if not designation_name.strip():
	        frappe.throw(_("Abbreviation is mandatory"))
	    sql = "select designation_name from `tabDesignation` where designation_name = '{0}' ".format(designation_name)
	    if frappe.db.sql(sql):
	        return append_number_if_name_exists("Designation", designation_name, fieldname="designation_name", separator="-", filters=None)
	    return designation_name	
