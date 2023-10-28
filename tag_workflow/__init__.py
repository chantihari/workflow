from __future__ import unicode_literals
import boto3
import frappe
from frappe.core.doctype.user.user import User
from frappe.model.document import Document
from frappe.core.doctype.navbar_settings.navbar_settings import NavbarSettings
from erpnext.setup.doctype.employee import employee
from erpnext.setup.doctype.employee.employee import Employee
from erpnext.setup.doctype.company.company import Company
from erpnext.crm.doctype.lead.lead import Lead
from erpnext.projects.doctype.timesheet.timesheet import Timesheet
from frappe.core.doctype.data_import.exporter import Exporter
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip
from frappe import handler
from tag_workflow.utils.whitelisted import upload_file
from tag_workflow.utils.doctype_method import send_password_notification,validate_username, suggest_username, send_login_mail, raise_no_permission_to, validate_duplicate_user_id, validate_abbr, validate_standard_navbar_items, create_contact, update_cost, validate_mandatory_fields, run_post_save_methods, check_if_latest,calculate_total_for_salary_slip_based_on_timesheet,set_time_sheet,salary_slip_validate,update_user_permissions,get_data_as_docs,validate_employee_roles
from tag_workflow.utils.doctype_method import create_task_and_notify_user
import requests, json
from frappe.core.doctype.data_import.exporter import Exporter
from hrms.controllers.employee_boarding_controller import EmployeeBoardingController
from frappe.desk.form import save
from tag_workflow.utils.whitelisted import   savedocs
from frappe.core.doctype.data_import import data_import
from tag_workflow.utils.data_import import download_template
from tag_workflow.utils.timesheet import validate_time_logs

__version__ = '0.0.1'


User.validate_username = validate_username 
User.suggest_username = suggest_username
User.send_login_mail = send_login_mail
User.send_password_notification = send_password_notification
Document.raise_no_permission_to = raise_no_permission_to
Document.run_post_save_methods = run_post_save_methods
Document.check_if_latest = check_if_latest
Employee.validate_duplicate_user_id = validate_duplicate_user_id
Company.validate_abbr = validate_abbr
NavbarSettings.validate_standard_navbar_items =validate_standard_navbar_items
Lead.create_contact = create_contact
Timesheet.update_cost = update_cost
Timesheet.validate_mandatory_fields = validate_mandatory_fields
Timesheet.validate_time_logs= validate_time_logs
SalarySlip.calculate_total_for_salary_slip_based_on_timesheet = calculate_total_for_salary_slip_based_on_timesheet
SalarySlip.set_time_sheet = set_time_sheet
SalarySlip.validate = salary_slip_validate
Employee.update_user_permissions = update_user_permissions
Exporter.get_data_as_docs = get_data_as_docs
employee.validate_employee_role = validate_employee_roles
EmployeeBoardingController.create_task_and_notify_user = create_task_and_notify_user
handler.upload_file = upload_file
save.savedocs = savedocs

data_import.download_template = download_template
def get_key(key):
    try:
        if(frappe.cache().get_value("aws")):
            return frappe.cache().get_value("aws")['tag_keys'][key]
        else:
            try:
                IP_1, IP_2, IP_3, IP_4 = "169.", "254.", "169.", "254"
                reg = "/latest/meta-data/placement/region"
                HTTP = "http"
                URL = HTTP+"://"+IP_1+IP_2+IP_3+IP_4+reg
                region = requests.get(URL)
                client = boto3.client('ssm', region.text)
                response = client.get_parameter(Name='env_details')
                server_details = json.loads(response['Parameter']['Value'])
                frappe.cache().set_value("aws", server_details)
                return server_details['tag_keys'][key]
            except Exception:
                return "Error"
    except Exception:
        return "Error"
