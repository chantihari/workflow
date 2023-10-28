# Copyright (c) 2021, SourceFuse and Contributors
# See license.txt
import frappe
import unittest
import json
from tag_workflow.utils.workbright_integration import authenticate_workbright, workbright_create_employee, save_workbright_employee_id
from tag_workflow.tag_data import create_job_applicant_and_offer

staffing_company1 = 'Test Staffing1'

class TestWorkbrightIntegration(unittest.TestCase):
    def test_workbright_create_employee(self):
        self.create_company()
        emp_onb_temp1, emp_onb_temp2 = self.create_emp_onb_temp()
        records_file = open('assets/tag_workflow/js/test_records/test_workbright/test_rec_emp.json')
        test_records = json.load(records_file)
        for record in test_records:
            '''
            Creating Employee Onboarding Docs
            One with a company having API Key and Subdomain, other with a company having none of them.
            '''
            emp_onb_doc = frappe.new_doc('Employee Onboarding')
            emp_onb_doc.first_name=record['first_name']
            emp_onb_doc.last_name=record['last_name']
            emp_onb_doc.employee_name=record['employee_name']
            emp_onb_doc.email=record['email']
            emp_onb_doc.staffing_company=record['staffing_company']
            emp_onb_doc.employee_onboarding_template= emp_onb_temp1 if record['staffing_company'] == staffing_company1 else emp_onb_temp2
            emp_onb_doc.contact_number=record['contact_number']
            emp_onb_doc.date_of_birth=record['date_of_birth']
            emp_onb_doc.gender=record['gender']
            emp_onb_doc.ssn=record['ssn']
            emp_onb_doc.enter_manually=record['enter_manually']
            emp_onb_doc.street_address=record['street_address'] if record['enter_manually'] else ''
            emp_onb_doc.state=record['state'] if record['enter_manually'] else ''
            emp_onb_doc.city=record['city'] if record['enter_manually'] else ''
            emp_onb_doc.zip=record['zip']if record['enter_manually'] else ''
            emp_onb_doc.search_on_maps=record['search_on_maps']
            emp_onb_doc.complete_address=record['complete_address'] if record['search_on_maps'] else ''
            emp_onb_doc.template_name='Temp Emp1' if record['staffing_company'] == staffing_company1 else 'Temp Emp2'
            emp_onb_doc.job_applicant, emp_onb_doc.job_offer = create_job_applicant_and_offer(emp_onb_doc.employee_name,emp_onb_doc.email,emp_onb_doc.staffing_company,emp_onb_doc.contact_number)
            emp_onb_doc.insert()

            self.test_contd(emp_onb_doc)

    def create_company(self):
        records_file = open('assets/tag_workflow/js/test_records/test_workbright/test_rec_comp.json')
        test_records = json.load(records_file)
        for record in test_records:
            company_exists = frappe.db.get_value('Company', {'name': record['company_name']}, ['company_name', 'workbright_subdomain', 'workbright_api_key'])
            if not company_exists:
                company_doc = frappe.new_doc("Company")
                company_doc.company_name=record['company_name']
                company_doc.organization_type=record['organization_type']
                company_doc.fein=record['fein']
                company_doc.title=record['title']
                company_doc.primary_language=record['primary_language']
                company_doc.phone_no=record['phone_no']
                company_doc.contact_name=record['contact_name']
                company_doc.email=record['email']
                company_doc.accounts_receivable_name=record['accounts_receivable_name']
                company_doc.accounts_receivable_rep_email=record['accounts_receivable_rep_email']
                company_doc.accounts_receivable_phone_number=record['accounts_receivable_phone_number']
                company_doc.set_primary_contact_as_account_receivable_contact=record['set_primary_contact_as_account_receivable_contact']
                company_doc.enter_manually=record['enter_manually']
                company_doc.address=record['address']
                company_doc.state=record['state']
                company_doc.city=record['city'] if record['city'] else None
                company_doc.zip=record['zip']
                company_doc.default_currency=record['default_currency']
                if record['company_name']==staffing_company1:
                    company_doc.workbright_subdomain=record['workbright_subdomain']
                    company_doc.workbright_api_key=record['workbright_api_key']
                company_doc.insert()
                if company_doc.workbright_subdomain and company_doc.workbright_api_key:
                    authenticate_response = authenticate_workbright(company_doc.company_name)
                    self.assertEqual(200, authenticate_response)
                else:
                    self.assertRaises(Exception, authenticate_workbright,company_doc.company_name)
            else:
                self.company_exists(company_exists)

    def company_exists(self, company_exists):
        if company_exists[1] and company_exists[2]:
            authenticate_response = authenticate_workbright(company_exists[0])
            self.assertEqual(200, authenticate_response)
        else:
            self.assertRaises(Exception, authenticate_workbright,company_exists[0])

    def create_emp_onb_temp(self):
        emp_onb_temp1 = frappe.new_doc("Employee Onboarding Template")
        emp_onb_temp1.company="Test Staffing1"
        emp_onb_temp1.template_name="Temp Emp1"
        emp_onb_temp1.insert()

        emp_onb_temp2 = frappe.new_doc("Employee Onboarding Template")
        emp_onb_temp2.company="Test Staffing2"
        emp_onb_temp2.template_name="Temp Emp2"
        emp_onb_temp2.insert()

        return emp_onb_temp1.name, emp_onb_temp2.name

    def test_contd(self, emp_onb_doc=None):
        if emp_onb_doc:
            if emp_onb_doc.staffing_company == staffing_company1:
                response = workbright_create_employee(emp_onb_doc.name, emp_onb_doc.staffing_company, emp_onb_doc.first_name, emp_onb_doc.last_name, emp_onb_doc.job_applicant, emp_onb_doc.contact_number, emp_onb_doc.complete_address, emp_onb_doc.gender, emp_onb_doc.date_of_birth)
                self.assertTrue(isinstance(response, dict))
                if response['status']==200:
                    self.assertEqual(1, save_workbright_employee_id(emp_onb_doc.job_applicant, response['workbright_emp_id']))
            else:
                self.assertRaises(Exception, workbright_create_employee, emp_onb_doc.name, emp_onb_doc.staffing_company, emp_onb_doc.first_name, emp_onb_doc.last_name, emp_onb_doc.job_applicant, emp_onb_doc.contact_number, emp_onb_doc.complete_address, emp_onb_doc.gender, emp_onb_doc.date_of_birth)
            self.delete_test_data(emp_onb_doc)
    
    def delete_test_data(self, emp_onb):
        frappe.delete_doc('Employee Onboarding', emp_onb.name)
        frappe.delete_doc('Job Offer', emp_onb.job_offer)
        frappe.delete_doc('Job Applicant', emp_onb.job_applicant)
        frappe.delete_doc('Employee Onboarding Template', emp_onb.employee_onboarding_template)
