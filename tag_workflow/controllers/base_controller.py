'''
        Developer: Sahil
        Email: sahil19893@gmail.com
'''

import frappe, json
from frappe import _, msgprint, throw

MASTER = ["Company", "User", "Item"]
CRM = ["Lead"]
PROJECT = ["Timesheet"]

def validate_controller(doc, method):
    doctype = doc.meta.get("name")

    try:
        if doctype in MASTER:
            from tag_workflow.controllers.master_controller import MasterController 
            if method == "validate":
                MasterController(doc, doctype, method).validate_master()
            elif method == "on_trash":
                MasterController(doc, doctype, method).validate_trash()
            elif method == "on_update":
                MasterController(doc, doctype, method).apply_user_permissions()
        elif doctype in CRM:
            from tag_workflow.controllers.crm_controller import CRMController
            if method == "validate":
                CRMController(doc, doctype, method).validate_crm()
        elif doctype in PROJECT:
            from tag_workflow.controllers.project_controller import ProjectController
            if method == "validate":
                ProjectController(doc, doctype, method).validate_project()
    except Exception as e:
        frappe.throw(_(" "))
        print(e)
        print("----"*10)
        print("----"*10)
        frappe.db.rollback()


'''
	Base controller for validation purpose
'''

class BaseController():
    def __init__(self, doc, doctype, method):
        self.dt = doctype
        self.doc = doc
        self.method = method

