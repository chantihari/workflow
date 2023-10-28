# Copyright (c) 2021, SourceFuse and contributors
# For license information, please see license.txt

from frappe.model.document import Document
import frappe
from frappe import _
from erpnext.setup.doctype.company.company import Company,install_country_fixtures
from frappe import enqueue
from frappe.utils.nestedset import NestedSet
create_default_accounts=Company.create_default_accounts
from datetime import datetime
import ast
import json

class CustomCompany(Company):
	def validate(self):
		self.update_default_account = False
		if self.is_new():
			self.update_default_account = True
		self.validate_abbr()
		self.validate_default_accounts()
		self.validate_currency()
		self.validate_coa_input()
		self.validate_provisional_account_for_non_stock_items()
		self.check_country_change()
		self.check_parent_changed()
		self.set_chart_of_accounts()
		self.validate_parent_company()
   	
	def on_update(self):
		NestedSet.on_update(self)
		frappe.db.commit()
		enqueue(self.update_enqueue,queue='long',timeout=10000, is_async=True)
		
	@frappe.whitelist()
	def update_enqueue(self):
		if not frappe.db.sql("""select name from tabAccount
				where company=%s and docstatus<2 limit 1""", self.name):
			if not frappe.local.flags.ignore_chart_of_accounts:
				frappe.flags.country_change = True
				self.create_default_accounts()
				self.create_default_warehouses()

		if not frappe.db.get_value("Cost Center", {"is_group": 0, "company": self.name}):
			self.create_default_cost_center()

		if frappe.flags.country_change:
			install_country_fixtures(self.name, self.country)
			self.create_default_tax_template()

		if not frappe.db.get_value("Department", {"company": self.name}):
			self.create_default_departments()

		if not frappe.local.flags.ignore_chart_of_accounts:
			self.set_default_accounts()
			if self.default_cash_account:
				self.set_mode_of_payment_account()

		if self.default_currency:
			frappe.db.set_value("Currency", self.default_currency, "enabled", 1)

		if (hasattr(frappe.local, "enable_perpetual_inventory") and self.name in frappe.local.enable_perpetual_inventory):
			frappe.local.enable_perpetual_inventory[self.name] = self.enable_perpetual_inventory

		if frappe.flags.parent_company_changed:
			from frappe.utils.nestedset import rebuild_tree

			rebuild_tree("Company", "parent_company")
		frappe.clear_cache()

@frappe.whitelist()
def check_ratings(company_name,comp_type):
	if comp_type == 'Staffing':
		sql = """select COUNT(*) from `tabCompany Review` where staffing_company="{}" """.format(company_name)
	else:
		sql = """select COUNT(*) from `tabHiring Company Review` where hiring_company="{}" """.format(company_name)
	row_count = frappe.db.sql(sql)
	return row_count[0][0]>0


@frappe.whitelist()
def check_staffing_reviews(company_name):
    """
    This function checks the staffing reviews of a company and returns the average rating if there are
    at least 10 reviews, otherwise it returns 0.
    :param company_name: The name of the staffing company for which you want to check the staffing
    reviews
    :return: a string representation of the average rating of a company if the number of reviews for the
    company is greater than or equal to 10. If the number of reviews is less than 10 or if there is an
    exception, the function returns 0.
    """
    try:
        sql = f'''select COUNT(*) from `tabCompany Review` where staffing_company="{company_name}"
		UNION ALL
		select round(AVG(staffing_ratings),1) from `tabCompany Review` where staffing_company="{company_name}"
		'''
        result = frappe.db.sql(sql)
        return str(float(result[1][0] or 0)) if int(result[0][0]) >= 10 else 0
    except Exception as e:
        print(e, frappe.get_traceback())


