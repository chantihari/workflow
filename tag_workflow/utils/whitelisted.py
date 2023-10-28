import re
import frappe
from frappe.utils import add_years, getdate
from frappe import DoesNotExistError
from json import loads
from frappe.desk.form.load import get_docinfo, run_onload, set_link_titles
import requests, json
from frappe import _, _dict
from frappe.model.utils import is_virtual_doctype
from frappe import _, throw, is_whitelisted
from frappe.utils import cint, flt, getdate, nowdate
from frappe.model.mapper import get_mapped_doc
from erpnext.selling.doctype.quotation.quotation import _make_customer
from tag_workflow.utils.doctype_method import checkingjobtitle_name
from tag_workflow.utils.notification import make_system_notification, share_doc
from frappe.desk.query_report import get_report_doc, generate_report_result,get_prepared_report_result
from frappe.desk.desktop import Workspace
from frappe import enqueue
from frappe.desk.form.save import set_local_name, send_updated_docs
from six import string_types
from mimetypes import guess_type
from frappe.utils import cint
from uuid import uuid4
from frappe.utils.image import optimize_image
from frappe.core.doctype.user.user import User,test_password_strength,handle_password_test_fail
from chat.utils import update_room, is_user_allowed_in_room, raise_not_authorized_error
from .notification import ses_email_send
from frappe.model.db_query import check_parent_permission
from frappe.utils import get_safe_filters
from frappe.client import get_list
from reportlab.pdfgen import canvas
import pdfkit
from io import BytesIO
from PyPDF2 import PdfReader, PdfWriter
from frappe.utils import scrub_urls
from pytz import timezone
from frappe.utils.pdf import prepare_options, get_wkhtmltopdf_version, LooseVersion, PDF_CONTENT_ERRORS, cleanup, get_file_data_from_writer

ALLOWED_MIMETYPES = (
	"image/png",
	"image/jpeg",
	"application/pdf",
	"application/msword",
	"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
	"application/vnd.ms-excel",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
	"application/vnd.oasis.opendocument.text",
	"application/vnd.oasis.opendocument.spreadsheet",
	"text/plain",
)

ALLOWED_FILE_EXTENSIONS = (
    "png",
    "jpeg",
    "jpg",
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "odt",
    "ods",
    "txt",
    "csv"
)


EVENT = 'refresh_data'
#-------global var------#
item = "Timesheet Activity Cost"
order = "Sales Order"
payment = "Payment Schedule"
taxes= "Sales Taxes and Charges"
team = "Sales Team"
JO = "Job Order"
url_link="https://api.resumatorapi.com/v1/applicants/"
apikey="?apikey="
tag_gmap_key = frappe.get_site_config().tag_gmap_key or ""
exclusive_hiring="Exclusive Hiring"
no_perm='Insufficient Permission for User'
hiring_user = "Hiring User"
Invalid_Action = "Invalid action."
#-----------------------------------#
def set_missing_values(source, target, customer=None, ignore_permissions=True):
    if customer:
        target.customer = customer.name
        target.customer_name = customer.customer_name
    target.ignore_pricing_rule = 1
    target.flags.ignore_permissions = ignore_permissions
    target.run_method("set_missing_values")
    target.run_method("calculate_taxes_and_totals")

def update_item(obj, target, source_parent):
    target.stock_qty = flt(obj.qty) * flt(obj.conversion_factor)

#----------- sales order -----------#
@frappe.whitelist()
def make_sales_order(source_name, target_doc=None):
    quotation = frappe.db.get_value("Quotation", source_name, ["transaction_date", "valid_till"], as_dict = 1)
    if quotation.valid_till and (quotation.valid_till < quotation.transaction_date or quotation.valid_till < getdate(nowdate())):
        frappe.throw(_("Validity period of this quotation has ended."))
    return _make_sales_order(source_name, target_doc)


def _make_sales_order(source_name, target_doc=None, ignore_permissions=True):
    customer = _make_customer(source_name, ignore_permissions)
    
    doclist = get_mapped_doc("Quotation", source_name, {
        "Quotation": {"doctype": order, "validation": {"docstatus": ["=", 1]}},
        "Quotation Item": {"doctype": "Sales Order Item", "field_map": {"rate": "rate", "amount": "amount", "parent": "prevdoc_docname", "name": "quotation_item_detail",},"postprocess": update_item},
        taxes: {"doctype": taxes, "add_if_empty": True},
        team: {"doctype": team, "add_if_empty": True},
        payment: {"doctype": payment, "add_if_empty": True}
    }, target_doc, set_missing_values, ignore_permissions=ignore_permissions)
    set_missing_values(source_name, doclist, customer=customer, ignore_permissions=ignore_permissions)
    return doclist

#--------- sales invoice -----------#
@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):
    return _make_sales_invoice(source_name, target_doc)

def _make_sales_invoice(source_name, target_doc=None, ignore_permissions=True):
    def customer_doc(source_name):
        customer = frappe.db.get_value(order, source_name, "customer")
        return frappe.get_doc("Customer", customer)

    def update_timesheet(doclist):
        total_amount = 0
        total_hours = 0
        job_order = frappe.db.get_value(order, source_name, "job_order")
        timesheet = frappe.db.get_list("Timesheet", {"job_order_detail": job_order, "docstatus": 1}, ["name"])
        
        for time in timesheet:
            sheet = frappe.get_doc("Timesheet", {"name": time.name})
            total_amount += sheet.total_billable_amount
            total_hours += sheet.total_billable_hours

            for logs in sheet.time_logs:
                activity = {"activity_type": logs.activity_type, "billing_amount": logs.billing_amount, "billing_hours": logs.billing_hours, "time_sheet": logs.parent, "from_time": logs.from_time, "to_time": logs.to_time, "description": sheet.employee}
                doclist.append("timesheets", activity)

        doclist.total_billing_amount = total_amount
        doclist.total_billing_hours = total_hours
        timesheet_item = {"item_code": item, "item_name": item, "description": item, "uom": "Nos", "qty": 1, "stock_uom": 1, "conversion_factor": 1, "stock_qty": 1, "rate": total_amount, "amount": total_amount}
        doclist.append("items", timesheet_item)

    def make_invoice(source_name, target_doc):
        return get_mapped_doc(order, source_name, {
            order: {"doctype": "Sales Invoice", "validation": {"docstatus": ["=", 1]}},
            "Sales Order Item": {"doctype": "Sales Invoice Item", "field_map": {"rate": "rate", "amount": "amount", "parent": "sales_order", "name": "so_detail",}, "postprocess": update_item},
            taxes: {"doctype": taxes, "add_if_empty": True},
            team: {"doctype": team, "add_if_empty": True},
            payment: {"doctype": payment,"add_if_empty": True}
        }, target_doc, set_missing_values, ignore_permissions=ignore_permissions)

    customer = customer_doc(source_name)
    doclist = make_invoice(source_name, target_doc)
    update_timesheet(doclist)
    set_missing_values(source_name, doclist, customer=customer, ignore_permissions=ignore_permissions)
    return doclist


#------------JazzHR-----------#
def preparing_employee_data(data, company):
    try:
        is_emp,is_exists,total = 0,0,0
        total = len(data)
        for i in data:
            name=i['id']
            sql_data=f'SELECT EXISTS(SELECT * from `tabEmployee` WHERE employee_number="{name}");'
            sql=frappe.db.sql(sql_data,as_list=1)
            if(sql[0][0]==0):
                data=frappe.db.sql('''select name from `tabEmployee` order by name desc limit 1''',as_list=1)
                last_series_name=data[0][0]
                name=str(last_series_name).split('-')
                series_number=name[0:-1]
                series_last_no=name[-1]
                new_series_number=str(int(series_last_no)+1).rjust(len(series_last_no), '0')
                series_name_data = '-'.join(series_number)
                new_series=series_name_data+'-'+str(new_series_number)
                b_id=i['id'].strip('"')
                first_name=i['first_name'].strip('"')
                last_name=i['last_name'].strip('"')
                is_emp += 1
                my_db=f'''insert into `tabEmployee` (name,employee_number,employee_name,first_name,last_name,company,contact_number) values("{new_series}","{b_id}","{first_name} {last_name}","{first_name}","{last_name}","{company}","{i['prospect_phone']}");'''
                frappe.db.sql(my_db)
                frappe.db.commit()
            else:
                is_exists += 1
        return "Total <b>"+str(total)+"</b> records found, out of these newly created recored are <b>"+str(is_emp)+"</b> and <b>"+str(is_exists)+"</b> already exists."
    except Exception as e:
        frappe.throw(e)
 
@frappe.whitelist()
def make_jazzhr_request(api_key, company):
    try:
        url = "https://api.resumatorapi.com/v1/applicants?apikey="+api_key
        response = requests.get(url)
        if(response.status_code == 200 and len(response.json()) > 0 and len(response.json()) == 100):
            data = response.json()
            enqueue("tag_workflow.utils.whitelisted.fetching_data", data=data, response=response, api_key=api_key, company=company)
            frappe.msgprint('Employees Added successfully')
        else:
            error = json.loads(response.text)['error']
            frappe.throw(_("{0}").format(error))
    except Exception as e:
        frappe.msgprint('Some Error Occur . Please Try Again')
        frappe.error_log(e, "JazzHR")
        frappe.throw(e)


