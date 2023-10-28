import frappe
import unittest
from frappe.utils import getdate

staff_company = 'Test1 Staffing'
staff_user = 'test1staff@company.com'

hire_company = 'Test1 Hiring'
hire_user = 'test1hiring@company.com'

inds_type='Administrative/Clerical1'
job_title="Test1 Job Title"
job_site="10110 Westview Drive, Houston, TX, USA"
state='New York'
city='New York'
zip='10016'
jobOrder='Job Order'
Job_Site = 'Job Site'
Ind_Type = 'Industry Type'
claimOrder = 'Claim Order'
EPR = 'Employee Pay Rate'
jobPayRates = "Pay Rates"

class SetUp(unittest.TestCase):
    
    def setUp(self) -> None:
        self.create_industry_type()
        self.create_job_title()
        self.create_hire_company()
        self.create_staff_company()
        self.create_job_site()
        self.create_job_order()
        return super().setUp()
    
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
        except Exception as e:
            frappe.log_error(e,'Test Employee Status Report: create_job_order Error')

class TestPayRates(SetUp):
    def test_create_pay_rates_success(self):
        self.pay_rates_doc = frappe.get_doc({
            'doctype': jobPayRates,
            'staffing_company':staff_company,
            'hiring_company' : hire_company,
            'job_site' :Job_Site,
            'parent':inds_type,
            'parenttype' : 'pay_rate',
            'employee_pay_rate' : 21
        }).insert()
        data = frappe.db.sql("select staffing_company from `tabPay Rates` WHERE  staffing_company='{0}'".format(staff_company),as_dict=1)
        self.assertEqual(data[0]['staffing_company'],staff_company)

    def test_create_pay_rates_failure(self):
        self.pay_rates_doc = frappe.get_doc({
            'doctype': jobPayRates,
            'staffing_company': '',
            'hiring_company' : hire_company,
            'job_site' :Job_Site,
            'parent':inds_type,
            'parenttype' : 'pay_rate',
            'employee_pay_rate' : 21
        })
        if not self.pay_rates_doc.staffing_company:
            self.pay_rates_doc.insert()
        else:
            print("Not create pay rates")
        
    def test_create_pay_rate(self):
        self.pay_rates_doc = frappe.get_doc({
            'doctype': jobPayRates,
            'staffing_company': staff_company,
            'hiring_company' : '',
            'job_site' : '',
            'parent':inds_type,
            'parenttype' : 'pay_rate',
            'employee_pay_rate' : ''
        })
        datas = frappe.db.exists('Item',job_title)
        employee_pay_rate = frappe.db.get_value('Item', {"name": datas}, ['rate'])
        if  self.pay_rates_doc.staffing_company and not self.pay_rates_doc.employee_pay_rate and not self.pay_rates_doc.hiring_company:
            self.pay_rates_doc.employee_pay_rate =  employee_pay_rate
        self.pay_rates_doc.insert()
        data = frappe.db.sql("select employee_pay_rate from `tabPay Rates` WHERE  staffing_company='{0}'".format(staff_company),as_dict=1)
        self.assertEqual(data[0]['employee_pay_rate'],employee_pay_rate)

    def test_delete_pay_rates_linked_with_joborder(self):
        data =  frappe.db.sql("select job_title from `tabJob Order` where select_job = '{0}' and category='{1}'".format(job_title,inds_type))
        if data:
            print("Alredy linked with job order")
        else:
            print("Delete pay rates")           

    def test_create_claim_order(self):
        emp_pay_rate = frappe.db.exists(EPR, {"hiring_company": hire_company,"job_title": job_title, "job_site": job_site, "staffing_company": staff_company})
        emp_pay_rate2 = frappe.db.exists(EPR, {"job_title": job_title, "staffing_company": staff_company})
        employee_pay_rate = frappe.db.get_value(EPR, {"name": emp_pay_rate}, ['employee_pay_rate']) if emp_pay_rate \
               else frappe.db.get_value(EPR, {"name": emp_pay_rate2}, ['employee_pay_rate']) 
        if not frappe.db.exists(claimOrder, {"job_order":'JO-00408'}):
            self.job_claim_doc = frappe.get_doc({
                'doctype' :claimOrder,
                'job_order':'JO-00408',
                'staffing_organization':staff_company,
                'no_of_workers_joborder':1,
                'no_of_remaining_employee':1,
                'staff_claims_no':1,
                'employee_pay_rate':employee_pay_rate if employee_pay_rate else 0.0,
                'e_signature':'test',
                'agree_to_contract':1
            }).insert()
        data = frappe.db.sql("select employee_pay_rate from `tabClaim Order`  WHERE job_order  = 'JO-00408'",as_dict=1)
        if not employee_pay_rate:
            employee_pay_rate = 0.0
        self.assertEqual(data[0]['employee_pay_rate'],employee_pay_rate)