@frappe.whitelist()
def create_salary_structure(doc,method):
	company_type = frappe.db.get_value("User", {"name": frappe.session.user}, ["organization_type"])
	if company_type == "Staffing" or company_type == "TAG":
		if doc.organization_type == "Staffing" or doc.organization_type =="TAG":
			comp_name = "Basic Temp Pay_"
			if not frappe.db.exists("Salary Component", {"name":comp_name+doc.company_name}):
				doc_sal_comp = frappe.new_doc('Salary Component')
				doc_sal_comp.creation = datetime.now()
				doc_sal_comp.name = comp_name+ doc.company_name
				doc_sal_comp.owner = frappe.session.user
				doc_sal_comp.salary_component =comp_name+ doc.company_name
				doc_sal_comp.salary_component_abbr = "BTP_" + doc.company_name
				doc_sal_comp.type = "Earning"
				doc_sal_comp.company = doc.company_name
				doc_sal_comp.salary_component_name = comp_name+ doc.company_name
				doc_sal_comp.insert()

			if not frappe.db.exists("Salary Structure", {"name":"Temporary Employees_"+doc.company_name}):
				doc_sal_struct=frappe.new_doc('Salary Structure')
				doc_sal_struct.name = "Temporary Employees_"+doc.company_name
				doc_sal_struct.creation = datetime.now()
				doc_sal_struct.owner = frappe.session.user
				doc_sal_struct.docstatus = 1
				doc_sal_struct.company = doc.company_name
				doc_sal_struct.is_active = "Yes"
				doc_sal_struct.payroll_frequency = "Weekly"
				doc_sal_struct.salary_slip_based_on_timesheet = 1
				doc_sal_struct.salary_component = comp_name +doc.company_name
				doc_sal_struct.insert()

@frappe.whitelist()	
def create_certificate_records(company,cert_list):
	cert_list = ast.literal_eval(cert_list)
	sql = '''delete from `tabCertificate and Endorsement Details` where company = "{0}"'''.format(company)
	print(cert_list,type(cert_list))
	frappe.db.sql(sql)
	for certificate in cert_list:
		doc_certificate = frappe.new_doc('Certificate and Endorsement Details')
		doc_certificate.company = certificate["company"]
		doc_certificate.certificate_type = certificate["cert_type"]
		doc_certificate.attached_certificate = certificate["link"]
		doc_certificate.sequence = certificate["sequence"]
		doc_certificate.save(ignore_permissions = True)


@frappe.whitelist()
def get_previous_certificate(company):
	records = frappe.db.sql('''select company,certificate_type,attached_certificate,sequence from `tabCertificate and Endorsement Details` where company = "{0}" order by sequence'''.format(company),as_list=True)
	print(records)
	return records

@frappe.whitelist()
def get_certificate_type(cert_attribute):
	sql = '''select name from `tabCertificate and Endorsement` where name like "{}%"''' .format(cert_attribute)
	cert_name = frappe.db.sql(sql)
	return cert_name

@frappe.whitelist()
def validate_saved_fields(doc,method):
	user = frappe.get_doc('User',frappe.session.user)
	if not doc.is_new() and user.tag_user_type=="Hiring User":
		company = frappe.get_doc('Company',doc.name)
		if doc.title!=company.title or doc.fein!=company.fein or doc.phone_no!=company.phone_no or doc.email!=company.email:
			frappe.throw('Insufficient Permission')

@frappe.whitelist()
def set_comp_id(doc, method):
	try:   	
		last_comp_index=frappe.db.sql('''SELECT last_comp_id FROM company_index WHERE id=1''', as_list=1)
		doc.comp_id = 'CO-'+str(last_comp_index[0][0]).zfill(6)
		frappe.db.sql('''UPDATE company_index SET last_comp_id=last_comp_id+1 WHERE id=1''')
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(e, 'set_comp_id error')
		print(e, frappe.get_traceback())

@frappe.whitelist()
def create_tag_job_title(company):
	try:
		enqueue(create_tag_job_title_job, queue="long", company=company)
	except Exception as e:
		frappe.log_error(e)