#--------get user data--------#
@frappe.whitelist()
def get_user_company_data():
    try:
        print("*************************' Company data loading started... '************************************")
        all_user = frappe.db.sql("select name,company from `tabUser` where tag_user_type IN ('Staffing Admin','Hiring Admin')")
        for each in all_user:
            company = each[1]
            user = each[0]
            if company and user:
                data = [company]
                user_doc = frappe.get_doc("User",user)
                company_exists=frappe.db.get_value('Companies Assigned',{'assign_multiple_company':company , 'parent':user})
                if not company_exists:
                    user_doc.append("assign_multiple_company",{"assign_multiple_company":company})
                    user_doc.save()
                a = frappe.db.get_list("Employee", {"user_id": user, "company": ('not in', (company))}, "company")
                for i in a:
                    company_exists=frappe.db.get_value('Companies Assigned',{'assign_multiple_company':i.company , 'parent':user},'name')
                    if not company_exists:
                        user_doc.append("assign_multiple_company",{"assign_multiple_company":i.company})
                        user_doc.save()
                        data.append(i.company)

        print("*************************' Company data loading completed successfully... '************************************")
    except Exception as e:
        print(e)

import ast
import json
#--------hiring orgs data----#
@frappe.whitelist(allow_guest=True)
def get_orgs(company,employee_lis):
    try:

        try:
            employee_lis = json.loads(employee_lis)
        except Exception as e:
            vendor_ids = json.dumps(employee_lis)
            employee_lis = ast.literal_eval(vendor_ids)
        sql = """ select hiring_organization from `tabAssign Employee` where company = '{0}' """.format(company)
        data=frappe.db.sql(sql, as_list=1)
        my_data=[]
        for i in data:
            if i not in my_data:
                my_data.append(i)
        res = []
        for index,value in enumerate(my_data):
            if value[0] not in employee_lis:
                res.append(value)
        return res
    except Exception as e:
        print(e)





#-------get company users----#
@frappe.whitelist(allow_guest=True)
def get_user(company):
    user = ""
    try:
        sql = """select name from `tabUser` where company = "{0}" and enabled = 1 """.format(company)
        users = frappe.db.sql(sql, as_dict=1)
        for u in users:
            user += "\n"+str(u.name)

        return user
    except Exception as e:
        print(e)
        return user

#-----------request signature----------------#
@frappe.whitelist()
def request_signature(staff_user, staff_company, hiring_user, name):
    try:
        site= frappe.get_site_config().env_url
        link = f'<a href="{site}/app/contract/{name}">Click Here For Signature</a>'
        msg=f"{staff_user} from {staff_company} is requesting an electronic signature for your contract agreement."
        subject = "Signature Request"
        make_system_notification([hiring_user], msg, 'Contract', name, subject)
        send_queued_mails(user=hiring_user,subject=subject, reference_name=name, args = dict(sitename=site, subject=subject, staff_user=staff_user, staff_company=staff_company, link = link))
        share_doc("Contract", name, hiring_user)
    except Exception as e:
        print(e)


@frappe.whitelist()
def send_queued_mails(user,subject, reference_name, args):
    user_doc=frappe.get_doc('User',user)
    user_doc.send_welcome_mail_to_user()
    # frappe.sendmail(user, subject=subject, delayed=False, reference_doctype='Contract', reference_name=reference_name, template="digital_signature", args = args)
    template="digital_signature"
    ses_email_send(emails=user,subject=subject,template=template,args=args)
#-------update lead--------#
@frappe.whitelist(allow_guest=True)
def update_lead(lead, staff_company, date, staff_user, name,hiring_signee,hiring_sign_date):
    try:
        frappe.db.set_value("Lead", lead, "status", 'Close')
        frappe.db.set_value("Contract", name, "signe_hiring", hiring_signee)
        frappe.db.set_value("Contract", name, "sign_date_hiring", hiring_sign_date)
        frappe.db.set_value("Contract", name, "docstatus", 1)

        date = date.split('-')
        new_date = date[1]+'-'+date[2]+'-'+date[0]
        message = f"Congratulations! A Hiring contract has been signed on <b>{new_date}</b> for <b>{staff_company}</b>."
        make_system_notification([staff_user], message, 'Contract', name, "Hiring Prospect signs a contract")
        site= frappe.utils.get_url().split('/')
        sitename=site[0]+'//'+site[2]
        # frappe.sendmail([staff_user], subject="Hiring Prospect signs a contract", delayed=False, reference_doctype='Contract', reference_name=name, template="digital_signature", args = dict(sitename=sitename, subject="Signature Request", staff_user=staff_user, staff_company=staff_company, date=date))
        subject="Hiring Prospect signs a contract"
        template="digital_signature"
        args = dict(sitename=sitename, subject="Signature Request", staff_user=staff_user, staff_company=staff_company, date=date)
        ses_email_send(emails=[staff_user],subject=subject,template=template,args=args)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "update_lead")
        print(e)

#-------company list-------#
@frappe.whitelist(allow_guest=True)
def get_company_list(company_type):
    try:
        data = []
        sql = """ select name from `tabCompany` where make_organization_inactive = 0 and organization_type = '{0}' """.format(company_type)
        companies = frappe.db.sql(sql, as_dict=1)
        data = [c['name'] for c in companies]
        return "\n".join(data)
    except Exception as e:
        print(e)
        return []

#-------check timesheet-----#
@frappe.whitelist()
def check_timesheet(job_order):
    try:
        is_value = True
        if(frappe.db.exists("Timesheet", {"job_order_detail": job_order, "docstatus": 0})):
            frappe.msgprint(_("All timesheets needs to be approved for this job order"))
            is_value = False
        return is_value
    except Exception as e:
        print(e)
        return is_value


@frappe.whitelist()
def get_staffing_company_list():
    try:
        data = []
        sql = """ select name from `tabCompany` where organization_type = 'Staffing' """
        companies = frappe.db.sql(sql, as_dict=1)
        data = [c['name'] for c in companies]
        return "\n".join(data)
    except Exception as e:
        print(e)
        return []



#----------------report issue----------------#
@frappe.whitelist()
@frappe.read_only()
def run(report_name, filters=None, user=None, ignore_prepared_report=False, custom_columns=None):
    if not user:
        user = frappe.session.user
    elif user!=frappe.session.user:
        frappe.throw('Insufficient Permission for User ' + user)
    detail_filters = json.loads(filters)
    if filters!='{}' and detail_filters.get('company'):
            company_doc=frappe.get_doc('Company',detail_filters['company'])
            if not company_doc.has_permission("read"):
                frappe.throw('Insufficient Permission for Company ' + detail_filters['company'])

    report = get_report_doc(report_name)

    if not frappe.has_permission(report.ref_doctype, "report"):
        frappe.msgprint(_("Must have report permission to access this report."), raise_exception=True,)
        return None

    result = None
    if(report.prepared_report and not report.disable_prepared_report and not ignore_prepared_report and not custom_columns):
        if filters and isinstance(filters, string_types):
                filters = json.loads(filters)
                dn = filters.get("prepared_report_name")
                filters.pop("prepared_report_name", None)
        else:
            dn = ""
        result = get_prepared_report_result(report, filters, dn, user)
    else:
        result = generate_report_result(report, filters, user, custom_columns)

    result["add_total_row"] = report.add_total_row and not result.get("skip_total_row", False)

    return result

#--------------------------#
@frappe.whitelist()
def get_order_data():
    try:
        company, company_type = frappe.db.get_value("User", {"name": frappe.session.user}, ["company", "organization_type"])
        result = []
        if not company or not company_type:
            return result

        return get_company_order(company_type, company, result)
    except Exception as e:
        frappe.msgprint(e)

def get_company_order(company_type, company, result):
    if(company_type == "Staffing"):
        job_list = set()
        claim  = frappe.db.sql(''' select job_order from `tabClaim Order` where staffing_organization = "{}" and approved_no_of_workers != 0 order by creation desc'''.format(company),as_list = 1)
        for i in claim:
            job_list.add(i[0])
        assign = frappe.db.sql(''' select job_order from `tabAssign Employee` where company = "{}" and tag_status = "Approved"'''.format(company),as_list = 1)
        for i in assign:
            job_list.add(i[0])

        sqlj  = f'select name from `tabJob Order`  where "{frappe.utils.nowdate()}"  between from_date and to_date order by creation desc'
        job_order = frappe.db.sql(sqlj,as_list=1)
        for j in job_order:
            if((j[0] in job_list) and len(result) <= 5):
                date,time, job_site, company, per_hour, select_job = frappe.db.get_value(JO, {"name": j[0]}, ["from_date","job_start_time","job_site", "company", "per_hour", "select_job"])
                result.append({"name": j, "date": (str(date.strftime("%d %b, %Y "))+ ' '+str(converttime(time))), "job_site": job_site, "company": company, "per_hour": per_hour, "select_job": select_job})
        return result

    elif(company_type in ["Hiring", exclusive_hiring]):
        order1 = f'''select jo.name,jo.from_date,mult.job_start_time,jo.job_site,jo.company,jo.per_hour,jo.order_status,mult.select_job,jo.total_workers_filled,jo.total_no_of_workers 
            from `tabJob Order` jo left join `tabMultiple Job Titles` mult on mult.parent = jo.name where 
            jo.company = "{company}" and "{frappe.utils.nowdate()}" between jo.from_date and jo.to_date 
            and (jo.cancellation_date IS NULL OR (jo.cancellation_date IS NOT NULL AND jo.cancellation_date >= '{frappe.utils.nowdate()}'))
            group by jo.name order by jo.creation desc limit 5'''
        order = frappe.db.sql(order1,as_dict=1)
        for o in order:
            result.append({"name":o['name'], "date":(str(o['from_date'].strftime("%d %b, %Y "))),"job_site": o['job_site'], "company": o['company'], "per_hour": o['per_hour'], "select_job": o['select_job'],"total_workers_filled":o['total_workers_filled'],"total_no_of_workers":o['total_no_of_workers']})
        return result

