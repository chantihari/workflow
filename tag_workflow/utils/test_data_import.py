from symbol import pass_stmt	
import frappe	
import unittest	
import json	
from tag_workflow.utils.data_import import form_start_import, get_import_list	

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

    #tes case to import employee data from CSV file	
    def test_data_import(self):	
        self.create_company()	
        records_file_path = '../sites/test_tag.site/public/files/test_employee_import_data.csv' #this file is manually added to the file section of the site. To run this make sure your file section is containing the "test_employee_import_data.csv". If not you can manually add.	
        import_data = {	
            "reference_doctype": "Employee",	
            "import_type": "Insert New Records"	
        }	
        old_imported_employee = frappe.db.sql("select COUNT(*) from `tabEmployee` where email='test_data_import_employee@yopmail.com'")	
        import_doc = frappe.new_doc("Data Import")	
        import_doc.reference_doctype = import_data['reference_doctype']	
        import_doc.import_type = import_data['import_type']	
        import_doc.import_file = records_file_path	
        import_doc.save()	
        doc_name = import_doc.name	
        resp  = form_start_import(doc_name)	
        self.assertEquals(resp,True)	
        data_import_data = frappe.db.sql(f"select COUNT(*) from `tabData Import` where name='{doc_name}'")	
        self.assertEquals(data_import_data[0][0],1)	
        new_imported_employee = frappe.db.sql("select COUNT(*) from `tabEmployee` where email='test_data_import_employee@yopmail.com'")	
        self.assertEquals(new_imported_employee[0][0],old_imported_employee[0][0]+1)	


    #test case to get import data list doctype name which is "Employee" in this case	
    def test_get_import_list(self):	

        resp = get_import_list(doctype=None, txt="Employee", searchfield=None, page_len=None, start=None, filters={"user_type":"Staffing"})	
        self.assertEquals(len(resp[0]),1)