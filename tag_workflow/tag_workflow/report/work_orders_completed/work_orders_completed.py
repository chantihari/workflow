# Copyright (c) 2013, SourceFuse and contributors
# For license information, please see license.txt

import frappe
import datetime
def execute(filters=None):
	if not filters:
		filters={}
	company_search=filters.get('companies')
	time_format = '%Y-%m-%d'
	from_date = datetime.datetime.strptime(str(filters.get('start_date')), time_format)
	to_date = datetime.datetime.strptime(str(filters.get('end_date')), time_format)
	today = datetime.datetime.now()
	staff_company='Staffing Company Name'
	fromdate='From Date'
	todate='To Date'

	if(today.date() < to_date.date()):
		frappe.msgprint("You Can't Fetch record of Future Date")
	elif(today.date() < from_date.date()):
		frappe.msgprint("You Can't Fetch record of Future Date")
	elif(to_date.date()<from_date.date()):
		frappe.msgprint("Start Date Can't be Future Date For End Date")
	else:
		current_company=frappe.db.sql(''' select company from `tabUser` where email='{}' '''.format(frappe.session.user),as_list=1)
		if(len(current_company)==0 or current_company[0][0]=='TAG'):
			columns,data=admin_data(filters,staff_company,fromdate,todate,from_date,to_date,company_search)
		
		else:
			current_company=current_company[0][0]
			columns,data=hiring_data(filters,staff_company,fromdate,todate,from_date,to_date,company_search,current_company)
			
	return columns, data



