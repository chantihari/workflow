# Copyright (c) 2021, SourceFuse and Contributors
# See license.txt

import unittest
import frappe
from frappe.utils import getdate
from datetime import datetime, timedelta
from frappe.share import add_docshare as add
from tag_workflow.tag_workflow.doctype.job_order.job_order import cancel_job_order

staffing_company = "UT Staffing"
staffing_user = "ut_staffing@yopmail.com"
hiring_company = "UT Hiring"
hiring_user = "ut_hiring@yopmail.com"
address = "1251 Avenue of the Americas, New York, NY, USA"
state = "New York"
city = "New York"
zip = "10020"

industry_type = "Virtual Sports"
job_title = "Gamer"
job_site = "1251 Avenue of the Americas, New York, NY, USA"

Job_Site = "Job Site"
Ind_Type = "Industry Type"
Job_Order = "Job Order"
Claim_Order = "Claim Order"
Assign_Emp = "Assign Employee"

class TestJobOrder(unittest.TestCase):
	def test_ClaimOrder(self):
		self.create_data()

	def create_data(self):
		create_job_industry()
		create_staffing_company()
		create_hiring_company()
		self.create_job_title()
		self.create_job_site()
		self.create_employee()

	def create_job_title(self):
		try:
			if not frappe.db.exists("Item", job_title):
				self.job_title_doc = frappe.get_doc(
					{
						"doctype": "Item",
						"industry": industry_type,
						"company": "UT Hiring",
						"job_titless": job_title,
						"rate": 20,
						"descriptions": job_title,
						"item_code": job_title,
						"item_group": "All Item Groups",
						"stock_uom": "Nos",
					}
				).insert(ignore_permissions=True)
		except Exception as e:
			print(e, "Test Employee Timesheet Report: create_job_title Error")

	def create_job_site(self):
		try:
			if not frappe.db.exists(Job_Site, job_site):
				self.job_site_doc = frappe.get_doc(
					{
						"doctype": Job_Site,
						"job_site": job_site,
						"job_site_name": job_site,
						"company": hiring_company,
						"search_on_maps": 1,
						"address": address,
						"state": state,
						"city": city,
						"zip": zip,
						"job_titles": [
							{
								"industry_type": industry_type,
								"job_titles": job_title,
								"bill_rate": 20,
								"description": job_title,
							}
						],
					}
				).insert(ignore_permissions=True)
		except Exception as e:
			print(e, "Test Job Order: create_job_site Error")
	
	def create_employee(self):
		try:
			frappe.set_user(staffing_user)
			self.employee_doc = frappe.get_doc({
				"doctype": "Employee",
				"email": "emp1@gmail.com",
				"date_of_birth":"2000-01-01",
				"employee_job_category": [{
					"job_category": job_title
				}],
				"company": staffing_company,
				"first_name":"Emp1",
				"last_name":"Test",
				"status": "Active",
				"date_of_joining": "2023-04-06",
				"date_of_retirement": "2133-01-01",
				"employee_name": "Emp1 Test"
			}).save(ignore_permissions=True)
		except Exception as e:
			print(e, frappe.get_traceback(),"Test Job Order: create_employee Error")

	def create_job_order(self, is_direct=0):
		try:
			frappe.set_user(hiring_user)
			self.job_order_doc = frappe.get_doc(
				{
					"doctype": Job_Order,
					"company": hiring_company,
					"from_date": datetime.today().strftime("%Y-%m-%d"),
					"to_date": (datetime.today() + timedelta(days=2)).strftime(
						"%Y-%m-%d"
					),
					"availability": "Everyday",
					"job_site": job_site,
					"staff_company": staffing_company if is_direct else "",
					"multiple_job_titles": [
						{
							"select_job": job_title,
							"category": industry_type,
							"no_of_workers": 5,
							"job_start_time": "09:00:00",
							"estimated_hours_per_day": 8,
						}
					],
					"is_single_share": is_direct,
					"e_signature_full_name": hiring_user,
					"agree_to_contract": 1,
					"company_type": "Non Exclusive",
					"order_status": "Upcoming",
					"claim": staffing_company,
					"staff_org_claimed": staffing_company
				}
			).insert(ignore_permissions=True)
			add(Job_Order, self.job_order_doc.name, hiring_user, read=1, write = 0, share = 0, everyone = 0, flags={"ignore_share_permission": 1})
		except Exception as e:
			print(e, frappe.get_traceback(), "Test Job Order: create_job_order Error")

	def claim_order(self, is_direct=0):
		try:
			frappe.set_user(staffing_user)
			self.claim_order_doc = frappe.get_doc(
				{
					"doctype": Claim_Order,
					"job_order": self.job_order_doc.name,
					"staffing_organization": staffing_company,
					"multiple_job_titles": [
						{
							"job_title": job_title,
							"industry": industry_type,
							"no_of_workers_joborder": 5,
							"no_of_remaining_employee": 5,
							"approved_no_of_workers": 5,
							"staff_claims_no": 5,
							"bill_rate": 20,
							"start_time": "09:00:00",
							"duration": 8,
							"employee_pay_rate": 15,
							"staff_class_code": "Demo123",
							"staff_class_code_rate": 7
						}
					],
					"single_share": is_direct,
					"e_signature": staffing_user,
					"agree_to_contract": 1,
					"claims": staffing_company,
					"staff_org_claimed": staffing_company,
					"bid": 1,
					"job_order_status": self.job_order_doc.order_status
				}
			).insert(ignore_permissions=True)
		except Exception as e:
			print(e, frappe.get_traceback(), "Test Job Order: claim_order Error")
	
	def assign_employee(self):
		try:
			frappe.set_user(hiring_user)
			self.assign_doc = frappe.get_doc({
				"doctype": Assign_Emp,
				"agree_contract": 1,
				"approve_employee_notification": 0,
				"claims_approved": 1,
				"company": staffing_company,
				"e_signature_full_name": staffing_user,
				"employee_details": [{
					"company": staffing_company,
					"distance_radius": "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&ndash;",
					"employee": self.employee_doc.name,
					"employee_name": "Emp1 Test",
					"estimated_hours_per_day": 6,
					"job_category": job_title,
					"job_start_time": "9:00",
					"pay_rate": 15,
				}],
				"hiring_organization": hiring_company,
				"is_single_share": 0,
				"job_location": job_site,
				"job_order": self.job_order_doc.name,
				"job_order_email": staffing_user,
				"multiple_job_title_details":[{
					"approved_workers": 5,
					"bill_rate": 20,
					"category": industry_type,
					"employee_pay_rate": 15,
					"estimated_hours_per_day": 8,
					"job_start_time": "09:00:00",
					"no_of_workers": 5,
					"staff_class_code_rate": 0,
					"select_job": job_title
				}],
				"no_of_employee_required": 5,
				"previous_worker": 0,
				"job_order_status": self.job_order_doc.order_status
			}).insert(ignore_permissions=True)
		except Exception as e:
			print(e, frappe.get_traceback(), "Test Job Order: assign_employee Error")
		
	def test_cancel_job_order(self):
		try:
			self.create_employee()
			self.create_job_order()
			self.claim_order()
			self.assign_employee()
			frappe.set_user(hiring_user)
			cancel_job_order(self.job_order_doc.name, hiring_user, self.job_order_doc.staff_org_claimed)
			frappe.db.commit()
			self.assertEqual('Canceled', frappe.db.get_value(Job_Order, self.job_order_doc.name, "order_status"))
			self.assertEqual(datetime.today().date(), frappe.db.get_value(Job_Order, self.job_order_doc.name, "cancellation_date"))
			self.assertEqual('Canceled', frappe.db.get_value(Claim_Order, self.claim_order_doc.name, "job_order_status"))
			self.assertEqual('Canceled', frappe.db.get_value(Assign_Emp, self.assign_doc.name, "job_order_status"))
			self.delete_data()
		except Exception as e:
			print(e, "Test Job Order: test_cancel_job_order Error")

	def delete_data(self):
		try:
			frappe.set_user("Administrator")
			frappe.delete_doc(Assign_Emp, self.assign_doc.name)
			frappe.delete_doc(Claim_Order, self.claim_order_doc.name)
			frappe.delete_doc(Job_Order, self.job_order_doc.name)
		except Exception as e:
			print(e, "Test Job Order: delete_data Error")


