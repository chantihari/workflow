# Copyright (c) 2013, SourceFuse and contributors
# For license information, please see license.txt


import frappe

def execute(filters=None):
	columns, data = [], []
	if not filters:
		filters={}
	columns=[
        {'fieldname':'name','label':('Work Order ID'),'fieldtype':'Link','options':'Job Order','width':150},
        {'fieldname':'company','label':('Company Name'),'fieldtype':'Data','width':150},
        {'fieldname':'select_job','label':('Job Title'),'fieldtype':'Data' ,'width':150},
		{'fieldname':'job_start_time','label':('Start Time'),'fieldtype':'Time' ,'width':100},
        {'fieldname':'per_hour','label':('Wage/Hour'),'fieldtype':'Currency','width':150},
        {'fieldname':'category','label':('Job Category'),'fieldtype':'Data','width':150},
        {'fieldname':'from_date','label':('Start Date'),'fieldtype':'Data','width':150},
        {'fieldname':'job_site','label':('Job Site'),'fieldtype':'Data' ,'width':150},
        {'fieldname':'no_of_workers','label':('No. of Workers'),'fieldtype':'Int','width':150}
    ]

	cond = get_cond(filters)
	data=frappe.db.sql(f'''
		SELECT jo.name, jo.company, mjt.select_job, TIME_FORMAT(mjt.job_start_time, "%H:%i") as job_start_time, mjt.rate as per_hour,
		mjt.category, jo.from_date, jo.job_site, mjt.no_of_workers
		FROM `tabMultiple Job Titles` mjt, `tabJob Order` jo
		WHERE jo.name = mjt.parent {cond}
		ORDER BY jo.name,
		SUBSTRING_INDEX(mjt.select_job, '-', 1),
        CAST(SUBSTRING_INDEX(mjt.select_job, '-', -1) AS UNSIGNED),
		mjt.job_start_time;
	''')
	return columns, data

def get_cond(filters):
	ongoing_order=filters.get('ongoing')
	upcoming_order=filters.get('future')
	closed_order=filters.get('closed')

	if (ongoing_order==None and upcoming_order==None and closed_order==None) or (ongoing_order==1 and upcoming_order==1 and closed_order==1):
		return ''
	elif ongoing_order==1 and upcoming_order==1:
		return "AND jo.order_status!='Completed'"
	elif closed_order==1 and upcoming_order==1:
		return "AND jo.order_status!='Ongoing'"
	elif ongoing_order==1 and closed_order==1:
		return "AND jo.order_status!='Upcoming'"
	elif ongoing_order==1:
		return "AND jo.order_status='Ongoing'"
	elif upcoming_order==1:
		return "AND jo.order_status='Upcoming'"
	elif closed_order==1:
		return "AND jo.order_status='Completed'"
