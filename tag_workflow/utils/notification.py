import frappe
from frappe import _
from frappe.share import add_docshare as add
from frappe.utils import get_fullname
from frappe.utils.jinja import get_email_from_template, render_template
import boto3
import json


aws_access_key_id = frappe.get_site_config().aws_access_key_id or ""
aws_secret_access_key = frappe.get_site_config().aws_secret_access_key or ""
sender_email_address = frappe.get_site_config().tag_email_sender_address or ""
region_name = frappe.get_site_config().region_name or ""

#------------email and system notification----------#
@frappe.whitelist()
def sendmail(emails, message, subject, doctype, docname,template=None,sender_full_name=None,sender=None):
    try:
        if isinstance(emails, str):
            emails=json.loads(emails)
        if not template:
            template = "email_template_custom"

        site= frappe.utils.get_url().split('/')
        sitename=site[0]+'//'+site[2]

        args = dict(sitename=sitename,content=message,subject=subject)
        ses_email_send(emails=emails, subject=subject, args=args,template=template,sender_full_name=sender_full_name,sender=sender)

        # frappe.sendmail(emails, subject=subject, delayed=False, reference_doctype=doctype, reference_name=docname, message=message, template="email_template_custom", args = dict(sitename=sitename,content=message,subject=subject),now=True)
    except Exception as e:
        print(e,doctype,docname)
        frappe.log_error(e, "Frappe Mail")

def ses_email_send(emails, subject, args, template="email_template_custom",sender_full_name=None,sender=None):
    if not emails: return
    if not args.get('sitename',None):
        site= frappe.utils.get_url().split('/')
        sitename=site[0]+'//'+site[2]
        args['sitename']=sitename
    if type(emails) is not list:
        emails = [emails]
    try:
        if frappe.db.get_value("User", frappe.session.user, "tag_user_type") == 'TAG Admin':
            sender_full_name = 'TAG Admin'
        if not sender_full_name:
            sender_full_name  = get_fullname(frappe.session.user)
            print(sender)
        message, _ = get_email_from_template(template,args)
        rec = emails
        while len(rec) > 48:
            try:
                send_batch_email_ses(subject, sender_full_name, rec[:48], message, sender_email_address)
            except Exception as e:
                print(e)
                print(frappe.get_traceback())
            finally:
                rec = rec[48:]
        if rec:
            try:
                send_batch_email_ses(subject, sender_full_name, rec, message, sender_email_address)
            except Exception as e:
                print(e)
                print(frappe.get_traceback())
        return
    except Exception:
        pass

def send_batch_email_ses(subject, sender_full_name, rec, message, sender_email_address):
    ses = boto3.client('ses', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=region_name)
    ses.send_email(
                        Source=f'\"{sender_full_name}\" {sender_email_address}',
                        Destination={
                            'BccAddresses': rec,
                        },
                        Message={
                            'Subject': {
                                'Data': subject,
                                'Charset': 'utf-8'
                            },
                            'Body': {
                                'Html': {
                                    'Data': message,
                                    'Charset': 'utf-8'
                                }
                            }
                        }
                    )
@frappe.whitelist()
def make_system_notification(users, message, doctype, docname,subject=None):
    try:
        if isinstance(users, str):
            users=json.loads(users)
        if subject and users:
            for user in users:
                notification = frappe.get_doc(dict(doctype="Notification Log", document_type=doctype, document_name=docname, subject=message, for_user=user, from_user=frappe.session.user,type="Alert"))
                notification.save(ignore_permissions=True)
    except Exception:
        pass

def share_doc(doctype, docname, user):
    try:
        add(doctype, docname, user=user, read=1, write=1, submit=1, notify=0, flags={"ignore_share_permission": 1})
    except Exception as e:
        frappe.log_error(e, "Share")

@frappe.whitelist()
def get_mail_list(user_list,app_field,mail_field):
    if user_list:
        if len(user_list)>1:
            user_list_app = frappe.db.sql(f'''select name from `tabUser` where name in {tuple(user_list)} and {app_field}="1" ''', as_list=1)
            user_list_mail = frappe.db.sql(f'''select name from `tabUser` where name in {tuple(user_list)} and {mail_field}="1" ''', as_list=1)
        else:
            user_list_app = frappe.db.sql(f'''select name from `tabUser` where name="{user_list[0]}" and {app_field}="1" ''', as_list=1)
            user_list_mail = frappe.db.sql(f'''select name from `tabUser` where name="{user_list[0]}" and {mail_field}="1" ''', as_list=1)
        user_list_app = [user[0] for user in user_list_app]
        user_list_mail = [user[0] for user in user_list_mail]
        return user_list_app,user_list_mail
    else:
        return [],[]