def admin_data(filters,staff_company,fromdate,todate,from_date,to_date,company_search):
	column, query_data = [], []

	if(filters.get('status')=="Total work orders, Time, and Cost for a staffing agency"):
		column=[
			{'fieldname':'employee_company','label':(staff_company),'fieldtype':'Data','width':150},
			{'fieldname':'from_date','label':(fromdate),'fieldtype':'Date','width':150},
			{'fieldname':'to_date','label':(todate),'fieldtype':'Date' ,'width':150},
			{'fieldname':'name','label':('Total Number of Work Orders'),'fieldtype':'Int','width':150},
			{'fieldname':'base_billing_amount','label':('Total Hours Billed'),'fieldtype':'Currency','width':150},
			{'fieldname':'hours','label':('Total Cost Billed'),'fieldtype':'Float','width':150}
		]
		if(filters.get('companies')):
			query_data=frappe.db.sql(''' select T.employee_company,min(JO.from_date),max(JO.to_date),count(JO.name),sum(TD.base_billing_amount),sum(TD.hours) from`tabJob Order` as JO,`tabTimesheet` as T,`tabTimesheet Detail` as TD where T.workflow_state='Approved' and T.name=TD.parent and T.job_order_detail=JO.name and from_date>'{0}' and end_date<'{1}' and T.employee_company like '{2}%' group by T.employee_company;'''.format(from_date,to_date,company_search))
		else:
			query_data=frappe.db.sql(''' select T.employee_company,min(JO.from_date),max(JO.to_date),count(JO.name),sum(TD.base_billing_amount),sum(TD.hours) from`tabJob Order` as JO,`tabTimesheet` as T,`tabTimesheet Detail` as TD where T.workflow_state='Approved' and T.name=TD.parent and T.job_order_detail=JO.name and from_date>'{0}' and end_date<'{1}' group by T.employee_company;'''.format(from_date,to_date))

	elif(filters.get('status')=="List of employees worked with, count of times, and hours worked"):
		column=[
			{'fieldname':'employee_company','label':(staff_company),'fieldtype':'Data','width':150},
			{'fieldname':'employee_name','label':('Employee Name'),'fieldtype':'Data','width':150},
			{'fieldname':'from_date','label':(fromdate),'fieldtype':'Date','width':150},
			{'fieldname':'to_date','label':(todate),'fieldtype':'Date' ,'width':150},
			{'fieldname':'total_hours_worked','label':('Total Days Worked'),'fieldtype':'Int','width':150},
			{'fieldname':'hours','label':('Total Hours Worked'),'fieldtype':'Int','width':150}
		]
		if(filters.get('companies')):
			query_data=frappe.db.sql(''' select T.employee_company,T.employee_name,min(JO.from_date),max(JO.to_date),ceil(sum((JO.to_date-JO.from_date)/(24*60*60*1000))) as total_hours_worked,sum(TD.hours) from`tabJob Order` as JO,`tabTimesheet` as T,`tabTimesheet Detail` as TD where T.workflow_state='Approved' and T.name=TD.parent and T.job_order_detail=JO.name and from_date>'{0}' and end_date<'{1}' and T.employee_company like '{2}%' group by employee_name;'''.format(from_date,to_date,company_search))
		else:
			query_data=frappe.db.sql(''' select T.employee_company,T.employee_name,min(JO.from_date),max(JO.to_date),ceil(sum((JO.to_date-JO.from_date)/(24*60*60*1000))) as total_hours_worked,sum(TD.hours) from`tabJob Order` as JO,`tabTimesheet` as T,`tabTimesheet Detail` as TD where T.workflow_state='Approved' and T.name=TD.parent and T.job_order_detail=JO.name and from_date>'{0}' and end_date<'{1}' group by employee_name;'''.format(from_date,to_date))

	else:
		column=[
			{'fieldname':'employee_company','label':(staff_company),'fieldtype':'Data','width':150},
			{'fieldname':'from_date','label':(fromdate),'fieldtype':'Date','width':150},
			{'fieldname':'to_date','label':(todate),'fieldtype':'Date' ,'width':150},
			{'fieldname':'total_hours_worked','label':('Total Cost'),'fieldtype':'Currency','width':150},
		]
		if(filters.get('companies')):
			query_data=frappe.db.sql(''' select T.employee_company,min(JO.from_date),max(JO.to_date),sum(TD.base_billing_amount) from`tabJob Order` as JO,`tabTimesheet` as T,`tabTimesheet Detail` as TD where T.workflow_state='Approved' and T.name=TD.parent and T.job_order_detail=JO.name and from_date>'{0}' and end_date<'{1}' and T.employee_company like '{2}%' group by T.employee_company; '''.format(from_date,to_date,company_search))
		else:
			query_data=frappe.db.sql(''' select T.employee_company,min(JO.from_date),max(JO.to_date),sum(TD.base_billing_amount) from`tabJob Order` as JO,`tabTimesheet` as T,`tabTimesheet Detail` as TD where T.workflow_state='Approved' and T.name=TD.parent and T.job_order_detail=JO.name and from_date>'{0}' and end_date<'{1}' group by T.employee_company; '''.format(from_date,to_date))
	return column,query_data

