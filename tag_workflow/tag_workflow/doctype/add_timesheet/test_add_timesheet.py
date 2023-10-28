# Copyright (c) 2022, SourceFuse and Contributors
# See license.txt

import frappe
import unittest
import json
import datetime
from tag_workflow.controllers.master_controller import check_employee
from tag_workflow.tag_data import claim_order_insert
from frappe.utils.data import getdate
from tag_workflow.tag_data import staff_email_notification,receive_hire_notification
from tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet import update_timesheet,checkreplaced_emp,update_billing_calculation,edit_update_record,update_list_page_calculation,job_order_name,update_todays_timesheet
Hire_Company = "Genpact Hire Test5"
Staff_Comp="Genpact Staff Test5"
Hire_Admin="genpact_test_hiring5@yopail.com"
Staff_Admin="genpact_test_staffing5@yopmail.com"
inds_type='Administrative/Clerical'
job_title="Auditor"
job_site="New York, NY 10016, USA"
state='New York'
city='New York'
zip='10016'
jobOrder='Job Order'
files="/files/testing doc.pdf"
asnEmp='Assign Employee'
jbSite='Job Site'
usrPerm='User Permission'
from tag_workflow.utils.test_timesheet import TestTimesheet
doc=TestTimesheet()
doc.create_basic_data()
class TestAddTimesheet(unittest.TestCase):
    ## unit test 1 -- update_timesheet   
    def test_update_timesheet(self):
        job_order=self.create_job_order(Hire_Company,getdate())
        self.assign_emp(job_order,Hire_Company)
        self.create_timesheet(job_order,0) 
        self.delete_data(job_order)      


    ## unit test 2 -- checkreplaced_emp
    def test_checkreplaced_emp(self):
        job_order=self.create_job_order(Hire_Company,getdate()+datetime.timedelta(days=1))
        self.assign_emp(job_order,Hire_Company)
        frappe.set_user(Hire_Admin)
        employee_records=frappe.db.get_value(asnEmp,{'job_order':job_order,'company':Staff_Comp},'name')
        employee_records=frappe.get_doc(asnEmp,employee_records)
        emp=employee_records.employee_details[0].employee
        check_replace=checkreplaced_emp(emp,job_order)
        self.assertEqual(check_replace,0)
        self.delete_data(job_order)      

    ## unit test 3 -- update_billing_hours
    def test_update_billing_hours(self): 
        job_order=self.create_job_order(Hire_Company,getdate()+datetime.timedelta(days=2))
        self.assign_emp(job_order,Hire_Company)
        self.create_timesheet(job_order,0)
        doc=frappe.db.sql('select TS.name,TS.job_order_detail,TS.date_of_timesheet,TS.employee,TD.flat_rate,TD.billing_rate from `tabTimesheet` as TS inner Join `tabTimesheet Detail` as TD on TS.name=TD.parent where company="{0}" and employee_company="{1}" and job_order_detail="{2}"'.format(Hire_Company,Staff_Comp,job_order),as_dict=1)
        response=update_billing_calculation(doc[0].name,doc[0].job_order_detail, str(doc[0].date_of_timesheet), doc[0].employee,'5',doc[0].flat_rate,doc[0].billing_rate)
        self.assertEqual(len(response),3)
        self.delete_data(job_order)

    ## unit test 4 -- edit_update_record
    def test_edit_update_record(self):
        job_order=self.create_job_order(Hire_Company,getdate()+datetime.timedelta(days=3))
        self.assign_emp(job_order,Hire_Company)
        self.create_timesheet(job_order,0)
        doc=frappe.db.sql('select name from `tabTimesheet` where job_order_detail="{0}"'.format(job_order),as_dict=1)
        if doc:
            edit_update_record(doc[0].name)
        self.delete_data(job_order)

    ## unit test 5 -- update_list_page_calculation
    def test_update_list_page_calculation(self):
        job_order=self.create_job_order(Hire_Company,getdate()+datetime.timedelta(days=4))
        self.assign_emp(job_order,Hire_Company)
        employee_records=frappe.db.get_value(asnEmp,{'job_order':job_order,'company':Staff_Comp},'name')
        employee_records=frappe.get_doc(asnEmp,employee_records)
        emp=employee_records.employee_details[0].employee
        job_ord=frappe.get_doc(jobOrder,job_order)
        result=update_list_page_calculation(None,job_ord.name,str(job_ord.from_date),emp,'6',0,5,'00:00:00')
        self.assertEqual(len(result),3)
        self.delete_data(job_order)
    ## unit test 6 -- update_todays_timesheet
    def test_update_todays_timesheet(self):
        job_order=self.create_job_order(Hire_Company,getdate()+datetime.timedelta(days=5))
        self.assign_emp(job_order,Hire_Company)
        self.create_timesheet(job_order,1)
        doc=frappe.db.sql('select TS.name,TS.job_order_detail,TS.date_of_timesheet,TS.employee,TS.workflow_state from `tabTimesheet` as TS where company="{0}" and employee_company="{1}" and job_order_detail="{2}"'.format(Hire_Company,Staff_Comp,job_order),as_dict=1)
        result=update_todays_timesheet(doc[0].job_order_detail, str(doc[0].date_of_timesheet), doc[0].employee,doc[0].name,Hire_Company)
        self.assertEqual(result,1)
        self.delete_data(job_order)
   
    def create_job_order(self,hire_company,job_date):
        frappe.set_user('Administrator')
        job_order = frappe.new_doc(jobOrder)
        job_order.company = hire_company
        job_order.select_job = job_title
        job_order.from_date = job_date
        job_order.job_start_time = '09:59:00.000000'
        job_order.availability ='Everyday'
        job_order.rate = 20
        job_order.to_date = job_date
        job_order.category = inds_type
        job_order.job_site = job_site
        job_order.no_of_workers = 4
        job_order.e_signature_full_name = 'kanchan'
        job_order.agree_to_contract = 1
        job_order.estimated_hours_per_day=4
        job_order.staff_company=Staff_Comp
        job_order.per_hour=10
        job_order.flat_rate=10
        job_order.save() 
        staff_email_notification(hire_company,job_order.name,job_title,Staff_Comp)
        return job_order.name
    def assign_emp(self,job_order,hire_company):
        job_order=frappe.get_doc(jobOrder,job_order)
        claim_order_insert('10', job_order.company,job_order.name,job_order.no_of_workers,job_order.e_signature_full_name,job_order.staff_company)
        self.assign_employee(job_order,hire_company)
    def assign_employee(self,job_order,hire_company):
        self.create_temp_employee()
        employee_records=frappe.db.get_value(asnEmp,{'job_order':job_order},'job_order')
        emp=frappe.db.sql('select name,employee_name from `tabEmployee` where company="{0}" and user_id is null'.format(Staff_Comp),as_dict=1)
        if not employee_records:
            a_emp = frappe.new_doc("Assign Employee")
            a_emp.job_order = job_order.name
            a_emp.no_of_employee_required = job_order.no_of_workers
            a_emp.job_category = job_order.select_job
            a_emp.claims_approved = job_order.no_of_workers
            a_emp.hiring_organization = hire_company
            a_emp.company = Staff_Comp
            a_emp.job_location = job_order.job_site
            a_emp.e_signature_full_name = job_order.e_signature_full_name
            a_emp.append("employee_details",{
                "company": Staff_Comp,
                "employee": emp[1].name,
                "employee_name": emp[1].employee_name,
                "pay_rate": 5
            })
            a_emp.save()
            assi_emp=frappe.get_doc(asnEmp,a_emp.name)
            frappe.set_user(Staff_Admin)
            receive_hire_notification(user=Staff_Admin, company_type="Staffing", hiring_org=hire_company, job_order=job_order.name, staffing_org=Staff_Comp, emp_detail=assi_emp.employee_details, doc_name=assi_emp.name,worker_fill=1)
            frappe.db.set_value(jobOrder, job_order.name, "worker_filled", 1)
    def create_temp_employee(self):
        records_file = open('assets/tag_workflow/js/test_record/test_temp_emps.json')
        test_records = json.load(records_file)
        for employee in test_records:
            employee_records=frappe.db.get_value('Employee',{'email':employee['email'],'company':Staff_Comp},'email')
            if not employee_records:
                emp = frappe.new_doc("Employee")
                emp.first_name = employee["first_name"]
                emp.last_name = employee["last_name"]
                emp.email = employee["email"]
                emp.status = employee["status"]
                emp.company = Staff_Comp
                emp.owner=Staff_Admin
                emp.date_of_birth = employee["date_of_birth"]
                emp.save()
    def create_timesheet(self,job_order,save,hire_admin=Hire_Admin):
        job_order=frappe.get_doc(jobOrder,job_order)
        frappe.set_user(hire_admin)
        employee_records=frappe.db.get_value(asnEmp,{'job_order':job_order.name,'company':Staff_Comp},'name')
        employee_records=frappe.get_doc(asnEmp,employee_records)
        emp=employee_records.employee_details[0].employee
        emp_name=employee_records.employee_details[0].employee_name
        items=[{"docstatus": 0, "doctype": "Timesheet Item", "name": "new-timesheet-item-1", "__islocal": 1, "__unsaved": 1, "owner": hire_admin, "company": Staff_Comp, "hours": 1, "amount": 20, "status": "", "working_hours": 1, "overtime_hours": 0, "parent": "Add Timesheet", "parentfield": "items", "parenttype": "Add Timesheet", "idx": 1, "employee": emp, "employee_name": emp_name, "from_time": "00:00:00", "to_time": "01:00:00", "break_from": "", "break_to": "", "timesheet_value": "", "overtime_rate": 0}]
        date=job_order.from_date
        date=str(date)
        update_timesheet(user=frappe.session.user, company_type='Hiring', items=str(items), cur_selected='[]', job_order=job_order.name, date=date, from_time="00:00:00", to_time="01:00:00", break_from_time=None, break_to_time=None,save=save)
    def delete_data(self,job_order,timesheet_name=None):
        frappe.set_user('Administrator')
        timesheet=frappe.db.get_list('Timesheet', filters={'job_order_detail':job_order}, fields={'name','docstatus'})
        if timesheet_name:
            user_permission=frappe.db.get_list(usrPerm,filters={'allow':'Timesheet','for_value':timesheet_name},fields={'name'})
            for user in user_permission:
                frappe.delete_doc(usrPerm,user.name)
            frappe.db.sql('delete from `tabTimesheet` where name = "{0}" '.format(timesheet_name))
        if timesheet:
            for order in timesheet:  
                user_permission=frappe.db.get_list(usrPerm,filters={'allow':'Timesheet','for_value':order.name},fields={'name'})
                for user in user_permission:
                    frappe.delete_doc(usrPerm,user.name)
                frappe.delete_doc('Timesheet',order.name)
        assign_emp=frappe.db.get_list('Assign Employee', filters={'job_order':job_order}, fields={'name'})
        if assign_emp:
            for order in assign_emp:
                frappe.delete_doc("Assign Employee",order.name)
        claim_orders= frappe.db.get_list('Claim Order', filters={'job_order':job_order}, fields={'name'})
        if claim_orders:
            for order in claim_orders:
                frappe.delete_doc('Claim Order',order.name)
        frappe.delete_doc(jobOrder,job_order)
