# Copyright (c) 2013, SourceFuse and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
	if not filters:
		filters={}
	from_date=filters.get('start_date')
	to_date=filters.get('end_date')
	columns,data=[],[]

	if frappe.utils.getdate(from_date) > frappe.utils.getdate(to_date):
		frappe.msgprint(" Start Date is Greater Than End Date")
		return columns,data

	columns=[
		{'fieldname':'employee_name','label':('Employee Name'),'fieldtype':'Data','width':150},
        {'fieldname':'activity_type','label':('Job Title'),'fieldtype':'Data','options':'Job Order','width':100},
        {'fieldname':'company','label':('Company'),'fieldtype':'Data','width':100},
        {'fieldname':'total_billable_hours','label':('Hours Worked'),'fieldtype':'Int','width':100},
        {'fieldname':'start_date','label':('Start Date'),'fieldtype':'Date','width':100},
        {'fieldname':'end_date','label':("End Date"),'fieldtype':'Date','width':100},
		{'fieldname':'base_billing_rate','label':('Rate'),'fieldtype':'Currency','width':100},
        {'fieldname':'total_billable_amount','label':('Total Paid'),'fieldtype':'Currency','width':100},
        {'fieldname':'non_satisfactory','label':("Unsatisfactory"),'fieldtype':'Check','width':150},
        {'fieldname':'dnr','label':('DNR'),'fieldtype':'Check','width':100}
	]
	current_company=frappe.db.sql(''' select company from `tabUser` where email='{}' '''.format(frappe.session.user),as_list=1)
	if(len(current_company)==0 or current_company[0][0]=='TAG'):
		sql = ''' SELECT `tabTimesheet`.employee_name, `tabTimesheet Detail`.activity_type, `tabTimesheet`.company, `tabTimesheet`.total_billable_hours, `tabTimesheet`.start_date, `tabTimesheet`.end_date, `tabTimesheet Detail`.base_billing_rate, `tabTimesheet`.total_billable_amount, `tabTimesheet`.non_satisfactory, `tabTimesheet`.dnr FROM `tabTimesheet`, `tabTimesheet Detail` WHERE `tabTimesheet`.start_date >= '{0}' and `tabTimesheet`.end_date <= '{1}' and `tabTimesheet`.name = `tabTimesheet Detail`.parent'''.format(from_date,to_date)
		data=frappe.db.sql(sql)
	else:
		current_company=current_company[0][0]
		sql = '''SELECT `tabTimesheet`.employee_name, `tabTimesheet Detail`.activity_type, `tabTimesheet`.company, `tabTimesheet`.total_billable_hours, `tabTimesheet`.start_date, `tabTimesheet`.end_date, `tabTimesheet Detail`.base_billing_rate, `tabTimesheet`.total_billable_amount, `tabTimesheet`.non_satisfactory, `tabTimesheet`.dnr FROM `tabTimesheet`, `tabTimesheet Detail` WHERE `tabTimesheet`.start_date >= '{0}' and `tabTimesheet`.end_date <= '{1}' and `tabTimesheet`.name = `tabTimesheet Detail`.parent and employee_company='{2}' '''.format(from_date,to_date,current_company)
		data=frappe.db.sql(sql)

	return columns, data
