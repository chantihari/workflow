import frappe
from frappe import _
import unittest
from frappe.utils import getdate
from tag_workflow.tag_data import claim_order_insert
from tag_workflow.tag_workflow.report.employee_status_report.employee_status_report import execute
from datetime import datetime as dt
from tag_workflow.tag_data import staff_email_notification,receive_hire_notification
from tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet import update_timesheet
from tag_workflow.controllers.master_controller import check_employee

staff_company = 'UT Kanchan Staff Test1'
staff_user = 'sa_ut_kanchan_sharma1@yopmail.com'

hire_company = 'UT Kanchan Hire Test1'
hire_user = 'ha_ut_kanchan_sharma1@yopmail.com'

inds_type='Administrative/Clerical'
job_title="Auditor"
job_site="New York, NY 10016, USA"
state='New York'
city='New York'
zip='10016'
emp_email = 'ut_kanchanemp1@yopmail.com'
jobOrder='Job Order'
Job_Site = 'Job Site'
Ind_Type = 'Industry Type'
asnEmp='Assign Employee'

class TestEmployeeTimesheetReport(unittest.TestCase):
    def test_employee_status_report_data(self):
        self.create_basic_info()
        self.check_report_data()
        self.delete_test_data()

    def test_employee_status_report_filter(self):
        self.check_report_filters()
        self.delete_test_data()


    def create_basic_info(self):
        self.create_industry_type()
        self.create_job_title()
        self.create_hire_company()
        self.create_staff_company()
        self.create_job_site()
        self.create_job_order()

    def create_industry_type(self):
        try:
            if not frappe.db.exists(Ind_Type, inds_type):
                frappe.get_doc({
                    'doctype': Ind_Type,
                    'industry': inds_type
                }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(e, 'Test Employee Status Report: Creating industry type Error')

    def create_job_title(self):
        try:
            if not frappe.db.exists('Item',job_title):
                self.job_title_doc = frappe.get_doc({
                    'doctype': 'Item',
                    'industry': inds_type,
                    'job_titless': job_title,
                    'rate': 20,
                    'descriptions': job_title,
                    'item_code': job_title,
                    'item_group': 'All Item Groups',
                    'stock_uom': 'Nos'
                }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(e, 'Test Employee Status Report: Creating job title Error')

    def create_hire_company(self):
        try:
            if not frappe.db.exists('Company', hire_company):
                frappe.get_doc({
                    'doctype': 'Company',
                    'company_name': hire_company,
                    'organization_type': 'Hiring',
                    'accounts_payable_contact_name': hire_user,
                    'fein': '987654321',
                    'title': hire_company,
                    'accounts_payable_email': hire_user,
                    'accounts_payable_phone_number': '+1903-539-7085',
                    'contact_name': 'HA UT Kanchan Hiring',
                    'phone_no': '+1903-539-7085',
                    'email': hire_user,
                    "enter_manually":1,
                    "address":job_site,
                    "state":state,
                    "city":city,
                    "zip":zip,
                    'default_currency': 'USD',
                    'primary_language': 'en',
                    'industry_type':[
                        {
                            'industry_type': inds_type
                        }
                    ],
                    "job_titles":[{
                        "industry_type":inds_type,
                        "job_titles":job_title,
                        "wages":20,
                        "description":job_title
                    }]
                }).insert(ignore_permissions=True)
            else:
                frappe.db.set_value('Company', hire_company, 'make_organization_inactive', 0)

            if not frappe.db.exists('User',hire_user):
                frappe.get_doc({
                    'doctype': 'User',
                    'organization_type': 'Hiring',
                    'email': hire_user,
                    'first_name': 'HA',
                    'last_name': 'UT KanchanHiring',
                    'tag_user_type': 'Hiring Admin',
                    'company': hire_company,
                    'date_of_joining': getdate()
                }).insert(ignore_permissions=True)
            user=frappe.get_doc('User',hire_user)
            check_employee(user.name, user.first_name, user.company, user.last_name, gender=None, date_of_birth=None, date_of_joining=None, organization_type=None)

        except Exception as e:
            frappe.log_error(e, 'Test Employee Status Report: create_hiring_company Error')
    
    def create_staff_company(self):
        try:
            if not frappe.db.exists('Company', staff_company):
                frappe.get_doc({
                    'doctype': 'Company',
                    'company_name': staff_company,
                    'organization_type': 'Staffing',
                    'fein': '987654321',
                    'default_currency': 'USD',
                    'title': staff_company,
                    'primary_language': 'en',
                    'contact_name': 'SA UT KanchanStaffing',
                    'phone_no': '+19034709848',
                    'email': staff_user,
                    'accounts_receivable_name': 'SA UT KanchanStaffing',
                    'accounts_receivable_rep_email': staff_user,
                    'accounts_receivable_phone_number': '+19034709848',
                    'set_primary_contact_as_account_receivable_contact': 1,
                    "enter_manually":1,
                    "address":job_site,
                    "state":state,
                    "city":city,
                    "zip":zip,
                }).insert()
            else:
                frappe.db.set_value('Company', staff_company, 'make_organization_inactive', 0)
            if not frappe.db.exists('User', staff_user):
                frappe.get_doc({
                    'doctype': 'User',
                    'organization_type': 'Staffing',
                    'email': staff_user,
                    'first_name': 'SA',
                    'last_name': 'UT KanchanStaffing',
                    'tag_user_type': 'Staffing Admin',
                    'company': staff_company,
                    'date_of_joining': getdate()
                }).insert(ignore_permissions=True)
            user=frappe.get_doc('User',hire_user)
            check_employee(user.name, user.first_name, user.company, user.last_name, gender=None, date_of_birth=None, date_of_joining=None, organization_type=None)
        except Exception as e:
            frappe.log_error(e, 'Test Employee Status Report: create_staffing_company Error')

        
    
   
    def create_job_site(self):
        try:
            if not frappe.db.exists(Job_Site,job_site):
                if not frappe.db.exists('Company',hire_company):
                    self.create_hiring_comp()
                frappe.get_doc({
                    'doctype':Job_Site,
                    'job_site_name':job_site,
                    'job_site':job_site,
                    'company':hire_company,
                    'manually_enter':1,
                    'state':state,
                    'city':city,
                    'zip':zip,
                    'address':job_site,
                    "job_titles":[{
                        "industry_type":inds_type,
                        "job_titles":job_title,
                        "bill_rate":20,
                        "description":job_title
                    }]
                }).insert() 
        except Exception as e:
            frappe.log_error(e,'Test Employee Status Report: create_job_site Error')

    def create_job_order(self):
        try:            
            frappe.set_user('Administrator')
            self.job_order_doc = frappe.get_doc({
                'doctype': jobOrder,
                'company': hire_company,
                'select_job': job_title,
                'from_date': getdate(),
                'staff_company':staff_company,
                'job_start_time': '01:00:00.000000',
                'availability': 'Everyday',
                'rate': 30,
                'to_date': getdate(),
                'category': inds_type,
                'job_site': job_site,
                'no_of_workers': 5,
                'e_signature_full_name': 'UT Kanchan',
                'agree_to_contract': 1,
                'estimated_hours_per_day': 6,
            }).insert(ignore_permissions=True)
            staff_email_notification(hire_company,self.job_order_doc.name,job_title,staff_company)
            self.assign_emp()
            self.create_timesheet()
        except Exception as e:
            frappe.log_error(e,'Test Employee Status Report: create_job_order Error')
    def assign_emp(self):
        job_order=frappe.get_doc(jobOrder,self.job_order_doc.name)
        claim_order_insert('10', job_order.company,job_order.name,job_order.no_of_workers,job_order.e_signature_full_name,job_order.staff_company)
        self.assign_employee(job_order)
    
    def assign_employee(self,job_order):
        try:
            self.create_emp()
            a_emp = frappe.new_doc("Assign Employee")
            a_emp.job_order = job_order.name
            a_emp.no_of_employee_required = job_order.no_of_workers
            a_emp.job_category = job_order.select_job
            a_emp.claims_approved = job_order.no_of_workers
            a_emp.hiring_organization = hire_company
            a_emp.company = staff_company
            a_emp.job_location = job_order.job_site
            a_emp.e_signature_full_name = job_order.e_signature_full_name
            a_emp.append("employee_details",{
                "company": staff_company,
                "employee": self.emp_doc.name,
                "employee_name": self.emp_doc.employee_name,
                "pay_rate": 5
            })
            a_emp.save()
            assi_emp=frappe.get_doc(asnEmp,a_emp.name)
            self.assign_doc=assi_emp
            frappe.set_user('Administrator')
            receive_hire_notification(user='Administrator', company_type="Staffing", hiring_org=hire_company, job_order=job_order.name, staffing_org=staff_company, emp_detail=assi_emp.employee_details, doc_name=assi_emp.name,worker_fill=1)
            frappe.db.set_value(jobOrder, job_order.name, "worker_filled", 1)
        except Exception as e:
            frappe.log_error(e,'Test Employee Status Report: assign_emp Error')
        
    def create_emp(self):
        try:
            emp_doc = frappe.db.get_value('Employee', {'email': emp_email}, ['name'])
            if not emp_doc:
                self.emp_doc = frappe.get_doc({
                    'doctype': 'Employee',
                    'first_name': 'UT Kanchan',
                    'last_name': 'Emp',
                    'email': emp_email,
                    'company': staff_company,
                    'status': 'Active',
                    'date_of_birth': '2000-01-01',
                    'employee_name': 'UT Kanchan Emp'
                }).insert(ignore_permissions=True)
            else:
                self.emp_doc = frappe.get_doc('Employee', {'email': emp_email})
        except Exception as e:
            frappe.log_error(e,'Test Employee Status Report: create_emp Error')

    def create_timesheet(self):
        try:
            job_order=frappe.get_doc(jobOrder,self.job_order_doc.name)
            frappe.set_user(hire_user)
            items=[{"docstatus": 0, "doctype": "Timesheet Item", "name": "new-timesheet-item-1", "__islocal": 1, "__unsaved": 1, "owner": hire_user, "company": staff_company, "hours": 1, "amount": 20, "status": "DNR", "working_hours": 1, "overtime_hours": 0, "parent": "Add Timesheet", "parentfield": "items", "parenttype": "Add Timesheet", "idx": 1, "employee": self.emp_doc.name, "employee_name": self.emp_doc.employee_name, "from_time": "00:00:00", "to_time": "01:00:00", "break_from": "", "break_to": "", "timesheet_value": "", "overtime_rate": 0}]
            date=job_order.from_date
            date=str(date)
            update_timesheet(user=frappe.session.user, company_type='Hiring', items=str(items), cur_selected='[]', job_order=job_order.name, date=date, from_time="00:00:00", to_time="01:00:00", break_from_time=None, break_to_time=None,save=0)
            timesheet=frappe.db.sql('select name from `tabTimesheet` where job_order_detail="{0}"'.format(job_order.name),as_dict=1)
            time_sheet=frappe.get_doc('Timesheet',timesheet[0]['name'])
            self.timesheet_doc=time_sheet
        except Exception as e:
            frappe.log_error(e,'Test Employee Status Report: create_timesheet Error')

    def check_report_data(self):
        column1, data1 = execute({'company':staff_company})
        expected_result1=[{"first_name":self.emp_doc.first_name,"last_name":self.emp_doc.last_name,"employee":self.emp_doc.name,"employee_company":staff_company,"job_order_detail":self.job_order_doc.name,"from_date":getdate(),"no_show": 0, "non_satisfactory": 0, "dnr": 1, "status":'DNR'}]
        self.check_column(column1)
        self.assertEqual(expected_result1, data1)
    
    def check_report_filters(self):
        column2, data2 = execute({'company': 'hire company'})
        self.check_column(column2)
        self.assertEqual([], data2)

    def check_column(self, res_column=None):
        columns = [
            {
                'fieldname': 'first_name',
                'fieldtype': 'Data',
                'label': 'Employee First Name',
                'width': 225
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
                'label': jobOrder,
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
        if res_column:
            self.assertEqual(columns, res_column)

    def delete_test_data(self):
        try:
            frappe.set_user('Administrator')
            job_order=self.job_order_doc.name
            timesheet=frappe.db.get_list('Timesheet', filters={'job_order_detail':job_order}, fields={'name','docstatus'})
            if timesheet:
                for order in timesheet:  
                    user_permission=frappe.db.get_list('User Permission',filters={'allow':'Timesheet','for_value':order.name},fields={'name'})
                    for user in user_permission:
                        frappe.delete_doc('User Permission',user.name)
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
        except Exception as e:
            frappe.log_error(e,'Test Employee Status Report: delete_test_data Error')