def create_job_industry():
    try:
        if not frappe.db.exists(Ind_Type, industry_type):
            frappe.get_doc({"doctype": Ind_Type, "industry": industry_type}).insert(
                ignore_permissions=True
            )
    except Exception as e:
        print(e, "Test Job Order: create_job_industry Error")


def create_staffing_company():
    try:
        if not frappe.db.exists("Company", staffing_company):
            frappe.get_doc(
                {
                    "doctype": "Company",
                    "company_name": staffing_company,
                    "organization_type": "Staffing",
                    "fein": "987654321",
                    "default_currency": "USD",
                    "title": staffing_company,
                    "primary_language": "English",
                    "contact_name": "SA UT_Staffing",
                    "phone_no": "+19034709848",
                    "email": staffing_user,
                    "accounts_receivable_name": "SA UT_Staffing",
                    "accounts_receivable_rep_email": staffing_user,
                    "accounts_receivable_phone_number": "+19034709848",
                    "set_primary_contact_as_account_receivable_contact": 1,
                    "search_on_maps": 1,
                    "complete_address": address,
                    "state": state,
                    "city": city,
                    "zip": zip,
                }
            ).insert()
        else:
            frappe.db.set_value(
                "Company", staffing_company, "make_organization_inactive", 0
            )
        if not frappe.db.exists("User", staffing_user):
            frappe.get_doc(
                {
                    "doctype": "User",
                    "organization_type": "Staffing",
                    "email": staffing_user,
                    "first_name": "SA",
                    "last_name": "UT_Staffing",
                    "tag_user_type": "Staffing Admin",
                    "company": staffing_company,
                    "date_of_joining": getdate(),
                }
            ).insert(ignore_permissions=True)
    except Exception as e:
        print(e, "Test Job Order: create_staffing_company Error")


