# Copyright (c) 2022, SourceFuse and contributors
# For license information, please see license.txt

import json
from datetime import datetime
from uuid import uuid4

from tag_workflow.tag_workflow.doctype.company.company import check_staffing_reviews

import frappe
from frappe.model.document import Document
from frappe.share import add_docshare as add

from tag_workflow.tag_data import chat_room_created, joborder_email_template
from tag_workflow.utils.notification import get_mail_list, make_system_notification
from tag_workflow.utils.whitelisted import add_job_title_company
import re

jobOrder = "Job Order"
claimOrder = "Claim Order"
EPR = "Employee Pay Rate"
AssignEmp = "Assign Employee"
SCC = "Staffing Comp Code"
jobSite = "Job Site"


site = frappe.utils.get_url().split("/")
sitename = site[0] + "//" + site[2]
pattern = r'[+<>^?#/\\]'

class ClaimOrder(Document):
    def on_update(self):
        job_order = frappe.get_doc(jobOrder, self.job_order)
        create_pay_rate_comp_code_job_title(job_order, self)


@frappe.whitelist()
def staffing_claim_joborder(frm):
    try:
        frm = json.loads(frm)
        job_order = frm["job_order"]
        hiring_org = frm["hiring_organization"]
        staffing_org = frm["staffing_organization"]
        doc_name = frm["name"]
        single_share = frm["single_share"]
        job_title = frm["multiple_job_titles"]
        if int(single_share) == 1:
            no_required = sum(row["no_of_workers_joborder"] for row in job_title)
            no_assigned = sum(row["staff_claims_no"] for row in job_title)
            check_partial_claim(
                job_order, staffing_org, no_required, no_assigned, hiring_org, doc_name
            )
            return

        bid_receive = frappe.get_doc(jobOrder, job_order)

        if bid_receive.claim is None:
            bid_receive.bid = 1 + int(bid_receive.bid)
            bid_receive.claim = staffing_org
            chat_room_created(hiring_org, staffing_org, job_order)

        else:
            if staffing_org not in bid_receive.claim:
                bid_receive.bid = 1 + int(bid_receive.bid)
                bid_receive.claim = str(bid_receive.claim) + "~" + staffing_org
                chat_room_created(hiring_org, staffing_org, job_order)

        bid_receive.save(ignore_permissions=True)

        job_sql = '''select name,job_site,posting_date_time from `tabJob Order` where name = "{}"'''.format(
            job_order
        )
        job_detail = frappe.db.sql(job_sql, as_dict=1)

        lst_sql = """select name from `tabUser` where company = "{}" """.format(
            hiring_org
        )
        user_list = frappe.db.sql(lst_sql, as_list=1)

        user_list2 = [user[0] for user in user_list]
        for user in user_list2:
            add(
                claimOrder,
                doc_name,
                user,
                read=1,
                write=0,
                share=0,
                everyone=0,
                flags={"ignore_share_permission": 1},
            )

        sub = "Claim Order"
        msg = f'{staffing_org} has submitted a claim for {job_detail[0]["name"]} at {job_detail[0]["job_site"]} on {job_detail[0]["posting_date_time"]}'
        claim_order_app, claim_order_mail = get_mail_list(
            user_list2, app_field="jo_claim_app", mail_field="jo_claim_mail"
        )
        make_system_notification(claim_order_app, msg, claimOrder, job_order, sub)
        msg = f'{staffing_org} has submitted a claim for {job_detail[0]["name"]} at {job_detail[0]["job_site"]} on {job_detail[0]["posting_date_time"]}. Please review and/or approve this claim .'
        link = f'  href="{sitename}/app/claim-order/{doc_name}" '
        joborder_email_template(sub, msg, claim_order_mail, link)
        return 1

    except Exception as e:
        frappe.msgprint(e)
        print(e, frappe.get_traceback())
        frappe.db.rollback()


@frappe.whitelist(allow_guest=False)
def save_claims(approved_data, doc_name):
    """
    This function saves approved claims for a job order and sends notifications to relevant users.
    It also updates Claim Order accordingly.

    :param approved_data: The data containing the approved number of workers and notes for each job
    title and company in a claim order, in JSON format
    :param doc_name: The variable `doc_name` is a string that represents the name of a job order
    :return: the integer value 1.
    """
    try:
        approved_data = json.loads(approved_data)
        job = frappe.get_doc(jobOrder, doc_name)
        validate_total_workers(approved_data, job.total_no_of_workers, 'approved_no_of_workers')
        for comp, data in approved_data.items():
            total_approved = 0
            notes = ""
            claim = frappe.get_doc(
                claimOrder, {"job_order": doc_name, "staffing_organization": comp}
            )
            if not job.has_permission("read") or not claim.has_permission("read"):
                frappe.throw(('Insufficient Permission for user '+frappe.session.user))
            for update_dict in data:
                for row in claim.multiple_job_titles:
                    time = datetime.strptime(str(row.start_time), "%H:%M:%S")
                    if (
                        row.job_title == update_dict["job_title"]
                        and time.strftime("%H:%M") == update_dict["start_time"]
                    ):
                        validate_approved_claim(row, update_dict, "select")
                        row.approved_no_of_workers = update_dict[
                            "approved_no_of_workers"
                        ]
                        total_approved += update_dict["approved_no_of_workers"]
                        notes = re.sub(pattern, '', update_dict["notes"])
            claim.approved_no_of_workers = total_approved
            claim.notes = notes
            claim.save(ignore_permissions=True)

            update_jo(job, comp)
            user_data = """ select user_id from `tabEmployee` where company = "{}" and user_id IS NOT NULL """.format(
                comp
            )
            user_list = frappe.db.sql(user_data, as_list=1)
            user_list2 = [user[0] for user in user_list]
            sub = "Approve Claim Order"
            msg = f"{job.company} has approved {total_approved} employees for {doc_name}. Don't forget to assign employees to this order."
            claim_order_app, claim_order_mail = get_mail_list(
                user_list2, app_field="select_count_app", mail_field="select_count_mail"
            )
            make_system_notification(claim_order_app, msg, claimOrder, claim.name, sub)
            link = f'  href="{sitename}/app/claim-order/{claim.name}" '
            joborder_email_template(sub, msg, claim_order_mail, link)
        return 1
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.db.rollback()


def validate_total_workers(data, total_no_of_workers, fieldname):
    total_approved = sum(item[fieldname] for value in data.values() for item in value)
    if not total_approved:
        frappe.throw("You must claim one employee at least.")
    if total_no_of_workers < total_approved:
        frappe.throw("You cannot claim employees more than required.")


def validate_approved_claim(row, update_dict, event):
    if event=="select":
        if update_dict["approved_no_of_workers"] < 0:
            frappe.throw("Approved number of workers cannot be negative.")
        elif row.no_of_workers_joborder < update_dict["approved_no_of_workers"]:
            frappe.throw("You cannot approve workers greater than the no. of workers required.")
        elif row.staff_claims_no < update_dict["approved_no_of_workers"]:
            frappe.throw("You cannot approve workers greater than the no. of workers claimed by Staffing Company.")
    if event=="modify":
        if update_dict["updated_approved_no"] < 0:
            frappe.throw("Approved number of workers cannot be negative.")
        elif row.no_of_remaining_employee < update_dict["updated_approved_no"]:
            frappe.throw("You cannot approve workers greater than the no. of workers required.")
        elif row.staff_claims_no < update_dict["updated_approved_no"]:
            frappe.throw("Claims approved cannot be greater than the no. of workers claimed by Staffing Company.")
        elif update_dict["updated_approved_no"] < update_dict["workers_filled"]:
            frappe.throw("Claims approved cannot be less than the no. of employees already assigned by Staffing Company.")


@frappe.whitelist()
def update_jo(job, comp):
    """
    This function updates a job's staff_org_claimed field by adding a company to it if it is not already
    present.

    :param job: The variable "job" is likely an object or instance of a class that represents a job or
    task in a system. It is being used as a parameter in the "update_jo" function
    :param comp: It is a variable that represents the company that is being updated in the job object
    """
    try:
        claimed = job.staff_org_claimed if job.staff_org_claimed else ""
        value1 = ""
        if len(claimed) == 0:
            value1 += str(comp)
        elif str(comp) not in claimed:
            value1 += str(claimed) + "~" + str(comp)
        else:
            value1 = claimed
        job.staff_org_claimed = value1
        job.save(ignore_permissions=True)
    except Exception as e:
        print(e, frappe.get_traceback())


@frappe.whitelist()
def order_details(doc_name):
    """
    This function retrieves order details and job order dates from the database based on a given
    document name.

    :param doc_name: The parameter `doc_name` is a string variable that represents the name of a job
    order document in the system. It is used in the SQL queries to retrieve information related to the
    job order and its associated claim orders and multiple job title claims
    :return: The function `order_details` returns two values as a tuple. The first value is the result
    of a SQL query that fetches data from the `Claim Order` and `Multiple Job Title Claim` tables based
    on the `job_order` field matching the input `doc_name`. The second value is the result of a SQL
    query that fetches the `from_date` and `to_date` fields
    """
    try:
        data = f"""SELECT CO.name, CO.job_order, CO.staffing_organization,
        MT.job_title, MT.industry, MT.no_of_workers_joborder, MT.no_of_remaining_employee, MT.approved_no_of_workers,
        MT.staff_claims_no, MT.start_time, MT.duration, MT.bill_rate, CASE WHEN (SELECT COUNT(*) FROM `tabCompany Review` WHERE staffing_company = CO.staffing_organization) >= 10
            THEN (SELECT average_rating FROM `tabCompany` WHERE name = CO.staffing_organization)
            ELSE 0
        END AS avg_rate
        FROM `tabClaim Order` AS CO, `tabMultiple Job Title Claim` AS MT
        WHERE MT.parent=CO.name AND CO.job_order="{doc_name}" AND MT.staff_claims_no >0
        order by MT.job_title, MT.start_time, CO.staffing_organization"""
        data1 = (
            f'''SELECT from_date, to_date FROM `tabJob Order` WHERE name="{doc_name}"'''
        )
        data = frappe.db.sql(data, as_dict=True)
        for i in data:
            i['avg_rate'] = check_staffing_reviews(i['staffing_organization'])
        return data, frappe.db.sql(data1)
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.db.rollback()