@frappe.whitelist()
@frappe.read_only()
def get_desktop_page(page):
    json_data=json.loads(page)
    if '<' in json_data['title'] or '>' in json_data['title'] or '%' in json_data['title']:
        frappe.throw('Invalid Request')
    
    try:
        workspace = Workspace(loads(page))
        workspace.build_workspace()
        return {
			"charts": workspace.charts,
			"shortcuts": workspace.shortcuts,
			"cards": workspace.cards,
			"onboardings": workspace.onboardings,
			"quick_lists": workspace.quick_lists,
            "get_order_data": get_order_data()
		}
    except DoesNotExistError:
        frappe.log_error("Workspace Missing")
        return {}

def check_user_type(user):
    get_user_type = frappe.db.sql("select tag_user_type,owner from `tabUser`  WHERE name='{0}'".format(user),as_dict=1)
    if get_user_type[0]['tag_user_type'] == hiring_user:
        return get_user_type[0]['owner']
    return user
#----------------------#
@frappe.whitelist()
def search_staffing_by_hiring(data=None,search_choice_val='company_name'):
    try:
        if(data):
            key_val = {'company_name':'name','industry':'industry_type','city':'city'}
            key = key_val[search_choice_val]
            user_name = check_user_type(frappe.session.user)
            sql = ''' select company from `tabUser` where email='{}' '''.format(user_name)
            user_comp = frappe.db.sql(sql, as_list=1)
            if search_choice_val=="company_name":
                sql = """select distinct p.name from `tabCompany` p inner join `tabIndustry Types` c where p.name = c.parent and organization_type = "Staffing" and (p.name like '%{0}%') and c.industry_type in (select industry_type from `tabIndustry Types` where parent='{1}')""".format(data,user_comp[0][0])
            elif search_choice_val=="industry":
                sql  = """ select distinct(industry_type) from `tabJob Titles` where parent in (select assign_multiple_company from `tabCompanies Assigned` where parent="{0}") and industry_type like '%{1}%'""".format(user_name,data)
            elif search_choice_val=="city":
                sql = """select distinct p.city from `tabCompany` p inner join `tabIndustry Types` c where p.name = c.parent and organization_type = "Staffing" and (p.city like '%{0}%') and c.industry_type in (select industry_type from `tabIndustry Types` where parent='{1}')""".format(data,user_comp[0][0])
            data = frappe.db.sql(sql, as_dict=1)
            exc_par = frappe.db.get_value("Company", {"name": user_comp[0][0]}, "parent_staffing")
            if(exc_par):
                data1=[]
                data1.append({"name": exc_par})
                frappe.publish_realtime(event=EVENT,user=frappe.session.user)
                return [d[key] for d in data1]
            frappe.publish_realtime(event=EVENT,user=frappe.session.user)
            return [d[key] for d in data]
        return []
    except Exception as e:
        print(e)
        return []



@frappe.whitelist()
def validated_primarykey(company):
    try:
        sql = """  select * from  `tabContact` where company = "{0}" AND is_primary=1 """.format(company)
        return frappe.db.sql(sql)
    except Exception as e:
        print(e)
        
from datetime import datetime
def converttime(s):
    try:
        return  datetime.strptime(str(s), '%H:%M:%S.%f').strftime('%I:%M %p')
    except Exception:
        return  datetime.strptime(str(s), '%H:%M:%S').strftime('%I:%M %p')

 
def fetching_data(data,response,api_key,company):
    try:
        count = 1
        while(len(response.json()) == 100):
            url="https://api.resumatorapi.com/v1/applicants/page/"+str(count)+apikey+api_key
            response = requests.get(url)
            count += 1
            data.extend(response.json())
        emp_data(api_key, data, company)
    except Exception as e:
        frappe.msgprint('Error Occured')
        frappe.error_log(e, "JazzHR")
        frappe.throw(e)
 
def emp_data(api_key, data, company):
    try:
        for d in data:
            try:
                if not frappe.db.exists("Employee", {"employee_number": d['id'], "company": company}):
                    url = url_link+ d['id'] + apikey + api_key
                    response = requests.get(url)
                    emp_response_data(response, company)
            except Exception as e:
                frappe.msgprint('Some Error Occured while storing data. Please try again')
                frappe.error_log(e, "JazzHR")
                frappe.throw(e)
    except Exception as e:
        frappe.msgprint('Some Error Occured. Please try again')
        frappe.error_log(e, "JazzHR")
        frappe.throw(e)

def emp_response_data(response, company):
    try:
        if(response.status_code == 200 and len(response.json())>0):
            state, city = "", ""
            zip_code = 0
            data=response.json()
            emp = frappe.new_doc("Employee")
            emp.employee_number = data['id'].strip('"')
            emp.first_name = data['first_name'].strip('"')
            emp.last_name = data['last_name'].strip('"')
            emp.company = company
            emp.contact_number = data['phone'] or ""
            emp.employee_gender = data['eeo_gender'] if data['eeo_gender'] in ["Male", "Female", "Decline to answer"] else ''
            emp.military_veteran = 1 if data['eeoc_veteran'] == 'I AM A PROTECTED VETERAN' else 0
            emp.street_address = data['address'] if data['address'] != 'Unavailable' and data['address'] != '' else ''
            emp.email = data['email'] or ""
            state, city, zip_code = emp_city_state(data)
            emp.city = city
            emp.state = state
            emp.zip_code = zip_code
            emp.save(ignore_permissions=True)
    except Exception as e:
        frappe.msgprint('Some Error Occured')
        frappe.error_log(e, "JazzHR")
        frappe.throw(e)

def emp_city_state(data):
    try:
        if((data['location']) != '(No City Provided) (No State Provided) (No Postal Code Provided)' and data['location']):
            address_data="https://maps.googleapis.com/maps/api/geocode/json?key="+tag_gmap_key+"&address="+data['location']
            state, city, zip_code = '', '', 0
            try:
                response = requests.get(address_data)
            except Exception as e:
                print(e)
                return state, city, zip_code
            if(response.status_code == 200 and len(response.json())>0 and len(response.json()['results'])>0):
                address_dt = response.json()
                state, city, zip_code = emp_zip_city(address_dt)
            return state, city, zip_code
        else:
            return '', '', 0
    except Exception as e:
        frappe.msgprint('Some Error Occured while fetching address')
        frappe.error_log(e, "JazzHR")
        print(e)
        return '', '', 0
           
def emp_zip_city(address_dt):
    try:
        state, city, zip_code = '', '', 0
        state_data = address_dt['results'][0]['address_components']
        for i in state_data:
            if 'administrative_area_level_1' in i['types']:
                state = i['long_name'] if i['long_name'] else ''
            elif 'postal_code' in i['types']:
                zip_code = i['long_name'] if i['long_name'].isdigit() else 0

        city_zip = address_dt['results'][0]['formatted_address'].split(',')
        city = city_zip[-3].strip() if len(city_zip)>2 and city_zip[-3].strip() else ''
        return state,city,zip_code
    except Exception as e:
        frappe.msgprint('Some Error Occured while fetching address')
        frappe.error_log(e, "JazzHR")
        print(e)
        return '', '', 0

@frappe.whitelist()
def update_employees_data_jazz_hr(api_key,company):
    try:
        enqueue(emp_data_update(api_key,company))
        frappe.msgprint('Employee Data Updated Successfully')
        return True

    except Exception as e:
        frappe.msgprint('Error Occured')
        frappe.error_log(e, "JazzHR")
        frappe.throw(e)
def emp_data_update(api_key,company):
    try:
        emp_list=frappe.db.sql('select employee_number from `tabEmployee` where employee_number is NOT NULL and company="{0}" and updated_once!=1'.format(company),as_list=1)
        if(len(emp_list)>0):
            for i in emp_list:
                try:
                    name=i[0]
                    sql_data=f'SELECT EXISTS(SELECT * from `tabEmployee` WHERE employee_number="{name}");'
                    sql=frappe.db.sql(sql_data,as_list=1)
                    if(sql[0][0]==1):
                        employee_doc=f'select name from `tabEmployee` where employee_number="{name}"'
                        emp_doc=frappe.db.sql(employee_doc,as_list=1)
                        emp_number=emp_doc[0][0]
                        url = url_link+name+apikey+api_key
                        response = requests.get(url)
                        if(response.status_code == 200 and len(response.json())>0):
                            data=response.json()
                            doc_emp=frappe.get_doc('Employee',emp_number)
                            updates_value(emp_number,data,doc_emp)
                except Exception as e:
                    frappe.msgprint('Some Error Occured while data updating ')
                    frappe.error_log(e, "JazzHR")
                    frappe.throw(e)
    except Exception as e:
        frappe.msgprint('Some Error Occur')

        make_system_notification([frappe.session.user], "Updation Is not Successful", 'Company', company, 'Updation Error')
        frappe.error_log(e, "JazzHR")
        frappe.throw(e)
@frappe.whitelist()
def update_single_employee(employee_id,name,comp_name,updated_once):
    try:
        if(updated_once!='1'):
            api_key=frappe.get_doc('Company',comp_name)
            url = url_link+employee_id+apikey+api_key.jazzhr_api_key
            response = requests.get(url)
            if(response.status_code == 200 and len(response.json())>0):
                data=response.json()
                doc_emp=frappe.get_doc('Employee',name)
                updates_value(name,data,doc_emp)
            return True
        else:
            frappe.msgprint('Employee Data Already Update')

    except Exception as e:
        frappe.msgprint('Some Error Occur')
        make_system_notification([frappe.session.user], "Updation Is not Successful", 'Company', comp_name, 'Updation Error')

        frappe.error_log(e, "JazzHR")
        frappe.throw(e)
