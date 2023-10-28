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
            'fieldname': 'comp_code',
            'fieldtype': 'Data',
            'label': 'Code',
            'width': 150
        },
        {
            'fieldname': 'emp_count',
            'fieldtype': 'Int',
            'label': 'Emp Count',
            'width': 150
        },
		{
            'fieldname': 'rate',
            'fieldtype': 'float',
            'label': 'Rate',
            'width': 100,
            'preision':5
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
            'fieldname': 'other_wages',
            'fieldtype': 'Currency',
            'label': 'Other Wages',
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
        return condition

    except Exception as e:
        frappe.msgprint(e, 'Employment Comp Summary: Get Condition Error')

def fetch_data(start_date,end_date,company,condition):
    try:
        if(start_date>end_date):
            frappe.msgprint("Start Date Can't be Future Date For End Date")
        else:
            mandatory_condition=f' and TS.date_of_timesheet between "{start_date}" and "{end_date}" and TS.employee_company="{company}"'
            if condition:
                mandatory_condition+=condition
            data1=frappe.db.sql('''select count(distinct(TS.employee)) as emp_count,sum(timesheet_hours-todays_overtime_hours) as reg_hours,sum(todays_overtime_hours)as ot_hours,sum(timesheet_payable_amount-timesheet_billable_overtime_amount_staffing-timesheet_unbillable_overtime_amount) as reg_wages,sum(timesheet_billable_overtime_amount_staffing) as ot_wages,CO.staff_class_code as comp_code,CO.staff_class_code_rate as rate,sum(TD.tip) as other_wages,JS.state from `tabTimesheet` as TS inner join `tabJob Order` as JO on JO.name=TS.job_order_detail inner join `tabEmployee` as EM on EM.name=TS.employee inner join `tabClaim Order` as CO on CO.job_order=JO.name inner join `tabJob Site` as JS on JS.name=JO.job_site inner join `tabTimesheet Detail` as TD on TS.name=TD.parent where TS.workflow_state='Approved' and JO.resumes_required=0 and CO.staff_class_code is not null %s group by JS.state,comp_code order by TS.name desc;''' % mandatory_condition,as_dict=1)
            data2=frappe.db.sql('''select count(distinct(TS.employee)) as emp_count,sum(timesheet_hours-todays_overtime_hours) as reg_hours,sum(todays_overtime_hours)as ot_hours,sum(timesheet_payable_amount-timesheet_billable_overtime_amount_staffing-timesheet_unbillable_overtime_amount) as reg_wages,sum(timesheet_billable_overtime_amount_staffing) as ot_wages,AE.staff_class_code as comp_code,AE.staff_class_code_rate as rate,sum(TD.tip) as other_wages,JS.state from `tabTimesheet` as TS inner join `tabJob Order` as JO on JO.name=TS.job_order_detail inner join `tabEmployee` as EM on EM.name=TS.employee inner join `tabAssign Employee` as AE on AE.job_order=JO.name inner join `tabJob Site` as JS on JS.name=JO.job_site inner join `tabTimesheet Detail` as TD on TS.name=TD.parent where TS.workflow_state='Approved' and JO.resumes_required=1 and AE.staff_class_code is not null %s group by JS.state,comp_code order by TS.name desc;''' % mandatory_condition,as_dict=1)
            data1=check_repeated_emps(data1,mandatory_condition)
            data1=update_wages(data1)
            data2=update_wages(data2)
            data1=update_data(data1,data2)
            

            return data1
    except Exception as e:
        frappe.msgprint(e, 'Employment Comp Summary:Passing data')
def update_wages(data):
    try:
        for i in range(len(data)):
            data[i]['gross_wages']=data[i]['reg_wages']+data[i]['ot_wages']
            data[i]['comp_wages']=data[i]['reg_wages']+(data[i]['ot_wages']/1.5)
            data[i]['comp_pay']=data[i]['comp_wages']*data[i]['rate']
        return data
    except Exception as e:
        frappe.msgprint(e, 'Employment Comp Summary:Update wages')
def check_repeated_emps(data,mandatory_condition):
    try:
        for i in range(len(data)):
            new_condition=f"{mandatory_condition} and AE.staff_class_code='{data[i]['comp_code']}' and JS.state='{data[i]['state']}'"
            new_assign_emp_cond=f"{mandatory_condition} and CO.staff_class_code='{data[i]['comp_code']}' and JS.state='{data[i]['state']}'"
            d1=f'select distinct(TS.employee) from `tabTimesheet` as TS inner join `tabJob Order` as JO on JO.name=TS.job_order_detail inner join `tabEmployee` as EM on EM.name=TS.employee inner join `tabAssign Employee` as AE on AE.job_order=JO.name inner join `tabJob Site` as JS on JS.name=JO.job_site where TS.workflow_state="Approved" and JO.resumes_required=1 and AE.staff_class_code is not null {new_condition} and TS.employee in (select TS.employee from `tabTimesheet` as TS inner join `tabJob Order` as JO on JO.name=TS.job_order_detail inner join `tabEmployee` as EM on EM.name=TS.employee inner join `tabClaim Order` as CO on CO.job_order=JO.name inner join `tabJob Site` as JS on JS.name=JO.job_site where TS.workflow_state="Approved" and JO.resumes_required=0 and CO.staff_class_code is not null {new_assign_emp_cond}) order by TS.name desc;'
            data2=frappe.db.sql(d1,as_list=1)
            if(len(data2)>0):
                data[i]['emp_count']-=len(data2)
        return data
    except Exception as e:
        frappe.msgprint(e, 'Employment Comp Summary:Checking repeated emps')
def update_data(data1,data2):
    try:
        for i in range(len(data1)):
            for j in range(len(data2)):
                if(data1[i]['comp_code']==data2[j]['comp_code'] and data1[i]['state']==data2[j]['state']):
                    data1[i]['emp_count']+=data2[j]['emp_count']
                    data1[i]['reg_hours']+=data2[j]['reg_hours']
                    data1[i]['ot_hours']+=data2[j]['ot_hours']
                    data1[i]['reg_wages']+=data2[j]['reg_wages']
                    data1[i]['ot_wages']+=data2[j]['ot_wages']
                    data1[i]['other_wages']+=data2[j]['other_wages']
                else:
                    data1.append(data2[j])
        return data1
    except Exception as e:
        frappe.msgprint(e, 'Employment Comp Summary:Updating data')