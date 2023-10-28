# Copyright (c) 2013, SourceFuse and contributors
# For license information, please see license.txt
import frappe
from pypika.terms import EdgeT


def execute(filters=None):
    user = frappe.session.user
	
    columns = [
        {"fieldname": "invoice", "label": "Invoice Name","fieldtype": "Link", 'options': 'Sales Invoice', "width": 200,},
        {"fieldname": "company", "label": "Staffing Company","fieldtype": "Data", "width": 150, },
        {"fieldname": "hiring_company", "label": "hiring Company","fieldtype": "Data", "width": 150},
        {'fieldname': "job_order", 'label': ('Work Order'), 'fieldtype': 'Link', 'options': 'Job Order', 'width': 200},
        {"fieldname": "select_job", "label": "Job Title","fieldtype": "Link", 'options': 'Designation', "width": 200},
        {'fieldname': "start_date", 'label': ('Start Date'), 'fieldtype': 'Date', 'width': 200},
        {'fieldname': "total_billing_hours", 'label': ('Total Hours'), 'fieldtype': 'Int', 'width': 100},
        {'fieldname': "rate", 'label': 'Rate', 'fieldtype': 'Currency', 'width': 100},
        {'fieldname': "total_invoiced", 'label': 'Total Invoiced','fieldtype': 'Currency', 'width': 150},
        {"fieldname": "status", "label": "Status","fieldtype": "Select", "width": 150},
        {'fieldname': "total_to_tag", 'label': 'Total To Tag','fieldtype': 'Currency', 'width': 150},
    ]
    row  = list()
    current_user_type = frappe.db.sql(''' select tag_user_type,company from `tabUser` where name = '{}' '''.format(user), as_dict=1)

    condition = ""
    status = " in ('Ongoing','Upcoming','Completed')"

    if current_user_type[0]['tag_user_type'] == 'TAG Admin':
        if filters.get("company"):
            staff_comp = filters.get("company")
            condition += f" and company = '{staff_comp}'"
    
    elif current_user_type[0]['tag_user_type'] == 'Staffing Admin' or current_user_type[0]['tag_user_type'] =='Staffing User' :
        condition += f" and company = '{current_user_type[0]['company']}'"


    months = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,"July": 7, "August": 8, "September": 10, "October": 10, "November": 11, "December": 12}

    date = filters.get("month")
    year = filters.get('from_fiscal_year').strip()
    get_month_digit = months[date]

    current_month_str = str(year)+'-'+str(get_month_digit)+'-'+'01' 
    current_date = frappe.utils.getdate(current_month_str)
    previous_month = frappe.utils.add_months(current_date, months=-1)
    first_day = frappe.utils.get_first_day(previous_month)
    last_day = frappe.utils.get_last_day(first_day)
    time_format = " 12:00:00"
    condition += f"  and creation between '{first_day}{time_format}' and '{last_day}{time_format}'"

        
    if filters.get("status"):
        value = filters.get("status").strip()
        status = f" = '{value}'"
  
    try:
        data = frappe.db.sql('''select name,company,job_order,total_billing_hours,total_billing_amount from `tabSales Invoice` where docstatus = 1 and job_order != ""  %s ''' % condition, as_dict=True)

        for d in data:
            joborder = frappe.db.sql(f'''select company,select_job,from_date,rate,order_status from `tabJob Order` where name = "{d.job_order}" and order_status{status}''', as_dict=True)
            tag_charge = frappe.db.get_value("Company", {"name": d.company}, ["tag_charges"])
            row.append({"invoice": d.name, "company": d.company, "hiring_company": joborder[0].company, "job_order": d.job_order, "select_job": joborder[0].select_job, "start_date": joborder[0].from_date, "total_billing_hours": float(d.total_billing_hours), "rate": joborder[0].rate, "total_invoiced": d.total_billing_amount, "status": joborder[0].order_status, "total_to_tag": (d.total_billing_amount*float(tag_charge/100))})
        return columns,row
    except Exception as e:
        print(e)
        return columns,row



