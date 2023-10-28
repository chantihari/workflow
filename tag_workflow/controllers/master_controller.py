'''
	Added by Sahil
	Email sahil19893@Gmail.com
'''

import frappe
from frappe.share import add_docshare as add
from frappe import _
from tag_workflow.controllers import base_controller
from frappe import enqueue
from requests_oauthlib import OAuth2Session

GROUP = "All Customer Groups"
TERRITORY = "All Territories"
PERMISSION = "User Permission"
EMP = "Employee"
COM = "Company"
JOB = "Job Order"
USR = "User"
STANDARD = ["Administrator", "Guest"]
HIR = ["Hiring", "Exclusive Hiring"]
HIR_TYPE = ["Hiring Admin", "Hiring User"]
STF_TYPE = ["Staffing Admin", "Staffing User"]
#--------------------------#

class MasterController(base_controller.BaseController):
    def validate_master(self):
        self.update_master_data()

    def update_master_data(self):
        if(self.dt == COM):
            self.check_mandatory_field()
            if not frappe.db.exists("Customer", {"name": self.doc.name}): 
                customer = frappe.get_doc(dict(doctype="Customer", customer_name=self.doc.name, customer_type="Company", territory=TERRITORY, customer_group=GROUP))
                customer.insert(ignore_permissions=True)
            client_id_decrypt=client_id_values(self.doc.client_id,self.doc)
            if not self.doc.authorization_url and client_id_decrypt and self.doc.redirect_url and self.doc.quickbooks_company_id:
                self.oauth = OAuth2Session(client_id=client_id_decrypt, redirect_uri=self.doc.redirect_url, scope=self.doc.scope)
                self.doc.authorization_url = self.oauth.authorization_url(self.doc.authorization_endpoint)[0]

        elif(self.dt == "User"):
            if(frappe.session.user not in STANDARD and (not self.doc.tag_user_type or not self.doc.organization_type)):
                frappe.msgprint(_("Please select <b>Company Type</b> and <b>TAG User Type</b> before saving the User."))
            self.check_profile()
        elif(self.dt == "Item"):
            self.check_activity_type()

    def check_mandatory_field(self):
        if not frappe.db.exists("Territory", {"name": TERRITORY}):
            tre_doc = frappe.get_doc(dict(doctype="Territory", territory_name=TERRITORY, is_group=0))
            tre_doc.save(ignore_permissions=True)

        if not frappe.db.exists("Customer Group", {"name": GROUP}):
            group_doc = frappe.get_doc(dict(doctype="Customer Group", customer_group_name=GROUP, is_group=1))
            group_doc.save(ignore_permissions=True)

    def check_activity_type(self):
        if not frappe.db.exists("Activity Type", {"name": self.doc.name}):
            item = frappe.get_doc(dict(doctype = "Activity Type", activity_type = self.doc.name))
            item.save(ignore_permissions=True)

    def validate_trash(self):
        if(self.dt == "Company"):
            frappe.throw(_("User is not allowed to delete the organisation: <b>{0}</b>").format(self.doc.name))

    def apply_user_permissions(self):
        if(self.dt == "User" and self.doc.enabled):
            check_employee(self.doc.email, self.doc.first_name, self.doc.company, self.doc.last_name, self.doc.gender, self.doc.birth_date, self.doc.date_of_joining, self.doc.organization_type)

    def check_profile(self):
        if((self.doc.organization_type in HIR and self.doc.tag_user_type not in HIR_TYPE) or (self.doc.organization_type == "Staffing" and self.doc.tag_user_type not in STF_TYPE)):
            frappe.throw(_("Incorrect value for <b>User Type</b> or <b>Company Type</b>"))


