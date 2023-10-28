# Copyright (c) 2013, SourceFuse and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters = None):
    columns, data = [], []
    columns = fetch_columns()
    data = fetch_data(filters)
    if filters.get('total_hours'):
        data = [i for i in data if 'total_hours' in i and filters.get('total_hours') in str(i['total_hours'])]
    if filters.get('emp_status'):
        data = [i for i in data if 'emp_status' in i and filters.get('emp_status') in i['emp_status']]
        
    return columns, data

def fetch_columns():
    columns = [
        {
            'fieldname': 'emp_id',
            'fieldtype': 'Data',
            'label': _('Employee Code'),
            'width': 150
        },
        {
            'fieldname': 'first_name',
            'fieldtype': 'Data',
            'label': _('First Name'),
            'width': 150
        },
        {
            'fieldname': 'last_name',
            'fieldtype': 'Data',
            'label': 'Last Name',
            'width': 150
        },
        {
            'fieldname': 'company',
            'fieldtype': 'Data',
            'label': _('Staffing Company'),
            'width': 200
        },
        {
            'fieldname': 'job_order',
            'fieldtype': 'Data',
            'label': _('Job Order'),
            'width': 100
        },
        {
            'fieldname': 'job_title',
            'fieldtype': 'Data',
            'label': _('Job Title'),
            'width': 150
        },
        {
            'fieldname': 'start_date',
            'fieldtype': 'Date',
            'label': _('Start Date'),
            'width': 100
        },
        {
            'fieldname': 'total_hours',
            'fieldtype': 'Float',
            'label': _('Total Hours Worked'),
            'width': 150
        },
        {
            'fieldname': 'emp_status',
            'fieldtype': 'Data',
            'label': _('Status'),
            'width': 250
        }
    ]

    return columns

def get_condition(filters):
    try:
        condition = ''

        if(filters.get('emp_id')):
            condition += " and AED.employee = '{0}'".format(filters.get('emp_id'))

        if(filters.get('emp_name')):
            condition += " and AED.employee_name = '{0}'".format(filters.get('emp_name'))

        if(filters.get('company')):
            condition += " and AE.company = '{0}'".format(filters.get('company'))

        if(filters.get('job_order')):
            condition += " and AE.job_order = '{0}'".format(filters.get('job_order'))

        if(filters.get('job_title')):
            condition += " and AE.job_category = '{0}'".format(filters.get('job_title'))

        if(filters.get('start_date')):
            condition += " and JO.from_date = '{0}'".format(filters.get('start_date'))

        return condition
    
    except Exception as e:
        frappe.msgprint(e, 'Employment History: Get Condition Error')

def fetch_data(filters=None):
    try:
        data = fetch_data_contd(filters)
        for i in data:
            sql = '''SELECT ROUND(total_hours, 3), no_show, non_satisfactory, dnr FROM tabTimesheet WHERE workflow_state = 'Approved' AND employee = "{0}" AND job_order_detail = "{1}"'''.format(i['emp_id'], i['job_order'])
            timesheet_data = frappe.db.sql(sql, as_list = True)
            total_hours = 0
            if len(timesheet_data) > 0:
                for j in timesheet_data:
                    total_hours += j[0]
                i['total_hours'] = total_hours
                i['emp_status'] = get_status(timesheet_data)
                
        return data
    
    except Exception as e:
        frappe.msgprint(e, 'Employment History: Fetch Data Error')

@frappe.whitelist()
def fetch_data_contd(filters=None):
    try:
        if filters:
            condition = get_condition(filters)
        else:
            condition = ''
        user_data = frappe.db.get_value('User', frappe.session.user, ['organization_type', 'company'])
        if user_data[0] == 'Hiring' or user_data[0] == 'Exclusive Hiring':
            sql = f'''
                SELECT AED.employee AS emp_id, EMP.first_name AS first_name, EMP.last_name AS last_name, AED.employee_name as emp_name,
                AE.company AS company, AE.job_order AS job_order, AED.job_category AS job_title, JO.from_date AS start_date
                FROM `tabAssign Employee` AS AE,`tabAssign Employee Details` AS AED, tabEmployee AS EMP, `tabJob Order` AS JO
                WHERE AED.approved = CASE WHEN JO.resumes_required=1 THEN 1 ELSE 0 END AND AE.name = AED.parent AND AE.hiring_organization = "{user_data[1]}"
                AND AE.tag_status = "Approved" AND EMP.name = AED.employee AND JO.name = AE.job_order {condition}
                ORDER BY AE.job_order, AE.company, EMP.first_name
            '''
        elif user_data[0] == 'TAG' or frappe.session.user == 'Administrator':
            sql = f'''
                SELECT AED.employee AS emp_id, EMP.first_name AS first_name, EMP.last_name AS last_name, AED.employee_name as emp_name,
                AE.company AS company, AE.job_order AS job_order, AED.job_category AS job_title, JO.from_date AS start_date
                FROM `tabAssign Employee` AS AE,`tabAssign Employee Details` AS AED, tabEmployee AS EMP, `tabJob Order` AS JO
                WHERE AED.approved = CASE WHEN JO.resumes_required=1 THEN 1 ELSE 0 END AND AE.name = AED.parent AND AE.tag_status = "Approved"
                AND EMP.name = AED.employee AND JO.name = AE.job_order {condition} ORDER BY AE.job_order, AE.company, EMP.first_name
            '''
        return frappe.db.sql(sql, as_dict=True)
    except Exception as e:
        frappe.msgprint(e, 'Employment History: Fetch Data Contd Error')

def get_status(timesheet_data):
    status = []
    for i in timesheet_data:
        if i[1] == 1 and 'No Show' not in status:
            status.append('No Show')
        if i[2] == 1 and 'Non Satisfactory' not in status:
            status.append('Non Satisfactory')
        if i[3] == 1 and 'DNR' not in status:
            status.append('DNR')
    return ', '.join(status)