@frappe.whitelist()
def remaining_emp(doc_name):
    try:
        datas = """ select sum(approved_no_of_workers) as approved_no_of_workers  from `tabClaim Order` where job_order = "{}"  """.format(
            doc_name
        )
        data = frappe.db.sql(datas, as_dict=True)
        if len(data):
            if data[0]["approved_no_of_workers"] is None:
                approved_claims = 0
            else:
                approved_claims = data[0]["approved_no_of_workers"]
        else:
            approved_claims = 0
        job_order = frappe.get_doc(jobOrder, doc_name)
        worker_required = job_order.total_no_of_workers
        return int(approved_claims), worker_required
    except Exception:
        frappe.db.rollback()


@frappe.whitelist()
def modify_heads(doc_name):
    try:
        job = frappe.db.sql(
            f"""SELECT from_date, to_date, total_workers_filled, total_no_of_workers FROM `tabJob Order` WHERE name='{doc_name}'"""
        )
        total_worker_filled = 0
        claim_data = None
        if job[0][2] == 0:
            claim_data = no_worker_claim(doc_name)
        else:
            claim_data = f"""
            SELECT CO.name, CO.job_order, CO.staffing_organization, CO.notes,
            MT.job_title, MT.industry, MT.no_of_workers_joborder, MT.no_of_remaining_employee, MT.approved_no_of_workers,
            MT.staff_claims_no, MT.start_time, MT.duration, MT.bill_rate,(
                SELECT COUNT(AED.employee)
                FROM `tabAssign Employee Details` AED
                JOIN `tabAssign Employee` AE ON AE.name = AED.parent
                WHERE AED.job_category = MT.job_title AND AED.remove_employee=0 AND AED.job_start_time = MT.start_time
                AND AE.job_order = CO.job_order AND AE.tag_status = 'Approved' AND AE.company = CO.staffing_organization
            ) AS worker_filled,
            CASE WHEN (SELECT COUNT(*) FROM `tabCompany Review` WHERE staffing_company = CO.staffing_organization) >= 10
                THEN (SELECT average_rating FROM `tabCompany` WHERE name = CO.staffing_organization)
                ELSE 0
            END AS avg_rate
            FROM `tabClaim Order` AS CO, `tabMultiple Job Titles` AS MJT, `tabMultiple Job Title Claim` AS MT
            WHERE MJT.parent = CO.job_order AND MT.parent = CO.name AND CO.job_order = '{doc_name}' AND MT.staff_claims_no > 0
            AND MJT.select_job = MT.job_title AND MJT.job_start_time = MT.start_time
            ORDER BY job_title, start_time, staffing_organization
        """
        claims = frappe.db.sql(claim_data, as_dict=True)
        for i in claims:
            i['avg_rate'] = check_staffing_reviews(i['staffing_organization'])
        total_worker_filled += sum([c["worker_filled"] for c in claims])
        return claims, job, total_worker_filled
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.db.rollback()


@frappe.whitelist()
def no_worker_claim(doc_name):
    """Modify Head Count"""
    # It is called from the if part if the worker filled is 0, then still why it checks if there are any assign employee form.
    assign_emp = frappe.db.sql(
        f'''SELECT COUNT(name) FROM `tabAssign Employee` WHERE job_order="{doc_name}"'''
    )
    if assign_emp[0][0] > 0:
        return f"""
            SELECT CO.name, CO.job_order, CO.staffing_organization, CO.notes,
            MT.job_title, MT.industry, MT.no_of_workers_joborder, MT.no_of_remaining_employee, MT.approved_no_of_workers,
            MT.staff_claims_no, MT.start_time, MT.duration, MT.bill_rate,
            (
                SELECT COUNT(AED.employee)
                FROM `tabAssign Employee Details` AED
                JOIN `tabAssign Employee` AE ON AE.name = AED.parent
                WHERE AED.job_category = MT.job_title AND AED.remove_employee=0 AND AED.job_start_time = MT.start_time
                AND AE.job_order = CO.job_order AND AE.tag_status = 'Approved' AND AE.company = CO.staffing_organization
            ) AS worker_filled, CASE WHEN (SELECT COUNT(*) FROM `tabCompany Review` WHERE staffing_company = CO.staffing_organization) >= 10
                THEN (SELECT average_rating FROM `tabCompany` WHERE name = CO.staffing_organization)
                ELSE 0
            END AS avg_rate
            FROM `tabMultiple Job Titles` AS MJT, `tabClaim Order` AS CO,
            `tabMultiple Job Title Claim` AS MT WHERE MJT.parent=CO.job_order AND MT.parent=CO.name AND CO.job_order="{doc_name}"
            AND MT.staff_claims_no > 0 AND MJT.select_job=MT.job_title AND MJT.job_start_time=MT.start_time
            ORDER BY job_title, start_time, staffing_organization
        """

    else:
        return f"""
            SELECT CO.name, CO.job_order, CO.staffing_organization, CO.notes,
            MT.job_title, MT.industry, MT.no_of_workers_joborder, MT.no_of_remaining_employee, MT.approved_no_of_workers,
            MT.staff_claims_no, MT.start_time, MT.duration, MT.bill_rate, (
                SELECT COUNT(AED.employee)
                FROM `tabAssign Employee Details` AED
                JOIN `tabAssign Employee` AE ON AE.name = AED.parent
                WHERE AED.job_category = MT.job_title AND AED.remove_employee=0 AND AED.job_start_time = MT.start_time
                AND AE.job_order = CO.job_order AND AE.tag_status = 'Approved' AND AE.company = CO.staffing_organization
            ) AS worker_filled, CASE WHEN (SELECT COUNT(*) FROM `tabCompany Review` WHERE staffing_company = CO.staffing_organization) >= 10
                THEN (SELECT average_rating FROM `tabCompany` WHERE name = CO.staffing_organization)
                ELSE 0
            END AS avg_rate
            FROM `tabMultiple Job Titles` AS MJT, `tabClaim Order` AS CO,
            `tabMultiple Job Title Claim` AS MT WHERE MJT.parent=CO.job_order AND MT.parent=CO.name AND CO.job_order="{doc_name}"
            AND MT.staff_claims_no > 0 AND MJT.select_job=MT.job_title AND MJT.job_start_time=MT.start_time
            ORDER BY job_title, start_time, staffing_organization
        """


@frappe.whitelist(allow_guest=False)
def save_modified_claims(doc_name, updated_data):
    """
    The function saves modified claims data and sends notifications to relevant users.

    :param updated_data: A JSON string containing the updated data for the claim order
    :param doc_name: The name of the job order document
    :param notes_dict: The notes_dict parameter is a dictionary containing notes related to the updated
    claims. It is used to update the notes field of the claim document
    :return: the integer value 1.
    """
    try:
        updated_data = json.loads(updated_data)
        job = frappe.get_doc(jobOrder, doc_name)
        validate_total_workers(updated_data, job.total_no_of_workers, 'updated_approved_no')
        updated_comps = []
        for comp_claim, data in updated_data.items():
            comp_claim = comp_claim.split("~")
            comp = comp_claim[0]
            claim = comp_claim[1]
            updated_approved = 0
            claim = frappe.get_doc(claimOrder, claim)
            if not job.has_permission("read") or not claim.has_permission("read"):
                frappe.throw(('Insufficient Permission for user '+frappe.session.user))
            for update_dict in data:
                for row in claim.multiple_job_titles:
                    time = datetime.strptime(str(row.start_time), "%H:%M:%S")
                    if (
                        row.job_title == update_dict["job_title"]
                        and time.strftime("%H:%M") == update_dict["start_time"]
                    ):
                        validate_approved_claim(row, update_dict, "modify")
                        update_comp(updated_comps,row.approved_no_of_workers, update_dict["updated_approved_no"], comp_claim)
                        row.approved_no_of_workers = update_dict["updated_approved_no"]
                        updated_approved += update_dict["updated_approved_no"]
                        notes = re.sub(pattern, '', update_dict["notes"])

            claim.approved_no_of_workers = updated_approved
            claim.notes = notes
            claim.save(ignore_permissions=True)

            update_jo(job, comp)
            frappe.db.commit()

        modified_notification(updated_comps, job.company, job.name)
        return 1
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.db.rollback()


def update_comp(updated_comps, approved_no_of_workers, updated_approved_no, comp_claim):
    """
    The function updates a list of computer claims if the number of approved workers has changed.
    
    :param updated_comps: A list of updated compensation claims
    :param approved_no_of_workers: The number of workers that were originally approved for the company
    :param updated_approved_no: The updated number of workers that have been approved for the company
    :param comp_claim: The comp_claim parameter represents a claim for compensation
    """
    if approved_no_of_workers != updated_approved_no:
        updated_comps.append(comp_claim)


