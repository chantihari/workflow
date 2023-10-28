from tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet import job_order_name
import frappe
import unittest
import json				
from tag_workflow.tag_workflow.doctype.job_site.job_site import checkingjobsiteandjob_site_contact, get_jobtitle_based_on_industry, get_jobtitle_based_on_company, get_industry_title_rate, exist_values
JO='Job Order'
jo_test_records = frappe.get_test_records(JO)

class TestJobSite(unittest.TestCase):

#	FUNCTION 2 JT based on IND 
	def test_get_jobtitle_based_on_industry(self): 
		IT = 'Industry Types'
		title_list = frappe.db.get_list(IT, fields={'job_titles'})

		self.create_company()
		for record in jo_test_records:
			job_order = frappe.new_doc(JO)
			job_order.company = record['company']
			job_order.select_job = record['select_job']
			job_order.from_date = record['from_date']
			job_order.job_start_time = record['job_start_time']
			job_order.availability = record['availability']
			job_order.rate = record['rate']
			job_order.to_date = record['to_date']
			job_order.category = record['category']
			job_order.job_site = record['job_site']
			job_order.no_of_workers = record['no_of_workers']
			job_order.e_signature_full_name = record['e_signature_full_name']
			job_order.agree_to_contract = record['agree_to_contract']
			job_order.estimated_hours_per_day=record['estimated_hours_per_day']
			job_order.staff_company=record['staff_company']
			job_order.per_hour=record['per_hour']
			job_order.flat_rate=record['flat_rate']
			job_order.save()  
   
			result = get_jobtitle_based_on_industry(job_order.company,job_order.industry,job_order.title_list)
			self.assertEqual(1,result)
			job_order_updated = frappe.get_doc(JO, job_order.name)
			self.assertEqual('vibhu_hiring',job_order_updated.company)
			self.assertEqual('IT',job_order_updated.industry)
			self.assertEqual(title_list,job_order_updated.title_list)
			self.delete_test_data(job_order.name)    

		
	def create_company(self):
		records_file = open('/home/vibhu.singh/frappe/frappe-bench/apps/tag_workflow/tag_workflow/public/js/test_record_company/test_records_c.json')
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
					company_doc.append('industry_type', {
						'industry_type':industry['industry_type']
					})
					print(industry['industry_type'])
				company_doc.save()	 
#-------------------------------------------------------------------------      

#	FUNCTION 3 JT based on COM 
	def test_get_jobtitle_based_on_company(self): 

		self.create_company()
		for record in jo_test_records:
			job_order = frappe.new_doc(JO)
			job_order.company = record['company']
			job_order.select_job = record['select_job']
			job_order.from_date = record['from_date']
			job_order.job_start_time = record['job_start_time']
			job_order.availability = record['availability']
			job_order.rate = record['rate']
			job_order.to_date = record['to_date']
			job_order.category = record['category']
			job_order.job_site = record['job_site']
			job_order.no_of_workers = record['no_of_workers']
			job_order.e_signature_full_name = record['e_signature_full_name']
			job_order.agree_to_contract = record['agree_to_contract']
			job_order.estimated_hours_per_day=record['estimated_hours_per_day']
			job_order.staff_company=record['staff_company']
			job_order.per_hour=record['per_hour']
			job_order.flat_rate=record['flat_rate']
			job_order.save()  
   
			result = get_jobtitle_based_on_industry(job_order.company,job_order.industry,job_order.title_list)
			self.assertEqual(1,result)
			job_order_updated = frappe.get_doc(JO, job_order.name)
			self.assertEqual('vibhu_hiring',job_order_updated.company)
			self.assertEqual(frappe.db.get_list(),job_order_updated.title_list)
			self.delete_test_data(job_order.name)    
 
#-------------------------------------------------------------------------      

#	FUNCTION 4
	def get_industry_based_on_jobtitle(self): 

		self.create_company()
		for record in jo_test_records:
			job_order = frappe.new_doc(JO)
			job_order.company = record['company']
			job_order.select_job = record['select_job']
			job_order.from_date = record['from_date']
			job_order.job_start_time = record['job_start_time']
			job_order.availability = record['availability']
			job_order.rate = record['rate']
			job_order.to_date = record['to_date']
			job_order.category = record['category']
			job_order.job_site = record['job_site']
			job_order.no_of_workers = record['no_of_workers']
			job_order.e_signature_full_name = record['e_signature_full_name']
			job_order.agree_to_contract = record['agree_to_contract']
			job_order.estimated_hours_per_day=record['estimated_hours_per_day']
			job_order.staff_company=record['staff_company']
			job_order.per_hour=record['per_hour']
			job_order.flat_rate=record['flat_rate']
			job_order.save()  
   
			result = get_jobtitle_based_on_industry(job_order.company,job_order.industry,job_order.title_list)
			self.assertEqual(1,result)
			job_order_updated = frappe.get_doc(JO, job_order.name)
			self.assertEqual('vibhu_hiring',job_order_updated.company)
			self.assertEqual(frappe.db.get_value(job_order_updated.title_name),'vibhu_hiring')
			self.delete_test_data(job_order.name)   
