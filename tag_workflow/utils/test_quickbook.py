import frappe
from frappe import _
import unittest
from frappe.utils import getdate
from tag_workflow.tag_data import claim_order_insert
from tag_workflow.utils.quickbooks import auth_quickbook_and_sync


staffing_company = 'UT_Sahil_Staffing'
staffing_user = 'st_utsahil@yopmail.com'
hiring_company = 'UT Sahil Hiring'
hiring_user = 'ha_utsahil@yopmail.com'

industry_type = 'Virtual Sports'
job_title = 'Gamer'
job_site='UT Job Site sahil'
emp_email = 'ut_sahil_newemp@yopmail.com'

Job_Site = 'Job Site'
Ind_Type = 'Industry Type'

class TestQuickbook(unittest.TestCase):
    def test_Quickbook(self):
        self.create_data()
        

    def create_data(self):
        self.create_staffing_company()
        self.create_hiring_company()
        self.create_job_industry()
        self.create_job_title()
        self.create_job_site()
        self.create_job_order()
        self.create_invoice()
        
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
                    'contact_name': 'SA UT SahilStaffing',
                    'phone_no': '+19034709848',
                    'email': staffing_user,
                    'accounts_receivable_name': 'SA UT SahilStaffing',
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
                    'last_name': 'UT SahilStaffing',
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
                    'contact_name': 'HA UT SahilHiring',
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
                    'last_name': 'UT SahilHiring',
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
            self.emp_doc = frappe.db.get_value('Employee', {'email': emp_email}, ['name'])
            if not self.emp_doc:
                self.emp_doc = frappe.get_doc({
                    'doctype': 'Employee',
                    'first_name': 'UT Sahil',
                    'last_name': 'Emp',
                    'email': emp_email,
                    'company': staffing_company,
                    'status': 'Active',
                    'date_of_birth': '2000-01-01',
                }).insert(ignore_permissions=True)
            else:
                self.emp_doc = frappe.get_doc('Employee', {'email': emp_email})
        except Exception as e:
            frappe.log_error(e,'Test Employee Timesheet Report: create_emp Error')

    def create_timesheet(self):
        try:
            print("creating time sheet")
            self.timesheet_doc = frappe.get_doc({
                'doctype': 'Timesheet',
                'docstatus': 0,
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
                'approval_notification': 1,
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
                    'from_time': '2022-11-05 9:00:00', 
                    'to_time': '2022-11-05 15:00:00',
                    'hrs': '2 hrs',
                    'hours': 6
                }]
            }).insert(ignore_permissions=True)
            self.timesheet_doc.submit()
            
        except Exception as e:
            frappe.log_error(e,'Test Employee Timesheet Report: create_timesheet Error')

    def create_invoice(self):
        try:
            print("creating Invoice")
            self.invoice = frappe.get_doc({
                'doctype':'Sales Invoice',
                'customer':hiring_company,
                'posting_date':getdate(),
                'due_date':getdate(),
                'posting_time':"09:00:00.000000",
                'job_order':self.job_order_doc.name,
                'company':staffing_company,
                'total_billing_amount':180,
                'total_billing_hours':6,
                'items':[{
                    'item_code':"",
                    'item_name':self.job_order_doc.select_job,
                    'description':"Service",
                    'qty':1,
                    'rate':180,
                    'amount':180,
                    'conversion_factor':1,
                    'cost_center':frappe.db.get_value("Company",{"name":staffing_company},["cost_center"]),
                    'uom':"Nos",
                    'stock_uom':"Nos",
                    'stock_qty':1,
                    'default_expense_account':frappe.db.get_value('Company', {"name":staffing_company}, ['default_expense_account']),
                    'income_account':frappe.db.get_value('Company', {"name":staffing_company}, ['default_income_account']),
                }],
                'timesheets':[{
                    'time_sheet':self.timesheet_doc.name,
                    'activity_type':self.job_order_doc.select_job,
                    'from_time':self.job_order_doc.from_date,
                    'to_time':self.job_order_doc.to_date,
                    'overtime_rate': 0,
                    'overtime_hour': 0,
                    'billing_hours':6,
                    'billing_amount':180,
                    'per_hr_rate':0,
                    'flat_rate':0,
                    'employee_name':self.emp_doc.name,


                    
                }]


            }).insert(ignore_permissions=True)
            self.invoice.submit()
            data = auth_quickbook_and_sync(staffing_company,self.invoice.name)
            if len(data["invoice_id"])>0:
                print("####---------------Invoice Exported Successfully------------####")
            else:
                print("Error Occur while Exporting Invoice")
            self.delete_test_data()
        except Exception as e:
            frappe.log_error(e,'Test Employee Invoice : create_invoice Error')




    def delete_test_data(self):
            try:
                sql = """delete from `tabGL Entry` where name = '{0}'"""
                sql2 = """delete from `tabEmployee` where name = '{0}'"""
                sql_for_invoice= """delete from `tabSales Invoice` where name = '{0}'"""
                sql_for_timesheet = """delete from `tabTimesheet` where name = '{0}'"""
                gl_entry_name = "GL Entry"
                frappe.db.set_value('Company', staffing_company, 'make_organization_inactive', 1)
                frappe.db.set_value('Company', hiring_company, 'make_organization_inactive', 1)
                gl_entry = frappe.db.get_value(gl_entry_name, {'voucher_no': self.invoice.name}, ['name'])
                frappe.db.sql(sql.format(gl_entry))
                gl_entry2 = frappe.db.get_value(gl_entry_name, {'voucher_no': self.invoice.name}, ['name'])
                frappe.db.sql(sql.format(gl_entry2))
                frappe.db.sql(sql_for_invoice.format(self.invoice.name))
                frappe.db.sql(sql2.format(self.emp_doc.name))
                frappe.db.sql(sql_for_timesheet.format(self.timesheet_doc.name))
                frappe.delete_doc('Assign Employee', self.assign_doc.name)
                claim_order = frappe.db.get_value('Claim Order', {'job_order': self.job_order_doc.name, 'staffing_organization': staffing_company}, ['name'])
                frappe.delete_doc('Claim Order', claim_order)
                frappe.delete_doc('Job Order', self.job_order_doc.name)
                frappe.delete_doc('Employee', self.emp_doc.name)
            except Exception as e:
                frappe.log_error(e,'Test Employee Timesheet Report: delete_test_data Error')