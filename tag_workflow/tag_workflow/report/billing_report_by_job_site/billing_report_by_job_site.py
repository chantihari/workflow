# Copyright (c) 2023, SourceFuse and contributors
# For license information, please see license.txt

import frappe
import datetime

def execute(filters=None):
	if not filters:
		filters={}
	js_search=filters.get('job_sites')
	time_format = '%Y-%m-%d'
	condition=""
	if(filters.get('start_date')):
		from_date = datetime.datetime.strptime(str(filters.get('start_date')), time_format)
		condition+=f" and JO.from_date>'{from_date}'"
	else:
		from_date=""
	if(filters.get('end_date')):
		to_date = datetime.datetime.strptime(str(filters.get('end_date')), time_format)
		condition+=f" and JO.to_date<'{to_date}'"
	else:
		to_date=""

	today = datetime.datetime.now()
	job_site_name='Job Site Name'
	fromdate='From Date'
	todate='To Date'
	columns, data = [], []
	columns=[
			{'fieldname':'job_sites','label':(job_site_name),'fieldtype':'Data','width':520},
			{'fieldname':'from_date','label':(fromdate),'fieldtype':'Date','width':150},
			{'fieldname':'to_date','label':(todate),'fieldtype':'Date' ,'width':150},
			{'fieldname':'total_hours_worked','label':('Total Cost'),'fieldtype':'Currency','width':200}
		]
	if(to_date and today.date() < to_date.date()):
		frappe.msgprint("You Can't Fetch record of Future Date")
	elif(from_date and today.date() < from_date.date()):
		frappe.msgprint("You Can't Fetch record of Future Date")
	elif(to_date and from_date and to_date.date()<from_date.date()):
		frappe.msgprint("To Date can't be before From Date")
	else:
		current_company=frappe.db.sql('''select company from `tabUser` where email='{}' '''.format(frappe.session.user),as_list=1)
		data= fields_data(current_company,filters,js_search,condition)
		
			
	return columns, data

def fields_data(current_company,filters,js_search,condition):
	data=[]
	if(len(current_company)==0 or current_company[0][0]=='TAG'):
		print('For admins'*50)
		if(filters.get('job_sites')):
			data=frappe.db.sql('''select JO.job_site,min(JO.from_date),max(JO.to_date),sum(TD.billing_amount) from`tabJob Order` as JO,`tabTimesheet` as T,`tabTimesheet Detail` as TD where T.workflow_state='Approved' and T.name=TD.parent and T.job_order_detail=JO.name and JO.job_site like '%{0}%' {1}  group by JO.job_site'''.format(js_search,condition))
		else:
			data=frappe.db.sql('''select JO.job_site,min(JO.from_date),max(JO.to_date),sum(TD.billing_amount) from`tabJob Order` as JO,`tabTimesheet` as T,`tabTimesheet Detail` as TD where T.workflow_state='Approved' and T.name=TD.parent and T.job_order_detail=JO.name {0} group by JO.job_site'''.format(condition))

	else:
		current_company=current_company[0][0]
		if(filters.get('job_sites')):
			data=frappe.db.sql('''select JO.job_site,min(JO.from_date),max(JO.to_date),sum(TD.billing_amount) from`tabJob Order` as JO,`tabTimesheet` as T,`tabTimesheet Detail` as TD where T.workflow_state='Approved' and T.name=TD.parent and T.job_order_detail=JO.name and JO.company='{0}' and JO.job_site like '%{1}%' {2} group by JO.job_Site'''.format(current_company,js_search,condition))
		else:
			data=frappe.db.sql('''select JO.job_site,min(JO.from_date),max(JO.to_date),sum(TD.billing_amount) from`tabJob Order` as JO,`tabTimesheet` as T,`tabTimesheet Detail` as TD where T.workflow_state='Approved' and T.name=TD.parent and T.job_order_detail=JO.name and JO.company='{0}' {1} group by JO.job_site'''.format(current_company,condition))
	return data
