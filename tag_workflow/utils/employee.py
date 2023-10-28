import frappe
from frappe import _

EMP = 'Employee'
@frappe.whitelist()
def delete_items():
	"""delete selected items"""
	import json
	
	items = sorted(json.loads(frappe.form_dict.get('items')), reverse=True)
	doctype = frappe.form_dict.get('doctype')

	if len(items) > 10 and doctype == EMP:
		frappe.enqueue('frappe.desk.reportview.delete_bulk_employee',
			doctype=doctype, items=items)
	elif len(items) > 10:
		frappe.enqueue('frappe.desk.reportview.delete_bulk',
			doctype=doctype, items=items)
	else:
		delete_bulk_employee(doctype,items) if doctype == EMP else delete_bulk(doctype, items)

def delete_bulk(doctype, items):
	for i, d in enumerate(items):
		try:
			frappe.delete_doc(doctype, d)
			if len(items) >= 5:
				frappe.publish_realtime("progress",
					dict(progress=[i+1, len(items)], title=_('Deleting {0}').format(doctype), description=d),
						user=frappe.session.user)
			# Commit after successful deletion
			frappe.db.commit()
		except Exception:
			# rollback if any record failed to delete
			# if not rollbacked, queries get committed on after_request method in app.py
			frappe.db.rollback()

def delete_bulk_employee(doctype, items):
	for i, d in enumerate(items):
		try:
			unlink_data(d)
			frappe.delete_doc(doctype, d)
			if len(items) >= 5:
				frappe.publish_realtime("progress",
					dict(progress=[i+1, len(items)], title=_('Deleting {0}').format(doctype), description=d),
						user=frappe.session.user)
			# Commit after successful deletion
			frappe.db.commit()
		except Exception as e:
			print(e)
			# rollback if any record failed to delete
			# if not rollbacked, queries get committed on after_request method in app.py
			frappe.db.rollback()

def unlink_data(emp):
	assign_employee = f"select name from `tabAssign Employee Details` where parenttype='Assign Employee' and employee ='{emp}'"
	assign_data = frappe.db.sql(assign_employee,as_dict=True)
	if len(assign_data)>0:
		for i in assign_data:
			frappe.db.sql(f"delete from `tabAssign Employee Details` where name='{i.name}'")
			frappe.db.commit()
	timesheet = f"select name from `tabTimesheet` where employee='{emp}'"
	timesheet_data = frappe.db.sql(timesheet,as_dict=True)
	if len(timesheet_data)>0:
		for i in timesheet_data:
			frappe.db.sql(f"delete from `tabTimesheet` where name='{i.name}'")
			frappe.db.commit()
	company = f"select name from `tabEmployee Assign Name` where parenttype='Company' and employee='{emp}'"
	company_data = frappe.db.sql(company,as_dict=True)
	if len(company_data)>0:
		for i in company_data:
			frappe.db.sql(f"delete from `tabEmployee Assign Name` where name='{i.name}'")
			frappe.db.commit()
	email = frappe.db.get_value(EMP,emp,'email')
	if frappe.db.exists('User',email):
		frappe.db.sql(f"update `tabUser` set enabled=0 where name='{email}'")

@frappe.whitelist()
def delete_data(emp):
	try:
		unlink_data(emp)
		frappe.delete_doc('Employee', emp)
		frappe.db.commit()
		return "Done"
	except Exception as e:
		frappe.log_error(e,'Employee deletion error')
		frappe.db.rollback()