@frappe.whitelist()
def create_tag_job_title_job(company):
	try:
		comp_changes = frappe.db.sql(f'''SELECT data FROM `tabVersion` WHERE docname = "{company}" ORDER BY modified DESC limit 1''', as_dict=1)
		comp_changed = json.loads(comp_changes[0].data) if len(comp_changes) > 0 else []
		if 'added' in comp_changed:
			jt_added=[i[1]["job_titles"] for i in comp_changed['added'] if i[0]=='job_titles']
		if 'row_changed' in comp_changed:
			jt_edited=[i[3][0][2] for i in comp_changed['row_changed'] if i[0]=='job_titles' and i[3][0][0]=='job_titles']
			if len(jt_edited)==0: check_other_change(comp_changed['row_changed'])

		final_jt_list = jt_added+jt_edited

		sql=''
		if len(final_jt_list)==1:
			sql=f'''select name from tabItem where name="{final_jt_list[0]}" and (company="" or company is null)'''
		elif len(final_jt_list)>1:
			sql= f'''select name from tabItem where name in {tuple(final_jt_list)} and (company="" or company is null)'''
		item_list = frappe.db.sql(sql, as_list=1) if sql else []

		for item in item_list:
			item_doc=frappe.get_doc("Item", item[0])
			new_doc = frappe.copy_doc(item_doc)
			item_name = frappe.db.sql(f'''select name from tabItem where name like "{item[0].split('-')[0]}%" order by CAST(SUBSTRING_INDEX(name, '-', -1) AS INT) desc limit 1''', as_list=1)
			item_last_no = int(item_name[0][0].split("-")[1])+1 if "-" in item_name[0][0] else 1
			new_doc.name = f"{item[0].split('-')[0]}-{item_last_no}"
			new_doc.company = company
			new_doc.job_titless = new_doc.item_code = new_doc.name
			new_doc.is_company=1

			details = frappe.db.sql(f'''select wages, description from `tabJob Titles` where parenttype="Company" and parent="{company}" and job_titles="{item[0]}"''', as_list=1)
			new_doc.rate = details[0][0]
			new_doc.descriptions=details[0][1]
			new_doc.insert(ignore_permissions=True)

			new_doc.item_name = new_doc.name
			new_doc.set("job_site_table", [])
			new_doc.set("pay_rate", [])
			new_doc.save(ignore_permissions=True)

			frappe.db.sql(f'''delete from `tabJob Titles` where parenttype="Company" and parent="{company}" and job_titles="{item[0]}" and industry_type="{new_doc.industry}"''')
			frappe.db.commit()
	except Exception as e:
		frappe.log_error(e)

@frappe.whitelist()
def check_other_change(changed_fields): 	
	for i in changed_fields:
		desc_changed=''
		wage_changed=''
		for j in i[3]:
			if j[0]=='description':
				desc_changed= f'''descriptions="{j[2]}"'''
			elif j[0]=='wages':
				wage = j[2].split(' ')[1]
				wage_changed=f'''rate="{wage}"'''
		item = frappe.db.sql(f"select job_titles from `tabJob Titles` where name='{i[2]}'",as_list=1)
		if desc_changed:
				sql=f'''update tabItem set {desc_changed}, {wage_changed} where name="{item[0][0]}"''' if wage_changed else f'''update tabItem set {desc_changed} where name="{item[0][0]}"'''
		elif wage_changed:
				sql=f'''update tabItem set {wage_changed} where name="{item[0][0]}"'''
		if sql :
			frappe.db.sql(sql)
			frappe.db.commit()


@frappe.whitelist()
def staffing_comp_premium(staff_comp_list):
	"""
	The function `staffing_comp_premium` takes a list of staffing company names as input and returns the
	names of other staffing companies that are not in the input list.
	
	:param staff_comp_list: The `staff_comp_list` parameter is a list of staffing company names
	:return: a string that contains the names of companies that have the organization type "Staffing"
	and are not in the given list of staff_comp_list. The names are separated by newlines.
	"""
	try:
		staff_comp_list = json.loads(staff_comp_list)
		if not len(staff_comp_list):
			sql = """
				SELECT name FROM
				(SELECT "Default" AS name FROM `tabCompany`
				UNION
				SELECT name FROM `tabCompany` WHERE organization_type="Staffing") AS subquery
			"""
		elif len(staff_comp_list)==1:
			sql = """
				SELECT name FROM
				(SELECT "Default" AS name FROM `tabCompany`
				UNION
				SELECT name FROM `tabCompany` WHERE organization_type="Staffing") AS subquery WHERE name!="{0}"
			""".format(
				staff_comp_list[0]
			)
		else:
			sql = """
				SELECT name FROM
				(SELECT "Default" AS name FROM `tabCompany`
				UNION
				SELECT name FROM `tabCompany` WHERE organization_type="Staffing") AS subquery WHERE name NOT IN {0}
			""".format(
				tuple(staff_comp_list)
			)
		companies = frappe.db.sql(sql)
		data = [c[0] for c in companies]
		return "\n".join(data)
	except Exception as e:
		print(e, frappe.get_traceback())
