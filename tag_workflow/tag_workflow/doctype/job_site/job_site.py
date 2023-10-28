# Copyright (c) 2021, SourceFuse and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
import re
from frappe.utils import cint

class JobSite(Document):
	pass



@frappe.whitelist()
def checkingjobsiteandjob_site_contact(job_site_name,job_site_contact=None):
	sql = "select job_site_name,job_site_contact from `tabJob Site` where job_site_name = '{0}' and job_site_contact = '{1}' ".format(job_site_name,job_site_contact)
	if frappe.db.sql(sql):
		return False
	return True



@frappe.whitelist()
def get_jobtitle_based_on_industry(doctype, txt, searchfield, page_len, start, filters):
	try:
		company = filters.get('company')
		industry=filters.get('industry')
		title_list = filters.get('title_list')
		value=exist_values(title_list)
		sql = ''' select job_titles from `tabJob Titles` where parent = "{0}" and industry_type="{1}" and job_titles NOT IN ('{2}') and job_titles like "%%{3}%%" '''.format(company, industry,value,'%s' % txt)
		return frappe.db.sql(sql)
	except Exception as e:
		frappe.msgprint(e)
		return tuple()

@frappe.whitelist()
def get_jobtitle_based_on_company(doctype, txt, searchfield, page_len, start, filters):
	try:
		company = filters.get('company')
		title_list = filters.get('title_list')
		value=exist_values(title_list)
		sql = ''' select job_titles from `tabJob Titles` where  parent ="{0}" and job_titles NOT IN ('{1}') and job_titles like "%%{2}%%" '''.format(company,value,'%s' % txt)
		return frappe.db.sql(sql)
	except Exception as e:
		frappe.msgprint(e)
		return tuple()
		
@frappe.whitelist()
def get_industry_based_on_jobtitle(doctype, txt, searchfield, page_len, start, filters):
	try:
		company = filters.get('company')
		title=filters.get('title')
		sql = ''' select distinct industry_type from `tabJob Titles` where parent = "{0}" and job_titles="{1}" and industry_type like "%%{2}%%" '''.format(company, title,'%s' % txt)
		return frappe.db.sql(sql)
	except Exception as e:
		frappe.msgprint(e)
		return tuple()

@frappe.whitelist()
def get_industry_based_on_company(doctype, txt, searchfield, page_len, start, filters):
	try:
		company = filters.get('company')
		sql = ''' select distinct industry_type from `tabJob Titles` where  parent ="{0}" and industry_type like "%%{1}%%" '''.format(company,'%s' % txt)
		return frappe.db.sql(sql)
	except Exception as e:
		frappe.msgprint(e)
		return tuple()
@frappe.whitelist()
def get_industry_title_rate(job_title,company):
	try:
		sql = ''' select industry_type,wages,description from `tabJob Titles` where  parent ="{0}" and job_titles="{1}" '''.format(company,job_title)
		dat=frappe.db.sql(sql,as_dict=1)
		if(len(dat)==1):
			return dat[0]['industry_type'],dat[0]['wages'],dat[0]['description']
		else:
			return 1
	except Exception as e:
		frappe.log_error(e,'Fetching rate error')
def exist_values(items):
	value = ''
	for index ,i in enumerate(items):
			if index >= 1:
					value = value+"'"+","+"'"+i
			else:
					value =value+i
	return value

@frappe.whitelist()
def update_changes(doc_name):
	try:
		d=f'select JO.name,IT.comp_code,JO.worker_comp_code from `tabJob Order` as JO inner join `tabIndustry Types Job Titles` as IT on JO.select_job=IT.job_titles where IT.parent="{doc_name}" and JO.job_site="{doc_name}" and (IT.comp_code!="" and IT.comp_code is not null);'
		job_order=frappe.db.sql(d,as_dict=1)
		if len(job_order)>0:
			for i in job_order:
				doc=frappe.get_doc('Job Order',i['name'])
				doc.worker_comp_code=i['comp_code']
				doc.save(ignore_permissions=True)
	except Exception as e:
		frappe.log_error(e,'Job Site Update')

@frappe.whitelist()
def get_sites_based_on_company(doctype, txt, searchfield, page_len, start, filters):
	try:
		company = filters.get('company')
		site_list = filters.get('site_list')
		value=exist_values(site_list)
		sql = ''' select name from `tabJob Site` where  company ="{0}" and name NOT IN ('{1}') and name like "%%{2}%%" '''.format(company,value,'%s' % txt)
		return frappe.db.sql(sql)
	except Exception as e:
		frappe.msgprint(e)
		return tuple()