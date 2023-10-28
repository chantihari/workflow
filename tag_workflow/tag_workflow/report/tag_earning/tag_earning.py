# Copyright (c) 2013, SourceFuse and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
	columns, data = [], []
	if not filters:
		filters={}
	columns=[
		{"fieldname":"company","label":"Staffing Company","fieldtype": "Link",'options':'Company',"width":200,},
		{"fieldname":"name","label":"Invoice ID","fieldtype": "Link",'options':'Sales Invoice',"width":200,},
		{"fieldname":"first_creation","label":"Start Date","fieldtype": "Date","width":200},
        {'fieldname':"last_creation",'label':"End Date",'fieldtype':'Date','width':200},
		{"fieldname":"total_received","label":"Gross Total Received","fieldtype": "Currency","width":200},
		{'fieldname':"total_pending",'label':"Gross Total Pending",'fieldtype':'Currency','width':200},
		{'fieldname':"approx_due",'label':"Approx. Total  due to TAG",'fieldtype':'Currency','width':200},
		{'fieldname':"total_due",'label':"Total due to TAG",'fieldtype':'Currency','width':200},
		{'fieldname':"is_paid",'label':"Paid",'fieldtype':'Check','width':200},
		{'fieldname':'button','label':'Link','fieldtype':'Button'}
	]

	row  = list()
	condition = ""
	start=filters.get('start_date')
	end=filters.get('end_date')
	condition += f"  and `tabSales Invoice`.creation >= '{start}' and `tabSales Invoice`.creation <= '{end}' "

	if filters.get("company"):
		staff_comp = filters.get("company")
		condition+=f"and `tabSales Invoice`.company='{staff_comp}'"

	try:
		data = frappe.db.sql('''select `tabSales Invoice`.name,customer,base_paid_amount,(base_grand_total-base_paid_amount) as due_amount,(base_paid_amount+(base_grand_total-base_paid_amount)) as due_amount,(base_paid_amount+(base_grand_total-base_paid_amount))*((`tabCompany`.tag_charges)/100) as approx_due,base_paid_amount*((`tabCompany`.tag_charges)/100) as total_due,is_pos from `tabSales Invoice`,`tabCompany` where `tabSales Invoice`.customer=`tabCompany`.name and `tabSales Invoice`.company='tag'  %s ''' % condition, as_dict=True)     
		for d in data:
			time=frappe.db.sql(f''' select min(creation) as start_time,max(creation) as last_time from `tabSales Invoice` where company="{d.customer}" group by company  ''',as_dict=True)
			row.append({"company":d.customer , "name": d.name, "first_creation": time[0].start_time, "last_creation": time[0].last_time, "total_received":d.base_paid_amount, "total_pending":d.due_amount, "approx_due": d.approx_due, "total_due": d.total_due, "is_paid":d.is_pos,"button":"<a href='/app/query-report/Tag%20Invoice?company={d.company}'>View Company Report</a>" })
		return columns,row
	except Exception as e:
		print(e)

