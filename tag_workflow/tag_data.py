import frappe
from frappe import _
from geopy.geocoders import Nominatim
from frappe.share import add_docshare as add
from frappe import enqueue
from tag_workflow.utils.notification import (
    sendmail,
    make_system_notification,
    get_mail_list,
)
from frappe.utils import date_diff
import json
import datetime
import requests, time
from frappe.utils.data import getdate
from frappe.model.mapper import get_mapped_doc
from frappe.core.doctype.user.user import User
from .utils.notification import ses_email_send
import pdfkit
from io import BytesIO
from PyPDF2 import PdfReader, PdfWriter
from frappe.utils.pdf import get_file_data_from_writer
from pytz import timezone
from datetime import timedelta
import ast

tag_gmap_key = frappe.get_site_config().tag_gmap_key or ""
GOOGLE_API_URL = (
    f"https://maps.googleapis.com/maps/api/geocode/json?key={tag_gmap_key}&address="
)
tagAdmin = "TAG Admin"
jobOrder = "Job Order"
claimOrder = "Claim Order"
salesInvoice = "Sales Invoice"
approvalRequest = "Approval Request"
assignEmployees = "Assign Employee"
activityType = "Activity Type"
NOASS = "No Access"
exclusive_hiring = "Exclusive Hiring"
non_exlusive = "Non Exclusive"
emp_onb = "Employee Onboarding"
emp_onb_temp = "Employee Onboarding Template"
TIMEZONE = "US/Eastern"
INSUFF_PERM = "Insufficient Permission for User "

site = frappe.utils.get_url().split("/")
sitename = site[0] + "//" + site[2]
response = "Not Found"
date_format = "%m-%d-%Y"


@frappe.whitelist(allow_guest=False)
def company_details(company_name=None):
    if frappe.session.user != "Administrator":
        comp_data = frappe.get_doc("Company", company_name)
        sql = """ select fein as "FEIN", title as "Title", address as "Address", city as "City", state as "State", zip as "Zip", contact_name as "Contact Name", email as "Contact Email", phone_no as "Company Phone No", primary_language as "Primary Language", accounts_payable_contact_name as "Accounts Payable Contact Name", accounts_payable_email as "Accounts Payable Email", accounts_payable_phone_number as "Accounts Payable Phone Number" from `tabCompany` where name="{}" """.format(
            company_name
        )
        required_field = []
        company_info = frappe.db.sql(sql, as_dict=1)
        if len(comp_data.industry_type) == 0:
            required_field.append("Industry")
        for i in company_info[0]:
            if company_info[0][i] is None or len(company_info[0][i]) == 0:
                required_field.append(i)
        if len(required_field):
            return required_field
        else:
            return "success"


@frappe.whitelist(allow_guest=False)
def update_timesheet(job_order_detail):
    sql = """select select_job,from_date,to_date,per_hour,flat_rate,estimated_hours_per_day from `tabJob Order` where name = "{}" """.format(
        job_order_detail
    )
    value = frappe.db.sql(sql, as_dict=1)
    time_differnce = date_diff(value[0]["to_date"], value[0]["from_date"])
    per_person_rate = value[0]["per_hour"]
    flat_rate = value[0]["flat_rate"]
    hours = time_differnce * value[0]["estimated_hours_per_day"]
    extra_hours = (hours - 40) if hours > 40 else 0
    extra_rate = (per_person_rate + flat_rate) * 1.5 if extra_hours > 0 else 0
    billing_rate = per_person_rate
    return (
        value[0]["select_job"],
        value[0]["from_date"],
        value[0]["to_date"],
        hours,
        billing_rate,
        value[0]["flat_rate"],
        extra_hours,
        extra_rate,
    )


def send_email(subject=None, content=None, recipients=None):
    from frappe.core.doctype.communication.email import make

    try:
        site = frappe.utils.get_url().split("/")
        sitename = site[0] + "//" + site[2]
        # make(subject = subject, content=frappe.render_template("templates/emails/email_template_custom.html",{"sitename": sitename,"content":content,"subject":subject}), recipients= recipients,send_email=True)
        args = {"sitename": sitename, "content": content, "subject": subject}
        template = "email_template_custom"
        ses_email_send(emails=recipients, subject=subject, args=args, template=template)
        frappe.msgprint("Email Sent Successfully")
        return True
    except Exception as e:
        frappe.log_error(e, "Doc Share Error")
        frappe.msgprint("Could Not Send")
        return False


def joborder_email_template(
    subject=None,
    content=None,
    recipients=None,
    link=None,
    sender_full_name=None,
    sender=None,
):
    try:
        from frappe.core.doctype.communication.email import make

        site = frappe.utils.get_url().split("/")
        sitename = site[0] + "//" + site[2]
        args = {
            "sitename": sitename,
            "content": content,
            "subject": subject,
            "link": link,
        }
        template = "email_template_custom"
        ses_email_send(
            emails=recipients,
            subject=subject,
            args=args,
            template=template,
            sender_full_name=sender_full_name,
            sender=sender,
        )
        # make(subject = subject, content=frappe.render_template("templates/emails/email_template_custom.html",
        #     {"sitename": sitename, "content":content,"subject":subject,"link":link}),
        #     recipients= recipients,send_email=True,sender_full_name=sender_full_name,sender=sender)
        return True
    except Exception as e:
        frappe.log_error(e, "Doc Share Error")
        frappe.msgprint("Could Not Send")
        return False


@frappe.whitelist(allow_guest=False)
def send_email_staffing_user(
    user, company_type, email_list=None, subject=None, body=None, additional_email=None
):
    try:
        if (
            company_type in ["TAG", "Staffing"]
            or frappe.session.user == "Administrator"
        ) and user == frappe.session.user:
            email = json.loads(email_list)
            emails = [i["email"] for i in email]
            if additional_email:
                v = additional_email.split(",")
                for i in v:
                    emails.append(i)
            # frappe.sendmail(recipients=emails,subject=subject, message=body, template="email_template_custom", args = dict(sitename=sitename,content=body,subject=subject))
            args = dict(sitename=sitename, content=body, subject=subject)
            template = ("email_template_custom",)
            ses_email_send(emails=emails, subject=subject, args=args, template=template)
            return 1
        else:
            return 0
    except Exception as e:
        print(e, frappe.get_traceback())
        return 0


# ----------assign data------------#
def assign_employee_data(hiringorg, name):
    try:
        sql = """ select employee from `tabAssign Employee Details` where parent = '{0}' """.format(
            name
        )
        emps = frappe.db.sql(sql, as_dict=1)
        users = frappe.db.get_list("User", {"company": hiringorg}, "name")

        for usr in users:
            for emp in emps:
                if not frappe.db.exists(
                    "DocShare",
                    {
                        "user": usr.name,
                        "share_doctype": "Employee",
                        "share_name": emp.employee,
                    },
                ):
                    add(
                        "Employee",
                        emp.employee,
                        usr.name,
                        read=1,
                        write=0,
                        share=0,
                        everyone=0,
                        notify=0,
                        flags={"ignore_share_permission": 1},
                    )
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(e, "employee share")


@frappe.whitelist(allow_guest=False)
def update_job_order(
    user, company_type, sid, job_name, employee_filled, staffing_org, hiringorg, name
):
    try:
        if user != frappe.session.user:
            frappe.throw("Invalid User")
        assign_employee_doc = frappe.get_doc(assignEmployees, name)
        if job_name and name and job_name != assign_employee_doc.job_order:
            frappe.throw("Job Order does not belong to the Assign Employees")
        if (
            company_type == "Hiring"
            or company_type == exclusive_hiring
            and user == frappe.session.user
        ):
            frappe.db.set_value(
                assignEmployees, name, "approve_employee_notification", 0
            )
            job = frappe.get_doc(jobOrder, job_name)
            claimed = job.staff_org_claimed if job.staff_org_claimed else ""
            if len(claimed) == 0:
                job.db_set("staff_org_claimed", (str(claimed) + str(staffing_org)))
            else:
                job.db_set(
                    "staff_org_claimed", (str(claimed) + "~" + str(staffing_org))
                )
            frappe.db.commit()
            sub = f"New Message regarding {job_name} from {hiringorg} is available"
            msg = f"Your Employees have been approved for Work Order {job_name}"
            lst_sql = """ select user_id from `tabEmployee` where company = '{0}' and user_id IS NOT NULL""".format(
                staffing_org
            )
            user_list = frappe.db.sql(lst_sql, as_dict=1)
            users = [usr["user_id"] for usr in user_list]
            users_app, users_mail = get_mail_list(
                users, app_field="approve_emp_app", mail_field="approve_emp_mail"
            )
            enqueue(
                make_system_notification,
                users=users_app,
                message=msg,
                doctype="Assign Employee",
                docname=name,
                subject=sub,
                now=True,
            )
            enqueue(
                "tag_workflow.tag_data.assign_employee_data",
                hiringorg=hiringorg,
                name=name,
                now=True,
            )

            sql = """ UPDATE `tabAssign Employee` SET approve_employee_notification = 0 where name="{0}" """.format(
                name
            )
            frappe.db.sql(sql)
            frappe.db.commit()
            enqueue(
                sendmail,
                emails=users_mail,
                message=msg,
                subject=sub,
                doctype=assignEmployees,
                docname=name,
                now=True,
            )
            return 1
        return []
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(e, "final_notification")


def check_employee_exists(v):
    for emp in v:
        emp_doc = frappe.get_doc("Employee", emp["employee"])
        if not emp_doc or (emp_doc and emp_doc.employee_name != emp["employee_name"]):
            frappe.local.response["http_status_code"] = 500
            frappe.throw("Invalid Request")


@frappe.whitelist(allow_guest=False)
def receive_hiring_notification(
    user,
    company_type,
    hiring_org,
    job_order,
    staffing_org,
    emp_detail,
    doc_name,
    no_of_worker_req,
    is_single_share,
    job_title,
    employee_filled,
    notification_check,
):
    try:
        v = json.loads(emp_detail)
        check_employee_exists(v)
        if company_type == "Staffing" and user == frappe.session.user:
            if int(notification_check) == 0:
                bid_receive = frappe.get_doc(jobOrder, job_order)

            if int(is_single_share):
                check_partial_employee(
                    bid_receive,
                    staffing_org,
                    emp_detail,
                    no_of_worker_req,
                    job_title,
                    hiring_org,
                    doc_name,
                )
                return

            bid_receive.bid = 1 + int(bid_receive.bid)
            if bid_receive.claim is None:
                bid_receive.claim = staffing_org
                chat_room_created(hiring_org, staffing_org, job_order)
            elif staffing_org not in bid_receive.claim:
                bid_receive.claim = str(bid_receive.claim) + str("~") + staffing_org
                chat_room_created(hiring_org, staffing_org, job_order)

            bid_receive.save(ignore_permissions=True)
            jo_name = bid_receive.name
            job_site = bid_receive.job_site
            posting_date_time = bid_receive.posting_date_time
            lst_sql = """ select user_id from `tabEmployee` where company = "{}" and user_id IS NOT NULL """.format(
                hiring_org
            )
            user_list = frappe.db.sql(lst_sql, as_list=1)
            s = ""
            for i in v:
                s += i["employee_name"] + ","
            l = [l[0] for l in user_list]
            l_app, l_mail = get_mail_list(
                l,
                app_field="assign_emp_resume_app",
                mail_field="assign_emp_resume_mail",
            )
            for user in l:
                add(
                    assignEmployees,
                    doc_name,
                    user,
                    read=1,
                    write=0,
                    share=0,
                    everyone=0,
                )
            sub = "Employee Assigned"
            msg = f'{staffing_org} has submitted a claim for {s[:-1]} for {jo_name} at {job_site} on {posting_date_time}'
            make_system_notification(
                users=l_app,
                message=msg,
                doctype=assignEmployees,
                docname=doc_name,
                subject=sub,
            )
            # frappe.enqueue(make_system_notification,now=True,users=l_app,message=msg,doctype=assignEmployees,docname=doc_name,subject=sub)
            msg = f'{staffing_org} has submitted a claim for {s[:-1]} for {jo_name} at {job_site} on {posting_date_time}. Please review and/or approve this claim .'
            link = f'  href="{sitename}/app/assign-employee/{doc_name}" '
            frappe.db.set_value(assignEmployees, doc_name, "notification_check", 1)
            joborder_email_template(
                subject=sub, content=msg, recipients=l_mail, link=link
            )
            # frappe.enqueue(joborder_email_template,now=True,sub=sub, msg=msg, l=l_mail, link=link)
            return 1
        else:
            return NOASS
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.db.rollback()


def check_partial_employee(
    job_order,
    staffing_org,
    emp_detail,
    no_of_worker_req,
    job_title,
    hiring_org,
    doc_name,
):
    try:
        emp_detail = json.loads(emp_detail)
        if int(no_of_worker_req) > len(emp_detail):
            job_order.is_single_share = "0"

        job_order.bid = 1 + int(job_order.bid)
        if job_order.claim is None:
            job_order.claim = staffing_org
            chat_room_created(hiring_org, staffing_org, job_order.name)

        else:
            if staffing_org not in job_order.claim:
                job_order.claim = str(job_order.claim) + str("~") + staffing_org
                chat_room_created(hiring_org, staffing_org, job_order.name)

        job_order.save(ignore_permissions=True)
        print(job_title)
        sql1 = '''select email from `tabUser` where organization_type='hiring' and company = "{}"'''.format(
            hiring_org
        )

        hiring_list = frappe.db.sql(sql1, as_list=True)
        hiring_user_list = [user[0] for user in hiring_list]
        hiring_user_list_app, hiring_user_list_mail = get_mail_list(
            hiring_user_list, app_field="jo_claim_app", mail_field="jo_claim_mail"
        )

        if int(no_of_worker_req) > len(emp_detail):
            sql = f'''select email from `tabUser` where organization_type='Staffing' and company != "{staffing_org}"'''
            share_list = frappe.db.sql(sql, as_list=True)
            assign_notification(share_list, hiring_user_list, doc_name, job_order)
            subject = "Job Order Notification"
            msg = f"{staffing_org} placed partial claim on your work order: {job_order}. Please review & approve the candidates matched with this work order."
            make_system_notification(
                hiring_user_list_app, msg, assignEmployees, doc_name, subject
            )
            sql2 = f"""select email from `tabUser` where organization_type='Staffing' and company != "{staffing_org}" and company in (select staffing_company from `tabStaffing Radius` where job_site="{job_order.job_site}" and radius != "None" and radius <= 25 and hiring_company="{job_order.company}")"""
            share_list2 = frappe.db.sql(sql2, as_list=True)
            staffing_user_list = [user[0] for user in share_list2]
            staffing_user_list_app, staffing_user_list_mail = get_mail_list(
                staffing_user_list, app_field="jo_claim_app", mail_field="jo_claim_mail"
            )
            stff_email_with_resume_required(
                job_order,
                emp_detail,
                no_of_worker_req,
                hiring_org,
                staffing_user_list_app,
                staffing_user_list_mail,
                subject,
            )
            return send_email(subject, msg, hiring_user_list_mail)
        else:
            if hiring_user_list:
                subject = "Job Order Notification"
                for user in hiring_user_list:
                    add(
                        assignEmployees,
                        doc_name,
                        user,
                        read=1,
                        write=0,
                        share=0,
                        everyone=0,
                    )

                msg = f"{staffing_org} placed Full claim on your work order: {job_order}. Please review & approve the candidates matched with this work order."
                make_system_notification(
                    hiring_user_list_app, msg, assignEmployees, doc_name, subject
                )
                return send_email(subject, msg, hiring_user_list_mail)

    except Exception as e:
        frappe.log_error(e, "Partial Job order Failed ")


def stff_email_with_resume_required(
    job_order,
    emp_detail,
    no_of_worker_req,
    hiring_org,
    staffing_user_list_app,
    staffing_user_list_mail,
    subject,
):
    query = """select sum(approved_no_of_workers) from `tabClaim Order` where job_order = "{}" """.format(
        job_order.name
    )
    rem_emp = frappe.db.sql(query)
    notification_func(
        job_order,
        emp_detail,
        no_of_worker_req,
        hiring_org,
        staffing_user_list_app,
        staffing_user_list_mail,
        subject,
        rem_emp,
    )


