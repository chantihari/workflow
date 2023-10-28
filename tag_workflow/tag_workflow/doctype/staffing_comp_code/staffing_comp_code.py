# Copyright (c) 2022, SourceFuse and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document

class StaffingCompCode(Document):
	pass

@frappe.whitelist()
def get_title_industry_list(doctype, txt, searchfield, page_len, start, filters):
	try:
		industry_type=filters.get('industry_type')
		company=filters.get('company')
		if(industry_type):
			job_title=frappe.db.sql('select name from `tabItem` where industry="{0}" and company in ("{1}","") and job_titless not in (select job_title from `tabStaffing Comp Code` where staffing_company="{1}") and name like "%%{2}%%" order by name'.format(industry_type,company,'%s' % txt))
		else:
			job_title=frappe.db.sql('select name from `tabItem` where company in ("{0}","") and job_titless not in (select job_title from `tabStaffing Comp Code` where staffing_company="{0}") and name like  "%%{1}%%" order by name'.format(company,'%s' % txt))
		return job_title

	except Exception as e:
		frappe.log_error(e,'Fetching Job title error')
@frappe.whitelist()
def get_industry_title_list(doctype, txt, searchfield, page_len, start, filters):
	try:
		job_title=filters.get('job_title')
		if(job_title):
			job_industry=frappe.db.sql('select name from `tabIndustry Type` where name in (select industry from `tabItem` where job_titless="{0}") and name like  "%%{1}%%" order by name'.format(job_title,'%s' % txt))
		else:
			job_industry=frappe.db.sql('select name from `tabIndustry Type` where name like  "%%{0}%%" order by name'.format('%s' % txt))
		return job_industry

	except Exception as e:
		frappe.log_error(e,'Fetching Industry error')

@frappe.whitelist()
def check_previous_used_job_titles(industry_type,company,job_title):
	try:
		data=frappe.db.exists("Staffing Comp Code", {"job_title": job_title,"staffing_company":company,"job_industry":industry_type})
		if data:
			return 1
		else:
			return 0

	except Exception as e:
		frappe.log_error(e,'Checking Job Title error')