@frappe.whitelist()
def modified_notification(updated_comps, hiring_company, job_order):
    """
    The function `modified_notification` sends notifications to employees when a hiring company updates
    the approved number of employees needed for a specific job order.
    
    :param updated_comps: A list of tuples containing the company name and claim order ID for each
    updated company
    :param hiring_company: The `hiring_company` parameter represents the name of the company that is
    hiring for a job position
    :param job_order: The `job_order` parameter represents the specific job order for which the
    notification is being sent
    """
    try:
        for comp in updated_comps:
            msg = f"{hiring_company} has updated the approved no. of employees needed for {job_order}"
            user_data = f"""SELECT user_id FROM `tabEmployee` WHERE company = "{comp[0]}" AND user_id IS NOT NULL"""
            user_list = frappe.db.sql(user_data, as_list=1)
            user_list2 = [user[0] for user in user_list]
            sub = "Approve Claim Order"
            claim_order_app, claim_order_mail = get_mail_list(
                user_list2,
                app_field="select_count_app",
                mail_field="select_count_mail",
            )
            make_system_notification(claim_order_app, msg, claimOrder, comp[1], sub)
            link = f'  href="{sitename}/app/claim-order/{comp[1]}" '
            joborder_email_template(sub, msg, claim_order_mail, link)
    except Exception as e:
        print(e, frappe.get_traceback())


def check_partial_claim(
    job_order, staffing_org, no_required, no_assigned, hiring_org, doc_name
):
    """Partial Claim Direct Order"""
    try:
        job_order_data = frappe.get_doc(jobOrder, job_order)
        is_single_share = 0 if int(no_assigned) < int(no_required) else 1
        bid = 1 + int(job_order_data.bid)
        claimed = job_order_data.claim if job_order_data.claim else ""
        value1 = ""
        if len(claimed) == 0:
            value1 += str(staffing_org)
            chat_room_created(hiring_org, staffing_org, job_order)

        elif staffing_org not in claimed:
            value1 += str(claimed) + "~" + str(staffing_org)
            chat_room_created(hiring_org, staffing_org, job_order)
        else:
            value1 += str(claimed)
            chat_room_created(hiring_org, staffing_org, job_order)

        frappe.db.sql(
            'update `tabJob Order` set claim="{0}",bid="{1}",is_single_share={3} where name="{2}"'.format(
                value1, bid, job_order, is_single_share
            )
        )
        frappe.db.commit()

        sql1 = '''select email from `tabUser` where organization_type='hiring' and company = "{}"'''.format(
            hiring_org
        )
        hiring_list = frappe.db.sql(sql1, as_list=True)
        hiring_user_list = [user[0] for user in hiring_list]
        claim_order_app, claim_order_mail = get_mail_list(
            hiring_user_list, app_field="jo_claim_app", mail_field="jo_claim_mail"
        )
        if int(no_required) > int(no_assigned):
            sql = '''select email from `tabUser` where organization_type='staffing' and company != "{}"'''.format(
                staffing_org
            )
            share_list = frappe.db.sql(sql, as_list=True)
            assign_notification(share_list, hiring_user_list, doc_name, job_order)
            subject = "Job Order Notification"
            msg = f"{staffing_org} placed partial claim on your work order: {job_order_data.name}. Please review."
            make_system_notification(
                claim_order_app, msg, claimOrder, doc_name, subject
            )
            link = f'  href="{sitename}/app/claim-order/{doc_name}" '
            joborder_email_template(subject, msg, claim_order_mail, link)
            sql2 = """select email from `tabUser` where organization_type='staffing' and company != "{}" and company in (select staffing_company from `tabStaffing Radius` where job_site="{}" and radius != "None" and radius <= 25 and hiring_company="{}")""".format(
                staffing_org, job_order_data.job_site, job_order_data.company
            )
            share_list2 = frappe.db.sql(sql2, as_list=True)
            staffing_user_list = [user[0] for user in share_list2]
            staffing_user_list_app, staffing_user_list_mail = get_mail_list(
                staffing_user_list, app_field="jo_claim_app", mail_field="jo_claim_mail"
            )
            staff_email_sending_without_resume(
                job_order,
                no_required,
                no_assigned,
                hiring_org,
                job_order_data,
                staffing_user_list_app,
                staffing_user_list_mail,
                subject,
                doc_name,
            )
            return 1
        else:
            if hiring_user_list:
                subject = "Job Order Notification"
                for user in hiring_user_list:
                    add(
                        claimOrder,
                        doc_name,
                        user,
                        read=1,
                        write=0,
                        share=0,
                        everyone=0,
                        flags={"ignore_share_permission": 1},
                    )

                msg = f"{staffing_org} placed Full claim on your work order: {job_order_data.name}. Please review."
                make_system_notification(
                    claim_order_app, msg, claimOrder, doc_name, subject
                )
                link = f'  href="{sitename}/app/claim-order/{doc_name}" '
                joborder_email_template(subject, msg, claim_order_mail, link)
                return 1
    except Exception as e:
        frappe.log_error(e, "Partial Job order Failed ")


def staff_email_sending_without_resume(
    job_order,
    no_required,
    no_assigned,
    hiring_org,
    job_order_data,
    staffing_user_list_app,
    staffing_user_list_mail,
    subject,
    doc_name,
):
    query = f"""select sum(approved_no_of_workers) from `tabClaim Order` where job_order = "{job_order}" and name<>"{doc_name}" """
    rem_emp = frappe.db.sql(query)
    notification_func(
        job_order,
        no_required,
        no_assigned,
        hiring_org,
        job_order_data,
        staffing_user_list_app,
        staffing_user_list_mail,
        subject,
        rem_emp,
    )


def notification_func(
    job_order,
    no_required,
    no_assigned,
    hiring_org,
    job_order_data,
    staffing_user_list_app,
    staffing_user_list_mail,
    subject,
    rem_emp,
):
    count = (
        int(no_required) - int(rem_emp[0][0]) - int(no_assigned)
        if rem_emp[0][0] and job_order_data.is_repeat
        else int(no_required) - int(no_assigned)
    )
    if count > 0:
        if count == 1:
            newmsg = f"{hiring_org} has an order for {job_order_data.name} available with {count} opening available."
        else:
            newmsg = f"{hiring_org} has an order for {job_order_data.name} available with {count} openings available."
        make_system_notification(
            staffing_user_list_app, newmsg, jobOrder, job_order, subject
        )
        link_job_order = f'  href="{sitename}/app/job-order/{job_order}"'
        joborder_email_template(
            subject,
            newmsg,
            staffing_user_list_mail,
            link_job_order,
            sender_full_name=job_order_data.company,
            sender=job_order_data.owner,
        )


def assign_notification(share_list, hiring_user_list, doc_name, job_order):
    if share_list:
        for user in share_list:
            add(
                jobOrder,
                job_order,
                user[0],
                read=1,
                write=0,
                share=1,
                everyone=0,
                notify=0,
                flags={"ignore_share_permission": 1},
            )
    for user in hiring_user_list:
        add(
            claimOrder,
            doc_name,
            user,
            read=1,
            write=0,
            share=0,
            everyone=0,
            flags={"ignore_share_permission": 1},
        )


def claim_comp_assigned(claimed, doc_name, doc):
    if len(claimed) == 0:
        frappe.db.set_value(
            jobOrder,
            doc_name,
            "staff_org_claimed",
            (str(claimed) + str(doc.staffing_organization)),
        )
    elif str(doc.staffing_organization) not in claimed:
        frappe.db.set_value(
            jobOrder,
            doc_name,
            "staff_org_claimed",
            (str(claimed) + "~" + str(doc.staffing_organization)),
        )


@frappe.whitelist()
def claim_field_readonly(docname):
    try:
        sql = f'''select owner from tabVersion where docname = "{docname}"'''
        data = frappe.db.sql(sql, as_dict=1)
        if data:
            new_data = list({d["owner"] for d in data})
            for i in new_data:
                user_type = frappe.db.get_value(
                    "User", {"name": i}, ["organization_type"]
                )
                if user_type == "Hiring":
                    return "headcount_selected"
        return "headcount_not_selected"
    except Exception as e:
        frappe.log_error(e, "Claim Field Read Only Error")
        print(e, frappe.get_traceback())


@frappe.whitelist()
def set_pay_rate(hiring_company, job_title, job_site, staffing_company):
    """
    Old Function
    New Function : get_pay_rate_class_code
    """
    try:
        emp_pay_rate = frappe.db.exists(
            EPR,
            {
                "hiring_company": hiring_company,
                "job_title": job_title,
                "job_site": job_site,
                "staffing_company": staffing_company,
            },
        )
        if emp_pay_rate:
            return frappe.db.get_value(
                EPR, {"name": emp_pay_rate}, ["employee_pay_rate"]
            )
        else:
            all_query = "select job_pay_rate,hiring_company,job_site from `tabPay Rates`  where   parent = '{}' and staffing_company='{}' and hiring_company='{}' and job_site='{}'".format(
                job_title, staffing_company, hiring_company, job_site
            )
            hiring_company_query = "select job_pay_rate,hiring_company,job_site from `tabPay Rates`  where  parent = '{}' and staffing_company='{}' and hiring_company='{}'".format(
                job_title, staffing_company, hiring_company
            )
            only_job_title_query = "select job_pay_rate,hiring_company,job_site from `tabPay Rates`  where   parent = '{}' and staffing_company='{}'".format(
                job_title, staffing_company
            )

            job_title_query = "select wages from `tabJob Titles` where job_titles ='{}' and parent = '{}'".format(
                job_title, staffing_company
            )
            all_query_res = frappe.db.sql(all_query, as_dict=1)
            hiring_company_res = frappe.db.sql(hiring_company_query, as_dict=1)
            only_job_title_res = frappe.db.sql(only_job_title_query, as_dict=1)
            job_title_res = frappe.db.sql(job_title_query, as_dict=1)

            if all_query_res:
                return all_query_res[0]["job_pay_rate"]
            elif hiring_company_res:
                return hiring_company_res[0]["job_pay_rate"]
            elif only_job_title_res:
                return only_job_title_res[0]["job_pay_rate"]
            else:
                if job_title_res:
                    return job_title_res[0]["wages"]
    except Exception as e:
        frappe.log_error(e, "Set Pay Rate Error")


