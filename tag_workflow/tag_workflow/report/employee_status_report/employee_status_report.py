# Copyright (c) 2013, SourceFuse and contributors
# For license information, please see license.txt

import frappe
noShow = 'No Show'
Dnr = 'DNR'

def execute(filters=None):
    columns, data = [], []
    columns = fetch_columns()
    condition=get_condition(filters)
    data = fetch_data(condition)
    return columns, data

def fetch_columns():
    columns = [
        {
            'fieldname': 'first_name',
            'fieldtype': 'Data',
            'label': 'Employee First Name',
            'width': 200
        },
        {
            'fieldname': 'last_name',
            'fieldtype': 'Data',
            'label': 'Employee Last Name',
            'width': 225
        },
		{
            'fieldname': 'employee_company',
            'fieldtype': 'Data',
            'label': 'Staffing Company',
            'width': 250
		},
        {
            'fieldname': 'job_order_detail',
            'fieldtype': 'Data',
            'label': 'Job Order',
            'width': 225,
        },
        {
            'fieldname': 'from_date',
            'fieldtype': 'Date',
            'label': 'Start Date',
            'width': 225,

        },
        {
            'fieldname': 'status',
            'fieldtype': 'Data',
            'label': 'Status',
            'width': 225
        }
    ]
    return columns

def get_condition(filters):
    try:
        condition = ''
        if(filters.get('first_name')):
            condition += " and EP.first_name like '%%{0}%%'".format(filters.get('first_name'))
        if(filters.get('last_name')):
            condition += " and EP.last_name like '%%{0}%%'".format(filters.get('last_name'))
        if(filters.get('job_order')):
            condition += " and TS.job_order_detail like '%%{0}%%'".format(filters.get('job_order'))
        if(filters.get('start_date')):
            condition += " and JO.from_date between '{0}' and '{1}'".format(filters.get('start_date'),frappe.utils.data.getdate())
        if filters.get('company'):
            condition += ' and TS.employee_company ="{0}" '.format(filters.get('company'))
        if(filters.get('status')):
            status=filters.get('status')
            if status == Dnr:
                condition += " and TS.dnr = 1"
            elif status == 'Unsatisfactory':
                condition += " and TS.non_satisfactory = 1"
            elif status == noShow:
                condition += " and TS.no_show = 1"
        return condition
    except Exception as e:
        frappe.log_error(e, 'Employee Status Report: Get Condition Error')

def fetch_data(condition):
    try:
        data1=[]
        user_comp_type=getting_user_basic_info()
        email=frappe.session.user
        if user_comp_type=='Administrator' or user_comp_type=='TAG':
            sql=f'select EP.first_name,EP.last_name,TS.employee,TS.employee_company,TS.job_order_detail,JO.from_date,max(TS.no_show) as no_show,max(TS.non_satisfactory) as non_satisfactory,max(TS.dnr) as dnr from `tabTimesheet` as TS inner join `tabEmployee` as EP on TS.employee=EP.name inner join `tabJob Order` as JO on TS.job_order_detail=JO.name where (TS.no_show=1 or TS.non_satisfactory=1 or TS.dnr=1) {condition} group by JO.name,TS.employee;'
        elif user_comp_type=='Hiring':
            sql=f'select EP.first_name,EP.last_name,TS.employee,TS.employee_company,TS.job_order_detail,JO.from_date,max(TS.no_show) as no_show,max(TS.non_satisfactory) as non_satisfactory,max(TS.dnr) as dnr from `tabTimesheet` as TS inner join `tabEmployee` as EP on TS.employee=EP.name inner join `tabJob Order` as JO on TS.job_order_detail=JO.name where TS.company in (select company from `tabEmployee` where email="{email}") and (TS.no_show=1 or TS.non_satisfactory=1 or TS.dnr=1) {condition} group by JO.name,TS.employee;'
        else:
            sql=f'select EP.first_name,EP.last_name,TS.employee,TS.employee_company,TS.job_order_detail,JO.from_date,max(TS.no_show) as no_show,max(TS.non_satisfactory) as non_satisfactory,max(TS.dnr) as dnr from `tabTimesheet` as TS inner join `tabEmployee` as EP on TS.employee=EP.name inner join `tabJob Order` as JO on TS.job_order_detail=JO.name where TS.employee_company in (select company from `tabEmployee` where email="{email}") and (TS.no_show=1 or TS.non_satisfactory=1 or TS.dnr=1) {condition} group by JO.name,TS.employee;'
        data=frappe.db.sql(sql,as_dict=1)
        if data:
            data1=employee_status(data)
            return data1
        else: 
            return []
    except Exception as e:
        frappe.log_error(e, 'Employee Status Report:Fetching data')

def getting_user_basic_info():
    try:
        if frappe.session.user!='Administrator':
            usr= frappe.session.user
            user=frappe.get_doc('User',usr)
            user_type=user.organization_type
            return user_type
        else:
            return 'Administrator'
    except Exception as e:
        frappe.log_error(e,'Employee Status Report: Getting User Type')

def employee_status(data):
    try:
        for i in range(len(data)):
            status = []
            if data[i]['no_show'] == 1 and noShow not in status:
                status.append(noShow)
            if data[i]['non_satisfactory'] == 1 and 'Non Satisfactory' not in status:
                status.append('Non Satisfactory')
            if data[i]['dnr'] == 1 and Dnr not in status:
                status.append(Dnr)
            emp_status=', '.join(status)
            data[i]['status']=emp_status
        return data
    except Exception as e:
        frappe.log_error(e,'Employee Status Report: Checking Employee Status')
    
@frappe.whitelist()
def get_staffing_company(company_type=None,current_user=None,user_company=None):
    try:
        data = []
        if current_user=='Administrator' or company_type=='TAG':
            sql = """ select distinct employee_company from `tabTimesheet` """
        elif company_type=='Hiring' or company_type=='Exclusive Hiring':
            sql = """ select distinct employee_company from `tabTimesheet` where company in (select company from `tabEmployee` where email="{0}") """.format(current_user)
        else:
            sql = """ select distinct employee_company from `tabTimesheet` where employee_company in (select company from `tabEmployee` where email="{0}") """.format(current_user)
        companies = frappe.db.sql(sql, as_dict=1)
        data = [c['employee_company'] for c in companies]
        return "\n".join(data)
    except Exception as e:
        frappe.log_error(e, 'Employee Status Report: Getting Staffing Company')
        return []