def updates_value(name,data,doc_emp):
    try:
        if('eeo_gender' in data.keys()):
            state,city,zip_code=doc_emp.state,doc_emp.city,doc_emp.zip
            employee_gender,military_veteran,street_address,contact_number,email,state,city,zip_code=employee_basic_details(data,doc_emp)
            state,zip_code,city=emp_address_detail(data,doc_emp)
            state=state if doc_emp.state is None else doc_emp.state
            city=city if doc_emp.city is None or len(doc_emp.city)==0 else doc_emp.city
            zip_code=zip_code if doc_emp.zip is None or doc_emp.zip==0 else doc_emp.zip
            d=f'update `tabEmployee` set employee_gender="{employee_gender}",military_veteran="{military_veteran}",street_address="{street_address}",contact_number="{contact_number}",email="{email}",zip={zip_code},state="{state}",city="{city}",updated_once=1  where name="{name}"'
            frappe.db.sql(d)
            frappe.db.commit()
    except Exception as e:
        frappe.msgprint('Some Error Occured while fetching details')
        frappe.error_log(e, "JazzHR")
        frappe.throw(e)
 
def employee_basic_details(data,doc_emp):
    try:
        employee_gender=data['eeo_gender'] if doc_emp.employee_gender is None and data['eeo_gender'] else doc_emp.employee_gender
        military_veteran=1 if data['eeoc_veteran']=='I AM A PROTECTED VETERAN' else doc_emp.military_veteran
        street_address=data['address'] if doc_emp.street_address is None or len(doc_emp.street_address)==0 and data['address']!='' and data['address']!='Unavailable'  else doc_emp.street_address
        contact_number=data['phone'] if doc_emp.contact_number is None or len(doc_emp.contact_number)==0 else doc_emp.contact_number
        email=data['email'] if doc_emp.email is None or len(doc_emp.email)==0 else doc_emp.email
        state=doc_emp.state
        city=doc_emp.city
        zip_code=doc_emp.zip
        return employee_gender,military_veteran,street_address,contact_number,email,state,city,zip_code
    except Exception as e:
        frappe.msgprint('Some Error Occured')
        frappe.error_log(e, "JazzHR")
        frappe.throw(e)
def emp_address_detail(data,doc_emp):
    try:
        state,zip_code,city='',0,''
        if(data['location'])!='(No City Provided) (No State Provided) (No Postal Code Provided)':
            address_data="https://maps.googleapis.com/maps/api/geocode/json?key="+tag_gmap_key+"&address="+data['location']
            response = requests.get(address_data)
            if(response.status_code == 200 and len(response.json())>0 and len(response.json()['results'])>0):
                address_dt=response.json()
                address_dt['results'][0]['formatted_address']
                state_data=address_dt['results'][0]['address_components']
                state,zip_code=state_zip(state_data,doc_emp)
                city_zip=address_dt['results'][0]['formatted_address'].split(',')
                city=city_zip[-3].strip() if len(city_zip)>2 and city_zip[-3].strip() else ''
        else:
            city,state,zip_code='','',0
        return state,zip_code,city
    except Exception as e:
        frappe.msgprint('Some Error Occured while fetching address details')
        frappe.error_log(e, "JazzHR")
        frappe.throw(e)
def state_zip(state_data,doc_emp):
    try:
        state,zip_code=doc_emp.state,doc_emp.zip
        for i in state_data:
            if 'administrative_area_level_1' in i['types']:
                state=i['long_name'] if i['long_name'] else ''
            elif 'postal_code' in i['types']:
                zip_code=i['long_name'] if i['long_name'].isdigit() else 0
        return state,zip_code
    except Exception as e:
        frappe.msgprint('Some Error Occured while fetching state details')
        frappe.error_log(e, "JazzHR")
        frappe.throw(e)

@frappe.whitelist()
def get_staffing_company_invoices():
    try:
        data = get_staffing_company_list()
        comps = data.split('\n')
        companies = frappe.db.get_list('Sales Invoice',filters={'company':['in',comps],'status':['!=','Cancelled']},fields=['distinct(company)'])
        '''# if len(companies)>0:
            # final_data=[c['company'] for c in companies]'''
        return "\n".join([c['company'] for c in companies]) if companies else []
        '''# else:
        #     return []'''
    except Exception as e:
        frappe.log_error(e,'Company error')
        return  []

def run_onload(doc):
    doc.set("__onload", frappe._dict())
    doc.run_method("onload")

@frappe.whitelist(allow_guest=True)
def get_company_job_order(user_type):
    try:
        current_user=frappe.session.user
        '''# data = []'''
        if user_type=='Staffing':
            sql=f'''select name from `tabCompany` where organization_type="Hiring" or parent_staffing in (select company from `tabEmployee` where email="{current_user}") '''
            companies = frappe.db.sql(sql, as_dict=1)
            data = [c['name'] for c in companies]
            return "\n".join(data)
        elif user_type in ["Hiring",exclusive_hiring]:
            sql=f''' select name,company,email from `tabEmployee` where email="{current_user}" '''
            companies = frappe.db.sql(sql, as_dict=1)
            data = [c['company'] for c in companies]
            return "\n".join(data)
        else:
            sql = """ select name from `tabCompany` where organization_type in ('Hiring','Exclusive Hiring') """
            frappe.db.sql(sql)
            companies = frappe.db.sql(sql, as_dict=1)
            data = [c['name'] for c in companies]
            return "\n".join(data)
    except Exception as e:
        print(e) 


@frappe.whitelist(allow_guest=True)
def get_organization_type(user_type):
    try:
        current_user=frappe.session.user
        data = []
        if user_type=='Staffing':
            sql=f"""select company from `tabEmployee` where user_id='{current_user}'"""
            data1=frappe.db.sql(sql, as_dict=True)
            for c in data1:
                data.append(c["company"])
            
            sql1= f"select name from `tabCompany` where parent_staffing in (select company from `tabEmployee` where email='{current_user}')"
            data2=frappe.db.sql(sql1, as_dict=True)
            for c in data2:
                data.append(c["name"])
            
            return "\n".join(data)
        elif user_type=="Hiring" or user_type==exclusive_hiring:
            sql=f''' select name,company,email from `tabEmployee` where email="{current_user}" '''
            companies = frappe.db.sql(sql, as_dict=1)
            data = [c['company'] for c in companies]

            return "\n".join(data)
        else:
            sql = """ select name from `tabCompany`"""
            frappe.db.sql(sql)
            companies = frappe.db.sql(sql, as_dict=1)
            data = [c['name'] for c in companies]

            return "\n".join(data)
    except Exception as e:
        print(e) 

@frappe.whitelist(allow_guest=True)
def get_role_profile():
    try:
        role= frappe.db.get_list('Role Profile',fields=['name'])
        data= [c['name'] for c in role]
        data.sort()
        
        return "\n".join(data)
    except Exception as e:
        print(e)

from frappe.desk.search import search_widget, build_for_autosuggest
@frappe.whitelist()
def search_link(doctype, txt, query=None, filters=None, page_length=100, searchfield=None, reference_doctype=None, ignore_user_permissions=False):
    search_widget(doctype, txt.strip(), query, searchfield=searchfield, page_length=page_length, filters=filters, reference_doctype=reference_doctype, ignore_user_permissions=ignore_user_permissions)
    temp = build_for_autosuggest(frappe.response["values"],doctype=doctype)
    if temp and temp[0]['value']=='Monday' or reference_doctype == 'Assign Employee Details':
        frappe.response['results']=temp
    else:
        frappe.response['results'] = sorted(temp, key=lambda d: d['value'].lower())
    del frappe.response["values"]

@frappe.whitelist()
def get_contract_prepared_by(contract_prepared_by):
    sql1 = ''' select organization_type from `tabUser` where email='{}' '''.format(contract_prepared_by)
    organization_type=frappe.db.sql(sql1, as_list=1)
    return organization_type

@frappe.whitelist()
def fetch_data(filter_name):
    try:
        user_data = frappe.db.get_value('User', frappe.session.user, ['organization_type', 'company'])
        if user_data[0] == 'Hiring' or user_data[0] == exclusive_hiring:
            condition = '''AND AE.hiring_organization = "{0}"'''.format(user_data[1])
        elif user_data[0] == 'TAG' or frappe.session.user == 'Administrator':
            condition = ''
        if filter_name == 'emp_id':
            sql = '''SELECT AED.employee AS emp_id FROM `tabAssign Employee` AS AE,`tabAssign Employee Details` AS AED, `tabJob Order` AS JO  WHERE AED.approved = CASE WHEN JO.resumes_required=1 THEN 1 ELSE 0 END AND AE.name = AED.parent AND AE.tag_status = "Approved" AND JO.name = AE.job_order {0} GROUP BY AED.employee'''.format(condition)
        elif filter_name == 'emp_name':
            sql = '''SELECT AED.employee_name as emp_name FROM `tabAssign Employee` AS AE,`tabAssign Employee Details` AS AED, `tabJob Order` AS JO  WHERE AED.approved = CASE WHEN JO.resumes_required=1 THEN 1 ELSE 0 END AND AE.name = AED.parent AND AE.tag_status = "Approved" AND JO.name = AE.job_order {0} GROUP BY AED.employee_name'''.format(condition)
        elif filter_name == 'company':
            sql = '''SELECT AE.company AS company FROM `tabAssign Employee` AS AE,`tabAssign Employee Details` AS AED, `tabJob Order` AS JO  WHERE AED.approved = CASE WHEN JO.resumes_required=1 THEN 1 ELSE 0 END AND AE.name = AED.parent AND AE.tag_status = "Approved" AND JO.name = AE.job_order {0} GROUP BY AE.company'''.format(condition)
        elif filter_name == 'job_order':
            sql = '''SELECT AE.job_order AS job_order FROM `tabAssign Employee` AS AE,`tabAssign Employee Details` AS AED, `tabJob Order` AS JO  WHERE AED.approved = CASE WHEN JO.resumes_required=1 THEN 1 ELSE 0 END AND AE.name = AED.parent AND AE.tag_status = "Approved" AND JO.name = AE.job_order {0} GROUP BY AE.job_order'''.format(condition)
        else:
            sql = '''SELECT DISTINCT AE.job_category AS job_title FROM `tabAssign Employee` AS AE,`tabAssign Employee Details` AS AED, `tabJob Order` AS JO  WHERE AED.approved = CASE WHEN JO.resumes_required=1 THEN 1 ELSE 0 END AND AE.name = AED.parent AND AE.tag_status = "Approved" AND JO.name = AE.job_order {0} ORDER BY AE.job_category'''.format(condition)
        return frappe.db.sql(sql, as_list=True)
    except Exception as e:
        frappe.msgprint(e, 'Employment History Filter: Fetch Data Error')