@frappe.whitelist()
def payrate_change(docname):
    """
    This function checks if a specific field has been changed in a document and returns "success" if it
    has, and "failure" if it hasn't.

    :param docname: The parameter `docname` is a string variable that represents the name of a document
    in the database. The function `payrate_change` retrieves the data of the latest version of this
    document and checks if there has been a change in the "staff_claims_no" field. If there has been
    :return: either "success" or "failure" depending on certain conditions. If there is no new data, it
    returns "success". If there is new data and the field "staff_claims_no" has been changed, it also
    returns "success". Otherwise, it returns "failure".
    """
    try:
        sql = """select data from `tabVersion` where docname="{}" order by modified DESC""".format(
            docname
        )
        data = frappe.db.sql(sql, as_list=1)
        new_data = json.loads(data[0][0]) if data else []
        if not new_data:
            return "success"
        elif "row_changed" in new_data:
            for i in new_data["row_changed"]:
                for j in i[3]:
                    if j[0] == "staff_claims_no":
                        return "success"
        return "failure"
    except Exception as e:
        frappe.log_error(e, "Pay Rate Change Error")
        print(e, frappe.get_traceback())


@frappe.whitelist()
def create_pay_rate(hiring_company, job_order, employee_pay_rate, staffing_company):
    """
    Old function, will remove after assign employee flow is stabilized
    New function: create_pay_rate_new
    """
    try:
        frappe.enqueue(
            "tag_workflow.tag_workflow.doctype.claim_order.claim_order.create_pay_rate_job",
            now=True,
            hiring_company=hiring_company,
            job_order=job_order,
            employee_pay_rate=employee_pay_rate,
            staffing_company=staffing_company,
        )
    except Exception as e:
        print("create_pay_rate Error", e, frappe.get_traceback())
        frappe.log_error(e, "Set Pay Rate Error")


@frappe.whitelist()
def create_pay_rate_job(hiring_company, job_order, employee_pay_rate, staffing_company):
    """
    Old function, will remove after assign employee flow is stabilized
    New function: create_pay_rate_new
    """
    try:
        job_title, job_site = frappe.db.get_value(
            jobOrder, {"name": job_order}, ["select_job", "job_site"]
        )
        emp_pay_rate = frappe.db.exists(
            EPR,
            {
                "hiring_company": hiring_company,
                "job_title": job_title,
                "job_site": job_site,
                "staffing_company": staffing_company,
            },
        )
        if emp_pay_rate:
            pay_rate = frappe.db.get_value(
                EPR, {"name": emp_pay_rate}, ["employee_pay_rate"]
            )
            if pay_rate != employee_pay_rate:
                frappe.db.set_value(
                    EPR, emp_pay_rate, "employee_pay_rate", employee_pay_rate
                )

        else:
            doc = frappe.new_doc(EPR)
            doc.hiring_company = hiring_company
            doc.job_title = job_title
            doc.job_site = job_site
            doc.employee_pay_rate = employee_pay_rate
            doc.staffing_company = staffing_company
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(e, "Set Pay Rate Job Error")


@frappe.whitelist()
def auto_claims_approves(staffing_org, job, doc_claim):
    """
    The function updates job order and multiple job title claim records and sends notifications and
    emails for approved auto claims.

    :param staffing_org: The organization that is approving the auto claim
    :param job: The "job" parameter is a JSON object that contains information about a job order,
    including the name of the job, the company it belongs to, and the claims and staff organization
    claimed for the job
    :param doc_claim: The parameter `doc_claim` is a string representing the name of a document in the
    `Claim Order` doctype
    :return: the integer value 1.
    """
    try:
        job = json.loads(job)
        claims = job["claim"] if job["claim"] else ""
        claimed = job["staff_org_claimed"] if job["staff_org_claimed"] else ""
        value1 = ""
        if len(claimed) == 0:
            value1 += str(claimed) + str(staffing_org)
        elif staffing_org not in claimed:
            value1 += str(claimed) + "~" + str(staffing_org)
        else:
            value1 += str(claimed)
        value2 = ""
        if len(claims) == 0:
            value2 += str(claims) + str(staffing_org)
        elif str(staffing_org) not in claims:
            value2 += str(claims) + "~" + str(staffing_org)
        else:
            value2 += str(claims)

        sql = f"""
        UPDATE `tabJob Order` AS JO SET JO.staff_org_claimed = "{value1}", JO.claim = "{value2}"
        WHERE JO.name = "{job["name"]}"
        """
        frappe.db.sql(sql)

        sql = f"UPDATE `tabMultiple Job Title Claim` AS MJTC SET MJTC.approved_no_of_workers = MJTC.staff_claims_no WHERE MJTC.parent='{doc_claim}'"
        frappe.db.sql(sql)
        user_data = """
        select user_id from `tabEmployee` where user_id IS NOT NULL and company = "{}"
        UNION
        SELECT IFNULL(SUM(approved_no_of_workers), 0) FROM `tabMultiple Job Title Claim` WHERE parent="{}"
        """.format(
            staffing_org, doc_claim
        )
        user_list = frappe.db.sql(user_data, as_list=1)
        approved = user_list.pop()
        frappe.db.set_value(
            claimOrder, doc_claim, "approved_no_of_workers", int(approved[0])
        )
        frappe.db.commit()
        user_list2 = [user[0] for user in user_list]
        sub = "Approve Claim Orders"
        msg = f"{job['company']} has approved {approved[0]} employees for {job['name']}. Don't forget to assign employees to this order."
        claim_order_app, claim_order_mail = get_mail_list(
            user_list2, app_field="select_count_app", mail_field="select_count_mail"
        )
        make_system_notification(claim_order_app, msg, claimOrder, doc_claim, sub)
        link = f'  href="{sitename}/app/claim-order/{doc_claim}" '
        joborder_email_template(sub, msg, claim_order_mail, link)
        return 1
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.db.rollback()


@frappe.whitelist()
def update_notes(data):
    try:
        data = json.loads(data)
        for k, v in data.items():
            notes = frappe.db.get_value(claimOrder, {"name": k}, ["notes"])
            if str(notes).strip() == str(v).strip():
                continue
            frappe.db.set_value(claimOrder, k, "notes", v)
    except Exception as e:
        print(e, frappe.utils.get_traceback())


def hide_and_show(c, doc_name, assigned_worker):
    try:
        total_approved = (
            frappe.db.get_list(
                claimOrder,
                filters={
                    "staffing_organization": c["staffing_organization"],
                    "job_order": doc_name,
                },
                fields=["SUM(approved_no_of_workers) as total_approved"],
            )[0]["total_approved"]
            or 0
        )
        if (assigned_worker is not None and assigned_worker < total_approved) or c[
            "approved_no_of_workers"
        ] == 0:
            c["hide"] = 0
            c["assigned_worker"] = assigned_worker
        elif assigned_worker is not None and assigned_worker >= total_approved:
            c["hide"] = 1
    except Exception as e:
        print(e, frappe.utils.get_traceback())


@frappe.whitelist()
def create_staff_comp_code(
    job_order, staff_class_code, staffing_company, staff_class_code_rate
):
    """
    Old function, will remove after assign employee flow is stabilized
    New function: create_staff_comp_code_new
    """
    try:
        frappe.enqueue(
            "tag_workflow.tag_workflow.doctype.claim_order.claim_order.create_staff_comp_code_job",
            now=True,
            job_order=job_order,
            staff_class_code=staff_class_code,
            staffing_company=staffing_company,
            staff_class_code_rate=staff_class_code_rate,
        )
    except Exception as e:
        print("create_staff_comp_code Error", e, frappe.get_traceback())
        frappe.log_error(e, "create_staff_comp_code Error")