#-----------data update--------------#
def update_user_info(company, make_organization_inactive):
    try:
        if(make_organization_inactive == 1):
            user = """ select name, enabled from `tabUser` where company="{0}" """.format(company)
            user_list = frappe.db.sql(user, as_dict=1)
            for u in user_list:
                if(u.enabled == 0 and len(frappe.db.get_list("Employee", {"user_id": u.name}, "name")) == 1):
                    frappe.sessions.clear_sessions(user=u.name, keep_current=False, device=None, force=True)
    except Exception as e:
        frappe.log_error(e, "User disabled")

@frappe.whitelist()
def make_update_comp_perm(docname):
    try:
        doc = frappe.get_doc(COM, docname)
        if doc.organization_type == "Exclusive Hiring":
            user_list = get_user_list(doc.parent_staffing)
            enqueue("tag_workflow.controllers.master_controller.update_exclusive_perm", now=True, user_list=user_list, company=doc.name)
        elif doc.organization_type != "Staffing":
            user_list = get_user_list()
            enqueue("tag_workflow.controllers.master_controller.update_job_order_permission", now=True, user_list=user_list, company=doc.name)
        update_user_info(doc.name, doc.make_organization_inactive)
    except Exception as e:
        frappe.log_error(e, "Quotation and Job Order Permission")


