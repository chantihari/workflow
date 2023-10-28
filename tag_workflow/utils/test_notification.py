import frappe
import unittest
from frappe.utils import getdate,nowtime
from tag_workflow.tag_data import staff_email_notification
Hiring_User ="SF_hiring@yopmail.com"
Staffing_User = "SF_staffing@yopmail.com"
Hiring_Company = "SF_Hiring"
Staffing_Company = "Sf_Staffing"
JO = "Job Order"
inds_type='Administrative/Clerical'
job_title="SF_Developer"
job_site="New York, NY 10016, USA"
state='New York'
city='New York'
zip='10016'
file="/files/testing doc.pdf"

class TestEvents(unittest.TestCase):
    def test_notification(self):
        self.create_industry()
        self.create_job_title()
        self.create_company_hiring()
        self.create_job_site()
        self.create_staffing_company()
        self.create_user()
        self.create_job_order()
        self.remove_test_data()
    
    def create_company_hiring(self):
        if not frappe.db.exists('Company',Hiring_Company):
            self.hiring = frappe.get_doc({
                "doctype":"Company",
                "company_name":Hiring_Company,
		        "organization_type":"Hiring",
		        "accounts_payable_contact_name":Hiring_Company,
		        "fein":"test",
		        "title":Hiring_Company,
		        "accounts_payable_email":Hiring_User,
		        "accounts_payable_phone_number":"9419110424",
		        "contact_name":Hiring_Company,
		        "phone_no":"9419110424",
		        "email":Hiring_User,
		        "enter_manually":1,
                "address":job_site,
                "state":state,
                "city":city,
                "zip":zip,
		        "default_currency":"USD",
		        "primary_language":"en",
		        "industry_type":[
			    {
				    "industry_type":inds_type
			    }],
                "job_titles":[{
                    "industry_type":inds_type,
                    "job_titles":job_title,
                    "wages":20,
                    "description":job_title
                }]
            }).insert()

    def create_staffing_company(self):
        if not frappe.db.exists('Company',Staffing_Company):
             self.staffing = frappe.get_doc({
                "doctype":"Company",
                "company_name":Staffing_Company,
                "organization_type":"Staffing",
                "accounts_payable_contact_name":Staffing_Company,
                "fein":"9419110424",
                "title":Staffing_Company,
                "accounts_payable_email":Staffing_User,
                "accounts_payable_phone_number":"9419110424",
                "contact_name":Staffing_Company,
                "phone_no":"9419110424",
                "email":Staffing_User,
                "enter_manually":1,
                "address":job_site,
                "state":state,
                "city":city,
                "zip":zip,
                "default_currency":"USD",
                "primary_language":"en",
                "cert_of_insurance":file,
                "safety_manual":file,
                "w9":file,
                "accounts_receivable_rep_email":Staffing_User,
                "accounts_receivable_name":Staffing_User,
                "industry_type":[
                    {
				    "industry_type":inds_type
                    }]
            }).insert()

    def create_user(self):
        try:
            if not frappe.db.exists('User',Hiring_User):
                frappe.get_doc({
                'doctype':'User',
                'organization_type':'Hiring',
                'email':Hiring_User,
                'first_name':"Gourav",
                'last_name':'Sharma',
                'tag_user_type':'Hiring Admin',
                'company':Hiring_Company,
                'date_of_joining':frappe.utils.getdate()
                }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(e,'test_user error')
    
    def create_industry(self):
        if not frappe.db.exists('Industry Type',inds_type):
            frappe.get_doc({
                'doctype':'Industry Type',
                'industry':inds_type
            }).insert()

    def create_job_title(self):
        if not frappe.db.exists('Item',job_title):
            frappe.get_doc({
                'doctype':'Item',
                'industry':inds_type,
                'job_titless':job_title,
                'rate':20,
                'descriptions':job_title,
                "item_code": job_title,
		        'item_group':'All Item Groups',
		        'stock_uom':'Nos'
            }).insert()

    def create_job_site(self):
        if not frappe.db.exists('Job Site',job_site):
            frappe.get_doc({
                'doctype':'Job Site',
                'job_site_name':job_site,
                'job_site':job_site,
                'company':Hiring_Company,
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
    
    def create_job_order(self):
        self.order = frappe.get_doc({
            'doctype':JO,
            'company':Hiring_Company,
            'select_job':job_title,
            'from_date':getdate(),
            'job_start_time':nowtime(),
            'availability':'Everyday',
            'rate':20,
            'to_date':getdate(),
            'category':inds_type,
            'job_site':job_site,
            'no_of_workers':4,
            'e_signature_full_name':'Gourav',
            'agree_to_contract':1,
            'estimated_hours_per_day':4,
            'staff_company':Staffing_Company,
            'per_hour':10,
            'flat_rate':12,
            }).insert()
        if self.order:
            sent = staff_email_notification(Hiring_Company,self.order.name,job_title,Staffing_Company)
            self.assertEqual(1,sent)
        

    def remove_test_data(self):
        try:
            frappe.db.sql(""" delete from `tabJob Order` where name="{0}" """.format(self.order.name))
            frappe.db.sql(""" delete from `tabUser` where name="{0}" """.format(Hiring_User))
            frappe.db.sql(""" delete from `tabCompany` where name="{0}" """.format(Staffing_Company))
            frappe.db.sql(""" delete from `tabCompany` where name="{0}" """.format(Hiring_Company))
            frappe.db.sql(""" delete from `tabIndustry Type` where name="{0}" """.format(inds_type))
            frappe.db.sql(""" delete from `tabJob Site` where name="{0}" """.format(job_site))
            frappe.db.sql(""" delete from `tabItem` where name="{0}" """.format(job_title))
        except Exception as e:
            frappe.log_error(e,'test_data_error')
        