def check_password(user, old_password):
    check_user_password = User.find_by_credentials(user, old_password)
    return check_user_password['is_authenticated']

def check_password_policy(new_password):
    result = test_password_strength(new_password)
    if result:
        feedback = result.get("feedback", None)
        if feedback and not feedback.get("password_policy_validation_passed", False):
            handle_password_test_fail(feedback)
def existing_user_validate_password(user,old_password,new_password,doc):
    if old_password and not new_password:
        frappe.throw('New password is required')
    elif not old_password and  new_password:
        frappe.throw('Old password is required')
    elif old_password and new_password and (old_password == new_password):
        frappe.throw('Old and new password can not be same')
    elif old_password:
        if not check_password(user, old_password):
            frappe.throw("Old password is incorrect")
        else:
            check_password_policy(new_password)
            doc.old_password = None
            doc.save()
    else:
        doc.save()

def validate_passwords(user, old_password, new_password, doc):
    if frappe.session.user == user:
        existing_user_validate_password(user,old_password,new_password,doc)
    elif check_password(user, new_password):
        frappe.throw("Old and new password can not be same")
    else:
        check_password_policy(new_password)
        doc.save()


def set_job_title_value(industry,filters,company_name):
    try:
        if  'data' in filters:
            filters['name'] = filters['data']['filedname'] 
            company_name = filters['data']['Company_name'] 
            industry  = filters['data']['industry']
        check_item_data = frappe.db.sql(""" SELECT job_titless  from `tabItem` where industry='{0}' and  job_titless_name = '{1}' and company ='{2}' """.format(industry,filters['name'].split("-")[0],company_name),as_dict=1)
        if(len(check_item_data) > 0):
            value = [{"name":check_item_data[0]['job_titless'].split("-")[0]}]
        else:
            value = []
        return value
    except Exception:
        frappe.throw('Server Error')


@frappe.whitelist()
def get_value(doctype, fieldname, filters=None, as_dict=True, debug=False, parent=None,industry=None,company_name=None):
    """ Returns a value form a document
    :param doctype: DocType to be queried
    :param fieldname: Field to be returned (default `name`)
    :param filters: dict or string for identifying the record"""
    if frappe.is_table(doctype):
        check_parent_permission(parent, doctype)
    
    if not frappe.has_permission(doctype, parent_doctype=parent):
        frappe.throw(_("No permission for {0}").format(_(doctype)), frappe.PermissionError)
    
    filters = get_safe_filters(filters)
    if isinstance(filters, str):
        filters = {"name": filters}
    
    try:
        fields = frappe.parse_json(fieldname)
    except (TypeError, ValueError):
        #name passed, not json
        fields = [fieldname]
    
    #check whether the used filters were really parseable and usable 
    #and did not just result in an empty string or dict
    if not filters:
        filters = None
    
    if frappe.get_meta(doctype).issingle:
        value = frappe.db.get_values_from_single(fields, filters, doctype, as_dict=as_dict, debug=debug)
    
    else:
        if(doctype == "Item"):
            value = set_job_title_value(industry,filters,company_name)
        else:
            value = get_list(
				doctype,
				filters=filters,
				fields=fields,
				debug=debug,
				limit_page_length=1,
				parent=parent,
				as_dict=as_dict,
			)
        
    
    if as_dict:
        return value[0] if len(value) > 0 else []
    
    if not value:
        return 
    
    return value[0] if len(fields) > 1 else value[0][0]


def delete_job_title(doc,data):
    frappe.db.sql("DELETE FROM `tabIndustry Types Job Titles` WHERE   job_titles='{0}' and parent !='{1}'".format(doc.name,data.get("job_site")),as_dict=1)

def update_job_title(data,doc):
    create_and_update_job_site = """
                    UPDATE `tabIndustry Types Job Titles`
                    SET comp_code ='{0}', bill_rate='{1}'
                    WHERE job_titles like "{2}%" and  parent="{3}"
                """.format(data.get("comp_code") if data.get("comp_code") else "",
                    data.get("bill_rate"),doc.name,data.get("job_site"))
    frappe.db.sql(create_and_update_job_site)
    frappe.db.commit()
    doc.save()



def add_job_title_company(parent,job_title, description, rate, industry):
	check_job_title = frappe.db.sql(""" select * from  `tabJob Titles` tjt  WHERE job_titles like "{0}%" and parent="{1}" and wages="{2}" and description="{3}" and industry_type="{4}" """.format(job_title,parent,rate,description,industry))
	if not check_job_title:
		create_new_job_title = """ INSERT INTO `tabJob Titles` 
							(name,parent,parentfield,parenttype,
							job_titles,description,wages,industry_type)
							VALUES("{0}","{1}","job_titles","Company","{2}","{3}","{4}","{5}")
							""".format(uuid4().hex[:10],parent,job_title,description,rate,industry)
		frappe.db.sql(create_new_job_title)
		frappe.db.commit()
    
def save_job_title(doc): 
    check_item_data = frappe.db.sql("""SELECT job_titless from `tabItem` where industry='{0}' and  job_titless_name = '{1}' and company ='{2}' """.format(doc.industry,doc.item_code.split("-")[0],doc.company),as_dict=1)
    if check_item_data:
        return frappe.msgprint("Job Title already exists.")
    doc_name = checkingjobtitle_name(job_titless=doc.item_code.split("-")[0])
    doc.name = doc_name
    doc.item_code = doc_name
    doc.job_titless = doc_name
    doc.job_titless_name = doc.job_titless_name.split("-")[0]
    return doc


def populate_job_title(doc):
    try:
        if doc.name==None:
            doc=save_job_title(doc)
        job_title_validations(doc)
        if len(doc.job_site_table) > 0:
            last_item_id=frappe.db.sql('''SELECT last_item_id FROM company_index WHERE id=1''', as_list=1)
            for data in doc.job_site_table:
                check_job_title = frappe.db.sql('select name from `tabIndustry Types Job Titles` where job_titles like "{0}%" and parent="{1}"'.format(doc.name,data.get("job_site")),as_dict=1)
                if check_job_title:
                    update_job_title(data=data,doc=doc)
                else:
                    user = frappe.session.user
                    add_job_title = """ INSERT INTO `tabIndustry Types Job Titles`
                                        (modified_by,owner,docstatus,parent,parentfield,
                                        parenttype,idx,industry_type,job_titles,bill_rate,
                                        description,name,comp_code,item_id) values("{0}","{1}","0","{2}","job_titles",
                                        "Job Site","{3}","{4}","{5}","{6}","{7}","{8}","{9}","{10}") 
                                    """.format(user,user,data.get("job_site"),
                                        data.get("idx"),doc.industry,doc.name,
                                        data.get("bill_rate"),doc.description,uuid4().hex[:10],data.get("comp_code") if data.get("comp_code") else "","JT-"+str(last_item_id[0][0]).zfill(8))
                    data = frappe.db.sql(add_job_title)
                    frappe.db.commit()
                    last_item_id[0][0]+=1
                    doc.save()
            update_last_item_id(last_item_id[0][0])
        else:
            delete_job_title = "DELETE FROM `tabIndustry Types Job Titles` WHERE industry_type='{0}' and job_titles='{1}'".format(doc.industry,doc.item_code)
            frappe.db.sql(delete_job_title)
            doc.save()
    except Exception as e:
        print(e, frappe.get_traceback())


def delete_job_site(data,doc):
    frappe.db.sql("DELETE FROM `tabJob Sites` WHERE   job_site='{0}' and parent !='{1}'".format(doc.name,data.get("job_titles")),as_dict=1)

def update_job_site(data,doc):
    create_and_update_job_site = """
                    UPDATE `tabJob Sites`
                    SET comp_code ='{0}', bill_rate='{1}'
                    WHERE parent like "{2}%" and job_site="{3}"
                """.format(data.get("comp_code") if data.get("comp_code") else "",
                    data.get("bill_rate"),data.get("job_titles"),doc.name)
    frappe.db.sql(create_and_update_job_site)
    frappe.db.commit()
    doc.save()

def populate_job_site(doc):
    check_job_site = frappe.db.sql("select contact_name,contact_email from `tabJob Site` where  company='{0}'".format(doc.company))
    if(doc.get('__islocal') is None and check_job_site and (check_job_site[0][0] != doc.contact_name or check_job_site[0][1] != doc.contact_email)):
        frappe.throw('Unable to change the value')
    if len(doc.job_titles) > 0:
        last_item_id=frappe.db.sql('''SELECT last_item_id FROM company_index WHERE id=1''', as_list=1)
        for data in doc.job_titles:
            last_item_id[0][0] = set_item_id_job(data, last_item_id[0][0])
            check_job_site = frappe.db.sql(""" 
                SELECT name from `tabJob Sites` tjs where parent like "{0}%" and job_site="{1}"
            """.format(data.get("job_titles"),doc.name),as_dict=1)
            if check_job_site:
                update_job_site(data=data,doc=doc)
            else:
                user = frappe.session.user
                create_and_update_job_site = """
                    insert into `tabJob Sites`(name,modified_by,owner,docstatus,
                    idx,job_site,bill_rate,parent,parentfield,parenttype,comp_code) 
                    values("{0}","{1}","{2}","0","{3}","{4}","{5}","{6}",
                    "job_site_table","Item","{7}")
                """.format(uuid4().hex[:10],user,user,data.get("idx"),doc.name,
                    data.get("bill_rate"),data.get("job_titles"),data.get("comp_code")
                     if data.get("comp_code") else "")
                frappe.db.sql(create_and_update_job_site)
                frappe.db.commit()
                doc.save()
        update_last_item_id(last_item_id[0][0])
    else:
        doc.save()


