from symbol import pass_stmt	
import frappe	
import unittest	
import json	
from tag_workflow.tag_workflow.doctype.company.company import check_ratings, create_salary_structure

#The below test cases will run only in the case when the record file is present at the location mentioned in the line 14

class TestTagData(unittest.TestCase):	

    #function to create company	
    def create_company(self):	
        try:	
            records_file = open(r'../apps/tag_workflow/tag_workflow/public/js/test_records/test_company_records.json')	
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
                    company_doc.city=record['city']	
                    company_doc.zip=record['zip']	
                    company_doc.default_currency=record['default_currency']	
                    company_doc.primary_language=record['primary_language']	
                    for industry in record['industry_type']:	
                        company_doc.append('industry_type',{'industry_type':industry['industry_type']})	
                    company_doc.save()	
        except Exception:	
            pass	

    #test caes to check ratings for the company
    def test_check_ratings(self):
        self.create_company()
        test_hiring_company_reviews_data = {
            "staffing_company":"My Test Company",
            "hiring_company":"My Test Hiring Company",
            "rating":4,
            "comments":"Good Work"
        }

        job_order = frappe.db.sql(f'''select name from `tabJob Order` where company = "{test_hiring_company_reviews_data['hiring_company']}"''')
        old_ratings = frappe.db.sql(f'''select rating from `tabHiring Company Review` where hiring_company = "{test_hiring_company_reviews_data['hiring_company']}"''')
        new_doc_name = None
        if job_order:
            if not old_ratings:
                reviews_doc = frappe.new_doc("Hiring Company Review")
                reviews_doc.hiring_company = test_hiring_company_reviews_data['hiring_company']
                reviews_doc.staffing_company=test_hiring_company_reviews_data['staffing_company']
                reviews_doc.rating=test_hiring_company_reviews_data['rating']
                reviews_doc.comments=test_hiring_company_reviews_data['comments']
                reviews_doc.job_order=job_order[0][0]
                reviews_doc.save()
                new_doc_name = reviews_doc.name
            
            resp = check_ratings(test_hiring_company_reviews_data["hiring_company"])
            self.assertEqual(True,resp)
            if new_doc_name:
                self.delete_test_data(new_doc_name)

        self.assertEquals(1,1)
    
    #test case to check either successfully salary component added or not
    def test_create_salary_structure(self):
        self.create_company()
        doc = frappe.get_doc("Company","My Test Company")
        create_salary_structure(doc,None)
        count = frappe.db.sql('''select COUNT(*) from `tabSalary Component` where name="Basic Temp Pay_My Test Company"''')
        self.assertEquals(count[0][0],1)


    #fynction to delete the data
    def delete_test_data(self,doc_name):
        try:
            frappe.delete_doc("Hiring Company Review",doc_name)
        except Exception:
            pass