def notification_func(
    job_order,
    emp_detail,
    no_of_worker_req,
    hiring_org,
    staffing_user_list_app,
    staffing_user_list_mail,
    subject,
    rem_emp,
):
    if rem_emp[0][0] and job_order.is_repeat:
        count = int(no_of_worker_req) - int(rem_emp[0][0])
    else:
        count = int(no_of_worker_req) - len(emp_detail)

    if count > 0:
        if count == 1:
            newmsg = f"{hiring_org} has an order available with {count} opening available."
        else:
            newmsg = f"{hiring_org} has an order available with {count} openings available."
        make_system_notification(
            staffing_user_list_app, newmsg, jobOrder, job_order.name, subject
        )
        link_job_order = f'  href="{sitename}/app/job-order/{job_order.name}"'
        joborder_email_template(
            subject,
            newmsg,
            staffing_user_list_mail,
            link_job_order,
            sender_full_name=job_order.company,
            sender=job_order.owner,
        )


@frappe.whitelist(allow_guest=False)
def staff_email_notification(
    hiring_org=None,
    job_order=None,
    job_order_title=None,
    staff_company=None,
    multiple_comp=None,
):
    try:
        doc = frappe.get_doc(jobOrder, job_order)
        subject = "New Work Order"
        sql = """ select data from `tabVersion` where ref_doctype='Job Order' and docname='{}' """.format(
            job_order
        )
        multiple_comp = ast.literal_eval(multiple_comp)
        update_values = frappe.db.sql(sql, as_list=1)
        if len(update_values) < 2:
            sql = """select organization_type from `tabCompany` where name='{}' """.format(
                hiring_org
            )
            org_type = frappe.db.sql(sql, as_list=1)
            if staff_company and org_type[0][0] == "Hiring":
                staff_company = staff_comp_for_dir_order(
                    multiple_comp, staff_company, job_order
                )
                for i in staff_company:
                    user_list = frappe.db.sql(
                        """ select user_id from `tabEmployee` where company='{}' and user_id IS NOT NULL and user_id in (select name from `tabUser` where enabled="1") """.format(
                            i.strip()
                        ),
                        as_list=1,
                    )
                    l = [l[0] for l in user_list]
                    for user in l:
                        add(
                            jobOrder,
                            job_order,
                            user,
                            read=1,
                            write=0,
                            share=0,
                            everyone=0,
                        )
                        frappe.db.commit()
                    frappe.enqueue(
                        single_job_order_notification,
                        hiring_org=hiring_org,
                        job_order=job_order,
                        subject=subject,
                        l=l,
                        staff_company=i,
                        now=True,
                    )
                    frappe.db.commit()
                return 1
            else:
                frappe.enqueue(
                    staff_email_notification_cont,
                    hiring_org=hiring_org,
                    job_order=job_order,
                    job_order_title=job_order_title,
                    doc=doc,
                    subject=subject,
                    now=True,
                )
                return 1
    except Exception as e:
        print(e, frappe.get_traceback())


def staff_comp_for_dir_order(multiple_comp, staff_company, job_order):
    if multiple_comp and len(multiple_comp) > 1:
        enqueue(
            save_job_order_value,
            job_order=job_order,
            staff_company=staff_company,
            now=True,
        )
        return multiple_comp
    else:
        frappe.db.sql(
            '''update `tabJob Order` set is_single_share = 1 where name = "{}"'''.format(
                job_order
            )
        )
        return (staff_company.strip()).split("~")


def staff_email_notification_cont(
    hiring_org=None, job_order=None, job_order_title=None, doc=None, subject=None
):
    try:
        sql = """select organization_type from `tabCompany` where name='{}' """.format(
            hiring_org
        )
        org_type = frappe.db.sql(sql, as_list=1)
        if org_type[0][0] == "Hiring":
            doc.company_type = non_exlusive
            doc.save(ignore_permissions=True)

            frappe.enqueue(
                        share_job_order_hiring_background,
                        queue="default",
                        is_async=True,
                        now=True,
                        hiring_org=hiring_org,
                        job_order=job_order,
                    )
            is_radius = frappe.db.get_value('Job Site', doc.job_site, "is_radius")
            if is_radius:
                sql2 = f""" select email from `tabUser` where organization_type='staffing' 
                            and enabled="1" 
                            and company not in (select staffing_company_name from `tabBlocked Staffing Company` where parent="{hiring_org}") 
                            and company in (select staffing_company from `tabStaffing Radius` where job_site="{doc.job_site}" 
                            and radius != "None" and radius <= 25 and hiring_company="{doc.company}")
                        """
            else:
                sql2 = f"""
                   SELECT DISTINCT u.email
                    FROM tabUser u
                    JOIN tabCompany c ON u.company = c.name
                    JOIN `tabJob Site` j ON 3959 * ACOS(COS(RADIANS(c.lat)) * COS(RADIANS(j.lat)) * COS(RADIANS(j.lng) - RADIANS(c.lng)) + SIN(RADIANS(c.lat)) * SIN(RADIANS(j.lat))) <= 25
                    WHERE j.name = "{doc.job_site}" AND u.organization_type='staffing' AND u.enabled=1 AND c.name NOT IN
                    (SELECT staffing_company_name FROM `tabBlocked Staffing Company` WHERE parent="{hiring_org}") ;
                """
            staff_user_list = frappe.db.sql(sql2, as_list=1)
            l2 = [l2[0] for l2 in staff_user_list]
            job_order_notification(job_order_title, hiring_org, job_order, subject, l2)
        elif org_type[0][0] == exclusive_hiring:
            doc.company_type = "Exclusive"
            doc.save(ignore_permissions=True)

            own_sql = """ select owner from `tabCompany` where organization_type="Exclusive Hiring" and name="{}" """.format(
                hiring_org
            )
            owner_info = frappe.db.sql(own_sql, as_list=1)

            com_sql = """ select company from `tabUser` where name='{0}' and enabled="1" """.format(
                owner_info[0][0]
            )
            company_info = frappe.db.sql(com_sql, as_list=1)

            usr_sql = """ select user_id from `tabEmployee` where company='{}' and user_id IS NOT NULL """.format(
                company_info[0][0]
            )
            user_list = frappe.db.sql(usr_sql, as_list=1)

            l = [l[0] for l in user_list]
            frappe.enqueue(
                        share_job_order_exclusive_hiring_background,
                        queue="default",
                        is_async=True,
                        now=True,
                        job_order=job_order,
                        l=l
            )
            job_order_notification(job_order_title, hiring_org, job_order, subject, l)
    except Exception as e:
        print(e)

def share_job_order_exclusive_hiring_background(job_order, l):
    for user in l:
        add(jobOrder, job_order, user, read=1, write=0, share=0, everyone=0)

def share_job_order_hiring_background(hiring_org, job_order):
    sql = f""" select email from `tabUser` where organization_type='staffing'  
                       and company not in (select staffing_company_name from `tabBlocked Staffing Company` where parent="{hiring_org}")
                   """
    user_list = frappe.db.sql(sql, as_list=1)
    l = [l[0] for l in user_list]
    for user in l:
        add(jobOrder, job_order, user, read=1, write=0, share=0, everyone=0)


@frappe.whitelist(allow_guest=False)
def update_exclusive_org(
    exclusive_email, staffing_email, staffing_comapny, exclusive_company
):
    try:
        if (
            not frappe.db.exists(
                "DocShare",
                {"user": exclusive_email, "share_name": staffing_comapny, "read": 1},
            )
            and frappe.db.exists("Company", staffing_comapny)
            and frappe.db.get_value(
                "Company", {"name": staffing_comapny}, "organization_type"
            )
            == "Staffing"
        ):
            add(
                "Company",
                staffing_comapny,
                exclusive_email,
                write=0,
                read=1,
                share=0,
                everyone=0,
                notify=1,
                flags={"ignore_share_permission": 1},
            )

        if not frappe.db.exists(
            "DocShare",
            {
                "user": exclusive_email,
                "share_name": exclusive_company,
                "read": 1,
                "write": 1,
                "share": 1,
            },
        ) and frappe.db.exists("Company", exclusive_company):
            add(
                "Company",
                exclusive_company,
                exclusive_email,
                write=1,
                read=1,
                share=1,
                everyone=0,
                notify=1,
                flags={"ignore_share_permission": 1},
            )
    except Exception as e:
        frappe.log_error(e, "doc share error")


@frappe.whitelist(allow_guest=False)
def staff_org_details(company_details=None):
    comp_data = frappe.get_doc("Company", company_details)
    sql = """ select fein as "FEIN", title as "Title", address as "Address", city as "City", state as "State", zip as "Zip", contact_name as "Contact Name", email as "Contact Email", phone_no  as "Company Phone No", primary_language as "Primary Language",accounts_receivable_rep_email as "Accounts Receivable Rep email",accounts_receivable_name as "Accounts Receivable Name",accounts_receivable_phone_number as "Accounts Receivable phone number", cert_of_insurance as "Cert of Insurance",safety_manual as "Safety Manual",w9 as "W9" from `tabCompany` where name="{}" """.format(
        company_details
    )
    company_info = frappe.db.sql(sql, as_dict=1)
    mandatory_field = []
    if len(comp_data.industry_type) == 0:
        mandatory_field.append("Industry")
    for i in company_info[0]:
        if company_info[0][i] is None or len(company_info[0][i]) == 0:
            mandatory_field.append(i)
    if len(mandatory_field):
        return mandatory_field
    else:
        return "success"


@frappe.whitelist(allow_guest=False)
def update_staffing_user_with_exclusive(company, company_name):
    sql = """select name from `tabUser` where company = "{}" and tag_user_type = 'Staffing User' """.format(
        company
    )
    a = frappe.db.sql(sql, as_list=1)
    try:
        for i in a:
            add(
                "Company",
                company_name,
                i[0],
                write=0,
                read=1,
                share=0,
                notify=1,
                flags={"ignore_share_permission": 1},
            )

    except Exception as e:
        frappe.log_error(e, "doc share error")


@frappe.whitelist(allow_guest=False)
def check_assign_employee(total_employee_required, employee_detail=None):
    import json

    total = int(total_employee_required)
    try:
        if employee_detail:
            v = json.loads(employee_detail)
            total_employee = [i["employee_name"] for i in v]
            unique_employee = set(total_employee)

            if len(total_employee) == len(unique_employee):
                if len(total_employee) > total:
                    return "exceeds"
            else:
                return "duplicate"
        else:
            return "insert"
    except Exception:
        return 0


@frappe.whitelist(allow_guest=False)
def api_sec(doctype, frm=None):
    try:
        emp = frappe.get_doc(doctype, frm)
        if emp.ssn:
            return emp.get_password("ssn")
        return response
    except Exception:
        frappe.log_error("No Employee in Database", "Warning")


@frappe.whitelist(allow_guest=False)
def filter_blocked_employee(doctype, txt, searchfield, page_len, start, filters):
    emp_company = filters.get("emp_company")
    job_category = filters.get("job_category")

    company = filters.get("company")

    if job_category is None:
        sql = """ select name, employee_name from `tabEmployee` where company=%(emp_company)s and status='Active' and (name NOT IN (select parent from `tabBlocked Employees`  where blocked_from=%(company)s) and (name NOT IN (select parent from `tabUnsatisfied Organization`  where unsatisfied_organization_name='{0}')) and (name NOT IN (select parent from `tabDNR` BE where dnr='{1}')) """.format(
            emp_company, company
        )

        return frappe.db.sql(sql)
    else:
        sql = """select name, employee_name from `tabEmployee` where company='{0}' and status='Active' and (job_category = '{1}' or job_category IS NULL) and (name NOT IN (select parent from `tabBlocked Employees`  where blocked_from='{2}')) and (name NOT IN (select parent from `tabDNR`  where dnr='{2}' )) and (name NOT IN (select parent from `tabUnsatisfied Organization`  where unsatisfied_organization_name='{2}'))""".format(
            emp_company, job_category, company
        )

        return frappe.db.sql(sql)


@frappe.whitelist(allow_guest=False)
def get_org_site(doctype, txt, searchfield, page_len, start, filters):
    company = filters.get("job_order_company")
    sql = """ select job_site from `tabCompany Site` where parent="{0}" and job_site like "%%{1}%%" """.format(
        company, "%s" % txt
    )
    return frappe.db.sql(sql)


@frappe.whitelist(allow_guest=False)
def job_site_contact(doctype, txt, searchfield, page_len, start, filters):
    company = filters.get("job_order_company")
    sql = """ select name, full_name, email, mobile_no from `tabUser` where company="{0}" and name like '%%{1}%%' """.format(
        company, "%s" % txt
    )
    return frappe.db.sql(sql)


@frappe.whitelist(allow_guest=True)
def hiring_category(doctype, txt, searchfield, page_len, start, filters):
    company = filters.get("hiring_company")
    sql = '''select industry_type from `tabIndustry Types` where parent='{0}' and industry_type like "%%{1}%%"'''.format(
        company, "%s" % txt
    )
    return frappe.db.sql(sql)


@frappe.whitelist(allow_guest=False)
def org_industy_type(company=None):
    sql = (
        """select industry_type from `tabIndustry Types` where parent='{0}' """.format(
            company
        )
    )
    return frappe.db.sql(sql)


@frappe.whitelist(allow_guest=False)
def delete_file_data(file_name):
    sql = '''Delete from `tabFile` where file_name = "{}"'''.format(file_name)
    frappe.db.sql(sql)


def job_order_notification(job_order_title, hiring_org, job_order, subject, l):
    l_app, l_mail = get_mail_list(
        l, app_field="jo_create_app", mail_field="jo_create_mail"
    )
    msg = f"New Work Order has been created by {hiring_org}."
    print(job_order_title)
    frappe.enqueue(
                    make_system_notification,
                    queue="default",
                    is_async=True,
                    users=l_app,
                    message=msg,
                    doctype=jobOrder,
                    docname=job_order,
                    subject=subject
                )
    # make_system_notification(l_app, msg, jobOrder, job_order, subject)
    message = (
        f"New Work Order has been created by {hiring_org}."
    )
    link = f' href="{sitename}/app/job-order/{job_order}"'
    return joborder_email_template(subject, message, l_mail, link)


@frappe.whitelist(allow_guest=False)
def disable_user(company, check):
    try:
        if check == "1":
            check = int(0)
        else:
            check = int(1)

        sql = """ UPDATE `tabUser` SET `tabUser`.enabled ="{0}" where company="{1}" and `terminated`!=1 """.format(
            check, company
        )
        frappe.db.sql(sql)
        frappe.db.commit()
    except Exception as e:
        frappe.msgprint(e)


@frappe.whitelist()
def update_job_order_status():
    try:
        job_order_data = frappe.db.sql(
            """select jo.name,jo.from_date,jo.to_date,MIN(multi.job_start_time) AS min_job_start_time,jo.bid,jo.staff_org_claimed,jo.order_status,jo.creation,jo.total_no_of_workers,multi.worker_filled 
            from `tabJob Order` jo left join `tabMultiple Job Titles` multi on multi.parent = jo.name where jo.order_status not like '%Completed%'  and multi.job_start_time is not NULL group by jo.name""",
            as_dict=True,
        )
        current_date = datetime.date.today()
        for each in job_order_data:
            if each.order_status == 'Canceled': continue
            start = each.from_date if each.from_date else ""
            end = each.to_date if each.to_date else ""
            current_time = (
                datetime.datetime.now(timezone(TIMEZONE))
                .time()
                .strftime("%H:%M:%S")
            )
            current_time = datetime.datetime.strptime(current_time, "%H:%M:%S").time()
            current_time = timedelta(
                hours=current_time.hour,
                minutes=current_time.minute,
                seconds=current_time.second,
            )
            if type(start) is not str:
                set_job_order_status(current_date, each, start, end, current_time)
                free_redis(each.name)
                update_timesheet_status(each)
    except Exception as e:
        frappe.msgprint(e)


def update_timesheet_status(each):
    timesheets = frappe.db.sql(
        f"""select name from `tabTimesheet` where job_order_detail = '{each.name}'""",
        as_list=True,
    )
    lists = [a[0] for a in timesheets]
    if lists:
        if len(lists) == 1:
            sql = """UPDATE `tabTimesheet` set status_of_work_order='Completed' where name = '{}'""".format(
                lists[0]
            )
        else:
            sql = """UPDATE `tabTimesheet` set status_of_work_order='Completed' where name in {}""".format(
                tuple(lists)
            )
        frappe.db.sql(sql)
        frappe.db.commit()