def populate_contract_status(doc):
    contract_status={
                        "0":"Draft",
                        "1":"Submitted",
                        "2":"Canceled",
                        "3":"Signed"
                    }
    status_value = contract_status.get(str(doc.docstatus))
    frappe.db.sql(""" update `tabContract` SET document_status="{0}" WHERE docstatus="{1}" and name="{2}" """.format(status_value,doc.docstatus,doc.name))

def submit_contract_status(doc):
    if doc.doctype == "Contract":
            doc.submit()
            populate_contract_status(doc)
    else:
        doc.submit()


@frappe.whitelist()
def savedocs(doc, action):
    """save / submit / update doclist"""
    try:
        #if '__islocal' in json.loads(doc):
        doc_dict = json.loads(doc)
        doc = frappe.get_doc(doc_dict)
        set_local_name(doc)
        if '__islocal' in doc_dict and frappe.session.user!=doc.owner:
            frappe.throw('Invalid owner')
        user_type = frappe.db.get_value("User", frappe.session.user, "organization_type")
        doc.docstatus = {"Save":0, "Submit": 1, "Update": 1, "Cancel": 2}[action]
        if doc.docstatus==1:
           submit_contract_status(doc)
        else:
            handle_document_type(doc,doc_dict,user_type)
        run_onload(doc)
        send_updated_docs(doc)
        frappe.msgprint(frappe._("Saved"), indicator='green', alert=True)
    except Exception:
        frappe.errprint(frappe.utils.get_traceback())
        raise

def handle_document_type(doc,doc_dict,user_type):
    if doc.doctype == "User":
        user_doctype_process(doc, doc_dict, user_type)
    elif doc.doctype == 'Item':
        populate_job_title(doc)
        job_titless_name = doc_dict.get("job_titless_name")
        job_titless = doc_dict.get("job_titless")
        if job_titless_name is None or job_titless is None or len(job_titless_name)==0 or len(job_titless)==0:
            frappe.throw('Value missing for Item: Job Title')
    elif doc.doctype == "Job Site":
        populate_job_site(doc)
    elif doc.doctype == "Contract":
        contract_doctype_validations(doc)
        doc.save()
        populate_contract_status(doc)
    elif doc.doctype == 'Company':
        company_doctype(doc,doc_dict, user_type)
    elif doc.doctype == "Job Order":
        job_order_doctype(doc,doc_dict)
    elif doc.doctype == "Employee":
        employee_doctype_validations(doc)
        doc.save()
    elif doc.doctype == "Employee Onboarding Template":
        emp_setup_doctype_validations(doc)
    elif doc.doctype == "Lead":
        lead_doctype_validations(doc)
        doc.save()
    elif doc.doctype == "Claim Order":
        claim_doctype_validations(doc, user_type)
        doc.save()
    elif doc.doctype == "Employee Onboarding":
        employee_onboarding_doctype_validations(doc)
        doc.save()
    else:
        doc.save()

def employee_doctype_validations(doc):
    if(doc.ssn and len(doc.ssn) != 9):
        frappe.throw(_("Minimum and Maximum Characters allowed for SSN are 9."))
    if doc.naming_series != "HR-EMP-":
        frappe.throw("You cannot change the 'naming_series' value")

