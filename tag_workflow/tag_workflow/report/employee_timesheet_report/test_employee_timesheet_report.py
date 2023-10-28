import frappe
from frappe import _
import unittest
from frappe.utils import getdate
from tag_workflow.tag_data import claim_order_insert
from tag_workflow.tag_workflow.report.employee_timesheet_report.employee_timesheet_report import execute, get_condition
from datetime import datetime as dt

staffing_company = 'UT Ayushi Staffing'
staffing_user = 'sa_utayushi@yopmail.com'

hiring_company = 'UT Ayushi Hiring'
hiring_user = 'ha_utayushi@yopmail.com'

industry_type = 'UT Ayushi Technology'
job_title = 'UT Ayushi Engineer'
job_site='UT Job Site Ayushi'
emp_email = 'ut_ayushiemp@yopmail.com'

Job_Site = 'Job Site'
Ind_Type = 'Industry Type'

class TestEmployeeTimesheetReport(unittest.TestCase):
    def test_employee_timesheet_report(self):
        self.create_data()
        self.get_data_test1()
        self.delete_test_data()

    def test_employee_timesheet_filter(self):
        self.get_data_test2()

    def create_data(self):
        self.create_staffing_company()
        self.create_hiring_company()
        self.create_job_industry()
        self.create_job_title()
        self.create_job_site()
        self.create_job_order()
        
    def create_staffing_company(self):
        try:
            if not frappe.db.exists('Company', staffing_company):
                frappe.get_doc({
                    'doctype': 'Company',
                    'company_name': staffing_company,
                    'organization_type': 'Staffing',
                    'fein': '987654321',
                    'default_currency': 'USD',
                    'title': staffing_company,
                    'primary_language': 'en',
                    'contact_name': 'SA UT AyushiStaffing',
                    'phone_no': '+19034709848',
                    'email': staffing_user,
                    'accounts_receivable_name': 'SA UT AyushiStaffing',
                    'accounts_receivable_rep_email': staffing_user,
                    'accounts_receivable_phone_number': '+19034709848',
                    'set_primary_contact_as_account_receivable_contact': 1,
                    'enter_manually': 1,
                    'address': '2204 Pickens Way',
                    'state': 'Texas',
                    'city': 'Longview',
                    'zip': '75601',
                }).insert()
            else:
                frappe.db.set_value('Company', staffing_company, 'make_organization_inactive', 0)
            if not frappe.db.exists('User', staffing_user):
                frappe.get_doc({
                    'doctype': 'User',
                    'organization_type': 'Staffing',
                    'email': staffing_user,
                    'first_name': 'SA',
                    'last_name': 'UT AyushiStaffing',
                    'tag_user_type': 'Staffing Admin',
                    'company': staffing_company,
                    'date_of_joining': getdate()
                }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(e, 'Test Employee Timesheet Report: create_staffing_company Error')

    def create_hiring_company(self):
        try:
            if not frappe.db.exists('Company', hiring_company):
                frappe.get_doc({
                    'doctype': 'Company',
                    'company_name': hiring_company,
                    'organization_type': 'Hiring',
                    'accounts_payable_contact_name': hiring_user,
                    'fein': '987654321',
                    'title': hiring_company,
                    'accounts_payable_email': hiring_user,
                    'accounts_payable_phone_number': '+1903-539-7085',
                    'contact_name': 'HA UT AyushiHiring',
                    'phone_no': '+1903-539-7085',
                    'email': hiring_user,
                    'enter_manually': 1,
                    'address': '3962 Florence Street',
                    'state': 'Texas',
                    'city': 'Tyler',
                    'zip': '75702',
                    'default_currency': 'USD',
                    'primary_language': 'en',
                    'industry_type':[
                        {
                            'industry_type': industry_type
                        }
                    ]
                }).insert(ignore_permissions=True)
            else:
                frappe.db.set_value('Company', staffing_company, 'make_organization_inactive', 0)

            if not frappe.db.exists('User',hiring_user):
                frappe.get_doc({
                    'doctype': 'User',
                    'organization_type': 'Hiring',
                    'email': hiring_user,
                    'first_name': 'HA',
                    'last_name': 'UT AyushiHiring',
                    'tag_user_type': 'Hiring Admin',
                    'company': hiring_company,
                    'date_of_joining': getdate()
                }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(e, 'Test Employee Timesheet Report: create_hiring_company Error')
    
    def create_job_industry(self):
        try:
            if not frappe.db.exists(Ind_Type, industry_type):
                frappe.get_doc({
                    'doctype': Ind_Type,
                    'industry': industry_type
                }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(e, 'Test Employee Timesheet Report: create_job_industry Error')

    def create_job_title(self):
        try:
            if not frappe.db.exists('Item',job_title):
                self.job_title_doc = frappe.get_doc({
                    'doctype': 'Item',
                    'industry': industry_type,
                    'job_titless': job_title,
                    'rate': 20,
                    'descriptions': job_title,
                    'item_code': job_title,
                    'item_group': 'All Item Groups',
                    'stock_uom': 'Nos'
                }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(e, 'Test Employee Timesheet Report: create_job_title Error')

    def create_job_site(self):
        try:
            if not frappe.db.exists(Job_Site, job_site):
                self.job_site_doc = frappe.get_doc({
                    'doctype': Job_Site,
                    'job_site': job_site,
                    'job_site_name': job_site,
                    'company': hiring_company,
                    'manually_enter': 1,
                    'address': '3962 Florence Street',
                    'state': 'Texas',
                    'city': 'Tyler',
                    'zip': '75702',
                    'job_titles':[{
                        'industry_type': industry_type,
                        'job_titles': job_title,
                        'bill_rate': 20,
                        'description': job_title
                    }]
                }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(e,'Test Employee Timesheet Report: create_job_site Error')

    def create_job_order(self):
        try:
            self.job_order_doc = frappe.get_doc({
                'doctype': 'Job Order',
                'company': hiring_company,
                'select_job': job_title,
                'from_date': '2022-11-05',
                'job_start_time': '01:00:00.000000',
                'availability': 'Everyday',
                'rate': 30,
                'to_date': '2022-11-11',
                'category': industry_type,
                'job_site': job_site,
                'no_of_workers': 5,
                'e_signature_full_name': 'UT Ayushi',
                'agree_to_contract': 1,
                'estimated_hours_per_day': 6,
            }).insert(ignore_permissions=True)
            claim_order_insert(10, hiring_company, self.job_order_doc.name, self.job_order_doc.no_of_workers, self.job_order_doc.e_signature_full_name, staffing_company)
            self.assign_emp()
            self.create_timesheet()
        except Exception as e:
            frappe.log_error(e,'Test Employee Timesheet Report: create_job_order Error')

    def assign_emp(self):
        try:
            self.create_emp()
            self.assign_doc = frappe.get_doc({
                'doctype': 'Assign Employee',
                'job_order': self.job_order_doc.name,
                'no_of_employee_required': self.job_order_doc.no_of_workers,
                'job_category': job_title,
                'employee_pay_rate': 10,
                'hiring_organization': hiring_company,
                'company': staffing_company,
                'job_location': job_site,
                'employee_details':[{
                    'employee': self.emp_doc.name,
                    'employee_name': self.emp_doc.employee_name,
                    'pay_rate': 10,
                    'job_category': job_title,
                    'company': staffing_company,
                    'approved':1
                }]
            }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(e,'Test Employee Timesheet Report: assign_emp Error')
        
    def create_emp(self):
        try:
            emp_doc = frappe.db.get_value('Employee', {'email': emp_email}, ['name'])
            if not emp_doc:
                self.emp_doc = frappe.get_doc({
                    'doctype': 'Employee',
                    'first_name': 'UT Ayushi',
                    'last_name': 'Emp',
                    'email': emp_email,
                    'company': staffing_company,
                    'status': 'Active',
                    'date_of_birth': '2000-01-01',
                    'employee_name': 'UT Ayushi Emp'
                }).insert(ignore_permissions=True)
            else:
                self.emp_doc = frappe.get_doc('Employee', {'email': emp_email})
        except Exception as e:
            frappe.log_error(e,'Test Employee Timesheet Report: create_emp Error')

    def create_timesheet(self):
        try:
            self.timesheet_doc = frappe.get_doc({
                'doctype': 'Timesheet',
                'company': hiring_company,
                'employee': self.emp_doc.name,
                'employee_name': self.emp_doc.employee_name,
                'start_date': self.job_order_doc.from_date,
                'end_date': self.job_order_doc.from_date,
                'total_hours': 6,
                'base_total_billable_amount': 180,
                'total_billable_hours': 6,
                'total_billable_amount': 180,
                'job_order_detail': self.job_order_doc.name,
                'estimated_daily_hours': self.job_order_doc.estimated_hours_per_day,
                'employee_company': self.emp_doc.company,
                'job_name': self.job_order_doc.select_job,
                'from_date': self.job_order_doc.from_date,
                'to_date': self.job_order_doc.to_date,
                'per_hour_rate': self.job_order_doc.rate,
                'date_of_timesheet': self.job_order_doc.from_date,
                'job_title': self.job_order_doc.select_job,
                'status_of_work_order': self.job_order_doc.order_status,
                'employee_pay_rate': 10,
                'timesheet_hours': 6,
                'total_weekly_hours': 6,
                'total_weekly_hiring_hours': 6,
                'current_job_order_hours': 6,
                'timesheet_billable_amount': 180,
                'total_job_order_amount': 180,
                'time_logs': [{
                    'activity_type': self.job_order_doc.select_job, 
                    'from_time': '2022-11-05 02:00:00', 
                    'to_time': '2022-11-05 08:00:00',
                    'hrs': '06 hrs',
                    'hours': 6
                }]
            }).insert(ignore_permissions=True)
            self.timesheet_doc.submit()
        except Exception as e:
            frappe.log_error(e,'Test Employee Timesheet Report: create_timesheet Error')

    def get_data_test1(self):
        column1, data1 = execute({})
        expected_result1 = [{"employee": self.timesheet_doc.employee, "employee_name": self.timesheet_doc.employee_name, "job_title": self.timesheet_doc.job_title, "start_date": dt.strptime(self.timesheet_doc.from_date, '%Y-%m-%d').date(), "end_date": dt.strptime(self.timesheet_doc.to_date, '%Y-%m-%d').date(), "hours": self.timesheet_doc.total_billable_hours, "total_payment": self.timesheet_doc.total_billable_amount}]
        self.test_column(column1)
        self.assertEqual(expected_result1, data1)
    
    def get_data_test2(self):
        column2, data2 = execute({'company': 'UT Ayushi Staffing2'})
        self.test_column(column2)
        self.assertEqual([], data2)

    def test_column(self, res_column=None):
        columns = [
            {
                "label": _("Employee Code"),
                "fieldname": "employee",
                "fieldtype": "Link",
                "options": "EMployee",
                "width": 150
            },
            {
                "label": _("Employee Name"),
                "fieldname": "employee_name",
                "width": 150
            },
            {
                "label": _("Job Title"),
                "fieldname": "job_title",
                "fieldtype": "Data",
                "width": 150
            },
            {
                "label": _("Start Date"),
                "fieldname": "start_date",
                "fieldtype": "Date",
                "width": 150
            },
            {
                "label": _("End Date"),
                "fieldname": "end_date",
                "fieldtype": "Date",
                "width": 150
            },
            {
                "label": _("Hours Worked"),
                "fieldname": "hours",
                "fieldtype": "Float",
                "width": 150
            },
            {
                "label": _("Total Payment"),
                "fieldname": "total_payment",
                "fieldtype": "Currency",
                "width": 150
            }
        ]
        if res_column:
            self.assertEqual(columns, res_column)

    def delete_test_data(self):
        try:
            frappe.db.set_value('Company', staffing_company, 'make_organization_inactive', 1)
            frappe.db.set_value('Company', hiring_company, 'make_organization_inactive', 1)
            self.timesheet_doc.cancel()
            frappe.delete_doc('Timesheet', self.timesheet_doc.name)
            frappe.delete_doc('Assign Employee', self.assign_doc.name)
            claim_order = frappe.db.get_value('Claim Order', {'job_order': self.job_order_doc.name, 'staffing_organization': staffing_company}, ['name'])
            frappe.delete_doc('Claim Order', claim_order)
            frappe.delete_doc('Job Order', self.job_order_doc.name)
            frappe.delete_doc('Employee', self.emp_doc.name)
        except Exception as e:
            frappe.log_error(e,'Test Employee Timesheet Report: delete_test_data Error')
