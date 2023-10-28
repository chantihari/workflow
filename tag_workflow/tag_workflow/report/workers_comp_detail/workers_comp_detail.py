# Copyright (c) 2013, SourceFuse and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    columns, data = [], []
    start_date=filters.get('start_date')
    end_date=filters.get('end_date')
    company=filters.get('company')
    columns = fetch_columns()
    if(start_date and end_date and company):
        condition=get_condition(filters)
        data = fetch_data(start_date,end_date,company,condition)
    return columns, data

def fetch_columns():
    columns = [
        {
            'fieldname': 'emp_name',
            'fieldtype': 'Data',
            'label': 'Employee',
            'width': 150
        },
        {
            'fieldname': 'ssn',
            'fieldtype': 'Data',
            'label': 'SSN',
            'width': 150
        },
        {
            'fieldname': 'order_id',
            'fieldtype': 'link',
            'label': 'Order#',
			'option':'Job Order',
            'width': 150
        },
        {
            'fieldname': 'comp_code',
            'fieldtype': 'Data',
            'label': 'Comp Code',
            'width': 150
        },
        {
            'fieldname': 'rate',
            'fieldtype': 'float',
            'label': 'Rate',
            'width': 100,
            'precision':5
        },
        {
            'fieldname': 'reg_hours',
            'fieldtype': 'Float',
            'label': 'Reg Hrs',
            'width': 150,
            'precision':2
        },
        {
            'fieldname': 'ot_hours',
            'fieldtype': 'Float',
            'label': 'OT Hrs',
            'width': 100,
            'precision':2

        },
        {
            'fieldname': 'gross_wages',
            'fieldtype': 'Currency',
            'label': 'Gross Wages',
            'width': 150
        },
        {
            'fieldname': 'comp_wages',
            'fieldtype': 'Currency',
            'label': 'Comp Wages',
            'width': 150
        },
        {
            'fieldname': 'reg_wages',
            'fieldtype': 'Currency',
            'label': 'Reg Wages',
            'width': 150
        },
        {
            'fieldname': 'ot_wages',
            'fieldtype': 'Currency',
            'label': 'OT Wages',
            'width': 150
        },
        {
            'fieldname': 'comp_pay',
            'fieldtype': 'Currency',
            'label': 'Comp Pay',
            'width': 150
        }
    ]

    return columns
def get_condition(filters):
    try:
        condition = ''
        if(filters.get('state')):
            condition += " and JS.state = '{0}'".format(filters.get('state'))
        if(filters.get('comp_code')):
            condition += " and staff_class_code like '{0}%'".format(filters.get('comp_code'))
        return condition
    
    except Exception as e:
        frappe.msgprint(e, 'Employment History: Get Condition Error')

def fetch_data(start_date,end_date,company,condition):
    try:
        if(start_date>end_date):
            frappe.msgprint("Start Date Can't be Future Date For End Date")
        else:
            mandatory_condition=f' and TS.date_of_timesheet between "{start_date}" and "{end_date}" and TS.employee_company="{company}"'
            if condition:
                mandatory_condition+=condition
            data1=frappe.db.sql('''select TS.employee_name as emp_name,EM.ssn as ssn,TS.job_order_detail as order_id,TS.employee,sum(timesheet_hours-todays_overtime_hours) as reg_hours,sum(todays_overtime_hours)as ot_hours,sum(timesheet_payable_amount-timesheet_billable_overtime_amount_staffing-timesheet_unbillable_overtime_amount) as reg_wages,sum(timesheet_billable_overtime_amount_staffing) as ot_wages,CO.staff_class_code as comp_code,CO.staff_class_code_rate as rate from `tabTimesheet` as TS inner join `tabJob Order` as JO on JO.name=TS.job_order_detail inner join `tabEmployee` as EM on EM.name=TS.employee inner join `tabClaim Order` as CO on CO.job_order=JO.name inner join `tabJob Site` as JS on JS.name=JO.job_site where TS.workflow_state='Approved' and JO.resumes_required=0 and CO.staff_class_code is not null %s group by employee,JO.name order by TS.name desc;''' % mandatory_condition,as_dict=1)
            data2=frappe.db.sql('''select TS.employee_name as emp_name,EM.ssn as ssn,TS.job_order_detail as order_id,TS.employee,sum(timesheet_hours-todays_overtime_hours) as reg_hours,sum(todays_overtime_hours)as ot_hours,sum(timesheet_payable_amount-timesheet_billable_overtime_amount_staffing-timesheet_unbillable_overtime_amount) as reg_wages,sum(timesheet_billable_overtime_amount_staffing) as ot_wages,AE.staff_class_code as comp_code,AE.staff_class_code_rate as rate from `tabTimesheet` as TS inner join `tabJob Order` as JO on JO.name=TS.job_order_detail inner join `tabEmployee` as EM on EM.name=TS.employee inner join `tabAssign Employee` as AE on AE.job_order=JO.name inner join `tabJob Site` as JS on JS.name=JO.job_site where TS.workflow_state='Approved' and JO.resumes_required=1 and AE.staff_class_code is not null %s group by employee,JO.name order by TS.name desc;''' % mandatory_condition,as_dict=1)
            data1.extend(data2)
            for i in range(len(data1)):
                if(data1[i]['ssn']!=None and data1[i]['ssn']!=''):
                    doc=frappe.get_doc('Employee',data1[i]['employee'])
                    ssn_decrypt = doc.get_password('ssn')
                    data1[i]['ssn']=ssn_decrypt
                data1[i]['gross_wages']=data1[i]['reg_wages']+data1[i]['ot_wages']
                data1[i]['comp_wages']=data1[i]['reg_wages']+(data1[i]['ot_wages']/1.5)
                data1[i]['comp_pay']=data1[i]['comp_wages']*data1[i]['rate']
            return data1
    except Exception as e:
        frappe.msgprint(e, 'Employment History: Get Condition Error')