@frappe.whitelist()
def create_staff_comp_code_job(
    job_order, staff_class_code, staffing_company, staff_class_code_rate
):
    """
    Old function, will remove after assign employee flow is stabilized
    New function: create_staff_comp_code_new
    """
    try:
        job_title, job_site, industry_type = frappe.db.get_value(
            jobOrder, {"name": job_order}, ["select_job", "job_site", "category"]
        )
        if len(staff_class_code) > 0:
            job_titlename = job_title_value(job_title)
            state = frappe.db.get_value("Job Site", job_site, ["state"])
            check_industry_vals = frappe.db.sql(
                'select name from `tabStaffing Comp Code` where job_industry="{}" and staffing_company="{}" and job_title like "{}%" '.format(
                    industry_type, staffing_company, job_titlename
                ),
                as_dict=1,
            )
            if len(check_industry_vals) > 0:
                check_staff_comp_code_existence(
                    state,
                    staff_class_code_rate,
                    staff_class_code,
                    industry_type,
                    staffing_company,
                    job_titlename,
                    check_industry_vals,
                )
            else:
                doc = frappe.get_doc(
                    {
                        "doctype": SCC,
                        "job_industry": industry_type,
                        "job_title": job_titlename,
                        "staffing_company": staffing_company,
                        "class_codes": [
                            {
                                "class_code": staff_class_code,
                                "rate": staff_class_code_rate,
                                "state": state,
                            }
                        ],
                    }
                )
                meta = frappe.get_meta(SCC)
                for field in meta.get_link_fields():
                    field.ignore_user_permissions = 1
                doc.flags.ignore_permissions = True
                doc.insert()
                frappe.db.commit()
    except Exception as e:
        frappe.logger().debug("Set Class Code Job Error", frappe.get_traceback())
        frappe.log_error(e, "Set Class Code Job Error")


def job_title_value(job_title):
    job_title_name = job_title.split("-")
    if len(job_title_name) == 1:
        job_titlename = job_title
    else:
        job_names = job_title_name[-1]
        if (job_names).isnumeric():
            last_occurence = job_title.rfind("-")
            job_titlename = job_title[0:last_occurence]
        else:
            job_titlename = job_title
    return job_titlename


@frappe.whitelist()
def check_already_exist_class_code(job_order, staffing_company):
    try:
        job_title, job_site, industry_type = frappe.db.get_value(
            jobOrder, job_order, ["select_job", "job_site", "category"]
        )
        job_titlename = job_title_value(job_title)
        state = frappe.db.get_value(jobSite, job_site, ["state"])
        comp_code = frappe.db.sql(
            'select SCC.name from `tabStaffing Comp Code` as SCC inner join `tabClass Code` as CC on SCC.name=CC.parent where job_industry="{}" and CC.state="{}" and staffing_company="{}" and job_title like "{}%"'.format(
                industry_type, state, staffing_company, job_titlename
            ),
            as_dict=1,
        )
        if len(comp_code) > 0:
            data = frappe.db.sql(
                """ select class_code,rate from `tabClass Code` where parent="{}" and state="{}" """.format(
                    comp_code[0].name, state
                ),
                as_dict=1,
            )
            class_code = data[0].class_code
            rate = data[0].rate
            return class_code, rate
        else:
            return ["Exist"]
    except Exception as e:
        frappe.log_error(e, "Set Class Code Error")


def check_staff_comp_code_existence(
    state,
    staff_class_code_rate,
    staff_class_code,
    industry_type,
    staffing_company,
    job_titlename,
    check_industry_vals,
):
    comp_code = frappe.db.sql(
        'select SCC.name from `tabStaffing Comp Code` as SCC inner join `tabClass Code` as CC on SCC.name=CC.parent where job_industry="{}" and CC.state="{}" and staffing_company="{}" and job_title like "{}%" '.format(
            industry_type, state, staffing_company, job_titlename
        ),
        as_dict=1,
    )
    if len(comp_code) > 0:
        data = frappe.db.sql(
            """ select class_code,rate from `tabClass Code` where parent="{}" and state="{}" """.format(
                comp_code[0].name, state
            ),
            as_dict=1,
        )
        class_code = data[0].class_code
        code_rate = data[0].rate
        if code_rate != staff_class_code_rate or class_code != staff_class_code:
            frappe.db.sql(
                '''update `tabClass Code` set class_code="{}", rate="{}" where parent="{}" and state="{}"'''.format(
                    staff_class_code, staff_class_code_rate, comp_code[0].name, state
                )
            )
            frappe.db.commit()
    else:
        doc = frappe.get_doc(SCC, check_industry_vals[0].name)
        adding_values(doc, staff_class_code, staff_class_code_rate, state)


def adding_values(doc, staff_class_code, staff_class_code_rate, state):
    doc.append(
        "class_codes",
        {"class_code": staff_class_code, "rate": staff_class_code_rate, "state": state},
    )
    doc.save(ignore_permissions=True)


@frappe.whitelist()
def fetch_notes(company, job_order):
    try:
        return frappe.db.sql(
            """ select notes from `tabClaim Order` where job_order="{}" and staffing_organization="{}" and notes!=""  limit 1 """.format(
                job_order, company
            ),
            as_dict=1,
        )
    except Exception as e:
        print(e)


@frappe.whitelist()
def check_and_create_pay_rates(
    name, staffing_company, hiring_company, job_site, rate, job_order
):
    check_payrates = frappe.db.sql(
        """select name from `tabPay Rates`
        where staffing_company="{}" and parent="{}" and hiring_company="{}" and job_site="{}"
        """.format(
            staffing_company, name, hiring_company, job_site
        ),
        as_list=1,
    )
    if not check_payrates:
        insert_or_update_rates = """ INSERT INTO `tabPay Rates` (name,owner,parent,parentfield,parenttype,
        staffing_company,hiring_company,job_site,job_pay_rate,job_order) values
        """ + str(
            tuple(
                [
                    uuid4().hex[:10],
                    frappe.session.user,
                    name,
                    "pay_rate",
                    "Item",
                    staffing_company,
                    hiring_company,
                    job_site,
                    rate,
                    job_order,
                ]
            )
        )
    else:
        insert_or_update_rates = """update `tabPay Rates` set job_pay_rate= "{}"
        where staffing_company="{}" and hiring_company="{}" and job_site="{}"
        """.format(
            rate, staffing_company, hiring_company, job_site
        )
    frappe.db.sql(insert_or_update_rates)
    frappe.db.commit()


def get_item_series_name(title):
    split_value = title.split("-")
    if len(split_value) == 1:
        name = title + "-1"
    else:
        number = split_value[-1]
        if number.isnumeric():
            last_occurence = title.rfind("-")
            name = title[0:last_occurence] + "-" + str(int(number) + 1)
        else:
            name = title
    return name


@frappe.whitelist()
def get_or_create_jobtitle(
    job_order, staffing_company, hiring_company, employee_pay_rate
):
    """
    Old function, will remove after assign employee flow is stabilized
    New function: get_or_create_job_title_new
    """
    try:
        get_job_order_data = frappe.db.sql(
            "select select_job,job_site,rate,category,company from `tabJob Order` where name='{}'".format(
                job_order
            ),
            as_dict=1,
        )
        job_title_name = get_job_order_data[0]["select_job"]
        check_item_data = frappe.db.sql(
            "select name from `tabItem` where name like '{}%' and company='{}'".format(
                job_title_name.split("-")[0], staffing_company
            ),
            as_dict=1,
        )
        job_title = frappe.db.sql(
            """ select wages, industry_type, description from `tabJob Titles` where job_titles like '{}%' and parent = '{}'""".format(
                get_job_order_data[0]["select_job"], hiring_company
            ),
            as_dict=1,
        )
        if job_title:
            if check_item_data:
                check_and_create_pay_rates(
                    check_item_data[0]["name"],
                    staffing_company,
                    hiring_company,
                    get_job_order_data[0]["job_site"],
                    employee_pay_rate,
                    job_order,
                )
            else:
                item_doc = frappe.get_doc("Item", job_title_name)
                new_doc = frappe.copy_doc(item_doc)
                item_name = frappe.db.sql(
                    f"""select name from tabItem where name like "{job_title_name.split("-")[0]}%" order by CAST(SUBSTRING_INDEX(name, '-', -1) AS INT) desc limit 1""",
                    as_list=1,
                )
                item_last_no = (
                    int(item_name[0][0].split("-")[1]) + 1
                    if "-" in item_name[0][0]
                    else 1
                )
                new_doc.name = f"{item_name[0][0].split('-')[0]}-{item_last_no}"
                new_doc.company = staffing_company
                new_doc.job_titless = new_doc.item_code = new_doc.name
                new_doc.job_titless_name = new_doc.name.split("-")[0]
                new_doc.rate = employee_pay_rate
                new_doc.set("job_site_table", [])
                new_doc.set("pay_rate", [])
                new_doc.is_company = 1
                new_doc.insert(ignore_permissions=True)
                new_doc.item_name = new_doc.name
                new_doc.save(ignore_permissions=True)
                add_job_title_company(
                    parent=staffing_company,
                    job_title=new_doc.name,
                    description=job_title[0]["description"],
                    rate=employee_pay_rate,
                    industry=get_job_order_data[0]["category"],
                )
                frappe.db.commit()
                check_and_create_pay_rates(
                    new_doc.name,
                    staffing_company,
                    hiring_company,
                    get_job_order_data[0]["job_site"],
                    employee_pay_rate,
                    job_order,
                )
    except Exception as e:
        print(e, frappe.get_traceback())