#-------------------------------------------------------------------------     

#	FUNCTION 5 
	def et_industry_based_on_company(self): 

		self.create_company()
		for record in jo_test_records:
			job_order = frappe.new_doc(JO)
			job_order.company = record['company']
			job_order.select_job = record['select_job']
			job_order.from_date = record['from_date']
			job_order.job_start_time = record['job_start_time']
			job_order.availability = record['availability']
			job_order.rate = record['rate']
			job_order.to_date = record['to_date']
			job_order.category = record['category']
			job_order.job_site = record['job_site']
			job_order.no_of_workers = record['no_of_workers']
			job_order.e_signature_full_name = record['e_signature_full_name']
			job_order.agree_to_contract = record['agree_to_contract']
			job_order.estimated_hours_per_day=record['estimated_hours_per_day']
			job_order.staff_company=record['staff_company']
			job_order.per_hour=record['per_hour']
			job_order.flat_rate=record['flat_rate']
			job_order.save()  
   
			result = get_jobtitle_based_on_industry(job_order.company,job_order.industry,job_order.title_list)
			self.assertEqual(1,result)
			job_order_updated = frappe.get_doc(JO, job_order.name)
			self.assertEqual('vibhu_hiring',job_order_updated.company)
			self.assertEqual('IT',job_order_updated.industry)
			self.assertEqual(frappe.db.get_value(job_order_updated.title_name),'vibhu_hiring')
			self.delete_test_data(job_order.name)   
#-------------------------------------------------------------------------   
   
#	FUNCTION 6 industry title rate
	def test_get_industry_title_rate(self):

		self.create_company()
		for record in jo_test_records:
			job_order = frappe.new_doc(JO)
			job_order.company = record['company']
			job_order.select_job = record['select_job']
			job_order.from_date = record['from_date']
			job_order.job_start_time = record['job_start_time']
			job_order.availability = record['availability']
			job_order.rate = record['rate']
			job_order.to_date = record['to_date']
			job_order.category = record['category']
			job_order.job_site = record['job_site']
			job_order.no_of_workers = record['no_of_workers']
			job_order.e_signature_full_name = record['e_signature_full_name']
			job_order.agree_to_contract = record['agree_to_contract']
			job_order.estimated_hours_per_day=record['estimated_hours_per_day']
			job_order.staff_company=record['staff_company']
			job_order.per_hour=record['per_hour']
			job_order.flat_rate=record['flat_rate']
			job_order.save()  
   
			result = get_jobtitle_based_on_industry(job_order.company,job_order.industry,job_order.title_list)
			self.assertEqual(1,result)
			job_order_updated = frappe.get_doc(JO, job_order.name)
			self.assertEqual('IT',job_order_updated.industry_type)
			self.assertEqual('30',job_order_updated.rate)
			self.assertEqual('IT',job_order_updated.category) #description
			self.assertEqual(frappe.db.get_list(),job_order_updated.title_list)
   
			self.delete_test_data(job_order.name)    
#-------------------------------------------------------------------------     

#FUNCTION 7 EXIST VALUES
	def test_exist_values(self):    
  
		temp4=exist_values(["1","2","3"])
		self.assertEqual("1','2','3",temp4)
  

		temp4=exist_values(["1","2","3"])
		self.assertEqual("1','0','0",temp4)
  

		temp5=exist_values(["1","2","3"])
		self.assertEqual("a string",temp5)  
 #-------------------------------------------------------------------------      

#FUNCTION 1 checking site and contact

	def test_checkingjobsiteandjob_site_contact(self):
     
		temp =checkingjobsiteandjob_site_contact("vibhuHiring", '9011234588')
		self.assertEqual(True,temp)
  

		test =checkingjobsiteandjob_site_contact("vibhuHiring", '9011234588')
		self.assertEqual(False,test)  
  
		
 #-------------------------------------------------------------------------     