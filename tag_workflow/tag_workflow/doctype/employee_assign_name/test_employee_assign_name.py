import frappe
import unittest
import json
from tag_workflow.tag_workflow.doctype.employee_assign_name.employee_assign_name import employee_email_filter
from tag_workflow.controllers.master_controller import check_employee
class TestEmployeeAssignName(unittest.TestCase):
    def test_employee_assign_name(self):
        self.create_company(test_case=0)
    def test_employee_assign_name_fail_case(self):
        self.create_company(test_case=1)
    def create_company(self,test_case):
        records_file = open('assets/tag_workflow/js/test_record/test_record_new_comp.json')
        test_records = json.load(records_file)
        for record in test_records:
            company_exists=frappe.db.get_value('Company',{'company_name':record['company_name']},'name')
            if not company_exists:
                company_doc = frappe.new_doc("Company")
                company_doc.company_name=record['company_name']
                company_doc.organization_type=record['organization_type']
                company_doc.accounts_payable_contact_name=record['accounts_payable_contact_name']
                company_doc.fein=record['fein']
                company_doc.title=record['title']
                company_doc.accounts_payable_email=record['accounts_payable_email']
                company_doc.accounts_payable_phone_number=record['accounts_payable_phone_number']
                company_doc.contact_name=record['contact_name']
                company_doc.phone_no=record['phone_no']
                company_doc.email=record['email']
                company_doc.enter_manually=record['enter_manually']
                company_doc.address=record['address']
                company_doc.state=record['state']
                company_doc.city=record['city'] if record['city'] else None
                company_doc.zip=record['zip']
                company_doc.default_currency=record['default_currency']
                company_doc.primary_language=record['primary_language']
                company_doc.save()
                user=self.create_user(company_doc)
                self.create_employee(user)
                self.check_permissions(company_doc,user,test_case)
            else:
                company_doc=frappe.get_doc('Company',record['company_name'])
                user=self.create_user(company_doc)
                self.create_employee(user)
                self.check_permissions(company_doc,user,test_case)
    def create_user(self,comp_doc):
        user_exists=frappe.db.get_value('User',{'name':comp_doc.email},'name')
        if not user_exists:
            if comp_doc.organization_type=='Hiring':
                role="Hiring Admin"
            elif comp_doc.organization_type=='Staffing':
                role='Staffing Admin'
            elif comp_doc.organization_type=='Exclusive Hiring':
                role='Hiring Admin'
            else:
                role='TAG Admin'

            user_doc=frappe.new_doc("User")
            user_doc.organization_type=comp_doc.organization_type
            user_doc.role_profile_name=role
            user_doc.module_profile=comp_doc.organization_type
            user_doc.email=comp_doc.email
            user_doc.first_name='kanchan'
            user_doc.last_name='sharma'
            user_doc.enabled=1
            user_doc.company=comp_doc.name
            user_doc.date_of_joining='2022-11-04'
            user_doc.tag_user_type=role
            user_doc.save()
            return user_doc.name
        else:
            return comp_doc.email
    def create_employee(self,user):
        user=frappe.get_doc('User',user)
        check_employee(user.name, user.first_name, user.company, user.last_name, gender=None, date_of_birth=None, date_of_joining=None, organization_type=None)

    def check_permissions(self,company_doc,user,test_case):
        frappe.set_user(user)
        data=employee_email_filter(user)
        if test_case==1:
            self.assertEqual(company_doc.name,data+'1')
        else:
            self.assertEqual(company_doc.name,data)