@frappe.whitelist(allow_guest=False)
def additional_claim(
    job_order, staff_comp, no_of_workers=None, order_status=None, direct_comp=None
):
    """
    This function checks if an additional claim can be made based on various conditions related to job
    orders and staff companies.

    :param job_order: The name of the job order for which the additional claim is being requested
    :param staff_comp: `staff_comp` is a JSON string that contains a list of staff companies. It is used
    to determine if the staff company of the user creating the claim matches the staff company of the
    job order
    :param no_of_workers: The number of workers for the job order. If this parameter is not provided,
    the function will retrieve the total number of workers from the job order
    :param order_status: The order_status parameter is used to specify the current status of the job
    order. It is an optional parameter and if not provided, it will be fetched from the database
    :param direct_comp: The direct_comp parameter is an optional argument that represents the name of
    the company that directly ordered the job. If this parameter is not provided, the function will
    retrieve the staff_company2 value from the Job Order table
    :return: either "no_button", "new_claim", or the result of calling the function
    "additional_claim_contd" with the arguments "job_order" and "staff_comp".
    """
    try:
        user_comp = frappe.db.get_value("User", frappe.session.user, "company")
        if user_comp not in staff_comp:
            frappe.throw('Insufficient Permission for user')
        staff_comp = json.loads(staff_comp)
        jo_headcount = (
            frappe.db.sql(
                f'''select total_no_of_workers, order_status, staff_company2  from `tabJob Order` where name="{job_order}"''',
                as_list=1,
            )
            if not no_of_workers
            else [[no_of_workers, order_status]]
        )
        approved_headcount = frappe.db.sql(
            f'''select  IFNULL(sum(approved_no_of_workers),0), hiring_organization from `tabClaim Order` where job_order="{job_order}"''',
            as_list=1,
        )
        if (
            jo_headcount[0][1] in ["Completed", "Canceled"]
            or float(jo_headcount[0][0]) <= approved_headcount[0][0]
        ):
            return "no_button"
        direct_order = direct_comp if direct_comp else jo_headcount[0][2]
        if (
            direct_order
            and direct_order != "normal"
            and set(direct_order.split("~")) & set(staff_comp)
        ):
            return "new_claim"
        return additional_claim_contd(job_order, staff_comp)
    except Exception as e:
        print(frappe.get_traceback())
        frappe.log_error(e, "Additional Claim Error")


@frappe.whitelist()
def additional_claim_contd(job_order, staff_comp):
    try:
        claims = (
            f'select name from `tabClaim Order` where job_order="{job_order}" and staffing_organization="{staff_comp[0]}" order by name desc'
            if len(staff_comp) == 1
            else f'select name from `tabClaim Order` where job_order="{job_order}" and staffing_organization in {tuple(staff_comp)} order by name desc'
        )
        data = frappe.db.sql(claims, as_dict=1)
        if data:
            claims_version = f"select owner from `tabVersion` where docname='{data[0]['name']}' and ref_doctype='Claim Order' order by modified desc"
            claims_updater = frappe.db.sql(claims_version, as_dict=1)
            if claims_updater:
                for j in claims_updater:
                    user_type = frappe.db.get_value(
                        "User", {"name": j["owner"]}, ["organization_type"]
                    )
                    if user_type == "Hiring":
                        return "new_claim"
                    else:
                        return data[0]["name"]
            return data[0]["name"]
        return "new_claim"
    except Exception as e:
        print(frappe.get_traceback())
        frappe.log_error(e, "additional_claim_contd Error")


@frappe.whitelist()
def get_joborder_data(job_order):
    """
    The function retrieves data related to a job order, including job titles, start time, duration,
    number of workers, remaining employees, approved workers, and bill rate.

    :param job_order: The parameter `job_order` is a string variable that represents the name of a job
    order document in the ERPNext system. It is used to retrieve data related to the job order from the
    database and the job order document
    :return: a tuple containing three values: a list of dictionaries containing job order data, the
    company associated with the job order, and the contract add-on associated with the job order.
    """
    try:
        result = []
        claims = f"""
            SELECT MT.job_title, MT.start_time, IFNULL(SUM(MT.approved_no_of_workers),0) AS approved
            FROM `tabMultiple Job Title Claim` AS MT,
            `tabClaim Order` AS CO
            WHERE CO.name = MT.parent AND CO.job_order="{job_order}"
            GROUP BY MT.start_time, MT.job_title
        """
        claim_data = frappe.db.sql(claims, as_list=1)
        job_order_doc = frappe.get_doc(jobOrder, job_order)
        data = job_order_doc.multiple_job_titles
        for row in data:
            rows = {}
            rows["job_title"] = row.select_job
            rows["industry"] = row.category
            rows["start_time"] = row.job_start_time
            rows["duration"] = row.estimated_hours_per_day
            rows["no_of_workers_joborder"] = row.no_of_workers
            for claim in claim_data:
                if (
                    claim[0] == row.select_job
                    and claim[1] == row.job_start_time
                    and claim[2] is not None
                ):
                    rows["no_of_remaining_employee"] = int(row.no_of_workers) - int(claim[2])
                    rows["approved_no_of_workers"] = int(claim[2])
            rows["bill_rate"] = round(row.per_hour + row.flat_rate, 2)
            result.append(rows)
        return result, job_order_doc.company, job_order_doc.contract_add_on
    except Exception as e:
        frappe.log_error(e, "get_joborder_data Error")


@frappe.whitelist()
def get_pay_rate_class_code(job_order, staffing_company):
    """
    This function retrieves the pay rate class code and employee pay rate for a given job order and
    staffing company.

    :param job_order: The job order is a JSON object that contains information about a job opening, such
    as the job title, job site, and industry type
    :param staffing_company: The staffing company is a parameter that represents the company that
    provides staffing services to other companies. It is used in the function to retrieve pay rates and
    class codes for job orders based on the staffing company's information
    :return: a dictionary containing pay rate information for each job title in the job order. The
    dictionary has job titles as keys and nested dictionaries as values. The nested dictionaries contain
    information about the compensation code, rate, and employee pay rate for each job title.
    """
    try:
        job_order = json.loads(job_order)
        res = {}
        for row in job_order["multiple_job_titles"]:
            res1 = {}
            job_title, job_site, industry_type = (
                row["select_job"],
                job_order["job_site"],
                row["category"],
            )
            job_titlename = job_title_value(job_title)
            state = frappe.db.get_value(jobSite, job_site, ["state"])
            sql = f"""
            SELECT class_code,rate FROM `tabClass Code` WHERE state="{state}" AND parent IN
            (SELECT SCC.name FROM `tabStaffing Comp Code` AS SCC INNER JOIN `tabClass Code` AS CC
            ON SCC.name=CC.parent WHERE job_industry="{industry_type}" AND CC.state="{state}"
            AND staffing_company="{staffing_company}" AND job_title LIKE "{job_titlename}%")
            """

            comp_code = frappe.db.sql(sql, as_dict=1)
            if len(comp_code) > 0:
                res1["comp_code"] = comp_code[0].class_code
                res1["rate"] = comp_code[0].rate

            emp_pay_rate = frappe.db.get_value(
                EPR,
                {
                    "hiring_company": job_order["company"],
                    "job_title": job_title,
                    "job_site": job_site,
                    "staffing_company": staffing_company,
                },
                ["employee_pay_rate"],
            )
            if emp_pay_rate:
                res1["emp_pay_rate"] = emp_pay_rate
            else:
                sql = f"""
                SELECT job_pay_rate FROM `tabPay Rates` WHERE parent IN
                (SELECT name FROM tabItem WHERE name like "{job_title.split("-")[0]}%" AND industry="{industry_type}")
                AND staffing_company="{staffing_company}" AND hiring_company="{job_order["company"]}" AND job_site="{job_site}"
                UNION ALL
                SELECT job_pay_rate FROM `tabPay Rates` WHERE parent IN
                (SELECT name FROM tabItem WHERE name LIKE "{job_title.split("-")[0]}%" AND industry="{industry_type}")
                AND staffing_company="{staffing_company}" AND hiring_company="{job_order["company"]}"
                UNION ALL
                SELECT job_pay_rate FROM `tabPay Rates` WHERE parent IN
                (SELECT name FROM tabItem WHERE name LIKE "{job_title.split("-")[0]}%" AND industry="{industry_type}")
                AND staffing_company="{staffing_company}"
                UNION ALL
                SELECT wages from `tabJob Titles` WHERE job_titles LIKE "{job_title.split("-")[0]}%"
                AND parent = "{staffing_company}" AND industry_type="{industry_type}"
                """
                data = frappe.db.sql(sql, as_dict=1)
                if len(data) > 0:
                    res1["emp_pay_rate"] = data[0].job_pay_rate
            res[job_title] = res1
        return res
    except Exception as e:
        print(e, "get_pay_rate_class_code error")


@frappe.whitelist()
def create_pay_rate_comp_code_job_title(job_order, claim_order):
    """
    This function creates pay rate, staff compensation code, and job title for a claim order based on
    job order details in a background job.

    :param job_order: The job order is a JSON object that contains information about a job order
    :param claim_order: The parameter `claim_order` is a JSON object that contains information about a
    claim order, including the staffing organization, multiple job titles, and other relevant details
    """
    try:
        job_site = job_order.job_site
        staffing_company = claim_order.staffing_organization
        hiring_company = job_order.company
        for index, row in enumerate(claim_order.multiple_job_titles):
            job_title, industry_type = (
                row.job_title,
                job_order.multiple_job_titles[index].category,
            )
            if row.employee_pay_rate > 0:
                frappe.enqueue(
                    "tag_workflow.tag_workflow.doctype.claim_order.claim_order.create_pay_rate_new",
                    hiring_company=hiring_company,
                    job_title=job_title,
                    job_site=job_site,
                    staffing_company=staffing_company,
                    row=row,
                    now=True,
                )
                frappe.enqueue(
                    "tag_workflow.tag_workflow.doctype.claim_order.claim_order.get_or_create_jobtitle_new",
                    job_title=job_title,
                    staffing_company=staffing_company,
                    hiring_company=hiring_company,
                    job_site=job_site,
                    job_order=job_order,
                    row=row,
                    industry_type=industry_type,
                    now=True,
                )
            frappe.enqueue(
                "tag_workflow.tag_workflow.doctype.claim_order.claim_order.create_staff_comp_code_new",
                row=row,
                job_title=job_title,
                job_site=job_site,
                industry_type=industry_type,
                staffing_company=staffing_company,
                now=True,
            )
    except Exception as e:
        print(e, frappe.get_traceback(), "create_pay_rate_comp_code_job_title Error")