@frappe.whitelist(allow_guest=False)
def sales_invoice_notification(job_order, company, invoice_name, jo_company):
    try:
        jo_job_site = frappe.db.get_value(jobOrder, {"name": job_order}, "job_site")
        company_doc = frappe.get_doc("Company", company)
        invoice_doc = frappe.get_doc(salesInvoice, invoice_name)
        if not company_doc.has_permission("read"):
            frappe.flags.error_message = _("Insufficient Permission for {0}").format(
                frappe.bold("Company" + " " + company)
            )
            raise frappe.PermissionError(("read", "Company", company))
        if invoice_doc.company != company:
            frappe.throw("Invalid Company")
        if invoice_doc.job_order and invoice_doc.job_order != job_order:
            frappe.throw("Invalid Job Order")
        msg = (
            f"{company} has submitted an invoice for {job_order} at {jo_job_site}."
        )
        subject = "Invoice Submitted"
        sql = """ select name from `tabUser` where company='{}' """.format(jo_company)
        user_list = frappe.db.sql(sql, as_dict=1)
        users = [l.name for l in user_list]
        for usr in users:
            add(salesInvoice, invoice_name, usr, read=1, write=0, share=0, everyone=0)
        if users:
            users_app, users_mail = get_mail_list(
                users, app_field="inv_create_app", mail_field="inv_create_mail"
            )
            make_system_notification(
                users_app, msg, salesInvoice, invoice_name, subject
            )
            send_email(subject, msg, users_mail)
            return True
    except Exception as e:
        frappe.msgprint(frappe.get_traceback())
        frappe.log_error(e, "invoice notification")


@frappe.whitelist(allow_guest=False)
def hiring_org_name(current_user):
    sql = """ select company from `tabEmployee` where email='{0}' and company in (select name from `tabCompany` where make_organization_inactive='0') """.format(
        current_user
    )
    user_company = frappe.db.sql(sql, as_list=1)
    if len(user_company) == 1:
        return "success"


@frappe.whitelist(allow_guest=False)
def check_old_password(current_user, old_password):
    try:
        from Crypto.Cipher import PKCS1_OAEP
        from Crypto.PublicKey import RSA
        from Crypto.Hash import SHA256
        from base64 import b64decode

        pem_file_path = frappe.get_app_path('tag_workflow')+'/private_key.pem'

        with open(pem_file_path, 'rb') as pem_file:
            pem_data = pem_file.read()

        private_key = RSA.importKey(pem_data)

        cipher = PKCS1_OAEP.new(private_key, hashAlgo=SHA256)
        decrypted_message = cipher.decrypt(b64decode(old_password))
        old_password = decrypted_message.decode('utf-8')
    except Exception:
        print(frappe.get_traceback())
    user = User.find_by_credentials(current_user, old_password)
    return user["is_authenticated"]


@frappe.whitelist(allow_guest=False)
def designation_activity_data(doc, method):
    if not frappe.db.exists("Item", {"name": doc.name}):
        role_doc = frappe.get_doc(
            dict(
                doctype="Item",
                industry=doc.industry_type,
                job_titless=doc.name,
                rate=doc.price,
                item_code=doc.name,
                item_group="All Item Groups",
                stock_uom="Nos",
                descriptions=doc.description,
                company="",
            )
        )
        role_doc.save()
    if not frappe.db.exists(activityType, {"name": doc.name}):
        docs = frappe.new_doc(activityType)
        docs.activity_type = doc.name
        docs.insert()


@frappe.whitelist(allow_guest=False)
def filter_company_employee(doctype, txt, searchfield, page_len, start, filters):
    try:
        company = filters.get("company")
        employees_list = filters.get("employees_list")
        value = ""
        for index, i in enumerate(employees_list):
            if index >= 1:
                value = value + "'" + "," + "'" + i
            else:
                value = value + i
        sql = """ select name, employee_name,company from `tabEmployee` where company='{0}' and (name NOT IN ('{1}') and name like '%%{2}%%')""".format(
            company, value, "%s" % txt
        )
        return frappe.db.sql(sql)
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(e, "Staffing Company Error")
        frappe.throw(e)


@frappe.whitelist(allow_guest=False)
def contact_company(doctype, txt, searchfield, page_len, start, filters):
    company = filters.get("company")
    sql = """ select name from `tabCompany` where name='{}' """.format(company)
    return frappe.db.sql(sql)


@frappe.whitelist(allow_guest=False)
def email_recipient(doctype, txt, searchfield, page_len, start, filters):
    company = filters.get("company")
    recipients_list = filters.get("recipients_list")
    value = ""
    for index, i in enumerate(recipients_list):
        if index >= 1:
            value = value + "'" + "," + "'" + i
        else:
            value = value + i
    sql = """ select name from `tabContact` where company='{0}' and (name NOT IN ('{1}') and name like '%%{2}%%')""".format(
        company, value, "%s" % txt
    )
    return frappe.db.sql(sql)


def single_job_order_notification(
    hiring_org, job_order, subject, l, staff_company
):
    try:

        l_app, l_mail = get_mail_list(
            l, app_field="jo_create_app", mail_field="jo_create_mail"
        )
        frappe.enqueue("tag_workflow.tag_data.single_job_order_notification_background", l_app=l_app, hiring_org=hiring_org, job_order=job_order, subject=subject, staff_company=staff_company, queue="default", is_async=True)
        message = f'{hiring_org} is requesting a fulfilment of a work order for {job_order} specifically with {staff_company}. Please respond. <br> <br><a href="{sitename}/app/job-order/{job_order}" style=" color: #21B9E4">View Work Order</a>'
        link = f' href="{sitename}/app/job-order/{job_order}"'
        return joborder_email_template(subject, message, l_mail, link)
    except Exception as e:
        print(e,frappe.get_traceback())
        frappe.log_error(e, "Single Job Order Notification Error")

def single_job_order_notification_background(l_app, hiring_org, job_order, subject,staff_company):
    try:
        (
            is_repeat,
            total_no_of_workers,
            total_workers_filled,
            resumes_reqd,
        ) = frappe.db.get_value(
            jobOrder,
            {"name": job_order},
            [
                "is_repeat",
                "total_no_of_workers",
                "total_workers_filled",
                "resumes_required",
            ],
        )
        msg = None
        if is_repeat:
            emp_reqd = (
                total_no_of_workers - total_workers_filled if not resumes_reqd else 0
            )
            msg = (
                f"{hiring_org} is requesting a fulfilment of a work order for {job_order} specifically with {staff_company}. Please respond."
                if emp_reqd == 0
                else f"{hiring_org} is requesting a fulfilment of a work order for {job_order} specifically with {staff_company}."
                + " "
                + f"{emp_reqd} employees require replacing. Please assign additional employees."
            )
        else:
            msg = f"{hiring_org} is requesting a fulfilment of a work order for {job_order} specifically with {staff_company}. Please respond."
        make_system_notification(
            users=l_app,
            message=msg,
            doctype=jobOrder,
            docname=job_order,
            subject=subject,
        )
    except Exception as e:
        frappe.log_error(e, "Background job error single job")


def assign_notification(share_list, hiring_user_list, doc_name, job_order):
    if share_list:
        for user in share_list:
            add(
                jobOrder,
                job_order.name,
                user[0],
                read=1,
                write=0,
                share=1,
                everyone=0,
                notify=0,
                flags={"ignore_share_permission": 1},
            )
    for user in hiring_user_list:
        add(assignEmployees, doc_name, user, read=1, write=0, share=0, everyone=0)


def chat_room_created(hiring_org, staffing_org, job_order):
    try:
        hiring_comp_users = frappe.db.sql(
            """ select user_id from `tabEmployee` where company='{0}' and user_id IS NOT NULL""".format(
                hiring_org
            ),
            as_list=1,
        )
        staffing_users = frappe.db.sql(
            """ select user_id from `tabEmployee` where company='{0}' and user_id IS NOT NULL """.format(
                staffing_org
            ),
            as_list=1,
        )
        tag_users = frappe.db.sql(
            """ select email from `tabUser` where tag_user_type='TAG Admin' """,
            as_list=1,
        )

        user_list = hiring_comp_users + staffing_users + tag_users
        total_user_list = []
        members = ""
        for claim in user_list:
            value = claim[0].split(",")
            for name in value:
                if name:
                    total_user_list.append(name.strip())
        for k in total_user_list:
            members += k + ","
        doc = frappe.new_doc("Chat Room")
        doc.room_name = str(job_order) + "_" + staffing_org
        doc.type = "Group"
        doc.members = members
        doc.save()
    except Exception as e:
        frappe.log_error(e, "chat room creation error")


@frappe.whitelist(allow_guest=False)
def joborder_resume(name):
    sql = """ select resume from `tabEmployee` where name='{}' """.format(name)
    return frappe.db.sql(sql, as_dict=1)


@frappe.whitelist(allow_guest=False)
def approved_employee(id, name, job_order, assign_note, company):
    sql1 = """ UPDATE `tabAssign Employee Details` SET approved = 0 where parent="{0}" """.format(
        name
    )
    frappe.db.sql(sql1)

    g1 = json.loads(id)
    exist_job = frappe.get_doc(jobOrder, job_order)
    emp_count = exist_job.total_no_of_workers - exist_job.total_workers_filled

    if len(g1) > int(emp_count):
        return "error"
    for i in g1:
        sql = """ UPDATE `tabAssign Employee Details` SET approved = 1 where employee = "{0}" and parent="{1}" and job_category="{2}" and job_start_time like "%%{3}%%" """.format(
            i[0], name,i[1],i[2]
        )
        frappe.db.sql(sql)
        frappe.db.commit()
    assign_note = assign_note.replace('"', '""')
    sql = (
        """ UPDATE `tabAssign Employee` SET notes = "{0}" where name = "{1}" """.format(
            assign_note, name
        )
    )
    frappe.db.sql(sql)
    frappe.db.sql(
        """ UPDATE `tabAssign Employee` SET notes ="{0}" where job_order="{1}" and company="{2}" """.format(
            assign_note, job_order, company
        )
    )
    frappe.db.commit()


@frappe.whitelist(allow_guest=False)
def lead_org(current_user):
    sql = """ select company from `tabEmployee` where email='{0}' """.format(
        current_user
    )
    user_company = frappe.db.sql(sql, as_list=1)
    if len(user_company) == 1:
        return "success"


@frappe.whitelist(allow_guest=False)
def timesheet_detail(job_order, company_type):
    """
    The function `timesheet_detail` checks if a job order has timesheet and sales invoice records based
    on the company type, and returns a success message if the conditions are met.
    
    :param job_order: The `job_order` parameter is a string that represents the job order detail. It is
    used in the SQL queries to filter the data
    :param company_type: The `company_type` parameter is a string that specifies the type of company. It
    can have two possible values: "staffing" or any other value
    :return: a string value. The possible return values are "success1", "success", or None.
    """
    try:
        if company_type == 'staffing':
            sql = """SELECT COUNT(name) FROM `tabTimesheet` WHERE job_order_detail='{0}'""".format(
                job_order
            )
            sales_sql = """SELECT COUNT(name) FROM `tabSales Invoice` WHERE job_order='{0}'""".format(
                job_order
            )
            user_company = frappe.db.sql(sql)
            sales_company = frappe.db.sql(sales_sql)
            if user_company[0][0] > 0 and sales_company[0][0] > 0:
                return "success1"
            elif user_company[0][0] > 0:
                return "success"
        else:
            sales_sql = """SELECT COUNT(name) FROM `tabSales Invoice` WHERE job_order='{0}' AND docstatus=1""".format(
                job_order
            )
            sales_company = frappe.db.sql(sales_sql)
            if sales_company[0][0] > 0:
                return "success"
    except Exception as e:
        frappe.log_error(e, 'timesheet_detail error')


@frappe.whitelist(allow_guest=False)
def update_timesheet_is_check_in_sales_invoice(time_list, timesheet_used):
    try:
        timesheet_used = timesheet_used[1:-1]
        l = timesheet_used.split(",")
        time_list = json.loads(time_list)
        for i in l:
            time = i.strip()
            timesheet_name = time[1:-1]
            sql = """ UPDATE `tabTimesheet` SET `tabTimesheet`.is_check_in_sales_invoice = 1 where name = "{0}" """.format(
                timesheet_name.strip()
            )
            frappe.db.sql(sql)
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(e, "Update time sheet Invoice")


@frappe.whitelist(allow_guest=False)
def assigned_employees(job_order):
    try:
        sql = f" select name from `tabAssign Employee` where job_order='{job_order}' and tag_status='Approved'"
        assigned_data = frappe.db.sql(sql)
        if len(assigned_data) > 0:
            return "success1"
        return "failed"
    except Exception as e:
        frappe.log_error(e, "Assign Employee List")


@frappe.whitelist(allow_guest=False)
def assigned_employee_data(job_order):
    try:
        jo = frappe.get_doc(jobOrder, job_order)
        comp = jo.owner
        comp_detail = frappe.get_doc("User", comp)
        comp_type = comp_detail.organization_type
        if jo.resumes_required == 1 and comp_type != "Staffing":
            sql = f"""
                select ae.company as staff_company, ae.name AS name, aed.remove_employee AS remove,aed.employee_name as employee_name,
                aed.approved as approved, aed.employee as employee ,
                TIME_FORMAT(aed.job_start_time, "%H:%i") as job_start_time,
                aed.job_category as job_category
                from `tabAssign Employee` as ae,`tabAssign Employee Details` as aed
                where ae.name=aed.parent and job_order="{job_order}"
                and ae.tag_status="Approved" and aed.approved =1 and
                aed.remove_employee =0 
                order by staff_company,
                SUBSTRING_INDEX(aed.job_category, '-', 1),
                CAST(SUBSTRING_INDEX(aed.job_category, '-', -1) AS UNSIGNED),
                employee_name
            """

        else:
            sql = f"""
                SELECT ae.company AS staff_company, ae.name AS name, aed.remove_employee AS remove, aed.employee_name AS employee_name,
                aed.employee as employee, TIME_FORMAT(aed.job_start_time, "%H:%i") as job_start_time,
                aed.job_category as job_category
                FROM `tabAssign Employee` AS ae,`tabAssign Employee Details` AS aed
                WHERE ae.name=aed.parent and job_order="{job_order}" and tag_status="Approved"
                AND aed.remove_employee = 0
                ORDER BY staff_company,
                SUBSTRING_INDEX(aed.job_category, '-', 1),
                CAST(SUBSTRING_INDEX(aed.job_category, '-', -1) AS UNSIGNED),
                employee_name
            """
        emp_data = frappe.db.sql(sql, as_dict=1)
        emp_list = []
        for i in range(len(emp_data)):
            emp_dic = {}
            sql3 = f"""
                SELECT
                MAX(IF(no_show=1, "No Show", " ")) AS no_show,
                MAX(IF(non_satisfactory=1,"Non Satisfactory"," ")) AS non_satisfactory,
                MAX(IF(dnr=1,"DNR"," ")) AS dnr
                FROM `tabTimesheet`
                WHERE job_order_detail='{job_order}' AND employee='{emp_data[i].employee}' AND job_name='{emp_data[i].job_category}'
            """
            employees_data = frappe.db.sql(sql3, as_dict=True)
            if len(employees_data) == 0:
                emp_dic = {
                    "assign_name": emp_data[i].name,
                    "staff_company": emp_data[i].staff_company,
                    "employee": emp_data[i].employee_name,
                    "no_show": "",
                    "non_satisfactory": "",
                    "dnr": "",
                    "replaced": "",
                    "employee_id": emp_data[i].employee,
                    "removed": emp_data[i].remove,
                    "job_title": emp_data[i].job_category,
                    "job_start_time": emp_data[i].job_start_time,
                }
                emp_list.append(emp_dic)
            else:
                emp_dic = {
                    "assign_name": emp_data[i].name,
                    "staff_company": emp_data[i].staff_company,
                    "employee": emp_data[i].employee_name,
                    "no_show": employees_data[0].no_show,
                    "non_satisfactory": employees_data[0].non_satisfactory,
                    "dnr": employees_data[0].dnr,
                    "replaced": "",
                    "employee_id": emp_data[i].employee,
                    "removed": emp_data[i].remove,
                    "job_title": emp_data[i].job_category,
                    "job_start_time": emp_data[i].job_start_time,
                }
                emp_list.append(emp_dic)
        replaced = replaced_employees(job_order, None)
        return emp_list + replaced
    except Exception as e:
        frappe.log_error(e, assignEmployees)