def user_doctype_process(doc, doc_dict, user_type):
    last_name = doc_dict.get("last_name")
    first_name = doc_dict.get("first_name")
    if last_name is None or first_name is None or len(first_name)==0 or len(last_name)==0:
        frappe.throw('Value missing for User: Last Name or First Name')
    check_user = frappe.db.sql("select name, email, date_of_joining, company, enabled,`terminated`, tag_user_type, reset_password_key from `tabUser` where  name='{0}'".format(doc_dict["email"]))
    new_password = doc_dict["new_password"]

    validate_user_company_joining_date_email(doc, check_user)
    user_doc = {
        "mobile_number": doc_dict["mobile_no"]
    }
    validate_phone_numbers(user_doc)
    if new_password:
        pattern = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*[!@#$%^&*(),.?":{}|<>]).{8,}$'
        if re.match(pattern, new_password) is None:
            frappe.throw('Invalid Password')
    if check_user:
        old_password = doc_dict.get("old_password")
        validate_passwords(user=doc_dict["email"],
                        old_password=old_password,
                        new_password=new_password,
                        doc=doc)
        validate_enabled(doc, check_user, user_type)
    else:
        if doc.get('__islocal') and not doc.enabled:
            frappe.throw('Do not allow to uncheck ennabled')
        check_password_policy(new_password)
    user_validations(doc)
    staffing_user_validation(doc, user_type)
    doc.save()

def validate_user_company_joining_date_email(doc, check_user):
    default_joining_date = datetime.now(timezone('US/Eastern')).date()
    check_assigned_companies = [x.assign_multiple_company for x in doc.assign_multiple_company]
    check_assigned_companies.append(doc.company)
    check_company = []
    if len(check_assigned_companies)==1:
        check_company = frappe.db.sql(f'''select name from `tabCompany` where name = "{check_assigned_companies[0]}" and organization_type = "{doc.organization_type}"''',as_list=True)
        check_company = [x[0] for x in check_company]
    elif len(check_assigned_companies)>1:
        check_company = frappe.db.sql(f'''select name from `tabCompany` where name in {tuple(check_assigned_companies)} and organization_type = "{doc.organization_type}"''',as_list=True)
        check_company = [y[0] for y in check_company]
    if not check_company or (len(set(check_assigned_companies))!=len(set(check_company))):
        frappe.throw('Invalid Company Data')
    if (doc.get('__islocal') is not None and str(default_joining_date) != doc.date_of_joining) or (check_user and str(check_user[0][2]) != doc.date_of_joining):
        frappe.throw('Invalid Joining Date')
    if (not check_user and not doc.get('__islocal')) or (check_user and not doc.get('__islocal') and check_user[0][1] != doc.email):
            frappe.throw('Invalid Email Data')
    return default_joining_date

def company_doctype(doc,doc_dict,user_type):
    company_doc = {
        "accounts_payable_phone_number": doc_dict.get("accounts_payable_phone_number"),
        "accounts_receivable_phone_number": doc_dict.get("accounts_receivable_phone_number"),
        "phone_no": doc_dict.get("phone_no"),
    }
    validate_phone_numbers(company_doc)
    validate_company_doc(doc, user_type)
    check_parent_company = frappe.db.sql("select parent_staffing,organization_type, make_organization_inactive, enable_ats, enable_payroll from `tabCompany` where  name='{0}'".format(doc.name))
    if check_parent_company:
        if(doc.get('__islocal') is None and check_parent_company[0][1] != doc.organization_type):
            frappe.throw('Invalid Organization Type.')
            
        if(doc.get('__islocal') is None and doc.organization_type==exclusive_hiring and check_parent_company[0][0] != doc.parent_staffing):
            frappe.throw('Invalid Parent Company')

        if (check_parent_company[0][2] != doc.make_organization_inactive or check_parent_company[0][3] != doc.enable_ats or check_parent_company[0][4] != doc.enable_payroll) and user_type!="TAG":
            frappe.throw('Invalid User.')
        
    if(doc.get('__islocal') is None and doc.organization_type==exclusive_hiring and check_parent_company and check_parent_company[0][0] != doc.parent_staffing):
        frappe.throw('Invalid Parent Company')
    doc.save()

def job_order_doctype(doc,doc_dict):
        job_order = frappe.db.sql("select from_date,to_date,job_site,order_status from `tabJob Order` where  name='{0}'".format(doc_dict["name"]))
        from frappe.utils import today
        if (doc.get('__islocal') and (doc.from_date < str(today()) or doc.to_date < str(today()))) or (doc.get('__islocal') is None and job_order and job_order[0][3] in ["Completed", "Cancelled"] and (doc.from_date != str(job_order[0][0]) or doc.to_date != str(job_order[0][1]))):
            frappe.throw("Start Date or End Date Cannot be Past Date")
        if(doc.to_date < doc.from_date):
            frappe.throw("End Date Cannot be Less than Start Date")

        if(job_order and job_order[0][2] != doc.job_site):
            frappe.throw('Unable to change job site value')
        all_job_titles = [row.select_job for row in doc.multiple_job_titles]
        desc_sql = f"select descriptions from `tabItem` where name in {tuple(all_job_titles)}" if len(all_job_titles)>1 else f"select descriptions from `tabItem` where name='{all_job_titles[0]}'"
        mul_job_titles = frappe.db.sql(desc_sql)
        job_order_descriptions = [row[0] for row in mul_job_titles]
        for job_title in doc.multiple_job_titles:
            description = job_title.get("description")
            if description is not None and len(description)>0 and description not in job_order_descriptions:
                frappe.throw('Could not find description.')
        doc.save()
        
def validate_phone_numbers(doc_dict):
    import phonenumbers
    
    fields_to_validate = {
        "accounts_payable_phone_number": "Accounts Payable Phone Number",
        "accounts_receivable_phone_number":"Accounts Receivable Phone Number",
        "phone_no": "Phone Number",
        "mobile_number": "Mobile Number"
    }
    
    invalid_fields = []
    
    for field, label in fields_to_validate.items():
        phone_number_str = doc_dict.get(field)
        if phone_number_str:
            try:
                phone_number = phonenumbers.parse(phone_number_str)
                if not phonenumbers.is_valid_number(phone_number):
                    invalid_fields.append(label)
            except phonenumbers.NumberParseException:
                invalid_fields.append(label)
            except Exception as e:
                print(e)
    if invalid_fields:
        invalid_fields_str = ', '.join(invalid_fields)
        frappe.throw(f"Invalid {invalid_fields_str}!")

@frappe.whitelist()
def cancel(doctype=None, name=None, workflow_state_fieldname=None, workflow_state=None):
    try:
        """cancel a doclist"""
        doc = frappe.get_doc(doctype, name)

        if workflow_state_fieldname and workflow_state:
            doc.set(workflow_state_fieldname, workflow_state)

        doc.cancel()
        populate_contract_status(doc)    
        send_updated_docs(doc)
        frappe.msgprint(frappe._("Cancelled"), indicator="red", alert=True)
    except Exception as e:
        print(frappe.utils.get_traceback(), e)


@frappe.whitelist(methods=['POST', 'PUT'])
def save(doc):
	'''Update (save) an existing document

	:param doc: JSON or dict object with the properties of the document to be updated'''
	if isinstance(doc, string_types):
		doc = json.loads(doc)
	if '__islocal' in doc and frappe.session.user!=doc['owner']:
		frappe.throw('Invalid owner')
	doc = frappe.get_doc(doc)
	doc.save()

	return doc.as_dict()

@frappe.whitelist()
def get_onboarding_details(parent, parenttype):
	return frappe.get_all(
		"Employee Boarding Activity",
		fields=[
			"activity_name",
			"role",
			"user",
			"required_for_employee_creation",
			"description",
			"task_weight",
			"begin_on",
			"duration",
            "document_required",
            "document",
            "attach"
		],
		filters={"parent": parent, "parenttype": parenttype},
		order_by="idx",
	)

@frappe.whitelist()
def get_retirement_date(date_of_birth=None):
	if date_of_birth:
		try:
			retirement_age = cint(frappe.db.get_single_value("HR Settings", "retirement_age") or 120)
			dt = add_years(getdate(date_of_birth), retirement_age)
			return dt.strftime("%Y-%m-%d")
		except ValueError:
			# invalid date
			return


@frappe.whitelist(allow_guest=True)
def upload_file():
    user = None
    validation_message = "You can only upload JPG, PNG, PDF, TXT or Microsoft documents."
    if frappe.session.user == "Guest":
        if frappe.get_system_settings("allow_guests_to_upload_files"):
            ignore_permissions  = True
        else:
            raise frappe.PermissionError
    else:
        user : "User" = frappe.get_doc("User", frappe.session.user)
        ignore_permissions = False
	
    files = frappe.request.files
    is_private = frappe.form_dict.is_private
    doctype = frappe.form_dict.doctype
    docname = frappe.form_dict.docname
    fieldname = frappe.form_dict.fieldname
    file_url = frappe.form_dict.file_url
    folder = frappe.form_dict.folder or "Home"
    method = frappe.form_dict.method
    filename = frappe.form_dict.file_name
    optimize = frappe.form_dict.optimize
    content = None
    
    if "file" in files:
        upload_file  = files["file"]
        filename = upload_file.filename
        content_type = guess_type(filename)[0]
              
        split_file_name  = filename.rsplit(".",1)
        if len(split_file_name) <= 1:
            throw(_(validation_message))
        if split_file_name[1].lower() not in ALLOWED_FILE_EXTENSIONS:
            throw(_(validation_message))
        
        filename = re.sub(r"[!@#$%^&*(){};:,./<>?\|`+\s]", "", split_file_name[0]) + "." + split_file_name[1]
        content = upload_file.stream.read()
        if optimize and content_type.startswith("image/"):
            args = {"content": content, "content_type": content_type}
            if frappe.form_dict.max_width:
                args["max_width"] = int(frappe.form_dict.max_width)
            if frappe.form_dict.max_height:
                args["max_height"] = int(frappe.form_dict.max_height)
            content = optimize_image(**args)

    frappe.local.uploaded_file = content
    frappe.local.uploaded_filename = filename

    if content is not None and (
        frappe.session.user == "Guest" or (user and not user.has_desk_access())
    ):
        filetype = guess_type(filename)[0]
        if filetype not in ALLOWED_MIMETYPES:
            throw(_(validation_message))

    if method:
        method = frappe.get_attr(method)
        is_whitelisted(method)
        return method()

    else:
        return frappe.get_doc(
			{
				"doctype": "File",
				"attached_to_doctype": doctype,
				"attached_to_name": docname,
				"attached_to_field": fieldname,
				"folder": folder,
				"file_name": filename,
				"file_url": file_url,
				"is_private": cint(is_private),
				"content": content,
			}
		).save(ignore_permissions=ignore_permissions)
	

queue_prefix = 'insert_queue_for_'

@frappe.whitelist()
def deferred_insert(doctype, records):
	records_json=json.loads(records)
	if records_json[0]['user']!=frappe.session.user:
		frappe.throw('Invalid request')
	frappe.cache().rpush(queue_prefix + doctype, records)

@frappe.whitelist()
def set_seen_value(value, user):
    if frappe.session.user==user:   	
        frappe.db.set_value('Notification Settings', user, 'seen', value, update_modified=False)
    else:
        frappe.throw(no_perm) 

@frappe.whitelist()
def mark_as_read(room):
    """Mark the message as read
    Args:
        room (str): Room's name.
    """
    members = frappe.db.get_value('Chat Room', {'name':room}, ['members'])
    if frappe.session.user in members:
        frappe.enqueue('chat.utils.update_room', room=room,
                    is_read=1, update_modified=False)
    else:
        frappe.throw(no_perm)

@frappe.whitelist(allow_guest=True)
def set_typing(room, user, is_typing, is_guest):
    """Set the typing text accordingly
    Args:
        room (str): Room's name.
        user (str): Sender who is typing.
        is_typing (bool): Whether user is typing.
        is_guest (bool): Whether user is guest or not.
    """
    if user==frappe.session.user:
        if not is_user_allowed_in_room(room, user, user):
            raise_not_authorized_error()
        result = {
            'room': room,
            'user': user,
            'is_typing': is_typing,
            'is_guest': is_guest
        }
        event = room + ':typing'
        frappe.publish_realtime(event=event,message=result)
    else:
        frappe.throw(no_perm)

@frappe.whitelist(allow_guest=True)
def send(content, user, room, email):
    """Send the message via socketio

    Args:
        message (str): Message to be sent.
        user (str): Sender's name.
        room (str): Room's name.
        email (str): Sender's email.
    """
    if email==frappe.session.user:
        if not is_user_allowed_in_room(room, email, user):
            raise_not_authorized_error()

        new_message = frappe.get_doc({
            'doctype': 'Chat Message',
            'content': content,
            'sender': user,
            'room': room,
            'sender_email': email
        }).insert()
        update_room(room=room, last_message=content)

        result = {
            'content': content,
            'user': user,
            'creation': new_message.creation,
            'room': room,
            'sender_email': email
        }

        typing_data = {
            'room': room,
            'user': user,
            'is_typing': 'false',
            'is_guest': 'true' if user == 'Guest' else 'false',
        }
        typing_event = room + ':typing'

        frappe.publish_realtime(event=room, message=result, after_commit=True)

        frappe.publish_realtime(event='latest_chat_updates',
                                message=result, after_commit=True)
        frappe.publish_realtime(event=typing_event,
                                message=typing_data, after_commit=True)
    else:
        raise_not_authorized_error()


@frappe.whitelist(allow_guest=True)
def get_all(room, email):
    """Get all the messages of a particular room

    Args:
        room (str): Room's name.

    """
    if email==frappe.session.user:
        if not is_user_allowed_in_room(room, email):
            raise_not_authorized_error()

        result = frappe.db.get_all('Chat Message',
                                filters={
                                    'room': room,
                                },
                                fields=['content', 'sender',
                                        'creation', 'sender_email'],
                                order_by='creation asc'
                                )
        return result
    else:
        raise_not_authorized_error()

from frappe.desk.doctype.tag.tag import DocTags
@frappe.whitelist()
def add_tags(tags, dt, docs, color=None):
    "adds a new tag to a record, and creates the Tag master"
    tags = frappe.parse_json(tags)
    docs = frappe.parse_json(docs)
    for doc in docs:
        jo_doc = frappe.get_doc('Job Order', doc)
        if not jo_doc.has_permission("read"):
            frappe.local.response['http_status_code'] = 500
            frappe.throw(('Insufficient Permission'))
        for tag in tags:
            DocTags(dt).add(doc, tag)

EPL="Energy Point Log"
@frappe.whitelist()
def get_energy_points_percentage_chart_data(user, field):
	if user!="Administrator" and user!=frappe.session.user:
		frappe.throw("Insufficient Permission for fetching chart data")
	result = frappe.get_all(
		EPL,
		filters={"user": user, "type": ["!=", "Review"]},
		group_by=field,
		order_by=field,
		fields=[field, "ABS(sum(points)) as points"],
		as_list=True,
	)

	return {
		"labels": [r[0] for r in result if r[0] is not None],
		"datasets": [{"values": [r[1] for r in result]}],
	}


@frappe.whitelist()
def get_user_rank(user):
	if user!="Administrator" and user!=frappe.session.user:
		frappe.throw("Insufficient Permission for fetching user rank")
	month_start = datetime.today().replace(day=1)
	monthly_rank = frappe.get_all(
		EPL,
		group_by="user",
		filters={"creation": [">", month_start], "type": ["!=", "Review"]},
		fields=["user", "sum(points)"],
		order_by="sum(points) desc",
		as_list=True,
	)

	all_time_rank = frappe.get_all(
		EPL,
		group_by="user",
		filters={"type": ["!=", "Review"]},
		fields=["user", "sum(points)"],
		order_by="sum(points) desc",
		as_list=True,
	)

	return {
		"monthly_rank": [i + 1 for i, r in enumerate(monthly_rank) if r[0] == user],
		"all_time_rank": [i + 1 for i, r in enumerate(all_time_rank) if r[0] == user],
	}


@frappe.whitelist()
def getdoc(doctype, name, user=None):
	"""
	Loads a doclist for a given document. This method is called directly from the client.
	Requries "doctype", "name" as form variables.
	Will also call the "onload" method on the document.
	"""
	if not (doctype and name): \
        frappe.throw( 
            title='Error',  
            msg=_('doctype and name required!')
            )

	if not name:
		name = doctype

	if not is_virtual_doctype(doctype) and not frappe.db.exists(doctype, name):
		return []

	doc = frappe.get_doc(doctype, name)
	run_onload(doc)

	if not doc.has_permission("read")  or (doctype=='Employee' and (frappe.get_doc("User", frappe.session.user)).organization_type in ('Hiring',exclusive_hiring)):
		frappe.flags.error_message = _("Insufficient Permission for {0}").format(
			frappe.bold(doctype + " " + name)
		)
		raise frappe.PermissionError(("read", doctype, name))

	doc.apply_fieldlevel_read_permissions()

	# add file list
	doc.add_viewed()
	get_docinfo(doc)

	doc.add_seen()
	set_link_titles(doc)
	if frappe.response.docs is None:
		frappe.local.response = _dict({"docs": []})
	frappe.response.docs.append(doc)

@frappe.whitelist()
def update_last_item_id(last_item_id):
    try:
        frappe.db.sql(f'''UPDATE company_index SET last_item_id={last_item_id} WHERE id=1''')
        frappe.db.commit()
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.log_error(e, 'update_last_item_id error')
    

@frappe.whitelist()
def set_item_id_job(job_sites_doc, last_item_id):
    try:
        if not job_sites_doc.item_id:
            job_sites_doc.item_id = 'JT-'+str(last_item_id).zfill(8)
            last_item_id+=1
        return last_item_id
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.log_error(e, 'set_item_id error')

def get_pdf(html, options=None, output: PdfWriter | None = None, doc = []):
    html = scrub_urls(html)
    html, options = prepare_options(html, options)

    options.update({"disable-javascript": "", "disable-local-file-access": ""})

    filedata = ""
    if LooseVersion(get_wkhtmltopdf_version()) > LooseVersion("0.12.3"):
        options.update({"disable-smart-shrinking": ""})

    try:
        filedata = pdfkit.from_string(html, options=options or {}, verbose=True)
        reader = PdfReader(BytesIO(filedata))
    except OSError as e:
        if any([error in str(e) for error in PDF_CONTENT_ERRORS]):
            if not filedata:
                frappe.throw(_("PDF generation failed because of broken image links"))

            if output:
                output.append_pages_from_reader(reader)
        else:
            raise
    finally:
        cleanup(options)

    if "password" in options:
        password = options["password"]

    if output:
        output.append_pages_from_reader(reader)
        return output

    writer = PdfWriter()
    writer.append_pages_from_reader(reader)

    add_header_footer(reader, doc)

    if "password" in options:
        writer.encrypt(password)

    filedata = get_file_data_from_writer(writer)

    return filedata

def add_header_footer(reader, doc):
    if doc and doc[0]=="Sales Invoice":   	
        header_height=footer_height = 12
        invoice_data = frappe.db.sql(f"select customer, job_order from `tabSales Invoice` where name='{doc[1]}'", as_list=1)
        header_right = invoice_data[0][0]
        header_left = frappe.utils.now_datetime().strftime("%m/%d/%Y %I:%M %p")
        footer_left = invoice_data[0][1] if invoice_data[0][1] else ''
        for page_num in range(len(reader.pages)):
            if page_num==0: continue

            page = reader.pages[page_num]
            first_page = reader.pages[0]

            page_width = float(first_page.mediabox.width)
            page_height = float(first_page.mediabox.height)

            packet = BytesIO()
            canvas_obj = canvas.Canvas(packet, pagesize=(page_width, page_height))
            canvas_obj.setFont('Helvetica', 9)
            
            canvas_obj.drawString(header_height, page_height-(header_height*2), header_left)

            canvas_obj.drawString(page_width-(canvas_obj.stringWidth(header_right)+header_height), page_height-(footer_height*2), header_right)

            canvas_obj.drawString(footer_height, footer_height, footer_left)

            footer_right = f"{page_num+1}/{len(reader.pages)}"
            canvas_obj.drawString(page_width-(canvas_obj.stringWidth(footer_right)+footer_height), footer_height, footer_right)

            canvas_obj.save()
            packet.seek(0)
            new_pdf = PdfReader(packet)
            page.merge_page(new_pdf.pages[0])


def emp_setup_doctype_validations(doc):
    if frappe.db.get_value("Company", doc.company, "organization_type")!="Staffing":
        frappe.throw('Invalid action')
    else:
        doc.save()


def validate_enabled(doc, check_user, user_type):
    if (check_user[0][4]!=doc.terminated or check_user[0][5]!=doc.enabled) and check_user[0][6] in [hiring_user, "Staffing User"]:
        frappe.throw('Invalid User')
    if user_type==exclusive_hiring and (doc.tag_user_type!=check_user[0][6] or doc.organization_type!=exclusive_hiring):
        frappe.throw(Invalid_Action)


def contract_doctype_validations(doc):
    email, lead_owner, company_name, owner_company = frappe.db.get_value("Lead", doc.lead, ["email_id", "lead_owner", "company_name", "owner_company"])
    if email != doc.end_party_user or lead_owner!=doc.contract_prepared_by or company_name!=doc.hiring_company or owner_company!=doc.staffing_company:
        frappe.throw("Invalid data")


def lead_doctype_validations(doc):
    if doc.naming_series!="CRM-LEAD-.YYYY.-":
        frappe.throw("You cannot change the 'naming_series' value")


def get_no_of_remaining(doc, row):
    if doc.get('__islocal'):
        no_of_workers = frappe.db.get_value("Multiple Job Titles", {
            "parent": doc.job_order,
            "select_job": row.job_title,
            "job_start_time": row.start_time
        }, "no_of_workers")
        worker_data_sql = f'''
        SELECT sum(approved_no_of_workers) 
        FROM `tabMultiple Job Title Claim` 
        WHERE parent IN 
            (SELECT name FROM `tabClaim Order` WHERE job_order="{doc.job_order}")
        AND job_title="{row.job_title}" AND start_time="{row.start_time}"'''
        worker_data = frappe.db.sql(worker_data_sql)
        no_of_remaining = no_of_workers - worker_data[0][0] if worker_data[0][0] else no_of_workers
        approved_workers = 0
    else:
        no_of_remaining, approved_workers = frappe.db.get_value("Multiple Job Title Claim", row.name, ["no_of_remaining_employee", "approved_no_of_workers"])
    return no_of_remaining, approved_workers


def claim_doctype_validations(doc, user_type):
    claimed, approved = 0, 0
    doc_approved_no_of_workers = doc.approved_no_of_workers or 0
    doc_staff_claims_no = doc.staff_claims_no or 0
    for row in doc.multiple_job_titles:
        claimed += row.staff_claims_no
        approved += row.approved_no_of_workers

        no_of_remaining, approved_workers = get_no_of_remaining(doc, row)

        if no_of_remaining != row.no_of_remaining_employee:
            frappe.throw("You cannot change the number of remaining employees.")
        elif approved_workers != row.approved_no_of_workers and user_type == "Staffing":
            frappe.throw("You cannot change the number of approved employees.")
        elif row.no_of_remaining_employee < row.staff_claims_no:
            frappe.throw("Claim cannot be greater than the number of remaining employees.")
    if claimed != doc_staff_claims_no or approved != doc_approved_no_of_workers:
        frappe.throw("Invalid data.")


def staffing_user_validation(doc, user_type):
    comp_type = frappe.db.get_value("Company", doc.company, "organization_type")
    if user_type == "Staffing" and not ((doc.organization_type==exclusive_hiring and doc.tag_user_type in ["Hiring Admin", hiring_user] and comp_type ==exclusive_hiring) or (doc.organization_type=="Staffing" and doc.tag_user_type in ["Staffing Admin", "Staffing User"] and comp_type =="Staffing")):
        frappe.throw(Invalid_Action)

def validate_company_doc(doc, user_type):
    for row in doc.industry_type:
        pattern = r'[+<>^?#\\]'
        if re.match(pattern, row.industry_type):
            frappe.throw("Invalid characters in Industry.")

    if user_type == "Staffing":
        if (doc.get("__islocal") and doc.organization_type != exclusive_hiring) or \
        (not doc.get("__islocal") and doc.organization_type not in ["Staffing", exclusive_hiring]):
            frappe.throw(Invalid_Action)

def user_validations(doc):
    if doc.get('__islocal') and doc.date_of_joining != datetime.now(timezone('US/Eastern')).date().strftime("%Y-%m-%d"):
        frappe.throw('Invalid Date of Joining')
    if doc.msg_from_staff_app != 1:
        frappe.throw('You cannot turn off email when message is received from staffing.')

def employee_onboarding_doctype_validations(doc):
    if doc.date_of_birth[0:4]==str(datetime.now().year):
        frappe.throw("Birth Year must be earlier than this year.")

def job_title_validations(doc):
    pattern = r'[+<>^?#\\]'
    throw_error=0
    attributes_to_check = ['job_titless', 'item_code', 'job_titless_name', 'descriptions', 'name', 'item_name']
    for attribute in attributes_to_check:
        value = getattr(doc, attribute)
        if re.match(pattern, value):
            setattr(doc, attribute, re.sub(pattern, '', value))
            throw_error=1
    if throw_error:
        frappe.throw('/ \\ < > + ? # special characters are not allowed.')