@frappe.whitelist()
def create_pay_rate_new(hiring_company, job_title, job_site, staffing_company, row):
    """
    This function creates or updates an employee pay rate based on certain conditions.

    :param hiring_company: The company that is hiring for the job position
    :param job_title: The job title for which the pay rate is being set
    :param job_site: The job site refers to the physical location where the job is being performed. It
    could be an office, a factory, a construction site, or any other place where work is being done
    :param staffing_company: The parameter "staffing_company" is a variable that holds the name of the
    staffing company for which the employee pay rate is being created or updated
    :param row: The "row" parameter is a dictionary containing the data for a single row of the table
    being processed. It likely contains information such as the employee's name and their corresponding
    pay rate
    """
    try:
        sql = f'''SELECT name, employee_pay_rate FROM `tabEmployee Pay Rate`
        WHERE hiring_company="{hiring_company}" AND job_title="{job_title}"
        AND job_site="{job_site}" AND staffing_company="{staffing_company}"'''
        emp_pay_rate = frappe.db.sql(sql)
        if not emp_pay_rate:
            frappe.get_doc(
                {
                    "doctype": EPR,
                    "hiring_company": hiring_company,
                    "job_title": job_title,
                    "job_site": job_site,
                    "employee_pay_rate": row.employee_pay_rate,
                    "staffing_company": staffing_company,
                }
            ).insert(ignore_permissions=True)
        elif row.employee_pay_rate != emp_pay_rate[0][1]:
            frappe.db.set_value(
                EPR, emp_pay_rate[0][0], "employee_pay_rate", row.employee_pay_rate
            )
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(e, "Set Pay Rate Job Error")


@frappe.whitelist()
def create_staff_comp_code_new(
    row, job_title, job_site, industry_type, staffing_company
):
    """
    This function creates a new Staffing Comp Code document with class codes based on input parameters,
    or updates an existing one if it already exists.

    :param row: The "row" parameter is a dictionary containing the data for a single row of the table
    being processed. It likely contains information such as the job title, worker's comp code and rate
    :param job_title: The job title of the staff member for whom the compensation code is being created
    :param job_site: job_site is a variable that contains the name of the job site for which the worker's
    compensation code is being created. It is used to fetch the state of the job site from the database
    :param industry_type: The industry type for which the staffing company is creating a new staff
    compensation code
    :param staffing_company: The name of the staffing company for which the staff compensation code is
    being created
    """
    try:
        if row.staff_class_code and len(row.staff_class_code) > 0:
            job_titlename = job_title_value(job_title)
            state = frappe.db.get_value(jobSite, job_site, ["state"])
            check_industry_vals = frappe.db.sql(
                """SELECT name FROM `tabStaffing Comp Code` WHERE job_industry="{}" AND staffing_company="{}" AND
                job_title LIKE "{}%" """.format(
                    industry_type, staffing_company, job_titlename
                ),
                as_dict=1,
            )
            if len(check_industry_vals) > 0:
                check_staff_comp_code_existence(
                    state,
                    row.staff_class_code_rate,
                    row.staff_class_code,
                    industry_type,
                    staffing_company,
                    job_titlename,
                    check_industry_vals,
                )
            else:
                doc = frappe.get_doc(
                    {
                        "doctype": SCC,
                        "job_industry": industry_type,
                        "job_title": job_titlename,
                        "staffing_company": staffing_company,
                        "class_codes": [
                            {
                                "class_code": row.staff_class_code,
                                "rate": row.staff_class_code_rate,
                                "state": state,
                            }
                        ],
                    }
                )
                meta = frappe.get_meta(SCC)
                for field in meta.get_link_fields():
                    field.ignore_user_permissions = 1
                doc.flags.ignore_permissions = True
                doc.insert()
                frappe.db.commit()
    except Exception as e:
        frappe.log_error(e, "Create Staff Comp Code Job Error")


@frappe.whitelist()
def get_or_create_jobtitle_new(
    job_title, staffing_company, hiring_company, job_site, job_order, row, industry_type
):
    """
    This function creates a new job title item and adds it to the database if it does not already exist,
    and then checks and creates pay rates for the job title.

    :param job_title: The name of the job title being created or retrieved
    :param staffing_company: The company that is providing staffing services
    :param hiring_company: The hiring_company parameter is the name of the company that is hiring for
    the job position
    :param job_site: The job site parameter is likely a reference to a specific job site where the job
    title is being used or required. It is used as a parameter in the function to create or update pay
    rates for the job title at that specific job site
    :param job_order: Based on the code, `job_order` is a dictionary object that contains information
    about the job order. It is passed as an argument to the `get_or_create_jobtitle` function.
    :param row: The "row" parameter is a dictionary containing the data for a single row of the table
    being processed. It likely contains information such as the job title and pay rate
    :param industry_type: The industry type is a parameter that is passed to the function
    `get_or_create_jobtitle()`. It is used to specify the industry type of the job title being created
    or updated. It is used in the function to add the job title to the appropriate industry type in the
    `add_job_title_company
    """
    try:
        check_item_data = frappe.db.sql(
            'SELECT name FROM `tabItem` WHERE name LIKE "{}%" AND company="{}"'.format(
                job_title.split("-")[0], staffing_company
            ),
            as_dict=1,
        )
        job_title_data = frappe.db.sql(
            'SELECT description FROM `tabJob Titles` WHERE job_titles LIKE "{}%" AND parent = "{}"'.format(
                job_title, hiring_company
            ),
            as_dict=1,
        )
        if job_title_data:
            if check_item_data:
                check_and_create_pay_rates(
                    check_item_data[0]["name"],
                    staffing_company,
                    hiring_company,
                    job_site,
                    row.employee_pay_rate,
                    job_order.name,
                )
            else:
                item_doc = frappe.get_doc("Item", job_title)
                new_doc = frappe.copy_doc(item_doc)
                item_name = frappe.db.sql(
                    f"""SELECT name FROM tabItem WHERE name LIKE "{job_title.split("-")[0]}%" ORDER BY CAST(SUBSTRING_INDEX(name, '-', -1) AS INT) DESC LIMIT 1""",
                    as_list=1,
                )
                item_last_no = (
                    int(item_name[0][0].split("-")[1]) + 1
                    if "-" in item_name[0][0]
                    else 1
                )
                new_doc.name = f"{item_name[0][0].split('-')[0]}-{item_last_no}"
                new_doc.company = staffing_company
                new_doc.job_titless = new_doc.item_code = new_doc.name
                new_doc.job_titless_name = new_doc.name.split("-")[0]
                new_doc.rate = row.employee_pay_rate
                new_doc.set("job_site_table", [])
                new_doc.set("pay_rate", [])

                new_doc.insert(ignore_permissions=True)
                new_doc.item_name = new_doc.name
                new_doc.save(ignore_permissions=True)
                add_job_title_company(
                    parent=staffing_company,
                    job_title=new_doc.name,
                    description=job_title_data[0]["description"],
                    rate=row.employee_pay_rate,
                    industry=industry_type,
                )
                frappe.db.commit()
                check_and_create_pay_rates(
                    new_doc.name,
                    staffing_company,
                    hiring_company,
                    job_site,
                    row.employee_pay_rate,
                    job_order.name,
                )
    except Exception as e:
        frappe.log_error(e, "Get or Create Job Title Job Error")


"""
The function `get_description` retrieves the description of a job title from a database table called
"Multiple Job Titles" based on the given job order and job title.

:param job_order: The `job_order` parameter is the parent document name in the "Multiple Job Titles"
doctype. It is used to identify the specific job order for which you want to retrieve the
description
:param job_title: The `job_title` parameter is the title of the job for which you want to retrieve
the description
:return: The function `get_description` is returning the value of the "description" field from the
"Multiple Job Titles" doctype, based on the given `job_order` and `job_title` parameters. If an
exception occurs during the execution of the function, it will print the exception and traceback and
return an empty string.
"""
@frappe.whitelist()
def get_description(job_order, job_title):
    try:
        return frappe.db.get_value("Multiple Job Titles", {"parent": job_order, "select_job": job_title}, ["description"])
    except Exception as e:
        print(e, frappe.get_traceback())
        return ''

@frappe.whitelist()
def get_total_approved_headcounts(job_order,industry,start_time,select_job):
    try:
        data = frappe.db.sql(f"""select sum(approved_no_of_workers) as total,parent,job_title,industry,start_time from `tabMultiple Job Title Claim` where parent in 
            (select name from `tabClaim Order`  where job_order="{job_order}")
            and job_title='{select_job}' and industry='{industry}' and start_time='{start_time}'""")
        return data[0][0] if data else 0
    except Exception as e:
        print(e)
        print(frappe.get_traceback())