@frappe.whitelist(allow_guest=False)
def staff_assigned_employees(job_order, user_email, resume_required):
    try:
        if int(resume_required) == 0:
            sql1 = f"select sum(approved_no_of_workers) as approved_no_of_workers from `tabClaim Order` where job_order='{job_order}' and staffing_organization in (select company from `tabEmployee` where user_id='{user_email}') group by staffing_organization "
            data1 = frappe.db.sql(sql1, as_dict=True)
            sql = f" select name, claims_approved from `tabAssign Employee` where job_order='{job_order}' and tag_status='Approved' and  company in (select company from `tabEmployee` where email='{frappe.session.user}')"
            assigned_data = frappe.db.sql(sql, as_dict=1)
            if len(assigned_data) > 0:
                emp_data = frappe.get_doc(assignEmployees, assigned_data[0]["name"])
                sql = f" select name from `tabAssign Employee` where job_order='{job_order}' and tag_status='Open' and  company in (select company from `tabEmployee` where email='{frappe.session.user}')"
                assigned_data = frappe.db.sql(sql)
                if len(assigned_data) > 0:
                    return "success2"
                return "success1", emp_data, data1[0]["approved_no_of_workers"]
        else:
            sql = f" select name from `tabAssign Employee` where job_order='{job_order}' and tag_status='Approved' and  company in (select company from `tabEmployee` where email='{frappe.session.user}')"
            assigned_data = frappe.db.sql(sql)
            if len(assigned_data) > 0:
                sql = f" select name from `tabAssign Employee` where job_order='{job_order}' and tag_status='Open' and  company in (select company from `tabEmployee` where email='{frappe.session.user}')"
                assigned_data = frappe.db.sql(sql)
                if len(assigned_data) > 0:
                    return "success2"
                return "success1"
    except Exception as e:
        frappe.log_error(e, "Staff Employee")


@frappe.whitelist(allow_guest=False)
def staffing_assigned_employee(job_order):
    try:
        doc = frappe.get_doc(jobOrder, job_order)
        owner_comp_type = frappe.get_doc("User", doc.owner)
        if (
            owner_comp_type.organization_type != "Staffing"
            and doc.resumes_required == 1
        ):
            assigned_emp = f"""
                SELECT ae.company, ae.name AS name, aed.remove_employee AS remove, aed.employee_name AS employee_name,
                aed.employee, aed.name AS child_name, aed.job_category AS job_category, TIME_FORMAT(aed.job_start_time, "%H:%i") AS job_start_time
                FROM `tabAssign Employee` AS ae, `tabAssign Employee Details` AS aed
                WHERE ae.name = aed.parent AND job_order = "{job_order}" AND tag_status = "Approved" AND aed.approved=1
                AND ae.company IN
                (SELECT company FROM `tabEmployee` WHERE email = '{frappe.session.user}')
                ORDER BY company, 
                SUBSTRING_INDEX(aed.job_category, '-', 1),
                CAST(SUBSTRING_INDEX(aed.job_category, '-', -1) AS UNSIGNED),
                employee_name"""
        else:
            assigned_emp = f"""
                SELECT ae.company, ae.name AS name, aed.remove_employee AS remove, aed.employee_name AS employee_name, aed.employee AS employee,
                aed.name AS child_name, aed.job_category AS job_category, TIME_FORMAT(aed.job_start_time, "%H:%i") AS job_start_time
                FROM `tabAssign Employee` AS ae, `tabAssign Employee Details` AS aed
                WHERE ae.name = aed.parent AND job_order = "{job_order}" AND tag_status = "Approved" AND ae.company IN
                (SELECT company FROM `tabEmployee` WHERE email = '{frappe.session.user}')
                ORDER BY company,
                SUBSTRING_INDEX(aed.job_category, '-', 1),
                CAST(SUBSTRING_INDEX(aed.job_category, '-', -1) AS UNSIGNED),
                employee_name
            """

        emp_data = frappe.db.sql(assigned_emp, as_dict=1)
        emp_list = []
        for i in range(len(emp_data)):
            emp_dic = {}
            sql3 = f"""
                SELECT max(IF(no_show=1, "No Show", " ")) AS no_show,
                MAX(IF(non_satisfactory=1,"Non Satisfactory"," ")) AS non_satisfactory,
                MAX(IF(dnr=1,"DNR"," ")) AS dnr
                FROM `tabTimesheet`
                WHERE job_order_detail='{job_order}' AND employee='{emp_data[i].employee}' AND job_name='{emp_data[i].job_category}'
            """
            employees_data = frappe.db.sql(sql3, as_dict=True)

            if len(employees_data) == 0:
                emp_dic = {
                    "assign_name": emp_data[i].name,
                    "staff_company": emp_data[i].staff_company,
                    "employee": emp_data[i].employee_name,
                    "no_show": "",
                    "non_satisfactory": "",
                    "dnr": "",
                    "replaced": "",
                    "child_name": emp_data[i].child_name,
                    "employee_id": emp_data[i].employee,
                    "removed": emp_data[i].remove,
                    "job_title": emp_data[i].job_category,
                    "job_start_time": emp_data[i].job_start_time,
                }
                emp_list.append(emp_dic)
            else:
                emp_dic = {
                    "assign_name": emp_data[i].name,
                    "staff_company": emp_data[i].staff_company,
                    "employee": emp_data[i].employee_name,
                    "no_show": employees_data[0].no_show,
                    "non_satisfactory": employees_data[0].non_satisfactory,
                    "dnr": employees_data[0].dnr,
                    "replaced": "",
                    "child_name": emp_data[i].child_name,
                    "employee_id": emp_data[i].employee,
                    "removed": emp_data[i].remove,
                    "job_title": emp_data[i].job_category,
                    "job_start_time": emp_data[i].job_start_time,
                }
                emp_list.append(emp_dic)

        replaced = replaced_employees(job_order, frappe.session.user)
        return emp_list + replaced
    except Exception as e:
        frappe.log_error(e, "Approved Employee")


# ------------------------------------#
def replaced_employees(job_order, user=None):
    try:
        data, emp = [], []
        if user:
            assigned_emp = f""" select `tabAssign Employee`.company, `tabAssign Employee`.name as name, `tabReplaced Employee`.employee_name as employee_name, `tabReplaced Employee`.employee, `tabReplaced Employee`.name as child_name, `tabReplaced Employee`.job_start_time as job_start_time, `tabReplaced Employee`.job_category as job_title from `tabAssign Employee`, `tabReplaced Employee` where `tabAssign Employee`.name = `tabReplaced Employee`.parent and job_order = "{job_order}" and tag_status = "Approved" and `tabAssign Employee`.company in (select company from `tabEmployee` where email = '{frappe.session.user}') order by company, employee_name"""
        else:
            assigned_emp = f""" select `tabAssign Employee`.company, `tabAssign Employee`.name as name, `tabReplaced Employee`.employee_name as employee_name, `tabReplaced Employee`.employee, `tabReplaced Employee`.name as child_name, `tabReplaced Employee`.job_start_time as job_start_time, `tabReplaced Employee`.job_category as job_title from `tabAssign Employee`, `tabReplaced Employee` where `tabAssign Employee`.name = `tabReplaced Employee`.parent and job_order = "{job_order}" and tag_status = "Approved" order by company, employee_name"""

        emp_data = frappe.db.sql(assigned_emp, as_dict=1)
        for e in emp_data:
            if e.employee_name and e.employee not in emp:
                data.append(
                    {
                        "assign_name": e.name,
                        "staff_company": e.company,
                        "employee": e.employee_name,
                        "replaced": "Replaced",
                        "child_name": e.child_name,
                        "job_title": e.job_title,
                        "job_start_time": e.job_start_time,
                    }
                )
                emp.append(e.employee)

        return data
    except Exception as e:
        return []


# -----------------------------------#


def unshare_job_order(job):
    creation = str(job.creation).split(" ")
    if (
        job.bid > 0
        and job.staff_org_claimed
        and (
            job.total_no_of_workers == job.total_workers_filled
            or str(job.from_date) != creation[0]
        )
    ):
        comp_name = f""" select distinct company from `tabUser` where organization_type='Staffing' and email in (select user from `tabDocShare` where share_doctype='Job Order' and share_name='{job.name}' )"""
        comp_data = frappe.db.sql(comp_name, as_list=True)
        for i in comp_data:
            if i[0] not in job.staff_org_claimed:
                user_name = f'select name from `tabUser` where company="{i[0]}"'
                user_data = frappe.db.sql(user_name, as_list=0)
                for i in user_data:
                    del_data = f'''DELETE FROM `tabDocShare` where share_doctype='Job Order' and share_name="{job.name}" and user="{i[0]}"'''
                    frappe.db.sql(del_data)
                    frappe.db.commit()


# checking condition for job_order_status in job order list
@frappe.whitelist()
def vals(name, comp):
    """# claims=frappe.db.get_value(jobOrder,name,'claim')"""

    claims = frappe.db.sql(
        f'''select claim from `tabJob Order` where name = "{name}"'''
    )
    if claims[0][0] is not None and comp in claims[0][0].split('~'):
        return "success"


@frappe.whitelist(allow_guest=False)
def receive_hire_notification(
    user,
    company_type,
    hiring_org,
    job_order,
    staffing_org,
    emp_detail,
    doc_name,
    worker_fill,
):
    try:
        if company_type == "Staffing" and user == frappe.session.user:
            dat = f'update `tabAssign Employee` set tag_status="Approved" where name="{doc_name}"'
            frappe.db.sql(dat)
            frappe.db.commit()
            job_sql = '''select select_job,name from `tabJob Order` where name = "{}"'''.format(
                job_order
            )
            job_detail = frappe.db.sql(job_sql, as_dict=1)
            lst_sql = """ select user_id from `tabEmployee` where company = "{}" and user_id IS NOT NULL """.format(
                hiring_org
            )
            user_list = frappe.db.sql(lst_sql, as_list=1)
            l = [l[0] for l in user_list]
            for user in l:
                add(
                    assignEmployees,
                    doc_name,
                    user,
                    read=1,
                    write=0,
                    share=0,
                    everyone=0,
                )
            sub = "Employee Assigned"
            msg = f'{staffing_org} has assigned employees for {job_detail[0]["name"]}'
            user_list_app, user_list_mail = get_mail_list(
                l, app_field="assign_emp_app", mail_field="assign_emp_mail"
            )
            make_system_notification(user_list_app, msg, assignEmployees, doc_name, sub)
            link = f'  href="{sitename}/app/assign-employee/{doc_name}" '
            joborder_email_template(sub, msg, user_list_mail, link)
            return 1
        else:
            return "Something Went Access"
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.db.rollback()


@frappe.whitelist()
def jobcategory_data(job_order):
    sql = f"""select job_categories from tabEmployee where name='{job_order}'"""
    data = frappe.db.sql(sql)
    sql1 = """ select job_category from `tabJob Category` where parent='{0}' and job_category!='{1}'""".format(
        job_order, data[0][0].split("+")[0] if data else None
    )
    return frappe.db.sql(sql1)


# number of claims approved for job order
@frappe.whitelist()
def approved_claims(workers, jo):
    data1 = f'select sum(approved_no_of_workers) from `tabClaim Order` where job_order="{jo}"'
    sq1 = frappe.db.sql(data1, as_list=True)
    if sq1[0][0] == None:
        sq1[0][0] = 0
    value = int(workers) - int(sq1[0][0])
    if value > 0:
        return 1
    return 0


@frappe.whitelist()
def claim_order_company(user_name, claimed, job_order):
    """
    The function `claim_order_company` checks if a user has permission to claim an order based on their
    company affiliation.
    
    :param user_name: The user_name parameter is the username of the user who is claiming the order
    :param claimed: The "claimed" parameter is a string that contains multiple company names separated
    by a tilde (~) character
    :return: either "success" or "unsuccess" based on certain conditions.
    """
    try:
        job_doc = frappe.get_doc(jobOrder, job_order)
        if user_name!=frappe.session.user or not frappe.has_permission(job_doc, "read", throw=False):
            frappe.throw('Insufficient Permission for user')
        data = f'select company from `tabEmployee` where email="{user_name}"'
        sq = frappe.db.sql(data, as_list=True)
        for i in sq:
            if i[0] in claimed:
                return "success"
        return "unsuccess"
    except Exception as e:
        print(e, frappe.get_traceback())


@frappe.whitelist(allow_guest=False)
def staffing_exclussive_org_name(job_order):
    sql = """ select staff_company from `tabJob Order` where name='{0}' """.format(
        job_order
    )
    return frappe.db.sql(sql, as_dict=1)


@frappe.whitelist()
def checkingdesignationandorganization(designation_name, company=None):
    sql = "select name,designation,organization from `tabDesignation` where designation = '{0}' and organization = '{1}' ".format(
        designation_name, company
    )
    if len(frappe.db.sql(sql, as_dict=True)) >= 1:
        return False
    return True


@frappe.whitelist()
def checkingjobtitleandcompany(job_titless, company=None):
    sql = "select name,job_titless_name,company from `tabItem` where job_titless_name = '{0}' and company = '{1}' ".format(
        job_titless, company
    )
    if len(frappe.db.sql(sql, as_dict=True)) >= 1:
        return False
    return True


@frappe.whitelist()
def company_exist(hiring_company):
    comp = f'select name from `tabCompany` where name="{hiring_company}"'
    sql = frappe.db.sql(comp, as_list=True)
    if sql:
        return "yes"
    else:
        return "no"


@frappe.whitelist(allow_guest=False)
def claim_order_insert(job_order):
    """
    This function inserts a claim order into the database based on a job order and sends notifications
    to relevant users.

    :param job_order: The parameter `job_order` is a JSON string containing information about a job
    order, such as the company name, job titles, number of workers, pay rate, and estimated duration.
    The function `claim_order_insert` parses this JSON string and creates a new document of type
    `claimOrder` in
    :return: the integer value 1.
    """
    try:
        job_order = json.loads(job_order)
        staffing_company = frappe.db.get_value(
            "Company", {"name": job_order["company"]}, ["parent_staffing"]
        )
        doc = frappe.get_doc(
            {
                "doctype": claimOrder,
                "agree_to_contract": 1,
                "hiring_organization": job_order["company"],
                "contract_add_on": claimOrder,
                "job_order": job_order["name"],
                "e_signature": job_order["e_signature_full_name"],
                "staffing_organization": staffing_company,
                "approved_no_of_workers": job_order["total_no_of_workers"],
                "staff_claims_no": job_order["total_no_of_workers"]
            }
        )
        for row in job_order["multiple_job_titles"]:
            doc.append(
                "multiple_job_titles",
                {
                    "job_title": row["select_job"],
                    "industry": row["category"],
                    "no_of_workers_joborder": row["no_of_workers"],
                    "no_of_remaining_employee": 0,
                    "approved_no_of_workers": row["no_of_workers"],
                    "staff_claims_no": row["no_of_workers"],
                    "employee_pay_rate": round(row["per_hour"] + row["flat_rate"], 2),
                    "start_time": row["job_start_time"],
                    "duration": row["estimated_hours_per_day"],
                },
            )
        doc.insert()
        sql1 = '''select email from `tabUser` where  company = "{}"'''.format(
            job_order["company"]
        )
        hiring_list = frappe.db.sql(sql1, as_dict=1)
        for i in hiring_list:
            add(
                claimOrder,
                doc.name,
                user=i["email"],
                share=1,
                read=1,
                write=1,
                flags={"ignore_share_permission": 1},
            )
        sql = """ UPDATE `tabJob Order` SET bid = 1, claim="{0}", staff_org_claimed="{0}", total_workers_filled={2} WHERE name="{1}" """.format(
            staffing_company, job_order["name"], job_order["total_no_of_workers"]
        )
        frappe.db.sql(sql)
        frappe.db.commit()
        return 1
    except Exception as e:
        print(e, frappe.get_traceback())


@frappe.whitelist(allow_guest=False)
def employee_company(doc, method):
    if not doc.user_id:
        comp_doc = frappe.get_doc("Company", doc.company)
        comp_doc.append(
            "employees",
            {
                "employee": doc.name,
                "employee_name": doc.employee_name,
                "resume": doc.resume if doc.resume else "",
            },
        )
        comp_doc.save(ignore_permissions=True)


@frappe.whitelist(allow_guest=False)
def update_company_employee(doc_name, employee_company):
    emp_doc = frappe.get_doc("Employee", doc_name)
    employee_list = frappe.db.get_list(
        "Employee Assign Name",
        filters={"parent": employee_company, "employee": doc_name},
        fields={"name"},
    )
    for employee in employee_list:
        child_employee_doc = frappe.get_doc("Employee Assign Name", employee)
        if emp_doc.employee_name != child_employee_doc.employee_name:
            child_employee_doc.db_set("employee_name", emp_doc.employee_name)
        if emp_doc.resume != child_employee_doc.resume:
            child_employee_doc.db_set("resume", emp_doc.resume)
    frappe.db.commit()


@frappe.whitelist()
def user_company(doctype, txt, searchfield, page_len, start, filters):
    try:
        owner_company = filters.get("owner_company")
        sql = (
            """ select name from `tabCompany` where organization_type="{0}" """.format(
                owner_company
            )
        )
        return frappe.db.sql(sql)
    except Exception as e:
        frappe.log_error(e, "User Company Error")
        frappe.throw(e)