@frappe.whitelist()
def check_item_group():
    try:
        item_group = "Item Group"
        if not frappe.db.exists(item_group, {"name": "Services"}):
            group = frappe.get_doc(dict(doctype=item_group, item_group_name="Services", is_group=0))
            group.save(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(e, item_group)


#-----------after company insert update-------------#
def get_user_list(company=None):
    if company:
        sql = """ select name from `tabUser` where enabled = 1 and tag_user_type in ("Staffing Admin", "Staffing User") and company = '{0}' """.format(company)
    else:
        sql = """ select name from `tabUser` where enabled = 1 and tag_user_type in ("Staffing Admin", "Staffing User")"""

    return frappe.db.sql(sql, as_dict=1)


def update_job_order_permission(user_list, company):
    try:
        for user in user_list:
            if not frappe.db.exists(PERMISSION,{"user": user['name'],"allow": COM,"applicable_for": JOB,"for_value": company,"apply_to_all_doctypes":0}):
                perm_doc = frappe.get_doc(dict(doctype=PERMISSION, user=user['name'], allow=COM, for_value=company, applicable_for=JOB, apply_to_all_doctypes=0))
                perm_doc.save(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(e, "Quotation and Job Order Permission")

def update_exclusive_perm(user_list, company):
    try:
        for user in user_list:
            if not frappe.db.exists(PERMISSION, {"user": user['name'], "allow":COM, "for_value": company, "apply_to_all_doctypes": 1}):
                add(COM, company, user['name'], write=1, read=1, share=0, everyone=0, notify=0, flags={"ignore_share_permission": 1})
                perm = frappe.get_doc(dict(doctype=PERMISSION, user=user['name'], allow=COM, for_value=company, apply_to_all_doctypes = 1))
                perm.save(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(e, "Exclusive Permission")


# remove message on user creation
def make_employee_permission(user, company):
    try:
        if not frappe.db.exists(PERMISSION,{"user": user,"allow": COM,"apply_to_all_doctypes":1, "for_value": company}):
            perm_doc = frappe.get_doc(dict(doctype=PERMISSION,user=user, allow=COM, for_value=company, apply_to_all_doctypes=1))
            perm_doc.save(ignore_permissions=True)
            print("permissions updated")
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(e, PERMISSION)

# user permission for order and exclusive
def new_user_job_perm(user):
    try:
        user_list = [{"name": user}]
        company = frappe.db.get_all(COM, {"organization_type": "Hiring"}, "name")
        for com in company:
            update_job_order_permission(user_list, com['name'])
    except Exception as e:
        frappe.log_error(e, "new_user_job_perm")

def user_exclusive_perm(user, company, organization_type=None):
    try:
        if not organization_type:
            organization_type = frappe.db.get_value("User", user, "organization_type")

        if(organization_type == "Staffing"):
            new_user_job_perm(user)
            exclusive = frappe.get_all("Company", {"parent_staffing": company}, "name")
            for ex in exclusive:
                update_exclusive_perm([{"name": user}], ex.name)

        sql = """ delete from `tabUser Permission` where user = "{0}" and allow = "Employee" """.format(user)
        frappe.db.sql(sql)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(e, "user_exclusive_permission")

def remove_tag_permission(user, emp, company):
    try:
        sql = """ select name from `tabUser Permission` where user = '{0}' and (for_value in ('{1}', '{2}')) """.format(user, emp, company)
        perms = frappe.db.sql(sql, as_dict=1)
        for per in perms:
            frappe.delete_doc(PERMISSION, per.name, force=1)
    except Exception as e:
        frappe.log_error(e, "remove_tag_permission")

@frappe.whitelist()
def check_employee(name, first_name, company, last_name=None, gender=None, date_of_birth=None, date_of_joining=None, organization_type=None):
    try:
        if not date_of_birth:
            date_of_birth = "1970-01-01"

        if(name in STANDARD): return

        users = [{"name": name, "company": company}]
        if not frappe.db.exists(EMP, {"user_id": name, "company": company}):
            emp = frappe.get_doc(dict(doctype=EMP, first_name=first_name, last_name=last_name, company=company, status="Active", gender=gender, date_of_birth=date_of_birth, date_of_joining=date_of_joining, user_id=name, create_user_permission=1, email=name))
            emp.save(ignore_permissions=True)
        else:
            emp = frappe.get_doc(EMP, {"user_id": name, "company": company})


        if(organization_type != "TAG"):
            enqueue("tag_workflow.controllers.master_controller.make_employee_permission", user=name, company=company)
            enqueue("tag_workflow.controllers.master_controller.user_exclusive_perm", user=name, company=company, organization_type=None)
            enqueue("tag_workflow.utils.trigger_session.share_company_with_user", users=users)
            enqueue("tag_workflow.controllers.master_controller.share_old_docs", queue='default', user=name, company=company, company_type=organization_type)
            enqueue("tag_workflow.controllers.master_controller.new_staff_company", now=True, user=name, company=company, company_type=organization_type)
        elif(organization_type == "TAG"):
            remove_tag_permission(name, emp.name, company)
    except Exception as e:
        frappe.msgprint(e)
        frappe.db.rollback()

@frappe.whitelist()
def multi_company_setup(user, company):
    user = frappe.get_doc(USR, user)
    company = company.split(",")
    for com in company:
        check_employee(user.name, user.first_name, com, user.last_name, user.gender, user.birth_date, user.date_of_joining, user.organization_type)

@frappe.whitelist()
def user_company_setup(user,company_name):
    user = frappe.get_doc(USR, user)
    user.append("assign_multiple_company",{"assign_multiple_company":company_name})
    user.save(ignore_permissions=True)
    
@frappe.whitelist()
def addjob_order(current_user,company):
    try:
        sql = """ select * from `tabUser` where company = '{0}' ORDER BY creation """.format(company)
        user_list = frappe.db.sql(sql,as_dict=1)
        if user_list:
            sql1 = """ select share_name from `tabDocShare` where user = '{0}' and share_doctype ='Job Order' """.format(user_list[0]['name'])
            job_list = frappe.db.sql(sql1,  as_dict=1)

            sql1 = """ select share_name from `tabDocShare` where user = '{0}' and share_doctype ='Timesheet' """.format(user_list[0]['name'])
            timesheet_list = frappe.db.sql(sql1,  as_dict=1)

            sql = """ select name from `tabSales Invoice` where company = '{0}' """.format(company)
            invoice_list = frappe.db.sql(sql, as_dict=1)
            share_file_list(job_list,timesheet_list,invoice_list,current_user)
    except Exception as e:
        frappe.error_log(e, "old Job Order ")
        frappe.throw(e) 
def share_file_list(job_list,timesheet_list,invoice_list,current_user):
    for job in job_list:
        x=f'select * from `tabJob Order` where name ="{job.share_name}"'
        d=frappe.db.sql(x,as_list=1)
        if(len(d)>0):
            add(JOB, job.share_name, user=current_user, share= 1,read=1,write=1,flags={"ignore_share_permission": 1})
    for time in timesheet_list:
        x=f'select * from `tabTimesheet` where name ="{time.share_name}"'
        d=frappe.db.sql(x,as_list=1)
        if(len(d)>0):
            add("Timesheet", time.share_name, user=current_user, share= 1,read=1,write=1,submit=1,flags={"ignore_share_permission": 1})
    for invoice in invoice_list:
        x=f'select * from `tabSales Invoice` where name ="{invoice.name}"'
        d=frappe.db.sql(x,as_list=1)
        if(len(d)>0):
            add("Sales Invoice", invoice.name, user=current_user, share= 1,read=1,write=1,flags={"ignore_share_permission": 1})


def share_old_docs(user, company, company_type):
    try:
        data = []
        if(company_type == "Staffing"):
            sql = f'''
                select DISTINCT share_name as docname, share_doctype as doctype from `tabDocShare` where user in (select name from `tabUser` where company = "{company}") and share_doctype in ("Job Order", "Timesheet")
                UNION
                select name as docname, "Job Order" as doctype from `tabJob Order` where company in (select name from `tabCompany` where parent_staffing = "{company}")
            '''
            data = frappe.db.sql(sql, as_dict=1)
        elif(company_type in ["Hiring", HIR[1]]):
            data = frappe.db.sql(""" select DISTINCT share_name as docname, share_doctype as doctype from `tabDocShare` where user in (select name from `tabUser` where company = %s) and share_doctype in ("Claim Order", "Assign Employee", "Sales Invoice") """,company, as_dict=1)


        for d in data:
            try:
                if not frappe.db.exists("DocShare", {"user": user, "share_name": d['docname'], "read": 1}) and frappe.db.exists(d['doctype'], d['docname']):
                    add(d['doctype'], d['docname'], user=user, share= 1, read=1, write=0, flags={"ignore_share_permission": 1})
            except Exception as e:
                frappe.error_log(e, "share error")
                continue
        frappe.db.commit()
    except Exception as e:
        frappe.error_log(e, "share_old_docs")
def new_staff_company(user,company,company_type):
    try:
        if company_type=='Staffing':
            only_single_emp=frappe.db.sql('select count(name) from `tabUser` where company="{0}"'.format(company),as_list=1)
            if(only_single_emp[0][0]==1):
                sql = '''select name from `tabJob Order` where (claim is null or claim="")  and order_status!="Completed" and (resumes_required=0 or resumes_required=1) and staff_company is null
                UNION
                select distinct job_order from `tabClaim Order` where job_order in (select name from `tabJob Order` where order_status!="Completed" and resumes_required=0 and staff_company is null)
                UNION
                select name from `tabJob Order` where order_status!="Completed" and staff_company is null and resumes_required=1 and total_no_of_workers!=total_workers_filled'''
                data=frappe.db.sql(sql, as_list=1)
                new_staff_old_order(data,user)
        frappe.db.commit()
    except Exception as e:
        frappe.error_log(e, "New Staffing Sharing")

def new_staff_old_order(data,user):
    for d in data:
        try:
            if not frappe.db.exists("DocShare", {"user": user, "share_name": d[0], "read": 1}) and frappe.db.exists('Job Order', d[0]):
                add('Job Order', d[0], user=user, share= 1, read=1, write=0, flags={"ignore_share_permission": True})
        except Exception as e:
            frappe.error_log(e, "share error")
            continue
def client_id_values(client_id,doc):
    if client_id != None and len(client_id)>0:
        client_id_decrypt = doc.get_password('client_id')
    else:
        client_id_decrypt = None
    return client_id_decrypt
