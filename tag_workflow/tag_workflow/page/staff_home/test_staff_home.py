import frappe
from frappe import _
import unittest
from frappe.utils import getdate
from tag_workflow.tag_data import claim_order_insert
from datetime import datetime as dt
from tag_workflow.tag_data import staff_email_notification
from tag_workflow.controllers.master_controller import check_employee
from tag_workflow.tag_workflow.page.staff_home.staff_home import get_order_info,order_info,filter_category
staff_company = 'UT Kanchan Staff Test1'
staff_user = 'sa_ut_kanchan_sharma1@yopmail.com'

hire_company = 'UT Kanchan Hire Test1'
hire_user = 'ha_ut_kanchan_sharma1@yopmail.com'

inds_type='Administrative/Clerical'
job_title="Auditor"
job_site="New York, NY 10016, USA-1"
state='New York'
city='New York'
zip='10016'
lat=40.74727
lng=-73.9800645
jobOrder='Job Order'
jbSite = 'Job Site'
industryType = 'Industry Type'

class TestStaffHome(unittest.TestCase):

    def test_get_order_info(self):
        self.create_basic_info()
        get_ord=get_order_info(staff_company)
        self.assertEqual(self.job_order_doc.name,get_ord['order'][0]['name'])
        self.delete_test_data()

    def test_order_info(self):
        self.create_basic_info()
        ord_info=order_info(self.job_order_doc.name)
        self.assertEqual(job_title,ord_info[0]['select_job'])
        self.delete_test_data()

    def test_filter_category(self):
        self.create_basic_info()
        filt_data=filter_category(staff_company,None,'Non Exclusive')
        self.assertEqual(self.job_order_doc.name,filt_data['order'][0]['name'])
        self.delete_test_data()

    def create_basic_info(self):
        self.create_industry_type()
        self.create_hire_company()
        self.create_staff_company()
        self.create_job_order()

    def create_industry_type(self):
        try:
            if not frappe.db.exists(industryType, inds_type):
                frappe.get_doc({
                    'doctype': industryType,
                    'industry': inds_type
                }).insert(ignore_permissions=True)
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
            if not frappe.db.exists(jbSite,job_site):
                if not frappe.db.exists('Company',hire_company):
                    self.create_hiring_comp()
                frappe.get_doc({
                    'doctype':jbSite,
                    'job_site_name':job_site,
                    'job_site':job_site,
                    'company':hire_company,
                    'manually_enter':1,
                    'state':state,
                    'city':city,
                    'zip':zip,
                    'lat':lat,
                    'lng':lng,
                    'address':job_site,
                    "job_titles":[{
                        "industry_type":inds_type,
                        "job_titles":job_title,
                        "bill_rate":20,
                        "description":job_title
                    }]
                }).insert() 
        except Exception as e:
            frappe.log_error(e,'Staff Home: Industry , job title ,job site Error')


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
            frappe.log_error(e, 'Staff Home: create_hiring_company Error')
    
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
            frappe.log_error(e, 'Staff Home: create_staffing_company Error')
        

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
        except Exception as e:
            frappe.log_error(e,'Staff Home: create_job_order Error')

    def assign_emp(self):
        job_order=frappe.get_doc(jobOrder,self.job_order_doc.name)
        claim_order_insert('10', job_order.company,job_order.name,job_order.no_of_workers,job_order.e_signature_full_name,job_order.staff_company)
    
    def delete_test_data(self):
        try:
            frappe.set_user('Administrator')
            job_order=self.job_order_doc.name
            claim_orders= frappe.db.get_list('Claim Order', filters={'job_order':job_order}, fields={'name'})
            if claim_orders:
                for order in claim_orders:
                    frappe.delete_doc('Claim Order',order.name)
            frappe.delete_doc(jobOrder,job_order)
        except Exception as e:
            frappe.log_error(e,'Staff Home: delete_test_data Error')