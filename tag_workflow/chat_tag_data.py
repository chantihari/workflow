from email import message
from webbrowser import get
import frappe
from frappe import _, msgprint
from frappe.share import add_docshare as add
from tag_workflow.utils.notification import get_mail_list, make_system_notification
from tag_workflow.utils.notification import ses_email_send

@frappe.whitelist()
def email_notification(doc,method):
    user = frappe.session.user
    if user == 'Administrator':
        return
    subject="New Message"
    chat_message="Chat Message"

    staffing = frappe.db.sql('''select tag_user_type,company from `tabUser` where name  = "{}" '''.format(user),as_dict=True)
    if staffing[0]['tag_user_type'] == 'Staffing Admin' or staffing[0]['tag_user_type'] == 'Staffing User' or staffing[0]['tag_user_type'] == 'Administrator':
        try:

            chat_room = frappe.db.sql('''select room_name from `tabChat Room` where name = "{}"'''.format(doc.room),as_list = True)
            job=chat_room[0][0].split('_')
            hiring_org = frappe.db.sql(''' select company from `tabJob Order` where name = "{}"'''.format(job[0]),as_dict=True)
            hiring_member = frappe.db.sql(''' select name from `tabUser` where company = "{}"'''.format(hiring_org[0]['company']),as_list=1)
            hiring_list = [name[0] for name in hiring_member]
            job_order = frappe.db.sql(''' select  name,from_date,job_site from `tabJob Order` where name="{0}" '''.format(job[0]),as_dict=True)

            message = f"New message from {job[1]} for {job_order[0]['name']} work order on {job_order[0]['from_date']} at {job_order[0]['job_site']}."
            hiring_list_app, hiring_list_mail = get_mail_list(hiring_list,app_field='msg_from_staff_app',mail_field='msg_from_staff_mail')
            make_system_notification(hiring_list_app,message=message,doctype=chat_message,docname=doc.name,subject=subject)
            # frappe.sendmail(hiring_list,subject=subject,reference_doctype=chat_message,reference_name=doc.name,message=message,delayed=False, template="email_template_custom", args = dict(content=message,subject=subject))
            args = dict(content=message,subject=subject)
            template = "email_template_custom"
            ses_email_send(emails=hiring_list_mail,subject=subject,args=args,template=template)
        except Exception:
            print('Staffing part is not running')
    elif staffing[0]['tag_user_type'] == 'Hiring Admin' or staffing[0]['tag_user_type'] == 'Hirig User' or staffing[0]['tag_user_type'] == 'Administrator' :

        try:

            chat_room = frappe.db.sql('''select room_name from `tabChat Room` where name = "{}"'''.format(doc.room),as_list = True)
            job=chat_room[0][0].split('_')
            staffing_member = frappe.db.sql(''' select name from `tabUser` where company = "{}"'''.format(job[1]),as_list=1)
            staffing_list = [name[0] for name in staffing_member]
            message=f"New Message regarding {job[0]} from {staffing[0]['company']} is available."
            staffing_list_app, staffing_list_mail = get_mail_list(staffing_list,app_field='msg_frm_hire_app',mail_field='msg_frm_hire_mail')
            make_system_notification(staffing_list_app,message=message,doctype=chat_message,docname=doc.name,subject=subject)
            # frappe.sendmail(staffing_list,subject=subject,reference_doctype=chat_message,reference_name=doc.name,message=message,delayed=False, template="email_template_custom", args = dict(content=message,subject=subject))
            args = dict(content=message,subject=subject)
            template = "email_template_custom"
            ses_email_send(emails=staffing_list_mail,subject=subject,args=args,template=template)
        except Exception:
            print('hiring part is not running')


@frappe.whitelist()
def job_order_name(username,company_type,company_name):
    company_list = set()
    company_user_list = list()
    if company_type == 'Hiring':
        try:
            get_claim_jb_order = frappe.db.sql('select name from `tabJob Order` where bid > 0 and (order_status="Ongoing" or order_status="Upcoming") and company = "{}"'.format(company_name),as_list=1)
            for claim in get_claim_jb_order:
                value = claim[0].split(',')
                for name in value:
                    if name:
                        company_list.add(name.strip())
                        company_user_list.append(name.strip())

            l=[]
            for i in company_user_list:
                get_claimed_comp = frappe.db.sql('''select claim from `tabJob Order` where name='{0}' '''.format(i),as_list=1)
                value = get_claimed_comp[0][0].split('~')
                for j in value:
                    l.append(i+"_"+j)

            return '\n'.join(l)
        except Exception as e:
            print(e)
            return []

    elif company_type == 'Staffing':
        try:
            job_details=frappe.db.sql(''' select job_order from `tabAssign Employee` where company='{0}' '''.format(company_name),as_list=1)
            for claim in job_details:
                value = claim[0].split(',')
                for name in value:
                    if name:
                        company_user_list.append(name.strip())


            l=[]
            for i in company_user_list:
                if(i+"_"+company_name) not in l:
                    l.append(i+"_"+company_name)


            return '\n'.join(l)

        except Exception as e:
            print(e)
            return []
    elif company_type=='Exclusive Hiring':
        try:
            get_claim_jb_order = frappe.db.sql('select name from `tabJob Order` where bid > 0 and (order_status="Ongoing" or order_status="Upcoming") and company = "{}"'.format(company_name),as_list=1)
            for claim in get_claim_jb_order:
                value = claim[0].split(',')
                for name in value:
                    if name:
                        company_user_list.append(name.strip())

            l=[]
            for i in company_user_list:
                if(i+"_"+company_name) not in l:
                    l.append(i+"_"+company_name)


            return '\n'.join(l)
        except Exception as e:
            print(e)
            return []
