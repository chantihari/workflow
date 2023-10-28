# Copyright (c) 2013, SourceFuse and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
	if not filters:
		filters={}
	columns, data = [], []

	columns=[
		{'fieldname':'invoice_name','label':"Sales Invoice",'fieldtype':'Link','options':"Sales Invoice","width":200},
		{'fieldname':'name','label':"Job Order Id",'fieldtype':'Link','options':'Job Order',"width":200},
		{'fieldname':'from_date','label':'From Date','fieldtype':'Date','width':150},
		{'fieldname':'hiring_company','label':'Hiring Company','fieldtype':'Data' ,'width':150},
		{'fieldname':'staffing_company','label':('Staffing Company'),'fieldtype':'Data','width':200},
		{'fieldname':'total_hours','label':('Total Hours'),'fieldtype':'Float','width':150},
		{'fieldname':'total_rate','label':('Total Rate'),'fieldtype':'Currency','width':150},
		{'fieldname':'over_time_hours','label':('Over Time Hours'),'fieldtype':'Float','width':150},
		{'fieldname':'over_time_rate','label':('Over Time Rate'),'fieldtype':'Currency','width':150},
		{'fieldname':'total','label':('Total'),'fieldtype':'Currency','width':150},
	]

	data=frappe.db.sql('''  select  SI.name as invoice_name , JO.name as name,JO.from_date as from_date,JO.company as hiring_company,T.employee_company as staffing_company,sum(total_hours) as total_hours,(sum(total_hours)*JO.per_hour)+JO.flat_rate as total_rate,sum(TD.extra_hours) as over_time_hours,(sum(TD.extra_hours)*1.5*JO.per_hour) as over_time_rate,((sum(total_hours)*JO.per_hour)+JO.flat_rate)+((sum(TD.extra_hours)*1.5*JO.per_hour)) as total from `tabJob Order` as JO,`tabTimesheet` as T,`tabTimesheet Detail` as TD ,`tabSales Invoice` as SI where SI.job_order = JO.name and JO.name=T.job_order_detail and TD.parent=T.name group by JO.name, T.employee_company;''')



	return columns, data
