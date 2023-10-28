# Copyright (c) 2022, SourceFuse and Contributors
# See license.txt

import frappe
import unittest
from frappe.utils import getdate
staffing_company = 'UT_Sahil_Staffing'
staffing_user = 'st_utsahil@yopmail.com'
certificate_name = "TEST- test certificate"
doc ='Certificate and Endorsement'


class TestCertificateandEndorsement(unittest.TestCase):

	def test_certificate_and_endorsement(self):
		self.prepare_test_data()



	def prepare_test_data(self):
		self.create_company()
		self.create_certificate_and_endorsement()
		self.delete_records()

	def create_company(self):
		try:
			if not frappe.db.exists('Company', staffing_company):
				frappe.get_doc({
					'doctype': 'Company',
					'company_name': staffing_company,
					'organization_type': 'Staffing',
					'fein': '987654321',
					'default_currency': 'USD',
					'title': staffing_company,
					'primary_language': 'en',
					'contact_name': 'SA UT AyushiStaffing',
					'phone_no': '+19034709848',
					'email': staffing_user,
					'accounts_receivable_name': 'SA UT Sahil_Mudaliar',
					'accounts_receivable_rep_email': staffing_user,
					'accounts_receivable_phone_number': '+19034709848',
					'set_primary_contact_as_account_receivable_contact': 1,
					'enter_manually': 1,
					'address': '2204 Pickens Way',
					'state': 'Texas',
					'city': 'Longview',
					'zip': '75601',
				}).insert()
			else:
				frappe.db.set_value('Company', staffing_company, 'make_organization_inactive', 0)
			if not frappe.db.exists('User', staffing_user):
				self.user = frappe.get_doc({
					'doctype': 'User',
					'organization_type': 'Staffing',
					'email': staffing_user,
					'first_name': 'SA',
					'last_name': 'UT SahilStaffing',
					'tag_user_type': 'Staffing Admin',
					'company': staffing_company,
					'date_of_joining': getdate()
				}).insert(ignore_permissions=True)
		except Exception as e:
			
			frappe.log_error(e, 'Test CertificateandEndorsement')

	def create_certificate_and_endorsement(self):
		try:
			if not frappe.db.exists(doc,certificate_name):
				self.certificate_doc = frappe.get_doc({
                    'doctype': 'Certificate and Endorsement',
                    'certificate_types': certificate_name,
					'certification_name':certificate_name,
					'attribute':"TEST"
                }).insert()
			self.assertEqual(certificate_name,self.certificate_doc.certificate_types)
			self.assertEqual(certificate_name,self.certificate_doc.certification_name)
			self.assertEqual("TEST",self.certificate_doc.attribute)
		
		except Exception as e:
			frappe.log_error(e, 'Test CertificateandEndorsement creating certificate')

	def delete_records(self):
		try:
			frappe.delete_doc("User", self.certificate_doc.name)
			frappe.db.sql("""delete from `tabUser` where name = 'st_utsahil@yopmail.com'""")
		except Exception as e:
			frappe.log_error(e, 'Test CertificateandEndorsement deleting records')


