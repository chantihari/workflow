from __future__ import unicode_literals
import frappe

def execute():
    """old company api key encryption"""
    records = frappe.db.get_list('Company', filters={"organization_type": "Staffing", "jazzhr_api_key": ("NOT IN", ("null", "undefined", "None", ""))}, fields=["name"])
    for r in records:
        try:
            company = frappe.get_doc("Company", r['name'])
            if(company.search_on_maps == 1):
                company.enter_manually = 1
                company.search_on_maps = 0
            else:
                company.search_on_maps = 1
                company.enter_manually = 0
            company.save(ignore_permissions=True)
        except Exception as e:
            print(e)
            continue

