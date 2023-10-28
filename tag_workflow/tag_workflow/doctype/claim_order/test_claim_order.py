# Copyright (c) 2022, SourceFuse and Contributors
# See license.txt


import unittest
import frappe
import json
from frappe.utils import getdate
from datetime import datetime, timedelta
from .claim_order import (
    auto_claims_approves,
    get_pay_rate_class_code,
    create_pay_rate_new,
    create_staff_comp_code_new,
    get_or_create_jobtitle_new,
    modify_heads,
    get_description
)

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
desc = 'Elevate gaming experiences through insights and expertise, ensuring seamless gameplay and enjoyment for all users.'
job_site = "1251 Avenue of the Americas, New York, NY, USA"

Job_Site = "Job Site"
Ind_Type = "Industry Type"


class TestClaimOrder(unittest.TestCase):
    def test_ClaimOrder(self):
        self.create_data()

    def create_data(self):
        create_job_industry()
        create_staffing_company()
        create_hiring_company()
        self.create_job_title()
        self.create_job_site()

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
                        "descriptions": desc,
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
                                "description": desc,
                            }
                        ],
                    }
                ).insert(ignore_permissions=True)
        except Exception as e:
            print(e, "Test Claim Order: create_job_site Error")

    def create_job_order(self, is_direct=0):
        try:
            frappe.set_user(hiring_user)
            self.job_order_doc = frappe.get_doc(
                {
                    "doctype": "Job Order",
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
                }
            ).insert(ignore_permissions=True)
        except Exception as e:
            print(e, frappe.get_traceback(), "Test Claim Order: create_job_order Error")

    def claim_order(self, is_direct=0):
        try:
            frappe.set_user(staffing_user)
            self.claim_order_doc = frappe.get_doc(
                {
                    "doctype": "Claim Order",
                    "job_order": self.job_order_doc.name,
                    "staffing_organization": staffing_company,
                    "multiple_job_titles": [
                        {
                            "job_title": job_title,
                            "industry": industry_type,
                            "no_of_workers_joborder": 5,
                            "no_of_remaining_employee": 5,
                            "approved_no_of_workers": 0,
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
                }
            ).insert(ignore_permissions=True)
        except Exception as e:
            print(e, frappe.get_traceback(), "Test Claim Order: claim_order Error")

    def test_auto_claims_approves(self):
        try:
            self.create_job_order(1)
            self.claim_order(1)
            job_order = {
                "claim": self.job_order_doc.claim,
                "staff_org_claimed": self.job_order_doc.staff_org_claimed,
                "company": self.job_order_doc.company,
                "name": self.job_order_doc.name,
            }
            res = auto_claims_approves(
                staffing_company, json.dumps(job_order), self.claim_order_doc.name
            )
            self.assertEqual(1, res, "Claim Approved for direct order")
            self.delete_data()
        except Exception as e:
            print(
                e,
                frappe.get_traceback(),
                "Test Claim Order: test_auto_claims_approves Error",
            )

    def test_get_pay_rate_class_code(self):
        try:
            self.create_job_order()
            self.claim_order()
            job_order = {
                "job_site": self.job_order_doc.job_site,
                "multiple_job_titles": [
                    {
                        "select_job": job_title,
                        "category": industry_type,
                    }
                ],
                "company": self.job_order_doc.company,
            }
            create_pay_rate_new(
                hiring_company,
                job_title,
                job_site,
                staffing_company,
                self.claim_order_doc.multiple_job_titles[0],
            )
            create_staff_comp_code_new(
                self.claim_order_doc.multiple_job_titles[0],
                job_title,
                job_site,
                industry_type,
                staffing_company,
            )
            res = get_pay_rate_class_code(json.dumps(job_order), staffing_company)
            self.assertEqual(isinstance(res, dict), True, "Result is a list")
            self.assertEqual(
                res,
                {job_title: {"comp_code": "Demo123", "rate": 7, "emp_pay_rate": 15}},
            )
            self.delete_data()
        except Exception as e:
            print(e, "Test Claim Order: test_get_pay_rate_class_code Error")

    def test_create_pay_rate_new(self):
        try:
            self.create_job_order()
            self.claim_order()
            frappe.set_user(staffing_user)
            self.claim_order_doc.multiple_job_titles[0].employee_pay_rate = 10
            self.claim_order_doc.save()
            create_pay_rate_new(
                hiring_company,
                job_title,
                job_site,
                staffing_company,
                self.claim_order_doc.multiple_job_titles[0],
            )
            pay_rate = frappe.db.get_value(
                "Employee Pay Rate",
                {
                    "hiring_company": hiring_company,
                    "job_title": job_title,
                    "job_site": job_site,
                    "staffing_company": staffing_company,
                },
                ["employee_pay_rate"],
            )
            self.assertEqual(pay_rate, 10, "Pay Rate Updated")
            self.delete_data()
        except Exception as e:
            print(e, "Test Claim Order: test_create_pay_rate_new Error")

    def test_create_staff_comp_code_new(self):
        try:
            self.create_job_order()
            self.claim_order()
            frappe.set_user(staffing_user)
            self.claim_order_doc.multiple_job_titles[0].staff_class_code = "Demo12345"
            self.claim_order_doc.multiple_job_titles[0].staff_class_code_rate = 5
            self.claim_order_doc.save()
            create_staff_comp_code_new(
                self.claim_order_doc.multiple_job_titles[0],
                job_title,
                job_site,
                industry_type,
                staffing_company,
            )
            frappe.db.commit()
            comp_code = frappe.db.sql(
                'select SCC.name from `tabStaffing Comp Code` as SCC inner join `tabClass Code` as CC on SCC.name=CC.parent where job_industry="{0}" and CC.state="{1}" and staffing_company="{2}" and job_title like "{3}%" '.format(
                    industry_type, state, staffing_company, job_title
                ),
                as_dict=1,
            )
            if len(comp_code) > 0:
                data = frappe.db.sql(
                    """ select class_code,rate from `tabClass Code` where parent="{0}" and state="{1}" """.format(
                        comp_code[0].name, state
                    ),
                    as_dict=1,
                )
                class_code = data[0].class_code
                code_rate = data[0].rate
                self.assertEqual(class_code, "Demo12345", "Class Code Updated")
                self.assertEqual(code_rate, 5, "Class Code Rate Updated")
            self.delete_data()
        except Exception as e:
            print(e, "Test Claim Order: test_create_staff_comp_code_new Error")

    def test_get_or_create_jobtitle_new(self):
        try:
            self.create_job_order()
            self.claim_order()
            get_or_create_jobtitle_new(
                job_title,
                staffing_company,
                hiring_company,
                job_site,
                self.job_order_doc,
                self.claim_order_doc.multiple_job_titles[0],
                industry_type,
            )
            staffing_job_title = frappe.db.get_value(
                "Item",
                {"name": ["like", f"{job_title}%"], "company": staffing_company},
                ["name"],
            )
            if staffing_job_title:
                self.assertTrue(
                    len(staffing_job_title) > 0, "Staffing Job Title Exists"
                )

            sql = f"""
            SELECT job_pay_rate FROM `tabPay Rates` WHERE staffing_company="{staffing_company}"
            AND parent="{staffing_job_title}" and hiring_company="{hiring_company}" and job_site="{job_site}"
            """
            pay_rate = frappe.db.sql(sql, as_list=1)
            if pay_rate:
                self.assertEqual(pay_rate[0][0], 15)
            self.delete_data()
        except Exception as e:
            print(e, "Test Claim Order: test_get_or_create_jobtitle_new Error")

    def test_modify_heads(self):
        try:
            self.create_job_order()
            self.claim_order()
            frappe.set_user(hiring_user)
            for row in self.claim_order_doc.multiple_job_titles:
                row.approved_no_of_workers = 3
            self.claim_order_doc.save(ignore_permissions = True)
            res1, res2, _res3 = modify_heads(self.job_order_doc.name)
            start_time = datetime.strptime("09:00:00", "%H:%M:%S")
            claims = [{
                'name': self.claim_order_doc.name, 
                'job_order': self.job_order_doc.name,
                'staffing_organization': staffing_company,
                'notes': None,
                'job_title': job_title,
                'industry': industry_type,
                'no_of_workers_joborder': 5,
                'no_of_remaining_employee': 5,
                'approved_no_of_workers': 3,
                'staff_claims_no': 5,
                'start_time': timedelta(hours=start_time.hour, minutes=start_time.minute, seconds=start_time.second),
                'duration': 8.0,
                'bill_rate': 20.0,
                'worker_filled': 0,
                'avg_rate': 0
            }]
            job = (
                datetime.today().date(),
                datetime.today().date() + timedelta(days=2),
                0,
                0
            )
            self.assertEqual(res1, claims)
            self.assertEqual(res2[0], job)
            self.delete_data()

        except Exception as e:
            print(e, frappe.get_traceback(), "Test Claim Order: test_modify_heads Error")
    
    def test_get_description(self):
        try:
            self.create_job_order()
            self.claim_order()
            description = get_description(self.job_order_doc.name, job_title)
            self.assertEqual(desc, description)
            self.delete_data()
        except Exception as e:
            print(e,"Test Claim Order: test_get_description Error")

    def delete_data(self):
        try:
            frappe.set_user("Administrator")
            frappe.delete_doc("Claim Order", self.claim_order_doc.name)
            frappe.delete_doc("Job Order", self.job_order_doc.name)
        except Exception as e:
            print(e, "Test Claim Order: delete_data Error")


def create_job_industry():
    try:
        if not frappe.db.exists(Ind_Type, industry_type):
            frappe.get_doc({"doctype": Ind_Type, "industry": industry_type}).insert(
                ignore_permissions=True
            )
    except Exception as e:
        print(e, "Test Claim Order: create_job_industry Error")


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
        print(e, "Test Claim Order: create_staffing_company Error")


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
        print(e, "Test Claim Order: create_hiring_company Error")