@frappe.whitelist()
def modify_heads_reduce_headcount_hiring(doc_name,job_title,industry,start_time):
    try:
        claim_data = f"""
        SELECT * FROM 
        (SELECT CO.name, CO.staffing_organization,
        MT.job_title, MT.industry, MT.no_of_workers_joborder, MT.no_of_remaining_employee, MT.approved_no_of_workers,
        MT.staff_claims_no, MT.start_time, MT.duration
        FROM `tabClaim Order` AS CO, `tabMultiple Job Titles` AS MJT, `tabMultiple Job Title Claim` AS MT
        WHERE MJT.parent = CO.job_order AND MT.parent = CO.name AND CO.job_order = '{doc_name}'
        AND MT.staff_claims_no > 0
        AND MJT.select_job = MT.job_title AND MJT.job_start_time = MT.start_time
        ORDER BY job_title, start_time, staffing_organization) as CL
        WHERE CL.job_title='{job_title}' AND CL.start_time='{start_time}'
        AND CL.industry='{industry}' AND CL.approved_no_of_workers > 0
        """
        claims = frappe.db.sql(claim_data, as_dict=True)
        return claims
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.db.rollback()

@frappe.whitelist()
def update_jo_direct_db(job, comp):
    """
    This function updates a job's staff_org_claimed field by adding a company to it if it is not already
    present.

    :param job: The variable "job" is likely an object or instance of a class that represents a job or
    task in a system. It is being used as a parameter in the "update_jo" function
    :param comp: It is a variable that represents the company that is being updated in the job object
    """
    try:
        claimed = job.staff_org_claimed if job.staff_org_claimed else ""
        value1 = ""
        if len(claimed) == 0:
            value1 += str(comp)
        elif str(comp) not in claimed:
            value1 += str(claimed) + "~" + str(comp)
        else:
            value1 = claimed
        update_jo_query = f'''update `tabJob Order` set staff_org_claimed="{value1}" where name="{job.name}"'''
        frappe.db.sql(update_jo_query)
        frappe.db.commit()
    except Exception as e:
        print(e, frappe.get_traceback())


@frappe.whitelist(allow_guest=False)
def save_modified_claims_hiring(doc_name, updated_data):
    """
    The function saves modified claims data and sends notifications to relevant users.

    :param updated_data: A JSON string containing the updated data for the claim order
    :param doc_name: The name of the job order document
    :param notes_dict: The notes_dict parameter is a dictionary containing notes related to the updated
    claims. It is used to update the notes field of the claim document
    :return: the integer value 1.
    """
    try:
        updated_data = json.loads(updated_data)
        job = frappe.get_doc(jobOrder, doc_name)
        updated_comps = []
        remaining_emp = [i[0]["new_headcount"] for i in updated_data.values()][0]
        for comp_claim, data in updated_data.items():
            comp_claim = comp_claim.split("~")
            comp = comp_claim[0]
            update_claims2(job, updated_comps, remaining_emp, comp_claim, data)
            update_jo_direct_db(job, comp)
            frappe.db.commit()
        modified_notification(updated_comps, job.company, job.name)
        return 1
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.db.rollback()


@frappe.whitelist(allow_guest=False)
def save_modified_claims_hiring_without_approved(job_order, no_of_workers_updated, key):
    """
    The function saves modified claims data and sends notifications to relevant users.

    :param no_of_workers_updated: Value of updated no of of workers for the claim order
    :param job_order: The name of the job order document
    :param notes_dict: The notes_dict parameter is a dictionary containing notes related to the updated
    claims. It is used to update the notes field of the claim document
    :return: the integer value 1.
    """
    try:
        job_title = key.split("~")[0]
        job_start_time = key.split("~")[1]
        get_all_claim_query = f'''select name from `tabClaim Order` where job_order="{job_order}"'''
        all_claims = frappe.db.sql(get_all_claim_query,as_list=True)
        all_claims_list = [x[0] for x in all_claims]
        total_remaining = int(no_of_workers_updated)
        for each_claim in sorted(all_claims_list):
            claim = frappe.get_doc(claimOrder, each_claim)
            
            for row in claim.multiple_job_titles:
                if (
                row.job_title == job_title
                and str(row.start_time) == job_start_time
                    ):
                    row.no_of_workers_joborder = int(no_of_workers_updated)
                    row.no_of_remaining_employee = total_remaining
                    total_remaining -= int(row.approved_no_of_workers)
                    if row.staff_claims_no > row.no_of_remaining_employee:
                        row.staff_claims_no = row.no_of_remaining_employee
                    claim.save(ignore_permissions=True)
            frappe.db.commit()
        return 1
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.db.rollback()


@frappe.whitelist(allow_guest=False)
def save_modified_claims_hiring_with_emp_assigned(list_array_removed_emps,job_order):
    """
    The function saves modified claims data and sends notifications to relevant users.

    :param no_of_workers_updated: Value of updated no of of workers for the claim order
    :param job_order: The name of the job order document
    :param notes_dict: The notes_dict parameter is a dictionary containing notes related to the updated
    claims. It is used to update the notes field of the claim document
    :return: the integer value 1.
    """
    try:
        list_array_removed_emps = json.loads(list_array_removed_emps)
        notification_helper_data = {}
        title_start_time_data = []
        for each in list_array_removed_emps:
            employee_name = each[0]
            job_title  =  each[3]
            start_time  =  each[4]
            lead_0 = start_time.split(":")
            if lead_0[0][0]=='0' and len(lead_0[0])==2:
                start_time = start_time[1:]
            assign_emp = frappe.db.sql(f''' select aed.parent,ae.company from `tabAssign Employee Details` aed join `tabAssign Employee` ae
            on ae.name=aed.parent
            where aed.employee="{employee_name}" and aed.job_category="{job_title}" 
            and aed.job_start_time="{start_time}" and aed.parent in (select name from `tabAssign Employee` where job_order="{job_order}")''')

            notification_helper_key = f'{job_title}~{assign_emp[0][1]}~{start_time}'
            title_start_time_data_key = f'{job_title}~{start_time}'
            if title_start_time_data_key not in title_start_time_data:
                title_start_time_data.append(title_start_time_data_key)
            
            if notification_helper_data.get(notification_helper_key):
                notification_helper_data[notification_helper_key] += 1
            else:
                notification_helper_data[notification_helper_key] = 1
                
        get_all_claim_query = f'''select name from `tabClaim Order` where job_order="{job_order}"'''
        all_claims = frappe.db.sql(get_all_claim_query,as_list=True)
        all_claims_list = [x[0] for x in all_claims]
        update_claims(title_start_time_data, all_claims_list)
        return "removed"
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.db.rollback()

def update_claims(title_start_time_data, all_claims_list):
    for each_claim in sorted(all_claims_list):
        claim = frappe.get_doc('Claim Order', each_claim)
        for row in claim.multiple_job_titles:
            claim_counts_update(title_start_time_data, claim, row)
        claim.approved_no_of_workers = sum([row.approved_no_of_workers for row in claim.multiple_job_titles])
        claim.staff_claims_no = sum([row.staff_claims_no for row in claim.multiple_job_titles])
        claim.save(ignore_permissions=True)
    frappe.db.commit()

def claim_counts_update(title_start_time_data, claim, row):
    key_title = f'{row.job_title}~{str(row.start_time)[:-3]}'
    if key_title in title_start_time_data:
        updated_required_count = frappe.db.sql(f'''select no_of_workers from `tabMultiple Job Titles` where select_job="{row.job_title}" and job_start_time="{str(row.start_time)}"''')
        row.no_of_workers_joborder = updated_required_count[0][0]
        if row.staff_claims_no>row.no_of_workers_joborder:
            row.staff_claims_no = row.no_of_workers_joborder
        updated_approved_count = frappe.db.sql(f'''select COUNT(name) from `tabAssign Employee Details` where job_category="{row.job_title}" and job_start_time="{str(row.start_time)[:-3]}" and parent in (select name from `tabAssign Employee` where job_order="{claim.job_order}" and company="{claim.staffing_organization}") and remove_employee=0''')
        row.approved_no_of_workers=updated_approved_count[0][0]
        row.no_of_remaining_employee = row.no_of_workers_joborder if row.no_of_workers_joborder<row.no_of_remaining_employee else row.no_of_remaining_employee
    claim.save(ignore_permissions=True)

def update_claims2(job, updated_comps, remaining_emp, comp_claim, data):
    claim = comp_claim[1]
    claim = frappe.get_doc(claimOrder, claim)
    if not job.has_permission("read") or not claim.has_permission("read"):
        frappe.throw(('Insufficient permission for user '+frappe.session.user))
    for update_dict in data:
        for row in claim.multiple_job_titles:
            time = datetime.strptime(str(row.start_time), "%H:%M:%S")
            if (
                row.job_title == update_dict["job_title"]
                and time.strftime("%H:%M") == update_dict["start_time"]
                    ):
                update_comp(updated_comps,row.approved_no_of_workers, update_dict["updated_approved_no"], comp_claim)
                row.approved_no_of_workers = update_dict["updated_approved_no"]
                row.no_of_workers_joborder = update_dict["new_headcount"]
                row.staff_claims_no = update_dict["updated_approved_no"] if update_dict["updated_approved_no"]<row.staff_claims_no else row.staff_claims_no
                row.no_of_remaining_employee = remaining_emp
    remaining_emp -= update_dict["updated_approved_no"]
    claim.approved_no_of_workers = sum([row.approved_no_of_workers for row in claim.multiple_job_titles])
    claim.staff_claims_no = sum([row.staff_claims_no for row in claim.multiple_job_titles])
    claim.save(ignore_permissions=True)
    frappe.db.commit()