def create_hiring_company():
    try:
        if not frappe.db.exists("Company", hiring_company):
            frappe.get_doc(
                {
                    "doctype": "Company",
                    "company_name": hiring_company,
                    "organization_type": "Hiring",
                    "accounts_payable_contact_name": hiring_user,
                    "fein": "987654321",
                    "title": hiring_company,
                    "accounts_payable_email": hiring_user,
                    "accounts_payable_phone_number": "+1903-539-7085",
                    "contact_name": "HA UT_Hiring",
                    "phone_no": "+1903-539-7085",
                    "email": hiring_user,
                    "search_on_maps": 1,
                    "complete_address": address,
                    "state": state,
                    "city": city,
                    "zip": zip,
                    "default_currency": "USD",
                    "primary_language": "English",
                    "industry_type": [{"industry_type": industry_type}],
                }
            ).insert(ignore_permissions=True)
        else:
            frappe.db.set_value(
                "Company", staffing_company, "make_organization_inactive", 0
            )

        if not frappe.db.exists("User", hiring_user):
            frappe.get_doc(
                {
                    "doctype": "User",
                    "organization_type": "Hiring",
                    "email": hiring_user,
                    "first_name": "HA",
                    "last_name": "UT_Hiring",
                    "tag_user_type": "Hiring Admin",
                    "company": hiring_company,
                    "date_of_joining": getdate(),
                }
            ).insert(ignore_permissions=True)
    except Exception as e:
        print(e, "Test Job Order: create_hiring_company Error")