def hiring_data(filters,staff_company,fromdate,todate,from_date,to_date,company_search,current_company):
	column, query_data = [], []
	if(filters.get('status')=="Total work orders, Time, and Cost for a staffing agency"):
		column=[
			{'fieldname':'employee_company','label':(staff_company),'fieldtype':'Data','width':150},
			{'fieldname':'from_date','label':(fromdate),'fieldtype':'Date','width':150},
			{'fieldname':'to_date','label':(todate),'fieldtype':'Date' ,'width':150},
			{'fieldname':'name','label':('Total Number of Work Orders'),'fieldtype':'Int','width':150},
			{'fieldname':'base_billing_amount','label':('Total Hours Billed'),'fieldtype':'Currency','width':150},
			{'fieldname':'hours','label':('Total Cost Billed'),'fieldtype':'Currency','width':150}
		]
		if(filters.get('companies')):
			query_data=frappe.db.sql(''' select T.employee_company,min(JO.from_date),max(JO.to_date),count(JO.name),sum(TD.base_billing_amount),sum(TD.hours) from`tabJob Order` as JO,`tabTimesheet` as T,`tabTimesheet Detail` as TD where T.workflow_state='Approved' and T.name=TD.parent and T.job_order_detail=JO.name and JO.company='{0}' and from_date>'{1}' and end_date<'{2}' and T.employee_company like '{3}%' group by T.employee_company;'''.format(current_company,from_date,to_date,company_search))
		else:
			query_data=frappe.db.sql(''' select T.employee_company,min(JO.from_date),max(JO.to_date),count(JO.name),sum(TD.base_billing_amount),sum(TD.hours) from`tabJob Order` as JO,`tabTimesheet` as T,`tabTimesheet Detail` as TD where T.workflow_state='Approved' and T.name=TD.parent and T.job_order_detail=JO.name and JO.company='{0}' and from_date>'{1}' and end_date<'{2}' group by T.employee_company;'''.format(current_company,from_date,to_date))


	elif(filters.get('status')=="List of employees worked with, count of times, and hours worked"):
		column=[
			{'fieldname':'employee_company','label':(staff_company),'fieldtype':'Data','width':150},
			{'fieldname':'employee_name','label':('Employee Name'),'fieldtype':'Data','width':150},
			{'fieldname':'from_date','label':(fromdate),'fieldtype':'Date','width':150},
			{'fieldname':'to_date','label':(todate),'fieldtype':'Date' ,'width':150},
			{'fieldname':'total_hours_worked','label':('Total Days Worked'),'fieldtype':'Int','width':150},
			{'fieldname':'hours','label':('Total Hours Worked'),'fieldtype':'Int','width':150}
		]
		if(filters.get('companies')):
			query_data=frappe.db.sql(''' select T.employee_company,T.employee_name,min(JO.from_date),max(JO.to_date),ceil(sum((JO.to_date-JO.from_date)/(24*60*60*1000))) as total_hours_worked,sum(TD.hours) from`tabJob Order` as JO,`tabTimesheet` as T,`tabTimesheet Detail` as TD where T.workflow_state='Approved' and T.name=TD.parent and T.job_order_detail=JO.name and JO.company='{0}' and from_date>'{1}' and end_date<'{2}' and T.employee_company like '{3}%' group by employee_name;'''.format(current_company,from_date,to_date,company_search))
		else:
			query_data=frappe.db.sql(''' select T.employee_company,T.employee_name,min(JO.from_date),max(JO.to_date),ceil(sum((JO.to_date-JO.from_date)/(24*60*60*1000))) as total_hours_worked,sum(TD.hours) from`tabJob Order` as JO,`tabTimesheet` as T,`tabTimesheet Detail` as TD where T.workflow_state='Approved' and T.name=TD.parent and T.job_order_detail=JO.name and JO.company='{0}' and from_date>'{1}' and end_date<'{2}' group by employee_name;'''.format(current_company,from_date,to_date))

	else:
		column=[
			{'fieldname':'employee_company','label':(staff_company),'fieldtype':'Data','width':150},
			{'fieldname':'from_date','label':(fromdate),'fieldtype':'Date','width':150},
			{'fieldname':'to_date','label':(todate),'fieldtype':'Date' ,'width':150},
			{'fieldname':'total_hours_worked','label':('Total Cost'),'fieldtype':'Currency','width':150},
		]
		if(filters.get('companies')):
			query_data=frappe.db.sql(''' select T.employee_company,min(JO.from_date),max(JO.to_date),sum(TD.base_billing_amount) from`tabJob Order` as JO,`tabTimesheet` as T,`tabTimesheet Detail` as TD where T.workflow_state='Approved' and T.name=TD.parent and T.job_order_detail=JO.name and JO.company='{0}' and from_date>'{1}' and end_date<'{2}' and T.employee_company like '{3}%' group by T.employee_company; '''.format(current_company,from_date,to_date,company_search))
		else:
			query_data=frappe.db.sql(''' select T.employee_company,min(JO.from_date),max(JO.to_date),sum(TD.base_billing_amount) from`tabJob Order` as JO,`tabTimesheet` as T,`tabTimesheet Detail` as TD where T.workflow_state='Approved' and T.name=TD.parent and T.job_order_detail=JO.name and JO.company='{0}' and from_date>'{1}' and end_date<'{2}' group by T.employee_company; '''.format(current_company,from_date,to_date))
	return column,query_data