@frappe.whitelist()
def send_email1(
    user,
    company_type,
    sid,
    name,
    doctype,
    recepients,
    subject=None,
    content=None,
    cc=None,
    bcc=None,
):
    site = frappe.utils.get_url().split("/")
    sitename = site[0] + "//" + site[2]
    if user == frappe.session.user:
        # frappe.sendmail(recipients=recepients,cc=cc, bcc=bcc,subject=subject, reference_name=name, message=content, template="email_template_custom", args = dict(sitename=sitename,content=content,subject=subject))
        args = dict(sitename=sitename, content=content, subject=subject)
        template = "email_template_custom"
        ses_email_send(emails=recepients, subject=subject, args=args, template=template)
        frappe.get_doc(
            {
                "doctype": "Communication",
                "subject": subject,
                "content": content,
                "sender": user,
                "recipients": recepients,
                "cc": cc or None,
                "bcc": bcc or None,
                "reference_doctype": doctype,
                "reference_name": name,
            }
        ).insert(ignore_permissions=True)
    else:
        frappe.throw("Insufficient Permission for User")


@frappe.whitelist(allow_guest=False)
def hide_decrypt_ssn(doctype, frm=None):
    try:
        emp = frappe.get_doc(doctype, frm)
        return not (bool(emp.ssn))
    except Exception:
        frappe.log_error("No Employee in Database", "Warning")


@frappe.whitelist()
def staff_own_job_order(job_order, emp_detail, doc_name, staffing_org):
    try:
        staff_job_order = frappe.get_doc(jobOrder, job_order)
        dat = f'update `tabAssign Employee` set tag_status="Approved" where name="{doc_name}"'
        frappe.db.sql(dat)
        frappe.db.commit()
        frappe.db.set_value(
            jobOrder,
            job_order,
            "total_workers_filled",
            (int(emp_detail) + int(staff_job_order.total_workers_filled)),
        )
        frappe.db.set_value(jobOrder, job_order, "claim", (str(staffing_org)))
        claimed = (
            staff_job_order.staff_org_claimed
            if staff_job_order.staff_org_claimed
            else ""
        )
        if len(claimed) == 0:
            frappe.db.set_value(
                jobOrder,
                job_order,
                "staff_org_claimed",
                (str(claimed) + str(staffing_org)),
            )
        else:
            frappe.db.set_value(
                jobOrder,
                job_order,
                "staff_org_claimed",
                (str(claimed) + "~" + str(staffing_org)),
            )
        return "success"
    except Exception as e:
        frappe.log_error(e, "Staff Job Order")
        frappe.throw(e)


@frappe.whitelist()
def update_jobtitle(
    company, job_title, description, price, name, industry, job_title_id=None
):
    try:
        if company:
            if job_title_id:
                sql = """ UPDATE `tabJob Titles` SET job_titles = "{0}" ,description='{1}',  wages='{2}' ,industry_type='{3}' where name="{4}" """.format(
                    job_title, description, price, industry, job_title_id
                )
                frappe.db.sql(sql)
                frappe.db.commit()
                return "success"

            job_ti = frappe.get_doc(
                dict(
                    doctype="Job Titles",
                    parenttype="Company",
                    parentfield="job_titles",
                    parent=company,
                    job_titles=job_title,
                    description=description,
                    wages=price,
                    industry_type=industry,
                )
            )
            job_ti.insert(ignore_permissions=True)

            sql = """ UPDATE `tabItem` SET job_title_id = "{0}"  where name="{1}" """.format(
                job_ti.name, name
            )
            frappe.db.sql(sql)
            frappe.db.commit()
            return "success"
    except Exception as e:
        frappe.log_error(e, "update JOb Titles")
        frappe.throw(e)


@frappe.whitelist(allow_guest=True)
def hiring_category_list(hiring_company):
    sql = (
        """ select industry_type from `tabIndustry Types` where parent='{0}' """.format(
            hiring_company
        )
    )
    return frappe.db.sql(sql, as_dict=True)


@frappe.whitelist(allow_guest=True)
def jobtitle_list(company):
    sql = """ select job_titles from `tabJob Titles` where parent = '{0}' """.format(
        company
    )
    return frappe.db.sql(sql, as_dict=True)


import json


@frappe.whitelist()
def get_jobtitle_list_page(doctype, txt, searchfield, page_len, start, filters):
    try:
        company = filters.get("company")
        data = filters.get("data")
        title_list = filters.get("title_list")
        value = ""
        for index, i in enumerate(title_list):
            if index >= 1:
                value = value + "'" + "," + "'" + i
            else:
                value = value + i
        if len(data) > 0:
            if len(data) == 1:
                sql = """ select name from `tabItem` where ((company is null) or (company = '{0}') or LENGTH(company)=0) and industry IN ('{1}') and (name NOT IN ('{2}') and name like '%%{3}%%')""".format(
                    company, data[0], value, "%s" % txt
                )
                return frappe.db.sql(sql)
            else:
                data = tuple(data)
                sql = """ select name from `tabItem` where ((company is null) or (company = '{0}') or LENGTH(company)=0) and industry IN {1} and (name NOT IN ('{2}') and name like '%%{3}%%')""".format(
                    company, data, value, "%s" % txt
                )
                return frappe.db.sql(sql)
        else:
            sql = """ select name from `tabItem` where ((company is null) or (company = '{0}') or LENGTH(company)=0) and industry is null and (name NOT IN ('{1}') and name like '%%{2}%%')""".format(
                company, value, "%s" % txt
            )
            return frappe.db.sql(sql)

    except Exception as e:
        frappe.msgprint(e)
        return tuple()


@frappe.whitelist()
def filter_jobsite(doctype, txt, searchfield, page_len, start, filters):
    try:
        company = filters.get("company")
        site_list = filters.get("site_list")
        value = ""
        for index, i in enumerate(site_list):
            if index >= 1:
                value = value + "'" + "," + "'" + i
            else:
                value = value + i
        sql = """select name from `tabJob Site` where company = '{0}' and (name NOT IN ('{1}') and name like '%%{2}%%')""".format(
            company, value, "%s" % txt
        )
        return frappe.db.sql(sql)
    except Exception as e:
        frappe.msgprint(e)
        return tuple()


@frappe.whitelist()
def get_industrytype_list_page(doctype, txt, searchfield, page_len, start, filters):
    try:
        data = filters.get("data")
        if len(data) == 1:
            sql = """ select name from `tabIndustry Type` where name in ('{0}')  """.format(
                data[0]
            )
            return frappe.db.sql(sql)
        else:
            data = tuple(data)

            sql = """ select name from `tabIndustry Type` where name in {0}  """.format(
                data
            )
            return frappe.db.sql(sql)
    except Exception as e:
        frappe.msgprint(e)
        return tuple()


@frappe.whitelist()
def my_used_job_title(company_name, company_type):
    z = []
    if company_type == "Hiring" or company_type == exclusive_hiring:
        l = frappe.db.sql(
            'select job_titles from `tabJob Titles` where parent="{0}"'.format(
                company_name
            ),
            as_list=1,
        )
        for i in l:
            z.append(i[0])
    elif company_type == "Staffing":
        exc_company = frappe.db.sql(
            'select job_title,job_site,staffing_company,hiring_company from `tabEmployee Pay Rate` where owner="{0}" '.format(
                frappe.session.user
            ),
            as_list=1,
        )
        for i in exc_company:
            z.append(i[0])
    else:
        return "TAG"
    return list(set(z))


def hiring_auto_approve(
    hiring_type, job_order, employee_filled, staffing_org, doc_name
):
    if hiring_type.organization_type == exclusive_hiring:
        job = frappe.get_doc(jobOrder, job_order)
        claimed = job.staff_org_claimed if job.staff_org_claimed else ""
        frappe.db.set_value(
            jobOrder, job_order, "total_workers_filled", (int(employee_filled))
        )
        if len(claimed) == 0:
            frappe.db.set_value(
                jobOrder,
                job_order,
                "staff_org_claimed",
                (str(claimed) + str(staffing_org)),
            )
        else:
            frappe.db.set_value(
                jobOrder,
                job_order,
                "staff_org_claimed",
                (str(claimed) + "~" + str(staffing_org)),
            )

        assign_emp_status_data = f'update `tabAssign Employee` set tag_status="Approved" where name="{doc_name}"'
        frappe.db.sql(assign_emp_status_data)
        frappe.db.commit()


@frappe.whitelist(allow_guest=False)
def previous_worker_count(name, previous_worker):
    try:
        frappe.db.set_value(
            assignEmployees, name, "previous_worker", int(previous_worker)
        )
        return "Something Went Access"
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.db.rollback()


