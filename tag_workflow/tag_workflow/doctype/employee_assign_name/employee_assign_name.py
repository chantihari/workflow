# Copyright (c) 2021, SourceFuse and contributors
# For license information, please see license.txt

from frappe.model.document import Document
import frappe

class EmployeeAssignName(Document):
    pass

@frappe.whitelist()
def employee_email_filter(email):
    emp_docname = frappe.db.get_value('Employee', {"user_id": email}, ['name'])
    if emp_docname:
        emp_doc = frappe.get_doc('Employee', emp_docname)
        if not emp_doc.has_permission("read"):
            frappe.local.response['http_status_code'] = 500
            frappe.throw(('Insufficient Permission for User '+email))
        if frappe.session.user!="Administrator" and frappe.db.get_value("User",frappe.session.user,"role_profile_name")!="Tag Admin":
            sql = """SELECT company from `tabEmployee` where user_id="{}" """.format(email)
            data = frappe.db.sql(sql, as_dict=True)
            for i in data:
                return i["company"]
    return None