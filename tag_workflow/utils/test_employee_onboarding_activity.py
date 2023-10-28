import frappe
import unittest
Staffing_Company = "Gourav_Staffing"
Staffing_User = "gourav_staffing@yopmail.com"

class TestEvents(unittest.TestCase):
    def test_employee_onboarding_activity(self):
        self.create_staffing_company()
        self.create_user()
        self.create_onboarding_employee_template()
        self.create_employee_onboarding()
        self.remove_test_data()

    
    def create_staffing_company(self):
        if not frappe.db.exists('Company',Staffing_Company):
             self.staffing = frappe.get_doc({
                "doctype":"Company",
                "company_name":Staffing_Company,
                "organization_type":"Staffing",
                "accounts_payable_contact_name":Staffing_Company,
                "fein":"9419110424",
                "title":Staffing_Company,
                "accounts_payable_phone_number":"9419110424",
                "contact_name":Staffing_Company,
                "phone_no":"9419110424",
                "default_currency":"USD",
                "primary_language":"en"
            }).insert()
    
    def create_user(self):
        if not frappe.db.exists('User',Staffing_User):
            frappe.get_doc({
                'doctype':'User',
                'organization_type':'Staffing',
                'email':Staffing_User,
                'first_name':"Gourav",
                'last_name':'Sharma',
                'tag_user_type':'Staffing Admin',
                'company':Staffing_Company,
                'date_of_joining':frappe.utils.getdate()
                }).insert()

    def create_onboarding_employee_template(self):
        self.template =frappe.get_doc({
            'doctype':'Employee Onboarding Template',
            'company':Staffing_Company
        }).insert()

    def create_employee_onboarding(self):
        self.onboarding = frappe.get_doc({
            'doctype':'Employee Onboarding',
            'first_name':'Test',
            'last_name':'Singh',
            'staffing_company':Staffing_Company,
            'email':'test@yopmail.com',
            'status':'Pending',
            'employee_onboarding_template':self.template.name,
            'activities':[{
                "activity_name":'Test',
                "user":Staffing_User,
                "status":'Completed',
                "completed_on":frappe.utils.getdate(),
                "document_required":0}]
        }).insert(ignore_mandatory=True)

    def remove_test_data(self):
        try:
            frappe.db.sql(""" delete from `tabUser` where name="{0}" """.format(Staffing_User))
            frappe.db.sql(""" delete from `tabCompany` where name="{0}" """.format(Staffing_Company))
            frappe.db.sql(""" delete from `tabEmployee Onboarding Template` where name="{0}" """.format(self.template.name))
            frappe.db.sql(""" delete from `tabEmployee Onboarding` where name="{0}" """.format(self.onboarding.name))

        except Exception as e:
            frappe.log_error(e,'test_data_error')
        