@frappe.whitelist()
def job_site_add(doc, method):
    try:
        if doc.company:
            new_site = frappe.get_doc("Company", doc.company)
            new_site.append("job_site", {"job_site": doc.name})
            new_site.save(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(e, "Job Site Add Error")


@frappe.whitelist()
def job_title_add(doc, method):
    try:
        if doc.company:
            new_title = frappe.get_doc("Company", doc.company)
            new_title.append(
                "job_titles",
                {
                    "industry_type": doc.industry,
                    "job_titles": doc.name,
                    "wages": doc.rate,
                    "description": doc.descriptions,
                },
            )
            for i in new_title.industry_type:
                if i.industry_type == doc.industry:
                    new_title.save(ignore_permissions=True)
                    break
            else:
                new_title.append("industry_type", {"industry_type": doc.industry})
                new_title.save(ignore_permissions=True)
    except Exception as e:
        frappe.error_log(e, "Job Title Add Error")


@frappe.whitelist()
def job_industry_type_add(company, user_industry):
    new_industry = frappe.get_doc("Company", company)
    for i in new_industry.industry_type:
        if i.industry_type == user_industry:
            break
    else:
        new_industry.append("industry_type", {"industry_type": user_industry})
        new_industry.save(ignore_permissions=True)


@frappe.whitelist()
def new_activity(activity):
    if not frappe.db.exists(activityType, {"name": activity}):
        docs = frappe.new_doc(activityType)
        docs.activity_type = activity
        docs.insert()


@frappe.whitelist()
def new_job_title_company(job_name, company, industry, rate, description):
    try:
        if company:
            new_title = frappe.get_doc("Company", company)
            for i in new_title.job_titles:
                if i.job_titles == job_name:
                    break
            else:
                new_title.append(
                    "job_titles",
                    {
                        "industry_type": industry,
                        "job_titles": job_name,
                        "wages": rate,
                        "description": description,
                    },
                )
            for i in new_title.industry_type:
                if i.industry_type == industry:
                    new_title.save(ignore_permissions=True)
                    break
            else:
                new_title.append("industry_type", {"industry_type": industry})
                new_title.save(ignore_permissions=True)
    except Exception as e:
        frappe.error_log(e, "Job Title Add Error")


@frappe.whitelist()
def employee_work_history(employee_no):
    sql = f'select name,job_order_detail,from_date,job_name,company,sum(total_hours) as total_hours,workflow_state from `tabTimesheet` where employee="{employee_no}" and workflow_state in ("Approved","Approval Request","Denied") group by job_order_detail order by job_order_detail desc'
    my_data = frappe.db.sql(sql, as_dict=True)
    if len(my_data) == 0:
        return "No Record"
    else:
        for i in range(len(my_data)):
            status = frappe.db.sql(
                'select workflow_state from `tabTimesheet` where job_order_detail="{0}" and employee="{1}" '.format(
                    my_data[i]["job_order_detail"], employee_no
                ),
                as_list=1,
            )
            if [approvalRequest] in status or ["Denied"] in status:
                my_data[i]["workflow_state"] = approvalRequest
        return my_data


@frappe.whitelist()
def employee_timesheets(employee_no):
    sql = f'select name,date_of_timesheet,workflow_state,job_title,job_order_detail,total_hours, status_of_work_order from`tabTimesheet` where employee="{employee_no}" and workflow_state in ("Approved","Approval Request","Denied")'
    my_data = frappe.db.sql(sql, as_dict=True)
    if len(my_data) == 0:
        return "No Record"
    else:
        return my_data


@frappe.whitelist(allow_guest=True)
def get_update_password_user(key):
    try:
        result = frappe._dict()
        if key:
            result.user = frappe.db.get_value("User", {"reset_password_key": key})
            if not result.user:
                return "set"
            else:
                user_type = frappe.get_doc("User", result.user)
                return user_type.organization_type
    except Exception as e:
        print(e, frappe.get_traceback())


@frappe.whitelist()
def update_lat_lng(company):
    try:
        frappe.enqueue(
            "tag_workflow.tag_data.update_old_emp_lat_lng",
            queue="long",
            job_name=company,
            is_async=True,
            company=company,
        )
    except Exception as e:
        frappe.msgprint(e)


def update_old_emp_lat_lng(company, employee_id=None):
    try:
        count = 0
        print("*------lat lng updtae--------------------------*\n")
        if employee_id != None:
            my_data = frappe.db.sql(
                """ select name, state, city, zip from `tabEmployee` where company = '{0}' and name ='{1}'  """.format(
                    company, employee_id
                ),
                as_dict=1,
            )
        else:
            my_data = frappe.db.sql(
                """ select name, state, city, zip from `tabEmployee` where (lat is null or lat ='' or lng is null or lng='') and employee_number is null and city is not null and state is not null and company = %s """,
                company,
                as_dict=1,
            )
        for d in my_data:
            address = (
                d.city
                + ", "
                + d.state
                + ", "
                + (d.zip if d.zip != 0 and d.zip is not None else "")
            )
            google_location_data_url = GOOGLE_API_URL + address
            if count % 80 == 0:
                time.sleep(5)
            google_response = requests.get(google_location_data_url)
            location_data = google_response.json()
            if (
                google_response.status_code == 200
                and len(location_data) > 0
                and len(location_data["results"]) > 0
            ):
                lat, lng = emp_location_data(location_data)
                frappe.db.set_value("Employee", d.name, "lat", lat)
                frappe.db.set_value("Employee", d.name, "lng", lng)
            count += 1
    except Exception as e:
        frappe.log_error(e, "longitude latitude error")
        print(e)


def emp_location_data(address_dt):
    try:
        lat, lng = "", ""
        if len(address_dt["results"]) > 0:
            location = address_dt["results"][0]["geometry"]["location"]
            lat = location["lat"]
            lng = location["lng"]
        return lat, lng
    except Exception as e:
        frappe.log_error(e, "Longitude latitude address")
        return "", ""


def save_job_order_value(job_order, staff_company):
    doc = frappe.get_doc(jobOrder, job_order)
    doc.company_type = non_exlusive
    doc.is_single_share = 1
    doc.claim = staff_company
    doc.save(ignore_permissions=True)


@frappe.whitelist()
def update_order_status(job_order_name):
    try:
        job_order_details_mul_title_query = f'''select jo.name,jo.from_date,jo.to_date,MIN(multi.job_start_time) AS min_job_start_time,jo.bid,jo.staff_org_claimed,jo.order_status,jo.creation,jo.total_no_of_workers,multi.worker_filled
                            from `tabJob Order` jo left join `tabMultiple Job Titles` multi on multi.parent = jo.name where 
                            jo.name="{job_order_name}"'''
        job_order_details_mul_title_data = frappe.db.sql(
            job_order_details_mul_title_query, as_dict=1
        )
        current_date = datetime.date.today()

        for each in job_order_details_mul_title_data:
            if each.order_status =='Canceled': continue
            start = each.from_date if each.from_date else ""
            end = each.to_date if each.to_date else ""
            current_time = (
                datetime.datetime.now(timezone(TIMEZONE))
                .time()
                .strftime("%H:%M:%S")
            )
            current_time = datetime.datetime.strptime(current_time, "%H:%M:%S").time()
            current_time = timedelta(
                hours=current_time.hour,
                minutes=current_time.minute,
                seconds=current_time.second,
            )
            if type(start) is not str:
                set_job_order_status(current_date, each, start, end, current_time)
        update_company_type(job_order_name)
    except Exception as e:
        frappe.msgprint(e)


def set_job_order_status(current_date, each, start, end, current_time):
    time_now = datetime.datetime.now(timezone(TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    if start < current_date <= end:
        order_status = 'Ongoing'
    elif current_date < start:
        order_status = 'Upcoming'
    elif current_date > end:
        order_status = 'Completed'
    elif start == current_date and current_time >= each.min_job_start_time:
        order_status = 'Ongoing'
    else:
        order_status = 'Upcoming'

    query = f"""
        UPDATE `tabJob Order`
        SET order_status = '{order_status}',
            modified_by = '{frappe.session.user}',
            modified = '{time_now}'
        WHERE name = '{each.name}'
    """
    claim_query = f"""
        UPDATE `tabClaim Order`
        SET job_order_status = '{order_status}'
        WHERE job_order = '{each.name}'
    """
    assign_query = f"""
        UPDATE `tabAssign Employee`
        SET job_order_status = '{order_status}'
        WHERE job_order = '{each.name}'
    """
    frappe.db.sql(query)
    frappe.db.sql(claim_query)
    frappe.db.sql(assign_query)
    frappe.db.commit()

@frappe.whitelist()
def update_section_status(company, jo):
    doc = frappe.get_doc(jobOrder, jo)
    sql1 = """ select docstatus from `tabSales Invoice` where job_order = '{0}' and company= "{1}" """.format(
        jo, company
    )
    jo_state = frappe.db.sql(sql1, as_dict=1)
    if doc.order_status=='Canceled': return 'Canceled'
    for i in jo_state:
        if i["docstatus"] == 1 and doc.order_status == "Completed":
            return "Complete"

    sql = """ select workflow_state from `tabTimesheet` where job_order_detail = '{0}' and employee_company= "{1}" """.format(
        jo, company
    )
    timesheet_state = frappe.db.sql(sql, as_dict=1)
    timesheet_state_data = []
    for i in timesheet_state:
        timesheet_state_data.append(i["workflow_state"])
    if "Approved" in timesheet_state_data:
        return "Approved"

    elif approvalRequest in timesheet_state_data:
        return approvalRequest


@frappe.whitelist()
def update_lat_lng_required(company, employee_id):
    try:
        update_old_emp_lat_lng(company, employee_id)
    except Exception as e:
        frappe.error_log(e, "Employee Lat Lng error")


def no_contact_by(company):
    try:
        sql = """select name from `tabUser` where company = '{0}'""".format(company)
        users = frappe.db.sql(sql, as_list=True)
        recipients = []
        if len(users) > 0:
            for user in users:
                recipients.append(user[0])
        return recipients
    except Exception as e:
        frappe.log_error(e, "Failed to retrieve users of a company for Lead Follow Up")


def lead_follow_up():
    try:
        sql = """select name, contact_date, contact_by, owner_company, lead_name, company_name from tabLead"""
        data = frappe.db.sql(sql, as_list=True)
        for i in data:
            if i[1] and (
                (getdate(i[1]) - datetime.date.today()).days == 1
                or (getdate(i[1]) == datetime.date.today())
            ):
                if not i[2]:
                    recipients = no_contact_by(i[3])
                else:
                    recipients = []
                    recipients.append(i[2])
                sub = "Follow Up Reminder"
                msg = f"Reminder to follow up with {i[4]} at {i[5]} on {i[1]}. Contact information and lead notes can be found in TAG."
                env_url = frappe.get_site_config().env_url
                link = f'href="{env_url}/app/lead/{i[0]}"'
                # make_system_notification(users=recipients,message=msg,doctype="Lead",docname=i[0],subject=sub)

                # enqueue(method=frappe.sendmail, recipients=recipients, subject=sub, reference_name=i[0], message=msg, template="email_template_custom", args = {"sitename":env_url,"content":msg,"subject":sub, "lead": "true", "link":link})
                recipients_app, recipients_mail = get_mail_list(
                    recipients, app_field="crm_app", mail_field="crm_mail"
                )
                template = "email_template_custom"
                args = {
                    "sitename": env_url,
                    "content": msg,
                    "subject": sub,
                    "lead": "true",
                    "link": link,
                }
                enqueue(
                    method=ses_email_send,
                    emails=recipients_mail,
                    template=template,
                    subject=sub,
                    args=args,
                )

                make_system_notification(
                    users=recipients_app,
                    message=msg,
                    doctype="Lead",
                    docname=i[0],
                    subject=sub,
                )
                # enqueue(method=frappe.sendmail, recipients=recipients_mail, subject=sub, reference_name=i[0], message=msg, template="email_template_custom", args = {"sitename":env_url,"content":msg,"subject":sub, "lead": "true", "link":link})
    except Exception as e:
        frappe.log_error(e, "Lead Follow Up")


@frappe.whitelist()
def update_complete_address(data):
    try:
        data = json.loads(data)
        address = (
            data["street_number"]
            + ", "
            + data["route"]
            + ", "
            + data["locality"]
            + ", "
            + data["administrative_area_level_1"]
            + ", "
            + data["postal_code"]
        )
        google_location_data_url = GOOGLE_API_URL + address
        google_response = requests.get(google_location_data_url)
        location_data = google_response.json()
        if (
            google_response.status_code == 200
            and len(location_data) > 0
            and len(location_data["results"]) > 0
        ):
            return location_data["results"][0]["formatted_address"]
        else:
            return "No Data"
    except Exception as e:
        frappe.log_error(e, "Update complete address")
        print(e)


@frappe.whitelist()
def timesheet_company(hiring_company):
    try:
        if hiring_company == "" or hiring_company == "TAG":
            sql = """SELECT DISTINCT(employee_company) FROM tabTimesheet ORDER BY employee_company"""
        else:
            sql = """SELECT DISTINCT(employee_company) FROM tabTimesheet WHERE company = "{0}" ORDER BY employee_company""".format(
                hiring_company
            )
        companies = frappe.db.sql(sql, as_dict=True)
        data = [c["employee_company"] for c in companies]
        return "\n".join(data)
    except Exception as e:
        frappe.log_error(e, "Staffing Company Filter Error on Timesheet")
        print(e)


@frappe.whitelist()
def job_title_list():
    try:
        sql = """SELECT name FROM `tabActivity Type` ORDER BY name"""
        job_titles = frappe.db.sql(sql, as_dict=True)
        data = [title["name"] for title in job_titles]
        return "\n".join(data)
    except Exception as e:
        frappe.log_error(e, "Staffing Company Filter Error on Timesheet")
        print(e)


def update_company_type(job_order_name):
    try:
        job_order = frappe.get_doc(jobOrder, job_order_name)
        if job_order.company_type == "":
            company_type = frappe.get_doc("Company", job_order.company)
            if company_type.organization_type == "Hiring":
                job_order.company_type = non_exlusive
            else:
                job_order.company_type = "Exclusive"
            job_order.save()
    except Exception as e:
        frappe.log_error(e, "Company Type update error")


@frappe.whitelist(allow_guest=False)
def remove_emp_from_order(assign_emp, employee_name, job_order, removed, job_title, start_time, user):
    try:
        lead_0 = start_time.split(":")
        if lead_0[0][0]=='0' and len(lead_0[0])==2:
            start_time = start_time[1:]
            
        job_order_name = frappe.get_doc(jobOrder, job_order)
        assign_doc = frappe.get_doc(assignEmployees, assign_emp)
        employee_name = frappe.get_doc("Employee", employee_name)
        if user != frappe.session.user or frappe.get_value("User", user, "company") != assign_doc.company:
            frappe.throw(INSUFF_PERM + frappe.session.user)
        if int(removed) == 1:
            if (job_order_name.total_no_of_workers) < (
                job_order_name.total_workers_filled + 1
            ):
                return "emp_not_required"
            else:
                job_order_name.total_workers_filled = (
                    job_order_name.total_workers_filled + 1
                )
                job_order_name.save(ignore_permissions=True)
                unremove_assign_emp(employee_name, assign_doc, job_title, start_time)
                update_vals = f'update `tabAssign Employee Details` set remove_employee=0 where parent="{assign_doc.name}" and employee="{employee_name.name}" and job_category="{job_title}" and job_start_time = "{start_time}"'
                frappe.db.sql(update_vals)
                frappe.db.commit()
                return "unremoved"
        else:
            lst_sql = """select user_id from `tabEmployee` where company = "{0}" and user_id IS NOT NULL""".format(
                job_order_name.company
            )
            user_list = frappe.db.sql(lst_sql)
            user_list = [l[0] for l in user_list]
            user_list_app, user_list_mail = get_mail_list(
                user_list, app_field="remove_emp_app", mail_field="remove_emp_mail"
            )
            sub = "Employee Removed"
            msg = f"{employee_name.employee_name} from {assign_doc.company} was removed from {job_order}.  "
            make_system_notification(user_list_app, msg, jobOrder, job_order, sub)
            link = f'  href="{sitename}/app/job-order/{job_order}" '
            args={"sitename": sitename, "content": msg, "subject": sub, "link": link}
            ses_email_send(emails=user_list_mail, subject=sub, args=args, template="email_template_custom")
            job_order_name.total_workers_filled = job_order_name.total_workers_filled - 1
            job_order_name.save(ignore_permissions=True)
            remove_assign_employee(employee_name, job_order_name, assign_doc, job_title, start_time)
            update_vals = f'update `tabAssign Employee Details` set remove_employee=1 where parent="{assign_doc.name}" and employee="{employee_name.name}" and job_category="{job_title}" and job_start_time = "{start_time}"'

            frappe.db.sql(update_vals)
            frappe.db.commit()
            return "removed"
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.log_error(e, "Staffing Company employee remove error")


@frappe.whitelist()
def remove_emp_from_order_hiring(list_array_removed_emps):
    try:
        list_array_removed_emps = json.loads(list_array_removed_emps)
        notification_helper_data = {}
        for each in list_array_removed_emps:
            employee_name = each[0]
            job_order  =    each[1]
            removed  =  each[2]
            job_title  =  each[3]
            start_time  =  each[4]
            lead_0 = start_time.split(":")
            if lead_0[0][0]=='0' and len(lead_0[0])==2:
                start_time = start_time[1:]
            assign_emp = frappe.db.sql(f''' select aed.parent,ae.company from `tabAssign Employee Details` aed join `tabAssign Employee` ae
            on ae.name=aed.parent
            where aed.employee="{employee_name}" and aed.job_category="{job_title}" 
            and aed.job_start_time="{start_time}" and aed.parent in (select name from `tabAssign Employee` where job_order="{job_order}")''')
            job_order_name = frappe.get_doc(jobOrder, job_order)
            assign_doc = frappe.get_doc(assignEmployees, assign_emp[0][0])
            employee_name = frappe.get_doc("Employee", employee_name)

            if int(removed) == 1:
                notification_helper_key = f'{job_order}~{job_title}~{assign_emp[0][1]}'
                if notification_helper_data.get(notification_helper_key):
                    notification_helper_data[notification_helper_key] += 1
                else:
                    notification_helper_data[notification_helper_key] = 1
                remove_assign_employee(employee_name, job_order_name, assign_doc, job_title, start_time, removed_by_hiring=1,removed_by_hiring_date=str(datetime.datetime.now(timezone(TIMEZONE)).date()))
                update_vals = f'''update `tabAssign Employee Details` set remove_employee=1,removed_by_hiring = 1,removed_by_hiring_date = "{str(datetime.datetime.now(timezone(TIMEZONE))
                                .date())}" where parent="{assign_doc.name}" and employee="{employee_name.name}" and job_category="{job_title}" and job_start_time = "{start_time}"'''
                frappe.db.sql(update_vals)
                frappe.db.commit()            
            frappe.db.commit()
        for each_key in notification_helper_data:
            staff_company = each_key.split("~")[2]
            job_title = each_key.split("~")[1]
            job_order = each_key.split("~")[0]
            reduced_workers_count = notification_helper_data[each_key]
            lst_sql = """ select user_id from `tabEmployee` where company = "{0}" and user_id IS NOT NULL """.format(
            staff_company
            )
            user_list = frappe.db.sql(lst_sql)
            user_list = [l[0] for l in user_list]
            user_list_app, user_list_mail = get_mail_list(
                user_list, app_field="jo_modify_app", mail_field="jo_modify_mail"
            )
            sub = "Employees Removed"
            msg = f"{reduced_workers_count} of employees with {job_title} have been removed from {job_order}"
            make_system_notification(user_list_app, msg, jobOrder, job_order, sub)
            link = f'  href="{sitename}/app/job-order/{job_order}" '
            args={"sitename": sitename, "content": msg, "subject": sub, "link": link}
            ses_email_send(emails=user_list_mail, subject=sub, args=args, template="email_template_custom")
        return "removed"
    except Exception as e:
        print(e,frappe.get_traceback(),"e "*1000)

@frappe.whitelist()
def remove_emp_from_order_staffing(list_array_removed_emps,notification_flag):
    try:
        list_array_removed_emps = json.loads(list_array_removed_emps)
        for each in list_array_removed_emps:
            assign_emp  =  each[0]
            employee_name = each[1]
            job_order  =    each[2]
            removed  =  each[3]
            job_title  =  each[4]
            start_time  =  each[5]
            try:
                lead_0 = start_time.split(":")
                if lead_0[0][0]=='0' and len(lead_0[0])==2:
                    start_time = start_time[1:]
                    
                job_order_name = frappe.get_doc(jobOrder, job_order)
                assign_doc = frappe.get_doc(assignEmployees, assign_emp)
                employee_name = frappe.get_doc("Employee", employee_name)

                if int(removed) == 0:
                    unremove_assign_emp(employee_name, assign_doc,job_title, start_time)
                    frappe.db.commit()
                else:
                    remove_assign_employee(employee_name, job_order_name, assign_doc, job_title, start_time)
                    frappe.db.commit()
                
            except Exception as e:
                print(e,frappe.get_traceback())
                frappe.log_error(e, "Staffing Company employee remove error")
        

        if list_array_removed_emps and notification_flag=='true':
            lst_sql = """ select user_id from `tabEmployee` where company = "{0}" and user_id IS NOT NULL """.format(
                        job_order_name.company
                    )
            user_list = frappe.db.sql(lst_sql)
            user_list = [l[0] for l in user_list]
            user_list_app, user_list_mail = get_mail_list(
                user_list, app_field="remove_emp_app", mail_field="remove_emp_mail"
            )
            sub = "Employee Removed"
            msg = f"Employee(s) from {assign_doc.company} was removed from {job_order}.  "
            make_system_notification(user_list_app, msg, jobOrder, job_order, sub)
            link = f'  href="{sitename}/app/job-order/{job_order}" '
            args={"sitename": sitename, "content": msg, "subject": sub, "link": link}
            ses_email_send(emails=user_list_mail, subject=sub, args=args, template="email_template_custom")
        return "removed"
    except Exception as e:
        print(e,frappe.get_traceback())

def remove_assign_employee(employee_name, job_order_name, assign_doc, job_title, start_time,removed_by_hiring=0,removed_by_hiring_date=None):
    removed_ids = [i.employee_id for i in assign_doc.employee_removed]
    if employee_name.name not in removed_ids:
        pay_rate =  [i.pay_rate for i in assign_doc.employee_details if i.employee == employee_name.name and i.job_category==job_title and i.job_start_time==start_time]
        assign_doc.append(
            "employee_removed",
            {
                "job_title": job_title,
                "start_time": start_time,
                "employee_id": employee_name.name,
                "employee_name": employee_name.employee_name,
                "order_status": job_order_name.order_status,
                "pay_rate": pay_rate[0] if len(pay_rate) else None,
                "removed_by_hiring": removed_by_hiring,
                "removed_by_hiring_date" : removed_by_hiring_date
            },
        )
        assign_doc.save(ignore_permissions=True)


def remove_assigned_emp(employee_name, job_order_name, assign_doc, job_title, start_time):
    assign_doc.append(
        "employee_removed",
        {
            "job_title": job_title,
            "start_time": start_time,
            "employee_id": employee_name.name,
            "employee_name": employee_name.employee_name,
            "order_status": job_order_name.order_status,
        },
    )
    assign_doc.save(ignore_permissions=True)


def unremove_assign_emp(employee_name, assign_doc, job_title, start_time):
    remove_row = None
    if len(assign_doc.employee_removed) != 0:
        for i in assign_doc.employee_removed:
            if i.employee_id == employee_name.name and i.job_title == job_title and str(i.start_time) == f"{start_time}:00":
                remove_row = i
        if remove_row:
            assign_doc.remove(remove_row)
            assign_doc.save(ignore_permissions=True)


@frappe.whitelist()
def create_job_applicant_and_offer(applicant_name, email, company, contact_number=None):
    try:
        user_company, user_company_type = frappe.db.get_value("User", frappe.session.user, ["company", "organization_type"])
        company_type = frappe.db.get_value("Company", company, "organization_type")
        print(user_company_type, user_company, company_type)
        if (user_company != company and user_company_type!="TAG") or (user_company_type in ["Hiring", "Exclusive Hiring"]):
            frappe.throw("Invalid action")
        if company_type and company_type != "Staffing":
            frappe.throw("Invalid company")
        job_applicant = frappe.get_doc(
            dict(
                doctype="Job Applicant",
                applicant_name=applicant_name,
                email_id=email,
                status="Accepted",
            )
        )
        job_applicant.insert(ignore_permissions=True)
        if contact_number:
            job_applicant.phone_number = contact_number
            job_applicant.save(ignore_permissions=True)

        job_offer = frappe.get_doc(
            dict(
                doctype="Job Offer",
                job_applicant=job_applicant.name,
                applicant_name=applicant_name,
                applicant_email=email,
                status="Accepted",
                offer_date=datetime.date.today(),
                designation="Temp Employee",
                company=company,
            )
        )
        job_offer.insert(ignore_permissions=True)
        return job_applicant.name, job_offer.name
    except Exception as e:
        frappe.log_error(e, "Error in creating job applicant and offer")
        print(e)


@frappe.whitelist()
def set_lat_lng(emp_name, address):
    try:
        loc = Nominatim(user_agent="GetLoc")
        get_loc = loc.geocode(address, exactly_one=True, timeout=15)
        if not get_loc:
            address_list = address.split(",")
            if len(address_list) >= 4:
                address_list.pop(0)
                address = "".join(address_list)
            get_loc = loc.geocode(address, exactly_one=True, timeout=15)
            if not get_loc:
                lat, lng = update_lat_lng_gmap(address)
            else:
                lat = get_loc.latitude
                lng = get_loc.longitude
        else:
            lat = get_loc.latitude
            lng = get_loc.longitude
        frappe.db.sql(f'''UPDATE `tabEmployee` SET lat={lat}, lng={lng} WHERE name="{emp_name}"''')
        frappe.db.commit()
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.log_error(e, "Longitude Latitude Error on Employee Onboarding")


@frappe.whitelist(allow_guest=False)
def filter_user(doctype, txt, searchfield, page_len, start, filters):
    try:
        company = filters.get("company")
        user_list = filters.get("user_list")
        value = ""
        for index, i in enumerate(user_list):
            if index >= 1:
                value = value + "'" + "," + "'" + i
            else:
                value = value + i
        sql = """select name, full_name from `tabUser` where company='{0}' and (name NOT IN ('{1}') and name like '%%{2}%%')""".format(
            company, value, "%s" % txt
        )
        return frappe.db.sql(sql)
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(e, "Employee Boarding Activity Error")
        frappe.throw(e)


@frappe.whitelist()
def check_employee(onb_email):
    emp = frappe.get_all("Employee", {"email": onb_email}, ["name"])
    return True if len(emp) > 0 else False


@frappe.whitelist()
def validate_employee_creation(emp_onb_name):
    emp_onb_details = frappe.get_doc(emp_onb, emp_onb_name)
    tasks = frappe.db.get_all(
        "Task",
        {"project": emp_onb_details.project, "status": ["!=", "Completed"]},
        ["name", "subject"],
    )
    tasks_list = [task["subject"].split(":")[0] for task in tasks]
    task_ids = [task["name"] for task in tasks]
    if len(tasks_list) > 0:
        return tasks_list, task_ids
    elif emp_onb_details.status != "Completed":
        return False
    else:
        return True


@frappe.whitelist()
def make_employee(source_name, target_doc=None):
    doc = frappe.get_doc(emp_onb, source_name)

    def set_missing_values(source, target):
        target.personal_email = frappe.db.get_value(
            "Job Applicant", source.job_applicant, "email_id"
        )
        target.status = "Active"

    emp = get_mapped_doc(
        emp_onb,
        source_name,
        {
            emp_onb: {
                "doctype": "Employee",
                "field_map": {
                    "first_name": "employee_name",
                    "employee_grade": "grade",
                    "gender": "employee_gender",
                },
            }
        },
        target_doc,
        set_missing_values,
    )
    for i in doc.activities:
        if i.document == "Resume":
            emp.resume = i.attach
        elif i.document == "W4":
            emp.w4 = i.attach
        elif i.document == "E verify":
            emp.e_verify = i.attach
        elif i.document == "New Hire Paperwork":
            emp.hire_paperwork = i.attach
        elif i.document == "I9":
            emp.i_9 = i.attach
        elif i.document == "ID Requirements":
            emp.append("id_requirements", {"id_requirements": i.attach})
        elif i.document == "Background Check/Drug Screen":
            emp.append("background_check_or_drug_screen", {"drug_screen": i.attach})
        elif i.document == "Direct Deposit Letter":
            emp.append("direct_deposit_letter", {"direct_deposit_letter": i.attach})
        elif i.document == "Miscellaneous":
            emp.append("miscellaneous", {"attachments": i.attach})
    if doc.sssn and doc.ssn:
        emp.ssn = doc.get_password("ssn")
    return emp


def free_redis(job_name):
    try:
        redis = frappe.cache()
        if redis.hgetall(job_name):
            for k in redis.hgetall(job_name):
                redis.hdel(job_name, k)
    except Exception as e:
        print(e, frappe.utils.get_traceback())


@frappe.whitelist()
def get_jobtitle_based_on_industry(doctype, txt, searchfield, page_len, start, filters):
    try:
        company = filters.get("company")
        industry = filters.get("industry")
        title_list = filters.get("title_list")
        value = ""
        for index, i in enumerate(title_list):
            if index >= 1:
                value = value + "'" + "," + "'" + i
            else:
                value = value + i
        sql = """ select name,industry,company from `tabItem` where company in ('{0}','') and industry="{1}" and (name NOT IN ('{2}') and name like '%%{3}%%')""".format(
            company, industry, value, "%s" % txt
        )
        return frappe.db.sql(sql)

    except Exception as e:
        frappe.msgprint(e)
        return tuple()


@frappe.whitelist()
def get_jobtitle_based_on_company(doctype, txt, searchfield, page_len, start, filters):
    try:
        company = filters.get("company")
        title_list = filters.get("title_list")
        value = ""
        for index, i in enumerate(title_list):
            if index >= 1:
                value = value + "'" + "," + "'" + i
            else:
                value = value + i
        sql = """ select name,industry,company from `tabItem` where (company in("{0}",'') or company is NULL) and (name NOT IN ('{1}') and name like '%%{2}%%') """.format(
            company, value, "%s" % txt
        )
        return frappe.db.sql(sql)

    except Exception as e:
        frappe.msgprint(e)
        return tuple()


def validate_user(doc, _method):
    error_message = _("Insufficient Permission for  {0}").format(
        frappe.bold("User" + " " + doc.email)
    )
    if not doc.is_new() and frappe.session.user != "Administrator":
        user_role = frappe.db.get_value(
            "User", {"name": frappe.session.user}, "tag_user_type"
        )
        doc_user_role = frappe.db.get_value("User", {"name": doc.name}, "tag_user_type")
        if doc_user_role and (
            (
                (user_role == "Staffing User" or user_role == "Hiring User")
                and (
                    doc_user_role == "Staffing Admin"
                    or doc_user_role == "Hiring Admin"
                    or doc_user_role == tagAdmin
                )
            )
            or (
                (user_role == "Staffing Admin" or user_role == "Hiring Admin")
                and doc_user_role == tagAdmin
            )
        ):
            frappe.flags.error_message = error_message
            raise frappe.PermissionError(("read", "User", doc.email))
    user = frappe.get_doc("User", frappe.session.user)

    if (
        not doc.is_new()
        and doc.owner != frappe.session.user
        and frappe.session.user != "Guest"
        and frappe.session.user != "Administrator"
        and user.tag_user_type != tagAdmin
        and (
            doc.email != user.email
            or doc.company != user.company
            or doc.tag_user_type != user.tag_user_type
            or doc.organization_type != user.organization_type
            or doc.role_profile_name != user.role_profile_name
        )
    ):
        frappe.throw("Insufficient Permission")


@frappe.whitelist()
def get_password(fieldname, comp_name):
    try:
        comp = frappe.get_doc("Company", comp_name)

        if fieldname == "jazzhr_api_key" and comp.jazzhr_api_key:
            return comp.get_password("jazzhr_api_key")
        elif fieldname == "client_id" and comp.client_id:
            return comp.get_password("client_id")
        elif fieldname == "client_secret" and comp.client_secret:
            return comp.get_password("client_secret")
        elif fieldname == "workbright_subdomain" and comp.workbright_subdomain:
            return comp.get_password("workbright_subdomain")
        elif fieldname == "workbright_api_key" and comp.workbright_api_key:
            return comp.get_password("workbright_api_key")
        elif fieldname == "branch_org_id" and comp.branch_org_id:
            return comp.get_password("branch_org_id")
        elif fieldname == "branch_api_key" and comp.branch_api_key:
            return comp.get_password("branch_api_key")
        return response
    except Exception as e:
        frappe.log_error("Password Not Found", e)


@frappe.whitelist(allow_guest=True)
def branch_key(branch_key=None):
    try:
        if branch_key:
            redis = frappe.cache()
            redis.hset("branch_data", "branch_key", branch_key)
            return "Success"
        else:
            return "Failed"
    except Exception as e:
        frappe.log_error("Branch API Call Error", e)


# -------------------checking employees mendatory fields--------------------------------#
@frappe.whitelist()
def check_mandatory_field(emp_id, check, emp_name):
    try:
        msg = ""
        emp_name = emp_name.title()
        data = frappe.db.sql(
            """select first_name,last_name,email,company,status,date_of_birth from `tabEmployee` where name = '{0}'""".format(
                emp_id
            ),
            as_dict=1,
        )
        emp_fields = []
        for field in data[0]:
            print(field)
            if data[0][field] == None:
                display_field_name = field.replace("_", " ")
                msg += "<span>&#8226;</span> " + display_field_name.title() + "<br>"
                emp_fields.append(field)

        if len(msg) == 0:
            return "success"
        elif check == 1:
            return emp_fields
        elif check == 2:
            return [msg, emp_name, 1]
        else:
            return [msg, emp_name]

    except Exception as e:
        print(e)


@frappe.whitelist()
def get_comp_code(title, company):
    try:
        return frappe.db.sql(
            """select comp_code from `tabJob Titles` where parent="{0}"  and job_titles="{1}" and parenttype="Company" """.format(
                company, title
            ),
            as_dict=1,
        )
    except Exception as e:
        print(e)
        return "Error"


@frappe.whitelist(allow_guest=False)
def get_template_name(company):
    """
    The function `get_template_name` retrieves a list of template names and the default template name
    for a given company, while also checking for user permissions.
    
    :param company: The "company" parameter is the name of the company for which you want to retrieve
    the template names
    :return: The function `get_template_name` returns a tuple containing two values. The first value is
    a string that represents a newline-separated list of template names. The second value is a string
    that represents the default template name.
    """
    try:
        user_company, user_company_type = frappe.db.get_value("User", frappe.session.user, ["company", "organization_type"])
        if user_company != company and user_company_type!="TAG":
            frappe.throw(INSUFF_PERM + frappe.session.user)
        template_list = []
        templates = frappe.get_all(
            emp_onb_temp, {"company": company}, ["name", "template_name"]
        )
        template_list = [
            temp["template_name"] if temp["template_name"] else temp["name"]
            for temp in templates
        ]
        default_temp = frappe.db.get_value(
            emp_onb_temp, {"company": company, "default_template": 1}, ["template_name"]
        )
        return "\n".join(template_list), default_temp
    except Exception as e:
        frappe.log_error(e, "get_template_name error")


@frappe.whitelist()
def set_status_complete(docname, tasks_list):
    try:
        tasks_list = ast.literal_eval(tasks_list)
        emp_onb_data = frappe.get_doc(emp_onb, docname)
        completed_date = str(getdate())
        frappe.db.set_value("Project", emp_onb_data.project, "status", "Completed")
        frappe.db.set_value("Project", emp_onb_data.project, "percent_complete", "100")
        frappe.db.set_value(emp_onb, docname, "status", "Completed")
        if len(tasks_list) > 0:
            update_activity_table(tasks_list, docname, completed_date)
            if len(tasks_list) == 1:
                sql = f"""UPDATE `tabTask` SET status="Completed", completed_on="{completed_date}" where name in ("{tasks_list[0]}")"""
            else:
                sql = f"""UPDATE `tabTask` SET status="Completed", completed_on="{completed_date}" where name in {tuple(tasks_list)}"""
            frappe.db.sql(sql)
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(e, "set_status_complete error")


@frappe.whitelist()
def update_activity_table(tasks_list, docname, completed_date):
    try:
        if len(tasks_list) == 1:
            sql = f'''UPDATE `tabEmployee Boarding Activity` SET status="Completed", completed_on="{completed_date}" where task in ("{tasks_list[0]}") and parent = "{docname}"'''
        else:
            sql = f'''UPDATE `tabEmployee Boarding Activity` SET status="Completed", completed_on="{completed_date}" where task in {tuple(tasks_list)} and parent = "{docname}"'''
        frappe.db.sql(sql)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(e, "update_activity_table error")


@frappe.whitelist()
def get_ats_and_payroll_status():
    try:
        """# user1 = frappe.get_doc('User',frappe.session.user)"""
        user = frappe.db.sql(
            f"""select name,organization_type from `tabUser` where name='{frappe.session.user}' and organization_type in ('Staffing')"""
        )
        if user[0][1]:
            return frappe.db.sql(
                """ 
            select count(*)-(count(*)-sum(enable_ats)) as ats,count(*)-(count(*)-sum(enable_payroll)) as payroll
            from `tabCompany` 
            where name in
            (select assign_multiple_company from `tabCompanies Assigned` 
            where parenttype="User" and  parent ="{0}")
            and make_organization_inactive="0" """.format(
                    user[0][0]
                ),
                as_dict=1,
            )
    except Exception as e:
        print(e)


@frappe.whitelist()
def employee_status_change(user):
    try:
        enqueue(
            "tag_workflow.tag_data.employee_status_change_job",
            queue="short",
            is_async="True",
            user=user,
        )
    except Exception:
        print("employee_status_change Error", frappe.get_traceback())
        frappe.log_error(frappe.get_traceback(), "employee_status_change Error")


@frappe.whitelist()
def employee_status_change_job(user):
    try:

        def emp_status(user, value):
            emp = frappe.db.get_value("Employee", {"user_id": user}, "name") or None
            if emp:
                frappe.db.set_value(
                    "Employee", emp, "status", "Active" if value == 1 else "Inactive"
                )

        sql = """select data from `tabVersion` where docname="{0}" order by modified DESC""".format(
            user
        )
        data = frappe.db.sql(sql, as_list=1)
        new_data = json.loads(data[0][0])
        if "changed" in new_data:
            for i in new_data["changed"]:
                if i[0] == "enabled":
                    emp_status(user, i[2])
                    break
    except Exception:
        print("employee_status_change_job Error", frappe.get_traceback())
        frappe.log_error(frappe.get_traceback(), "employee_status_change_job Error")


@frappe.whitelist()
def update_all_comp_lat_lng():
    try:
        update_comp_lat_lng()
        # frappe.enqueue("tag_workflow.tag_data.update_comp_lat_lng", queue='long', is_async=True)
    except Exception as e:
        frappe.msgprint(e)


def update_comp_lat_lng(company=None):
    try:
        count = 0
        print("*------lat lng company update--------------------------*\n")
        if company != None:
            my_data = frappe.db.sql(
                """ select address,name from `tabCompany` where company_name = "{0}" """.format(
                    company
                ),
                as_dict=1,
            )
        else:
            my_data = frappe.db.sql(
                """ select address,name from `tabCompany` where (lat is null or lat ="" or lng is null or lng="") and city is not null and state is not null """,
                as_dict=1,
            )
        for d in my_data:
            count = update_comp_lat_lng_contd(d, count)
    except Exception as e:
        frappe.log_error(e, "longitude latitude error")
        print(e)


def update_comp_lat_lng_contd(d, count):
    try:
        if count % 80 == 0:
            time.sleep(5)
        loc = Nominatim(user_agent="GetLoc")
        get_loc = loc.geocode(d.address, exactly_one=True, timeout=15)
        if not get_loc:
            address_list = d.address.split(",")
            if len(address_list) >= 4:
                address_list.pop(0)
                address = "".join(address_list)
            get_loc = loc.geocode(address, exactly_one=True, timeout=15)
            if not get_loc:
                lat, lng = update_lat_lng_gmap(address)
            else:
                lat = get_loc.latitude
                lng = get_loc.longitude
        else:
            lat = get_loc.latitude
            lng = get_loc.longitude
        frappe.db.sql(
            """update `tabCompany` set lat= "{0}", lng="{1}" where name="{2}" """.format(
                lat, lng, d.name
            )
        )
        frappe.db.commit()
        return count + 1
    except Exception:
        return count


def update_lat_lng_gmap(address):
    try:
        lat, lng = 0, 0
        google_location_data_url = GOOGLE_API_URL + address
        google_response = requests.get(google_location_data_url)
        location_data = google_response.json()
        if (
            google_response.status_code == 200
            and len(location_data) > 0
            and len(location_data["results"]) > 0
        ):
            location = location_data["results"][0]["geometry"]["location"]
            lat = location["lat"]
            lng = location["lng"]
        return lat, lng
    except Exception:
        return 0, 0


@frappe.whitelist()
def update_individual_company_lat_lng(company):
    try:
        update_comp_lat_lng(company)
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.log_error(e, "Company Lat Lng error")


@frappe.whitelist()
def create_pdf(html, name):
    margin = "0.5in"
    options = {
        "margin-top": margin,
        "margin-bottom": margin,
        "margin-left": margin,
        "margin-right": margin,
        "page-size": "A4",
        "orientation": "Portrait",
    }
    filedata = pdfkit.from_string(html, options=options, verbose=True)
    reader = PdfReader(BytesIO(filedata))
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    filedata = get_file_data_from_writer(writer)
    frappe.local.response.filename = name
    frappe.local.response.filecontent = filedata
    frappe.local.response.type = "pdf"


@frappe.whitelist()
def print_assigned_emp(company, job_order):
    data = (
        assigned_employee_data(job_order)
        if company == "hiring"
        else staffing_assigned_employee(job_order)
    )
    name = f"{job_order}_employees.pdf"
    html = get_pdf_content(job_order, name, data, company)
    create_pdf(html, name)


@frappe.whitelist()
def get_pdf_content(job_order, name, data, company):
    """
    The function `get_pdf_content` retrieves data from the database and renders a template with the
    provided arguments.
    
    :param job_order: The `job_order` parameter is the name of a job order. It is used to retrieve the
    job site information from the database
    :param name: The "name" parameter is a string that represents the title or name of the PDF content.
    It is used as a variable in the "args" dictionary to pass the value to the template for rendering
    :param data: The "data" parameter is a variable that contains information about employees assigned
    to a job order. It is likely a list or dictionary that holds employee data such as names, positions,
    and other relevant details
    :param company: The "company" parameter is a variable that represents the type of company. It is
    used in the function to pass the company type to the template for rendering
    :return: the rendered template "print_assigned_emp.html" with the provided arguments.
    """
    jo_data = frappe.db.sql(
        f'''select job_site from `tabJob Order` where name="{job_order}"'''
    )
    args = {
        "title": name,
        "job_order": job_order,
        "job_site": jo_data[0][0],
        "print_date": datetime.datetime.now().strftime("%m/%d/%Y"),
        "emp_data": data,
        "sitename": sitename,
        "company_type": company,
    }
    return frappe.render_template("templates/print_assigned_emp.html", args)


@frappe.whitelist()
def print_bulk_ts(selected_values):
    values = json.loads(selected_values)
    if values:
        html_list = ""
        name = ""
        if "_" in values[0]:
            html_list, name = multidate_ts(values)
        elif "TS" in values[0]:
            html_list, name = singledate_ts(values)
        create_pdf(html_list, name)
    else:
        frappe.msgprint("An error occurred. Please try again!")


from tag_workflow.utils.trigger_session import check_export_ts


@frappe.whitelist()
def singledate_ts(ts_list):
    """
    The function `singledate_ts` generates a PDF report of employee timesheets for a given date.
    
    :param ts_list: The `ts_list` parameter is a list of timesheet names. It is used to retrieve
    timesheet data for each timesheet in the list
    :return: a rendered template and a name. The rendered template is generated using the
    "print_bulk_ts.html" template and the provided arguments. The name is a string that is used as the
    title of the PDF file.
    """
    emp_details = []
    for ts in ts_list:
        status_list = []
        ts_data = frappe.get_doc("Timesheet", ts)
        if ts_data.no_show:
            status_list.append("No Show")
        if ts_data.non_satisfactory:
            status_list.append("Non Satisfactory")
        if ts_data.dnr:
            status_list.append("DNR")
        if ts_data.replaced:
            status_list.append("Replaced")
        start_time = ":".join(str(ts_data.time_logs[0].start_time).split(" ").pop().split(":")[:-1]).rjust(5, "0")
        emp_details.append(
            {
                "emp_id": ts_data.employee,
                "employee_name": ts_data.employee_name,
                "status": ts_data.workflow_state,
                "from_time": ts_data.time_logs[0].from_time.strftime("%H:%M"),
                "to_time": ts_data.time_logs[0].to_time.strftime("%H:%M"),
                "break_from": ts_data.time_logs[0].break_start_time.strftime("%H:%M")
                if ts_data.time_logs[0].break_start_time
                else "",
                "break_to": ts_data.time_logs[0].break_end_time.strftime("%H:%M")
                if ts_data.time_logs[0].break_end_time
                else "",
                "total_hours": ts_data.time_logs[0].hours,
                "employee_status": ", ".join(status_list),
                "exported": "No" if ts_data.ts_exported == 0 else "Yes",
                "job_title": ts_data.job_name,
                "start_time": start_time
            }
        )
    jo_data = frappe.db.sql(
        f'''select job_site, job_order_duration from `tabJob Order` where name="{ts_data.job_order_detail}"''',
        as_dict=1,
    )
    name = f"{ts_data.job_order_detail}_timesheets.pdf"
    export_ts = check_export_ts(ts_data.employee_company, 0)
    args = {
        "title": name,
        "job_order": ts_data.job_order_detail,
        "company": ts_data.employee_company,
        "date_of_ts": ts_data.date_of_timesheet.strftime(date_format),
        "job_site": jo_data[0].job_site,
        "job_duration": jo_data[0].job_order_duration,
        "from_date": ts_data.from_date.strftime(date_format),
        "to_date": ts_data.to_date.strftime(date_format),
        "emp_details": emp_details,
        "export_ts": export_ts,
        "sitename": sitename,
    }
    return frappe.render_template("templates/print_bulk_ts.html", args), name


@frappe.whitelist()
def multidate_ts(date_list):
    html_list = []
    for date in date_list:
        ts_list = frappe.db.get_list(
            "Timesheet",
            {
                "date_of_timesheet": date.split("_")[1],
                "job_order_detail": date.split("_")[0],
            },
            ["name"],
            pluck="name",
        )
        html, name = singledate_ts(ts_list)
        html_list.append(html)
    return '<div style="page-break-after: always;"></div>'.join(html_list), name


@frappe.whitelist()
def job_titles_listing_page_vals(job_order):
    job_titles = frappe.db.sql(
        f"""select distinct(select_job), sum(no_of_workers) as no_of_workers from `tabMultiple Job Titles` 
        where parent="{job_order}" group by select_job order by no_of_workers desc, select_job asc""",
        as_list=1,
    )
    if job_titles:
        title_list = [x[0] for x in job_titles]
        return title_list
    else:
        return "Single Title"


@frappe.whitelist()
def industry_listing_page_vals(job_order):
    industries = frappe.db.sql(
        f"""select distinct(category), sum(no_of_workers) as no_of_workers from `tabMultiple Job Titles` where parent="{job_order}" 
        group by category order by no_of_workers desc, select_job asc""",
        as_list=1,
    )
    if industries:
        industry_list = [x[0] for x in industries]
        return industry_list
    else:
        return "Single Industry"
    
@frappe.whitelist()
def total_approved_or_required(job_order):
    lst = []
    query = f"""SELECT select_job, CAST(SUM(no_of_workers) AS INTEGER) AS total_workers,  CAST(SUM(worker_filled) AS INTEGER) as worker_filled
            FROM `tabMultiple Job Titles`
            WHERE parent = '{job_order}'
            GROUP BY select_job 
            order by total_workers desc, select_job asc
        """
    order_workers_data = frappe.db.sql(query,as_list=1)
    if len(order_workers_data)>1:
        for i in order_workers_data:
            lst.append(f'{i[0]} {i[2]}/{i[1]}')
        return lst
    else:
        return "Single Industry"

@frappe.whitelist()
def min_job_start_time(job_order):
    time = frappe.db.sql(
        f"""SELECT MIN(job_start_time) FROM `tabMultiple Job Titles`
             WHERE parent = '{job_order}' """
    )
    return time

def check_permissions(company_to_favourite, user_company, user, comp_doc):
    """
    The function `check_permissions` checks if a user has sufficient permissions to access a company's
    information based on their user company and the company they want to access.
    
    :param company_to_favourite: The company that the user wants to favorite. This is a string value
    :param user_company: The user's company name
    :param user: The "user" parameter represents the user for whom the permissions are being checked
    :param comp_doc: The `comp_doc` parameter is a document object that represents a company. It
    contains information about the company, such as its name, industry type, and organization type
    """
    try:
        if user != frappe.session.user or frappe.db.get_value("User", frappe.session.user, "company") != user_company:
            frappe.throw(INSUFF_PERM + user)

        if len(comp_doc.industry_type) == 1:
            sql = '''
                SELECT parent 
                FROM `tabIndustry Types` 
                WHERE parent IN (
                    SELECT name 
                    FROM `tabCompany` 
                    WHERE organization_type=%s
                ) 
                AND industry_type = %s 
                AND parent = %s
            '''
            sql_params = ('Staffing', comp_doc.industry_type[0].industry_type, company_to_favourite)
        else:
            hiring_industries = [row.industry_type for row in comp_doc.industry_type]
            sql = '''
                SELECT parent 
                FROM `tabIndustry Types` 
                WHERE parent IN (
                    SELECT name 
                    FROM `tabCompany` 
                    WHERE organization_type='Staffing'
                ) 
                AND industry_type IN %s 
                AND parent = %s
            '''
            sql_params = (tuple(hiring_industries), company_to_favourite)
        if not frappe.db.sql(sql, sql_params):
            frappe.throw('Invalid Company ' + company_to_favourite)
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.log_error(str(e), "check_permissions error")

@frappe.whitelist(allow_guest=False)
def assigned_employee_data_title_wise(job_order,job_category,job_start_time,row_name):
    try:
        jo = frappe.get_doc(jobOrder, job_order)
        comp = jo.owner
        comp_detail = frappe.get_doc("User", comp)
        comp_type = comp_detail.organization_type
        actual_headcounts = frappe.db.sql(f'''select no_of_workers,estimated_hours_per_day,worker_filled from `tabMultiple Job Titles` where name="{row_name}"''')
        if jo.resumes_required == 1 and comp_type != "Staffing":
            sql = f"""
                select ae.company as staff_company,aed.resume, ae.name AS name, aed.remove_employee AS remove,aed.employee_name as employee_name,
                aed.approved as approved, aed.employee as employee ,
                TIME_FORMAT(aed.job_start_time, "%H:%i") as job_start_time,
                aed.job_category as job_category
                from `tabAssign Employee` as ae,`tabAssign Employee Details` as aed
                where ae.name=aed.parent and job_order="{job_order}"  and aed.job_category="{job_category}"
                and aed.job_start_time = "{job_start_time}"
                and ae.tag_status="Approved" and aed.approved =1 and
                aed.remove_employee =0 
                order by staff_company,
                SUBSTRING_INDEX(aed.job_category, '-', 1),
                CAST(SUBSTRING_INDEX(aed.job_category, '-', -1) AS UNSIGNED),
                employee_name
            """
        else:
            sql = f"""
                SELECT ae.company AS staff_company, ae.name AS name, aed.remove_employee AS remove, aed.employee_name AS employee_name,
                aed.employee as employee, TIME_FORMAT(aed.job_start_time, "%H:%i") as job_start_time,
                aed.job_category as job_category
                FROM `tabAssign Employee` AS ae,`tabAssign Employee Details` AS aed
                WHERE ae.name=aed.parent and job_order="{job_order}" and tag_status="Approved" and aed.job_category="{job_category}"
                and aed.job_start_time = "{job_start_time}"
                AND aed.remove_employee = 0
                ORDER BY staff_company,
                SUBSTRING_INDEX(aed.job_category, '-', 1),
                CAST(SUBSTRING_INDEX(aed.job_category, '-', -1) AS UNSIGNED),
                employee_name
            """
        emp_data = frappe.db.sql(sql, as_dict=1)
        emp_list = []
        for i in range(len(emp_data)):
            emp_dic = {}
            sql3 = f"""
                SELECT
                MAX(IF(no_show=1, "No Show", " ")) AS no_show,
                MAX(IF(non_satisfactory=1,"Non Satisfactory"," ")) AS non_satisfactory,
                MAX(IF(dnr=1,"DNR"," ")) AS dnr
                FROM `tabTimesheet`
                WHERE job_order_detail='{job_order}' AND employee='{emp_data[i].employee}' AND job_name='{emp_data[i].job_category}'
            """
            employees_data = frappe.db.sql(sql3, as_dict=True)
            if len(employees_data) == 0:
                emp_dic = {
                    "assign_name": emp_data[i].name,
                    "staff_company": emp_data[i].staff_company,
                    "employee": emp_data[i].employee_name,
                    "no_show": "",
                    "non_satisfactory": "",
                    "dnr": "",
                    "replaced": "",
                    "employee_id": emp_data[i].employee,
                    "removed": emp_data[i].remove,
                    "job_title": emp_data[i].job_category,
                    "job_start_time": emp_data[i].job_start_time,
                    "estimated_hours_per_day":actual_headcounts[0][1],
                    "resume": emp_data[i].resume
                }
                emp_list.append(emp_dic)
            else:
                emp_dic = {
                    "assign_name": emp_data[i].name,
                    "staff_company": emp_data[i].staff_company,
                    "employee": emp_data[i].employee_name,
                    "no_show": employees_data[0].no_show,
                    "non_satisfactory": employees_data[0].non_satisfactory,
                    "dnr": employees_data[0].dnr,
                    "replaced": "",
                    "employee_id": emp_data[i].employee,
                    "removed": emp_data[i].remove,
                    "job_title": emp_data[i].job_category,
                    "job_start_time": emp_data[i].job_start_time,
                    "estimated_hours_per_day":actual_headcounts[0][1],
                    "resume": emp_data[i].resume
                }
                emp_list.append(emp_dic)
        replaced = replaced_employees(job_order, None)
        return emp_list + replaced, [actual_headcounts[0][0],actual_headcounts[0][2]]
    except Exception as e:
        print(frappe.get_traceback())
        frappe.log_error(e, "Assigned Employees")

@frappe.whitelist(allow_guest=False)
def update_assign_emps_total_workers_reduced_head_count(total_no_of_workers,total_workers_filled,job_order):
    try:
        frappe.db.sql(f'''update `tabAssign Employee` set no_of_employee_required = {int(total_no_of_workers) - int(total_workers_filled)} where job_order="{job_order}" and tag_status not in ("Approved")''')
        all_title_data_query = f''' UPDATE `tabMultiple Job Title Details` AS aejt
            JOIN `tabMultiple Job Titles` AS jojt
            ON jojt.job_start_time = aejt.job_start_time
            AND jojt.select_job = aejt.select_job
            SET aejt.no_of_workers = jojt.no_of_workers - jojt.worker_filled
            WHERE aejt.parent IN (SELECT name FROM `tabAssign Employee` WHERE job_order = "{job_order}" and tag_status not in ("Approved"))
            AND jojt.parent = "{job_order}"'''
        frappe.db.sql(all_title_data_query)
        frappe.db.commit()
        return 'updated'
    except Exception as e:
        print(frappe.get_traceback())
        frappe.log_error(e, "Assigned Employee")


@frappe.whitelist(allow_guest=False)
def update_assign_emps_total_workers_reduced_head_count_non_resume(total_no_of_workers,job_order):
    try:
        frappe.db.sql(f'''update `tabAssign Employee` set no_of_employee_required = {int(total_no_of_workers)} where job_order="{job_order}"''')
        all_title_data_query = f''' UPDATE `tabMultiple Job Title Details` AS aejt
            JOIN `tabMultiple Job Titles` AS jojt
            ON jojt.job_start_time = aejt.job_start_time
            AND jojt.select_job = aejt.select_job
            SET aejt.no_of_workers = jojt.no_of_workers - jojt.worker_filled
            WHERE aejt.parent IN (SELECT name FROM `tabAssign Employee` WHERE job_order = "{job_order}")
            AND jojt.parent = "{job_order}"'''
        frappe.db.sql(all_title_data_query)
        frappe.db.commit()
        return 'updated'
    except Exception as e:
        print(frappe.get_traceback())
        frappe.log_error(e, "Assigned Employee")

@frappe.whitelist()
def check_can_reduce_count(job_start_time,row_name, start_date):
    try:
        current_time = datetime.datetime.now(timezone(TIMEZONE)).strftime("%H:%M:%S")
        compare_time = '0'+job_start_time if len(job_start_time.split(":")[0])==1 else job_start_time
        actual_headcounts = frappe.db.sql(f'''select no_of_workers from `tabMultiple Job Titles` where name="{row_name}"''')
        if current_time>compare_time:
            return [0,actual_headcounts[0][0]]
        return [1,actual_headcounts[0][0]]
    except Exception as e:
        print(e,frappe.get_traceback())