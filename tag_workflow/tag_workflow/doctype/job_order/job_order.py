# Copyright (c) 2021, SourceFuse and contributors
# For license information, please see license.txt
import frappe
from frappe.share import add_docshare as add
from tag_workflow.tag_data import joborder_email_template,chat_room_created,job_order_notification,free_redis
from tag_workflow.utils.notification import sendmail
from tag_workflow.utils.notification import make_system_notification, get_mail_list
from frappe.model.document import Document
from datetime import datetime, timedelta
import json
from frappe import _
from frappe.model.mapper import get_mapped_doc

#-----------------#
ORD = "Job Order"
item = "Timesheet Activity Cost"
payment = "Payment Schedule"
taxes= "Sales Taxes and Charges"
team = "Sales Team"
ASN = "Assign Employee"
CLM = "Claim Order"
jobOrder = 'Job Order Notification'
doc_name_job_order = 'Job Order'
salesInvoice = "Sales Invoice"
jo_modify_app = 'jo_modify_app'
jo_modify_mail = 'jo_modify_mail'

site = frappe.utils.get_url().split('/')
sitename = site[0]+'//'+site[2]

class JobOrder(Document):
    def after_insert(self):
        self.check_assign()

    def check_assign(self):
        if(self.is_repeat == 1 and self.repeat_staff_company and self.repeat_from and self.is_direct == 1 and self.repeat_staff_company == self.staff_company2):
            selected_companies = self.repeat_staff_company.strip()
            staff_selected_companies = selected_companies.split('~')
            frappe.db.set_value(ORD, self.name, "claim", selected_companies)
            frappe.db.set_value(ORD, self.name, "staff_org_claimed", "" if self.resumes_required else selected_companies)
            frappe.db.set_value(ORD, self.name, "bid", len(staff_selected_companies))
            worker_filled = 0
            worker_filled_job_title={}
            for comp in staff_selected_companies:
                comp = comp.strip()
                self.check_claims(comp)
                worker_filled_new, worker_filled_job_title=self.check_assign_doc(comp, worker_filled, worker_filled_job_title)
                worker_filled+=worker_filled_new
            if not self.resumes_required:
                for i in worker_filled_job_title:
                    job_category, start_time = i.split('~')
                    sql = f'UPDATE `tabMultiple Job Titles` SET worker_filled = {worker_filled_job_title[i]} WHERE select_job="{job_category}" and job_start_time="{start_time}" and parent="{self.name}"'
                    frappe.db.sql(sql)
            frappe.db.set_value(ORD, self.name, "total_workers_filled", worker_filled if self.resumes_required==0 else 0)
            frappe.db.commit()
            self.remaining_companies(self.repeat_staff_company, self.repeat_from, self.name, self.company, self.select_job)

    def check_assign_doc(self, comp, worker_filled, worker_filled_job_title):
        if(frappe.db.exists(ASN, {"job_order": self.repeat_from, "company": comp, "tag_status": "Approved"})):
            old_assign = frappe.get_doc(ASN, {"job_order": self.repeat_from, "company": comp, "tag_status": "Approved"})
            new_doc = frappe.copy_doc(old_assign)
            new_doc.tag_status = "Open"
            new_doc.items = []
            new_doc.employee_details = []
            new_doc.no_of_employee_required = self.total_no_of_workers
            new_doc.job_order= self.name
            new_doc = self.check_employee_active(old_assign, new_doc)
            if(new_doc.employee_details):
                for i in new_doc.employee_details: 
                    key = f"{i.job_category}~{i.job_start_time}"
                    worker_filled_job_title = update_total_worker_filled(key, worker_filled_job_title)
                    i.approved=0
                meta = frappe.get_meta(ASN)

                for field in meta.get_link_fields():
                    field.ignore_user_permissions = 1
                new_doc.flags.ignore_permissions = True
                new_doc.save(ignore_permissions=True)

                worker_filled = self.get_number_of_worker(new_doc)

                self.assign_doc(new_doc.name, ASN,comp)
                self.auto_email(new_doc,comp)
                self.emp_assignment(new_doc, comp)
                if(self.resumes_required==0):
                    worker_filled = len(new_doc.employee_details)+worker_filled
                    dat=f'update `tabAssign Employee` set tag_status="Approved" where name="{new_doc.name}"'
                    frappe.db.sql(dat)
                    frappe.db.commit()
                else:
                    new_doc.approve_employee_notification=1
                    new_doc.save()
            else:
                frappe.msgprint(_("Original order employees may not be available due to status change."))
        return worker_filled, worker_filled_job_title

    def check_employee_active(self, old_assign, new_doc):
        try:
            _new_doc = new_doc
            for emp in old_assign.employee_details:
                is_dnr = frappe.db.sql(""" select count(name) as count from `tabTimesheet` where (dnr = 1 or non_satisfactory = 1) and employee =%s and job_order_detail = %s """,(emp.employee, old_assign.job_order), as_dict=1)
                if(frappe.db.get_value("Employee", emp.employee, "status") == "Active" and is_dnr[0]['count'] == 0):
                    new_doc.append("employee_details", emp)
            return new_doc
        except Exception as e:
            frappe.msgprint(e)
            return _new_doc

    def check_claims(self,comp):
        if(frappe.db.exists(CLM, {"job_order": self.repeat_from, "staffing_organization": comp})):
            frappe.db.set_value(ORD, self.name, "claim", "~"+comp)
            old_claims = frappe.get_list(CLM, {"job_order": self.repeat_from, "staffing_organization": comp})
            for i in old_claims:
                old_claim= frappe.get_doc(CLM, i)
                new_claim = frappe.copy_doc(old_claim)
                new_claim.job_order = self.name
                new_claim.save(ignore_permissions=True)
                self.assign_doc(new_claim.name, CLM,comp)

    def assign_doc(self, name, doc_type,comp):
        stf_usr = frappe.db.get_list("Employee", {"company": comp, "user_id": ["not like", None]}, "user_id as name", ignore_permissions=1)
        hir_usr = frappe.db.get_list("User", {"company": self.company}, "name", ignore_permissions=1)
        usrs = hir_usr+stf_usr
        for u in usrs:
            add(doc_type, name, u.name, read=1, write = 1, share = 1, everyone = 0,flags={"ignore_share_permission": 1})

    def auto_email(self, new_doc,comp):
        emp = ""
        for e in new_doc.employee_details:
            emp += e.employee_name + ', '

        usr = frappe.db.get_list("User", {"company": self.company}, "name")
        usrs = [u.name for u in usr]
        job_order_app, job_order_mail = get_mail_list(usrs,app_field='jo_claim_app',mail_field='jo_claim_mail')

        sub = "Employee Assigned"
        msg = f'{comp} has submitted a claim for {emp[:-1]} for {new_doc.job_order} at {self.job_site} on {self.posting_date_time}'
        make_system_notification(job_order_app, msg, ASN, new_doc.name, sub)
        msg = f'{comp} has submitted a claim for {emp[:-1]} for {new_doc.job_order} at {self.job_site} on {self.posting_date_time}. Please review and/or approve this claim .'
        link = f'href="{sitename}/app/assign-employee/{new_doc.name}"'
        email_temp = joborder_email_template(sub, msg, job_order_mail, link)
        print(email_temp)
        chat_room_created(self.company, comp, self.name)

    def remaining_companies(self,staff_company,repeat_job_order_name,new_order,hiring_company,job_title):
        old_staff_companies=frappe.get_doc(ORD,repeat_job_order_name)
        staff_selected_companies=old_staff_companies.staff_org_claimed.split('~')
        new_selected_companies=staff_company.split('~')
        if(len(staff_selected_companies)!=len(new_selected_companies)):
            comp_list=[c.strip() for c in staff_selected_companies]
            comp_list=tuple(comp_list)
            usr_sql = '''select email from `tabUser` where organization_type='staffing' and company not in {0} '''.format(comp_list)
            user_list = frappe.db.sql(usr_sql, as_list=1)
            l = [l[0] for l in user_list if l[0]!=frappe.session.user]
            for user in l:
                add(ORD, new_order, user, read=1, write = 0, share = 0, everyone = 0)
            subject="New Work Order"
            job_order_notification(job_title,hiring_company,new_order,subject,l)

    def emp_assignment(self, new_doc, comp):
        try:
            worker_required = 0
            if(new_doc.resume_required == 1):
                worker_required = self.get_number_of_worker(new_doc)
            else:
                worker_required = len(new_doc.employee_details)

            if(worker_required < self.total_no_of_workers):
                required_emp = self.total_no_of_workers - worker_required
                self.send_emp_assignment_email(comp, new_doc, required_emp)
        except Exception as e:
            frappe.msgprint(e)

    def send_emp_assignment_email(self, comp, new_doc, required_emp):
        try:
            frappe.db.set_value(ASN, new_doc.name, "tag_status", "Open")
            usr = frappe.db.get_list("User", {"company": comp}, "name", ignore_permissions=1)
            usrs = [u.name for u in usr]
            sub = "Update Employee Assignments on Repeated Job Orders"
            msg = f'{new_doc.hiring_organization} is requesting a repeat of a work order for {new_doc.job_category} specifically with {comp}. {required_emp} employees require replacing. Please assign additional employees.'
            sendmail(emails=usrs, message=msg, subject=sub, doctype=ASN, docname=new_doc.name)
        except Exception as e:
            frappe.msgprint(e)

    def get_number_of_worker(self, new_doc):
        try:
            worker_required = 0
            if(new_doc.resume_required == 1):
                for emp in new_doc.employee_details:
                    if(emp.approved):
                        worker_required += 1
            return worker_required
        except Exception as e:
            frappe.msgprint(e)
            return 0

@frappe.whitelist()
def joborder_notification(organizaton,doc_name,company,job_title,posting_date,job_site=None):
    jo_doc=frappe.get_doc(ORD,doc_name)
    if not jo_doc.has_permission("read"):
        frappe.local.response['http_status_code'] = 500
        frappe.throw('Insufficient Permission for Job Order ' + doc_name)
    elif jo_doc.company!=company or jo_doc.select_job!=job_title or jo_doc.staff_org_claimed!=organizaton:
        frappe.local.response['http_status_code'] = 500
        frappe.throw('Invalid Parameter')
    sql = '''select data from `tabVersion` where docname = "{}" '''.format(doc_name)
    change = frappe.db.sql(sql, as_dict= True)
    if len(change) > 2:
        sql = ''' select data from `tabVersion` where docname='{}' order by modified DESC'''.format(doc_name)
        data=frappe.db.sql(sql, as_list=1)
        new_data=json.loads(data[0][0])
        if(new_data['changed'][0][0]=='total_no_of_workers'):
            now = datetime.now()
            dt_string = now.strftime("%d/%m/%Y %H:%M")
            msg = 'The number of employees requested for '+doc_name+' on '+dt_string+' has been modified. '
            is_send_mail_required(organizaton,doc_name,msg)
        else:
            msg = f'{company} has updated details for work order {doc_name} at {job_site} for {posting_date}. Please review work order details.'
            is_send_mail_required(organizaton,doc_name,msg)

def is_send_mail_required(organizaton,doc_name,msg):
    try:
        staffing = organizaton.split('~')
        staffing_list = []
        for name in staffing:
            sql = '''select user_id from `tabEmployee` where company = "{}" and user_id IS NOT NULL '''.format(name.strip())
            staffing_name = frappe.db.sql(sql, as_list = True) 
            for value in staffing_name:
                staffing_list.append(value[0])
                subject = jobOrder
        if staffing_list:
            staffing_list_app, staffing_list_mail = get_mail_list(staffing_list,app_field=jo_modify_app,mail_field=jo_modify_mail)
            make_system_notification(staffing_list_app, message = msg, doctype = ORD, docname =  doc_name, subject = subject)
            sendmail(emails = staffing_list_mail, message = msg, subject = subject, doctype = ORD, docname = doc_name)
    except Exception as e:
        frappe.log_error(e, "Job Order Notification Error")
        frappe.throw(e)


@frappe.whitelist()
def get_jobtitle_list(doctype, txt, searchfield, page_len, start, filters):
    try:
        company=filters.get('job_order_company')
        site=filters.get('job_site')
        if company is None:
            return None
        elif site is None:
            return ()
        else:
            sql = ''' select job_titles from `tabIndustry Types Job Titles` where parent = '{0}' and job_titles like "%%{1}%%"'''.format(site,'%s' % txt)
            return frappe.db.sql(sql)
    except Exception as e:
        frappe.log_error(e,'Getting Job Title Error')


@frappe.whitelist()
def get_jobtitle_list_page(doctype, txt, searchfield, page_len, start, filters):
    company=filters.get('job_order_company')
    if company is None:
        return None
    else:
        sql = ''' select job_titles from `tabJob Titles` where parent = '{0}' '''.format(company)
        return frappe.db.sql(sql)


@frappe.whitelist()
def update_joborder_rate_desc(job_site,job_title):  
    try:
        sql=frappe.db.sql(''' select industry_type,bill_rate,comp_code from `tabIndustry Types Job Titles` where parent='{0}' and job_titles='{1}' '''.format(job_site,job_title),as_dict=1)
        return sql
    except Exception as e:
        frappe.log_error(e,'Getting job order rate description value error')

@frappe.whitelist()
def direct_order_count_value(comp_name):
    sql = f"select COUNT(*) from `tabJob Order` where staff_company = '{comp_name}' and bid=0 and is_repeat= 0 and is_direct = 0 and is_single_share =1 and order_status <>'Completed'"
    count = frappe.db.sql(sql,as_list=True)
    return count[0] if count else []

@frappe.whitelist()
def after_denied_joborder(staff_company,joborder_name,job_title,hiring_name):
    sql = '''select email from `tabUser` where organization_type='staffing' and company != "{}"'''.format(staff_company)
    share_list = frappe.db.sql(sql, as_list=True)
    sql1 = ''' select email from `tabUser` where organization_type = 'hiring' and company = "{}"'''.format(hiring_name)
    hiring_list = frappe.db.sql(sql1,as_list=True)
    hiring_user_list = [user[0] for user in hiring_list]
    job_order_app, job_order_mail = get_mail_list(hiring_user_list,app_field='jo_claim_app',mail_field='jo_claim_mail')

    
    if share_list:
        for user in share_list:
            add(ORD, joborder_name, user[0], read=1,write=0, share=1, everyone=0, notify=0,flags={"ignore_share_permission": 1})

    try:
        jb_ord = frappe.get_doc(ORD,joborder_name)
        jb_ord.is_single_share = 0
        jb_ord.staff_company = None
        jb_ord.staff_company2 = None
        jb_ord.save(ignore_permissions = True)
        subject = jobOrder
        msg=f'{staff_company} unable to fulfill claim on your work order: {joborder_name}.'
        make_system_notification(job_order_app,msg,ORD,joborder_name,subject)   
        sendmail(emails = job_order_mail, message = msg, subject = subject, doctype = ORD, docname = joborder_name)
        
    except Exception as e:
        frappe.log_error(e,'job order not found')


@frappe.whitelist()
def make_invoice(source_name, target_doc=None):
    """
    The function `make_invoice` checks if there are any timesheets associated with a job order and
    prepares an invoice if there are.
    
    :param source_name: The `source_name` parameter is the name of the job order for which the invoice
    needs to be created
    :param target_doc: The `target_doc` parameter is an optional parameter that specifies the target
    document for the invoice. It is used to specify the document where the invoice will be created. If
    no target document is specified, the invoice will be created as a new document
    :return: The function `make_invoice` returns the result of the `prepare_invoice` function if there
    are timesheets found for the given job order. Otherwise, it returns None.
    """
    try:
        company = frappe.db.get_value("User", frappe.session.user, "company")
        # check if timesheet already in sales invoice and timesheet submitted
        len_sql = f'''
            SELECT name, total_billable_amount, total_billable_hours, no_show, non_satisfactory, dnr
            FROM `tabTimesheet` where job_order_detail = '{source_name}'
            AND docstatus = 1 AND employee_company="{company}" AND is_check_in_sales_invoice = 0
            ORDER BY creation
        '''
        timesheet = frappe.db.sql(len_sql, as_dict=1)
        if len(timesheet) <= 0:
            frappe.msgprint(
                _(f"Either Invoice For Timesheet OR No Timesheet found for this Job Order(<b>{source_name}</b>)")
            )
        else:
            return prepare_invoice(company, source_name, timesheet)
    except Exception as e:
        frappe.msgprint(frappe.get_traceback())
        frappe.log_error(e, "make_invoice")

@frappe.whitelist()
def prepare_invoice(company, source_name, timesheet):
    """
    The function `prepare_invoice` prepares an invoice for a company based on a source name and
    timesheet data.
    
    :param company: The "company" parameter represents the name of the company for which the invoice is
    being prepared
    :param source_name: The `source_name` parameter is the name of the source document from which the
    invoice is being prepared. It is used to fetch relevant data from the source document and populate
    the invoice
    :param timesheet: The "timesheet" parameter is a list of timesheet objects. Each timesheet object
    represents a record of the time spent by an employee on a specific task or project. The timesheet
    object contains various fields such as the employee name, task description, start time, end time,
    billable hours
    :return: the prepared invoice document.
    """
    try:
        def customer_doc(source_name):
            return frappe.get_doc("Customer", {"name": source_name})
        
        def make_invoice(source_name, target_doc):
            return get_mapped_doc(
                ORD,
                source_name,
                {
                    ORD: {
                        "doctype": salesInvoice,
                        "validation": {"docstatus": ["=", 0]},
                    },
                    taxes: {"doctype": taxes, "add_if_empty": True},
                    team: {"doctype": team, "add_if_empty": True},
                    payment: {"doctype": payment, "add_if_empty": True},
                },
                target_doc,
                set_missing_values,
                ignore_permissions=True,
            )
        
        #Check all invoices in draft
        invoice_exist = frappe.get_all(
            salesInvoice,
            fields=["name"],
            filters={"job_order": source_name, "company": company, "status": "Draft"},
        )
        customer = customer_doc(company)
        if len(invoice_exist):
            doclist = frappe.get_doc(salesInvoice, invoice_exist[0]["name"])
        else:
            doclist = make_invoice(source_name, target_doc=None)
        doclist.posting_date = frappe.utils.nowdate()
        doclist.due_date = frappe.utils.add_to_date(frappe.utils.nowdate(), days=30)

        total_amount = 0
        total_hours = 0
        hiring_org_name = frappe.db.get_value(ORD, source_name, ["company"])
        comp_data_query = f'''
            SELECT default_income_account, cost_center, default_expense_account, address, city, state, zip, complete_address_billing,
            city_billing, state_billing, zip_billing, display_account_receivables_on_invoices, accounts_receivable_name, accounts_receivable_rep_email,
            accounts_receivable_phone_number, accounts_payable_contact_name,accounts_payable_email,accounts_payable_phone_number
            FROM tabCompany WHERE name IN ("{company}", "{hiring_org_name}") ORDER BY organization_type DESC
        '''
        comp_data = frappe.db.sql(comp_data_query, as_dict=1)

        income_account = comp_data[0]["default_income_account"]
        cost_center = comp_data[0]["cost_center"]
        default_expense_account = comp_data[0]["default_expense_account"]

        doclist.items = []
        doclist.timesheets = []
        timesheet_used = []
        for time in timesheet:
            timesheet_used.append(time.name)
            try:
                add(
                    "Timesheet", time.name, user=frappe.session.user, read=1, write=1, submit=1, notify=0, flags={"ignore_share_permission": 1}
                )
            except Exception:
                continue

            if time.no_show == 1:
                total_amount += 0
                total_hours += 0
            else:
                total_amount += time.total_billable_amount
                total_hours += time.total_billable_hours

            doclist = update_time_timelogs(time.name, doclist, time)
        doclist.timesheet_used = str(timesheet_used)
        doclist.total_billing_amount = total_amount
        doclist.total_billing_hours = total_hours
        # for company detail
        for_company_details(
            doclist,
            comp_data[0]
        )
        # for receiver details
        receiver_company_details(
            doclist,
            comp_data[1]
        )

        params = (hiring_org_name, company, hiring_org_name)
        # Execute the SQL query to fetch the premium value
        query = """
            SELECT COALESCE(
                (SELECT invoice_premium
                FROM `tabInvoice Premium`
                WHERE parent=%s AND staffing_company=%s),
                (SELECT invoice_premium
                FROM `tabInvoice Premium`
                WHERE parent=%s AND staffing_company='Default')
            )
        """
        premium_value = frappe.db.sql(query, params)
        doclist.invoice_premium = premium_value[0][0]
        doclist.total_billing_amount_premium = (total_amount if doclist.invoice_premium == 0 else total_amount + (total_amount * (doclist.invoice_premium / 100)))
        ts_details = f'''
            SELECT ttd.activity_type, TIME_FORMAT(ttd.start_time, "%H:%i") AS start_time, SUM(tt.total_billable_amount) AS total_amount, SUM(tt.total_billable_hours) AS total_hours
            FROM `tabTimesheet Detail` ttd inner join tabTimesheet tt ON tt.name = ttd.parent 
            WHERE tt.job_order_detail = "{source_name}" AND tt.workflow_state="Approved" AND tt.employee_company="{company}" AND tt.is_check_in_sales_invoice = 0
            GROUP BY ttd.activity_type, ttd.start_time
        '''
        timesheet_item = frappe.db.sql(ts_details, as_dict = 1)
        for item in timesheet_item:
            doclist.append("items", {
                "item_code":"",
                "item_name": item.activity_type,
                "start_time": item.start_time,
                "description": "Service",
                "uom": "Nos",
                "qty": 1,
                "stock_uom": "Nos",
                "conversion_factor": 1,
                "stock_qty": 1,
                "rate": item.total_amount,
                "amount": item.total_amount,
                "income_account": income_account,
                "cost_center": cost_center,
                "default_expense_account": default_expense_account
            })
        doclist.company = company

        set_missing_values(
            source_name, doclist, customer=customer, ignore_permissions=True
        )
        hiring_org_name = frappe.db.get_value(ORD, source_name, ["company"])
        doclist.customer = hiring_org_name
        doclist = merge_employee_data(doclist)
        if len(invoice_exist):
            doclist.save()
        return doclist
    except Exception as e:
        frappe.msgprint(frappe.get_traceback())
        frappe.log_error(e, "make_invoice")

@frappe.whitelist()
def update_time_timelogs(ts_name, doclist, time):
    """
    The function `update_time_timelogs` takes a timesheet name, a document list, and a time object as
    input, and updates the time logs in the timesheet with the corresponding values from the time
    object.
    
    :param ts_name: The parameter "ts_name" is the name of the Timesheet document that you want to
    update
    :param doclist: The `doclist` parameter is a list that will store the updated time logs. It is
    passed as an argument to the function and will be modified within the function to include the
    updated time logs
    :param time: The "time" parameter is an object that contains information about the time logs. It has
    the following attributes:
    :return: the updated `doclist` after adding the time logs from the specified timesheet (`ts_name`).
    """
    sheet = frappe.get_doc("Timesheet", ts_name)
    for logs in sheet.time_logs:
        start_time = ":".join(str(logs.start_time).split(" ").pop().split(":")[:-1]).rjust(5, "0")
        status = []
        if sheet.no_show:
            status.append("No Show")
        if sheet.non_satisfactory:
            status.append("Non Satisfactory")
        if sheet.dnr:
            status.append("DNR")
        if sheet.replaced:
            status.append("Replaced")
        if time.no_show == 1:
            # add zero all value in timesheet in invoice
            activity = {
                "activity_type": logs.activity_type,
                "start_time":start_time,
                "activity_type_time": f"{logs.activity_type} ({start_time})",
                "billing_amount": 0,
                "billing_hours": 0,
                "time_sheet": logs.parent,
                "from_time": logs.from_time,
                "to_time": logs.from_time,
                "description": sheet.employee,
                "employee_name": sheet.employee_name,
                "status": ", ".join(status),
                "overtime_rate": 0,
                "overtime_hours": 0,
                "per_hour_rate1": 0,
                "flat_rate": 0,
            }
        else:
            activity = {
                "activity_type": logs.activity_type,
                "start_time": start_time,
                "activity_type_time": f"{logs.activity_type} ({start_time})",
                "billing_amount": logs.billing_amount,
                "billing_hours": logs.billing_hours,
                "time_sheet": logs.parent,
                "from_time": logs.from_time,
                "to_time": logs.to_time,
                "description": sheet.employee,
                "employee_name": sheet.employee_name,
                "status": ", ".join(status),
                "overtime_rate": logs.extra_rate,
                "overtime_hours": logs.extra_hours,
                "per_hour_rate1": logs.billing_rate,
                "flat_rate": logs.flat_rate,
            }
        doclist.append("timesheets", activity)
    return doclist

@frappe.whitelist()
def for_company_details(doclist, comp_data):
    """
    The function `for_company_details` sets various attributes of a `doclist` object based on the values
    in the `comp_data` dictionary.
    
    :param doclist: doclist is an object that represents a document or a list of documents. It is used
    to store and manipulate data related to a company's details
    :param comp_data: The comp_data parameter is a dictionary that contains various details about a
    company. Here are the keys and their corresponding values:
    """
    if comp_data["display_account_receivables_on_invoices"] and comp_data["complete_address_billing"]:
        doclist.creater_company = comp_data["complete_address_billing"]
        doclist.creater_city = comp_data["city_billing"]
        doclist.creater_state = comp_data["state_billing"]
        doclist.creater_zip = comp_data["zip_billing"]
    else:
        doclist.creater_company = comp_data["address"]
        doclist.creater_city = comp_data["city"]
        doclist.creater_state = comp_data["state"]
        doclist.creater_zip = comp_data["state"]

    if comp_data["display_account_receivables_on_invoices"]:
        if len(comp_data["accounts_receivable_name"]):
            doclist.accounts_receivable_name = comp_data["accounts_receivable_name"]
        if len(comp_data["accounts_receivable_rep_email"]):
            doclist.accounts_receivable_rep_email = comp_data["accounts_receivable_rep_email"]
        if len(comp_data["accounts_receivable_phone_number"]):
            doclist.accounts_receivable_phone_number = comp_data["accounts_receivable_phone_number"]


@frappe.whitelist()
def receiver_company_details(doclist, comp_data):
    """
    The function `receiver_company_details` sets the company details for a document based on the
    provided company data.
    
    :param doclist: doclist is an object that contains various attributes and properties related to a
    document. It is used to store and retrieve information about the document
    :param comp_data: The comp_data parameter is a dictionary that contains the company details. It has
    the following keys:
    """
    if comp_data["display_account_receivables_on_invoices"] and comp_data["complete_address_billing"]:
        doclist.for_company = comp_data["complete_address_billing"]
        doclist.for_company_city = comp_data["city_billing"]
        doclist.for_company_state = comp_data["state_billing"]
        doclist.for_company_zip = comp_data["zip_billing"]
    else:
        doclist.for_company = comp_data["address"]
        doclist.for_company_city = comp_data["city"]
        doclist.for_company_state = comp_data["state"]
        doclist.for_company_zip = comp_data["zip"]

    if comp_data["display_account_receivables_on_invoices"]:
        if len(comp_data["accounts_payable_contact_name"]):
            doclist.accounts_payable_contact_name = comp_data["accounts_payable_contact_name"]
        if len(comp_data["accounts_payable_email"]):
            doclist.accounts_payable_email = comp_data["accounts_payable_email"]
        if len(comp_data["accounts_payable_phone_number"]):
            doclist.accounts_payable_phone_number = comp_data["accounts_payable_phone_number"]


@frappe.whitelist()
def set_missing_values(source, target, customer=None, ignore_permissions=True):
    """
    The function sets missing values in the target object based on the source object, with optional
    customer information and permission settings.
    
    :param source: The source object from which the missing values will be copied
    :param target: The target parameter is an object that represents the entity or record that we want
    to set missing values for
    :param customer: The customer parameter is an optional parameter that represents a customer object.
    If a customer object is provided, the function will set the customer name and customer name
    attributes of the target object to the corresponding values from the customer object
    :param ignore_permissions: The `ignore_permissions` parameter is a boolean value that determines
    whether to ignore permission checks when setting missing values. If set to `True`, permission checks
    will be ignored. If set to `False`, permission checks will be performed, defaults to True (optional)
    """
    if customer:
        target.customer = customer.name
        target.customer_name = customer.customer_name
    target.ignore_pricing_rule = 1
    target.flags.ignore_permissions = ignore_permissions
    target.run_method("set_missing_values")
    target.run_method("calculate_taxes_and_totals")


@frappe.whitelist()
def merge_employee_data(doclist):
    """
    The function `merge_employee_data` merges employee data from timesheets into a document list.
    
    :param doclist: The `doclist` parameter is a document list object that contains employee data. It is
    assumed to have a property called `timesheets` which is a list of timesheet objects
    :return: the updated `doclist` object.
    """
    try:
        items = []
        if doclist.timesheets:
            employees = get_timesheet_employees(doclist.timesheets)
            for e in employees:
                ts_details = get_ts_details(doclist, e)
                print(ts_details)
                items.append(ts_details)

        if items:
            doclist.timesheets = []
            for i in items:
                doclist.append("timesheets", i)
        return doclist
    except Exception as e:
        frappe.msgprint(e)


@frappe.whitelist()
def get_timesheet_employees(items):
    """
    The function `get_timesheet_employees` takes a list of items and returns a list of unique employees
    based on their activity type and description.
    
    :param items: The `items` parameter is a list of objects representing activities in a timesheet.
    Each object has the following attributes:
    :return: a list of unique employee names with their activity type and description.
    """
    try:
        employees = []
        for i in items:
            if f"{i.activity_type_time}_{i.description}" not in employees:
                employees.append(f"{i.activity_type_time}_{i.description}")
        return employees
    except Exception as e:
        frappe.msgprint(e)


@frappe.whitelist()
def get_ts_details(doclist, e):
    """
    The function `get_ts_details` takes a list of documents and an activity type as input, and returns a
    dictionary containing details related to that activity type.
    
    :param doclist: The `doclist` parameter is a list of documents that contains timesheet information.
    Each document in the list represents a timesheet entry
    :param e: The parameter "e" is a string that represents the activity type and description of a
    timesheet entry. It is used to filter the timesheet entries in the "doclist" and retrieve the
    details of the matching entry
    :return: a dictionary with various details related to a timesheet entry.
    """
    bill_amount, bill_hours, overtime_rate, overtime_hours, per_hr_rate, flat_rate = (0, 0, 0, 0, 0, 0)
    timesheet, employee_name, activity_type, status, start_time, from_time, to_time  = "", "", "", [], "", datetime.today(), datetime(1999, 12, 12, 12, 12, 12)
    for item in doclist.timesheets:
        if f"{item.activity_type_time}_{item.description}"==e:
            bill_amount += item.billing_amount
            bill_hours += item.billing_hours
            overtime_hours += item.overtime_hours
            overtime_rate = item.overtime_rate
            per_hr_rate = item.per_hour_rate1
            flat_rate = item.flat_rate
            timesheet = item.time_sheet
            employee_name = item.employee_name
            activity_type = item.activity_type
            start_time = item.start_time
            from_time = item.from_time if item.from_time < from_time else from_time
            to_time = item.to_time if item.to_time > to_time else to_time
            if item.status:
                status.append(item.status)
    if len(status) == 0:
        status.append("-")
    return {
        "activity_type": activity_type,
        "start_time": start_time,
        "activity_type_time": f"{activity_type} ({start_time})",
        "billing_amount": bill_amount,
        "billing_hours": bill_hours,
        "time_sheet": timesheet,
        "from_time": from_time,
        "to_time": to_time,
        "description": e.split("_")[1],
        "employee_name": employee_name,
        "status": ", ".join(list(set(status))),
        "overtime_rate": overtime_rate,
        "overtime_hours": overtime_hours,
        "per_hour_rate1": per_hr_rate,
        "flat_rate": flat_rate,
    }


@frappe.whitelist()
def make_notes(company):
    try:
        doc=frappe.get_doc("Company",company)
        l=[doc.drug_screen,doc.background_check,doc.shovel,doc.mvr]
        return l
    except Exception as e:
        frappe.msgprint(frappe.get_traceback())
        frappe.log_error(e, 'job order company')


@frappe.whitelist()
def get_company_details(comp_name):
    try:
        company_doc=frappe.get_doc('Company',comp_name)
        if not frappe.has_permission(company_doc, "read", throw=False):
            '''#user_details=frappe.db.get_all('User Permission', filters={'user': frappe.session.user,'allow':'Company','for_value':comp_name,'applicable_for':ORD}, fields={'name'})'''
            user_details = frappe.db.sql(f'''select name from `tabUser Permission` where user="{frappe.session.user}" and allow="Company" and for_value="{comp_name}" and applicable_for="{ORD}"''')
            if not user_details:
                frappe.local.response['http_status_code'] = 500
                frappe.throw('Insufficient Permission for Company ' + comp_name)
        company_details=frappe.db.get_all('Company', filters={'name': comp_name}, fields={'name','organization_type','address','state' ,'city' ,'phone_no'})
        if company_details:
            return company_details[0]
    except Exception as e:
        frappe.log_error(e, 'Job order list')
        return []
    

@frappe.whitelist(allow_guest=False)
def get_joborder_value(user, company_type, name):
    try:
        jo_doc=frappe.get_doc(ORD,name)
        if not jo_doc.has_permission("read"):
            frappe.local.response['http_status_code'] = 500
            frappe.throw(_('Insufficient Permission for Job Order '+name))
        if(company_type and company_type in ["Staffing", "Hiring", "TAG", "Exclusive Hiring"] and frappe.session.user and user and user == frappe.session.user and name):
            sql = ''' select name,from_date,to_date,job_order_duration,job_site,total_no_of_workers from `tabJob Order` where name = "{0}" '''.format(name)
            value = frappe.db.sql(sql,as_dict=True)
            if value:
                return value[0]
        else:
            return "No Access"
    except Exception as e:
        print(e)
        frappe.log_error(str(e)+','+name+',session user-'+frappe.session.user+','+company_type+',user-'+user, 'Job order list popup')
        return 'error_occur'
        
@frappe.whitelist()
def selected_days(doctype, txt, searchfield, page_len, start, filters):
   days="select name from `tabDays` order by creation desc"
   data=frappe.db.sql(days)
   return data

@frappe.whitelist(allow_guest=False)
def order_details():
    current_user=frappe.session.user
    sql=f'''select distinct company from `tabJob Order` where name in (select distinct share_name from `tabDocShare` where user='{current_user}' and share_doctype='{doc_name_job_order}') '''
    dat=frappe.db.sql(sql,as_dict=1)
    company_data = [c['company'] for c in dat]
    comp_dat="\n".join(company_data)
    return comp_dat

@frappe.whitelist(allow_guest=False)
def data_deletion(job_order):
    try:
        sales_invoice_date=f"select name from `tabSales Invoice` where job_order='{job_order}' "
        invoice=frappe.db.sql(sales_invoice_date,as_list=True)
        if len(invoice)>0:
            for i in invoice:
                del_data=f'''DELETE FROM `tabSales Invoice` where name="{i[0]}" '''
                frappe.db.sql(del_data)
                frappe.db.commit()
        timesheet_data=f"select name from `tabTimesheet` where job_order_detail='{job_order}'"
        timesheet=frappe.db.sql(timesheet_data,as_list=True)
        if len(timesheet)>0:
            for i in timesheet:
                del_data=f'''DELETE FROM `tabTimesheet` where name="{i[0]}" '''
                frappe.db.sql(del_data)
                frappe.db.commit()
        assigned_emp=f"select name from `tabAssign Employee` where job_order='{job_order}'"
        assign_emp=frappe.db.sql(assigned_emp,as_list=True)
        if len(assign_emp)>0:
            for i in assign_emp:
                del_data=f'''DELETE FROM `tabAssign Employee` where name="{i[0]}" '''
                frappe.db.sql(del_data)
                frappe.db.commit()
        claim_order=f"select name from `tabClaim Order` where job_order='{job_order}'"
        claims=frappe.db.sql(claim_order,as_list=True)
        if len(claims)>0:
            for i in claims:
                del_data=f'''DELETE FROM `tabClaim Order` where name="{i[0]}" '''
                frappe.db.sql(del_data)
                frappe.db.commit()
        del_data=f'''DELETE FROM `tabJob Order` where name="{job_order}" '''
        frappe.db.sql(del_data)
        frappe.db.commit()
        free_redis(job_order)
        return 'success'
    except Exception as e:
        frappe.log_error(e, 'Some Deletion error')

@frappe.whitelist()
def get_industry_type_list(doctype, txt, searchfield, page_len, start, filters):
    company=filters.get('job_order_company')
    if company is None:
        return None
    else:
        sql = ''' select industry_type from `tabIndustry Types` where parent = '{0}' and industry_type like "%%{1}%%"'''.format(company, '%s' % txt)
        return frappe.db.sql(sql)



@frappe.whitelist()
def get_redirect_doc(company, name):
    try:
        docname = frappe.db.get_value("Assign Employee", {"job_order": name, "company": ['in', tuple(json.loads(company))]}, "name")
        return docname
    except Exception as e:
        frappe.msgprint(e)
@frappe.whitelist()
def claim_data_list(job_order_name=None,exist_comp=None):
    try:
        data = []
        sql = """ select staff_org_claimed from `tabJob Order` where name='{0}' """.format(job_order_name)
        companies = frappe.db.sql(sql, as_dict=1)
        company=companies[0].staff_org_claimed
        data=company.split("~")
        comp_data=[]
        if exist_comp:
            for c in data:
                if c not in exist_comp:
                    comp_data.append(c)
        else:
            comp_data = [c for c in data]
        return "\n".join(comp_data)
    except Exception as e:
        print(e)
        return []

@frappe.whitelist()
def hiring_diff_status(job_order_name):
    doc=frappe.get_doc(doc_name_job_order,job_order_name)
    sql=f'select docstatus from `tabSales Invoice` where job_order="{job_order_name}"'
    invoice_comp_data=frappe.db.sql(sql,as_list=1)
    if(len(invoice_comp_data)>0 and doc.order_status=='Completed'):
        for i in invoice_comp_data:
            if i[0]==0:
                break
        else:
            return 'Completed'

    sql=f'select name from `tabSales Invoice` where job_order="{job_order_name}" and docstatus=1'
    invoice_data=frappe.db.sql(sql,as_list=1)
    if(len(invoice_data)>0):
        return 'Invoice'
    sql=f'select name from `tabTimesheet` where job_order_detail="{job_order_name}" and workflow_state="Denied" '
    timesheet_data=frappe.db.sql(sql,as_list=1)
    if(len(timesheet_data)>0):
        return 'Timesheet'

@frappe.whitelist()
def no_of_workers_changed(doc_name):
    change = frappe.db.sql('''SELECT data FROM `tabVersion` WHERE docname = "{0}"'''.format(doc_name), as_dict = True)
    if len(change) > 2:
        data = frappe.db.sql('''SELECT data FROM `tabVersion` WHERE docname = "{0}" ORDER BY modified DESC'''.format(doc_name), as_list = True)
        new_data = json.loads(data[0][0])
        if(new_data['changed'] and new_data['changed'][0][0] == 'total_no_of_workers'):
            frappe.db.sql('''UPDATE `tabClaim Order` SET no_of_workers_joborder = "{0}" WHERE job_order = "{1}"'''.format(new_data['changed'][0][2], doc_name))
            frappe.db.commit()
            sql = '''SELECT name, no_of_workers_joborder, staff_claims_no FROM `tabClaim Order` WHERE job_order = "{0}"'''.format(doc_name)
            result = frappe.db.sql(sql, as_list = True)
            for i in result:
                if i[1] < i[2]:
                    frappe.db.sql('''UPDATE `tabClaim Order` SET staff_claims_no = "{0}" WHERE name = "{1}"'''.format(i[2]+(i[1]-i[2]), i[0]))
                    frappe.db.commit()
            change_assigned_emp(doc_name, new_data)

@frappe.whitelist()
def change_assigned_emp(doc_name, new_data=None):
    if new_data == None:
        data = frappe.db.sql('''SELECT data FROM `tabVersion` WHERE docname="{0}" ORDER BY modified DESC'''.format(doc_name), as_list = True)
        new_data = json.loads(data[0][0])
    if new_data['changed'] and new_data['changed'][0][0] == 'total_no_of_workers':
        assign_emp = frappe.db.sql('''SELECT name FROM `tabAssign Employee` WHERE job_order="{0}"'''.format(doc_name), as_list=True)
        for name in assign_emp:
            frappe.db.sql('''UPDATE `tabAssign Employee` SET no_of_employee_required = "{0}" WHERE name="{1}"'''.format(new_data['changed'][0][2],name[0]))
            frappe.db.commit()


@frappe.whitelist()
def submit_headcount(job_order, job_titles):
    """
    The function takes a job order and job titles as input, retrieves data from the database, and
    returns a list of dictionaries containing information about the job titles and their corresponding
    headcounts.
    
    :param job_order: The job order is a string parameter that represents the name or identifier of a
    job order. It is used to retrieve data related to the job order from the database
    :param job_titles: The `job_titles` parameter is a JSON string containing information about job
    titles, their start times, estimated hours per day, number of workers required, and billing rates
    :return: a list of dictionaries containing information about job titles, including the job title,
    start time, duration, number of workers specified in the job order, number of remaining employees,
    approved number of workers, and bill rate.
    """
    try:
        data = json.loads(job_titles)
        result = []
        claims = f"""
            SELECT MT.job_title, MT.start_time, IFNULL(SUM(MT.approved_no_of_workers),0) AS approved
            FROM `tabMultiple Job Title Claim` AS MT,
            `tabClaim Order` AS CO
            WHERE CO.name = MT.parent AND CO.job_order="{job_order}"
            GROUP BY MT.start_time, MT.job_title
        """
        claim_data = frappe.db.sql(claims, as_list=1)
        for row in data:
            rows = {}
            rows['job_title'] = row['select_job']
            rows['industry'] = row['category']
            rows['start_time'] = row['job_start_time']
            rows['duration'] = row['estimated_hours_per_day']
            rows['no_of_workers_joborder'] = row['no_of_workers']
            if not claim_data:
                rows["no_of_remaining_employee"] = int(row["no_of_workers"])
                rows["approved_no_of_workers"] = 0
            else:
                for claim in claim_data:
                    job_start_time = datetime.strptime(row["job_start_time"], "%H:%M:%S")
                    job_start_time = timedelta(hours=job_start_time.hour, minutes=job_start_time.minute, seconds=job_start_time.second)
                    if claim[0] == row["select_job"] and claim[1] == job_start_time and claim[2] is not None:
                        rows["no_of_remaining_employee"] = int(row["no_of_workers"]) - int(claim[2])
                        rows["approved_no_of_workers"] = int(claim[2]) or 0
            rows['bill_rate'] = round(row["per_hour"] + row["flat_rate"], 2)
            result.append(rows)
        return result
    except Exception:
        print(frappe.get_traceback())


@frappe.whitelist()
def claim_headcount(job_order):
    sql = '''SELECT ifnull(sum(approved_no_of_workers),0) from `tabClaim Order` where job_order = "{0}"'''.format(job_order)
    res = frappe.db.sql(sql, as_list = True)
    return res[0][0]

@frappe.whitelist()
def assigned_emp_comp(job_order):
    sql = '''SELECT company from `tabAssign Employee` where job_order = "{0}"'''.format(job_order)
    res = frappe.db.sql(sql, as_list = True)
    return [element for innerList in res for element in innerList]
@frappe.whitelist()
def check_order_already_exist(frm):    
    try:
        data=json.loads(frm)
        query_condition = ""
        for i in range(len(data['multiple_job_titles'])):
            if data['multiple_job_titles'][i].get('select_job'):
                query_condition += f''' (multi.select_job="{data['multiple_job_titles'][i]['select_job']}" and multi.category="{data['multiple_job_titles'][i]['category']}") '''
                if i!=(len(data['multiple_job_titles'])-1):
                    query_condition+= " or"
        if query_condition:
            query_condition = f'''and ({query_condition})'''
        company=data['company']
        job_site=data['job_site']
        start_date=data['from_date']
        end_date=data['to_date']
        check_data_base=f'''select jo.name as name,jo.job_site ,jo.from_date ,jo.to_date,multi.category,multi.select_job from `tabJob Order` jo left join `tabMultiple Job Titles` multi on multi.parent = jo.name where 
                            company="{company}" and jo.order_status!="completed" 
                            and jo.job_site="{job_site}" 
                            and ((jo.from_date between "{start_date}" and "{end_date}") 
                            or (jo.to_date between "{start_date}" and "{end_date}")) 
                            {query_condition} group by jo.name'''
        data_exist=frappe.db.sql(check_data_base,as_dict=1)
        if(data_exist):
            '''# l=[]
            # for i in data_exist:
            #     l.append(i['name'])'''
            l=[i['name'] for i in data_exist]
            s = ", ".join(l)
            return l,s
        else:
            return 1
    except Exception as e:
        frappe.error_log(e,'Check same order') 
@frappe.whitelist()
def my_used_job_orders(company_name,status):
    my_aval_claims=[]
    z=[]
    unclaimed_noresume_by_company=[]
    if status=='All':
        my_claims,unclaimed_noresume_by_company=all_orders_data(company_name)
        '''# for i in my_claims:
        #     z.append(i[0])'''
        z=[i[0] for i in my_claims]
        '''# if(len(my_aval_claims)>0):
        #     for i in my_aval_claims:
        #         z.append(i[0])'''
        if(len(unclaimed_noresume_by_company)>0):
            '''# for i in unclaimed_noresume_by_company:
            #     z.append(i)'''
            z.extend(unclaimed_noresume_by_company)
        return list(set(z)) 
        
    elif status=='Available':
        unclaimed_resume_by_comp=f'select name from `tabJob Order` where (claim not like "%{company_name}%" or claim is Null) and order_status!="Completed" and resumes_required=1 and total_workers_filled!=total_no_of_workers'
        my_aval_claims=frappe.db.sql(unclaimed_resume_by_comp,as_list=1)
        my_claims=check_avail(company_name,unclaimed_noresume_by_company)
        for i in my_claims:
            z.append(i)
        if(len(my_aval_claims)>0):
            for i in my_aval_claims:
                z.append(i[0])
    else:
        l=f'select name from `tabJob Order` where claim like "%{company_name}%" and order_status="{status}"'
        my_claims=frappe.db.sql(l,as_list=1)
    
        for i in my_claims:
            z.append(i[0])
        '''# if(len(my_aval_claims)>0):
        #     for i in my_aval_claims:
        #         z.append(i[0])
    # if(len(unclaimed_noresume_by_company)>0):
    #     # for i in unclaimed_noresume_by_company:
    #     #     z.append(i)
    #     z.extend(unclaimed_noresume_by_company)'''
    return list(set(z)) 
@frappe.whitelist()
def claims_left(name,comp):
    data=frappe.get_doc(ORD,name)
    if(data.order_status=='Completed'):
        return "success"
    else:
        if(data.resumes_required==1):
            if(data.total_no_of_workers!=data.total_workers_filled):
                return data.total_no_of_workers-data.total_workers_filled
            else:
                return '0'
        else:
            claims=f'select sum(approved_no_of_workers) from `tabClaim Order` where job_order="{name}"'
            data1=frappe.db.sql(claims,as_list=1)
            d=data_receive(data1,data)
            return d
def all_orders_data(company_name):
    '''# my_aval_claims=[]'''
    unclaimed_noresume_by_company=[]
    l=f'select name from `tabJob Order` where claim like "%{company_name}%"  or ((claim not like "%{company_name}%" or claim is Null) and order_status!="Completed" and resumes_required=1 and total_workers_filled!=total_no_of_workers)'
    my_claims=frappe.db.sql(l,as_list=1)
    '''# unclaimed_resume_by_comp=f'select name from `tabJob Order` where (claim not like "%{company_name}%" or claim is Null) and order_status!="Completed" and resumes_required=1 and worker_filled!=no_of_workers'
    # my_aval_claims=frappe.db.sql(unclaimed_resume_by_comp,as_list=1)'''
    unclaimed_noresume_by_company=check_avail(company_name,unclaimed_noresume_by_company)
    return my_claims,unclaimed_noresume_by_company

def check_avail(company_name,unclaimed_noresume_by_company):
    '''# unclaimed_noresume_by_comp=f'select name from `tabJob Order` where (claim not like "%{company_name}%" or claim is Null) and order_status!="Completed" and resumes_required=0'
    # my_unaval_claims=frappe.db.sql(unclaimed_noresume_by_comp,as_list=1)
    # print(unclaimed_noresume_by_comp,my_unaval_claims,"= "*500)
    # for i in my_unaval_claims:
    #     data=frappe.get_doc(ORD,i[0])
    #     claims=f'select sum(approved_no_of_workers) from `tabClaim Order` where job_order="{data.name}"'
    #     data1=frappe.db.sql(claims,as_list=1)
    #     print(data1, " & "*500)
    #     if(data1[0][0]!=None):
    #         if int(data.no_of_workers)-int(data1[0][0])>0:
    #             unclaimed_noresume_by_company.append(data.name)
    #     else:
    #         unclaimed_noresume_by_company.append(data.name)'''
    print(unclaimed_noresume_by_company)
    unclaimed_noresume_by_comp=f'select jo.name,jo.total_no_of_workers ,cl.approved_no_of_workers as app from `tabJob Order` jo left join `tabClaim Order` cl on jo.name = cl.job_order where (claim not like "%{company_name}%" or claim is Null) and order_status!="Completed" and resumes_required=0 group by jo.name having cl.approved_no_of_workers is null or jo.total_no_of_workers > sum(cl.approved_no_of_workers)'
    my_unaval_claims=frappe.db.sql(unclaimed_noresume_by_comp,as_list=1)
    unclaimed_noresume_by_company_updated = [d[0] for d in my_unaval_claims]
    return unclaimed_noresume_by_company_updated

@frappe.whitelist()
def no_of_claims(job_order):
    doc=frappe.get_doc(ORD,job_order)
    if(doc.resumes_required==1):
        sql = '''SELECT COUNT(name) FROM `tabAssign Employee` WHERE job_order = "{0}"'''.format(job_order)
    else:
        sql = '''SELECT COUNT(name) FROM `tabClaim Order` WHERE job_order = "{0}"'''.format(job_order)
    no_of_claims = frappe.db.sql(sql, as_list=1)
    return no_of_claims[0][0]

@frappe.whitelist()
def claim_order_updated_by(docname,staff_company):
    try:
        claims=f'select name from `tabClaim Order` where job_order="{docname}" and staffing_organization="{staff_company}" order by name desc'
        data = frappe.db.sql(claims, as_dict=1)
        if data:
            claims_versin=f"select owner from `tabVersion` where docname='{data[0]['name']}' order by modified DESC;"
            claims_updater=frappe.db.sql(claims_versin,as_dict=1)
            if claims_updater:
                for j in claims_updater:
                    user_type = frappe.db.get_value('User', {"name": j['owner']}, ['organization_type'])
                    if user_type == 'Hiring':
                        return 'headcount_selected'
                return 'headcount_not_selected'

    except Exception as e:
        frappe.log_error(e, 'Claim order Error')
        print(e, frappe.get_traceback())

@frappe.whitelist()
def check_increase_headcounts(no_of_workers_updated,name,company):
    no_of_workers_updated = json.loads(no_of_workers_updated)
    sql = f'''select jo.is_single_share,jo.staff_company,multi.no_of_workers,jo.job_site,jo.claim,multi.select_job from `tabJob Order` jo 
    left join `tabMultiple Job Titles` multi on multi.parent = jo.name where jo.name="{name}"'''
    old_headcounts = frappe.db.sql(sql, as_dict=1)

    for i in old_headcounts:
        old_no_of_workers = i.no_of_workers
        select_job = i.select_job
        new_no_of_workers = no_of_workers_updated.get(select_job)

        if new_no_of_workers and int(new_no_of_workers) > old_no_of_workers:
            subject = jobOrder
            link = f'href="{sitename}/app/job-order/{name}"'
            msg = f'{company} has increased the number of requested employees to {new_no_of_workers} on {name}.'
            sql = """select organization_type from `tabCompany` where name='{}' """.format(
                        company
                    )
            org_type = frappe.db.sql(sql, as_list=1)
            if i.is_single_share:
                sql = f'''select email from `tabUser` where organization_type="staffing" and enabled="1" and company="{i.staff_company}"'''
                share_list = frappe.db.sql(sql, as_list=True)
                share_user_list = [user[0] for user in share_list]
                job_order_app, job_order_mail = get_mail_list(share_user_list, app_field=jo_modify_app, mail_field=jo_modify_mail)
                make_system_notification(job_order_app, msg, doc_name_job_order, name, subject)
                joborder_email_template(subject, msg, job_order_mail, link)
            elif org_type[0][0] == "Exclusive Hiring":
                own_sql = """ select owner from `tabCompany` where organization_type="Exclusive Hiring" and name="{}" """.format(
                    company
                )
                owner_info = frappe.db.sql(own_sql, as_list=1)

                com_sql = """ select company from `tabUser` where name='{0}' and enabled="1" """.format(
                    owner_info[0][0]
                )
                company_info = frappe.db.sql(com_sql, as_list=1)

                usr_sql = """ select user_id from `tabEmployee` where company='{}' and user_id IS NOT NULL """.format(
                    company_info[0][0]
                )
                share_list = frappe.db.sql(usr_sql, as_list=1)

                share_user_list = [user[0] for user in share_list]
                job_order_app, job_order_mail = get_mail_list(share_user_list, app_field=jo_modify_app, mail_field=jo_modify_mail)
                make_system_notification(job_order_app, msg, doc_name_job_order, name, subject)
                joborder_email_template(subject, msg, job_order_mail, link)
            else:
                sql = f'''select email from `tabUser` where organization_type="staffing" and enabled="1" and 
                company in (select staffing_company from `tabStaffing Radius` 
                where job_site="{i.job_site}" and radius != "None" and radius <= 25 and hiring_company="{company}")'''
                if i.staff_company and i.claim and i.staff_company in i.claim.split('~'):
                    sql += f''' or company="{i.staff_company}"'''
                share_list = frappe.db.sql(sql, as_list=True)
                share_user_list = [user[0] for user in share_list]
                job_order_app, job_order_mail = get_mail_list(share_user_list, app_field=jo_modify_app, mail_field=jo_modify_mail)
                make_system_notification(job_order_app, msg, doc_name_job_order, name, subject)
                joborder_email_template(subject, msg, job_order_mail, link)


@frappe.whitelist()
def change_is_single_share(bid,name):
    sql = f'''select is_single_share from `tabJob Order` where name="{name}"'''
    iss = frappe.db.sql(sql, as_list=1)
    if iss:
        is_single_share = iss[0][0]
        return is_single_share
      
@frappe.whitelist()
def workers_required_order_update(doc_name):
    try:
        claim_data=f''' select name,staffing_organization,no_of_workers_joborder,staff_claims_no,approved_no_of_workers from `tabClaim Order` where job_order="{doc_name}" and staffing_organization in (select company from `tabAssign Employee` where job_order="{doc_name}" and tag_status="Approved")'''
        claims=frappe.db.sql(claim_data,as_dict=True)
        if len(claims)==0:
            claim_data=f''' select name,staffing_organization,no_of_workers_joborder,staff_claims_no,approved_no_of_workers from `tabClaim Order` where job_order="{doc_name}"'''
            claims=frappe.db.sql(claim_data,as_dict=True)
        return claims
    except Exception as e:
        print(e,frappe.get_traceback())
        frappe.db.rollback()
@frappe.whitelist()
def update_new_claims(my_data,doc_name):
    try:
        claims_id=[]
        my_data=json.loads(my_data)
        for key in my_data:
            claims_id.append(key)
        if claims_id:
            for i in claims_id:
                if isinstance(my_data[i]['approve_count'], int):
                    doc=frappe.get_doc('Claim Order',i)
                    data=claim_comp_assigned(doc_name,doc,my_data[i]['approve_count'])
                    if(data==0):
                        return 0
                    else:                           
                        doc.approved_no_of_workers=my_data[i]["approve_count"]
                        doc.save(ignore_permissions=True)
            return 1
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.db.rollback()

def claim_comp_assigned(doc_name,doc,claimed_approved):
    assined_emp=frappe.db.sql('select name from `tabAssign Employee` where job_order="{0}" and company="{1}"'.format(doc_name,doc.staffing_organization),as_dict=1)
    if(len(assined_emp)>0):
        count=frappe.db.sql('select count(name) from `tabAssign Employee Details` where parent="{0}" and remove_employee=0'.format(assined_emp[0]['name']),as_list=1)
        if doc.approved_no_of_workers<count[0][0]:
            frappe.msgprint(doc.staffing_organization+' has assigned all of their claims. An employee must be removed from this job order to by '+doc.staffing_organization+' before their claim can be modified.')
            return 0
        elif(int(claimed_approved)!=count[0][0]):
            frappe.msgprint("The number of assigned claims does not match the new required head count of "+str(claimed_approved))
            return 0
        else:
            return 1

@frappe.whitelist()
def validate_company(doc,method):
    user_doc = frappe.get_doc('User', frappe.session.user)
    if doc.is_new() and user_doc.organization_type == 'Staffing' and doc.company:
        company_doc = frappe.get_doc('Company', doc.company)
        if company_doc.organization_type!='Exclusive Hiring':
            frappe.throw('Insufficient Permission to create Job Order')
    
def data_receive(data1,data):
    if(data1[0][0]!=None):
        if(int(data.no_of_workers)-int(data1[0][0])>0):
            return str(int(data.no_of_workers)-int(data1[0][0]))
        else:
            return str(0)
    else:
        return int(data.no_of_workers)


@frappe.whitelist()
def repeat_no_of_workers(job_order,staff_comp,no_of_worker):
    try:
        staff=staff_comp.split('~')
        if len(staff)>1:
            approved_worker = frappe.db.sql(f'''SELECT SUM(approved_no_of_workers) from `tabClaim Order` where job_order="{job_order}" and staffing_organization in {tuple(staff)}''', as_list=1)
        else:
            approved_worker = frappe.db.sql(f'''SELECT SUM(approved_no_of_workers) from `tabClaim Order` where job_order="{job_order}" and staffing_organization in ("{staff[0]}")''', as_list=1)
        return "failed" if approved_worker[0][0] and approved_worker[0][0] > float(no_of_worker) else "success"
    except Exception as e:
        print(e, frappe.get_traceback())

def update_total_worker_filled(key, worker_filled_job_title):
    worker_filled_job_title[key] = worker_filled_job_title[key]+1 if key in worker_filled_job_title else 1
    return worker_filled_job_title

@frappe.whitelist(allow_guest=False)
def cancel_job_order(job_order, user, approved_claims=None):
    try:
        job_order_doc = frappe.get_doc(ORD, job_order)
        user_type = frappe.db.sql(f"select organization_type from tabUser where name = '{user}'")
        perm_error=False
        if job_order_doc.company_type == "Exclusive":
            owner_company = frappe.get_value("User", job_order_doc.owner, "company")

            query = '''
                SELECT COUNT(name)
                FROM `tabUser`
                WHERE (company = %s OR company = %s) AND name = %s
            '''

            result = frappe.db.sql(query, (owner_company, job_order_doc.company, user.name))

            if not result[0][0]:
                perm_error = True
        if not frappe.has_permission(job_order_doc, "read", throw=False) or user!=frappe.session.user or (job_order_doc.company_type == "Non Exclusive" and user_type[0][0] != "Hiring") or perm_error:
            frappe.throw("Insufficient Permission for user "+user)

        job_order_doc.order_status = "Canceled"
        job_order_doc.cancellation_date = datetime.today().date()
        job_order_doc.save(ignore_permissions = True)

        frappe.db.sql(f'''UPDATE `tabClaim Order` SET job_order_status="Canceled" WHERE job_order="{job_order}"''')
        frappe.db.sql(f'''UPDATE `tabAssign Employee` SET job_order_status="Canceled" WHERE job_order="{job_order}"''')
        frappe.db.commit()
        if approved_claims:
            if not job_order_doc or job_order_doc.staff_org_claimed != approved_claims:
                frappe.throw("Invalid Parameter")
            
            msg = f'Job Order {job_order} has been canceled.'
            subject = 'Job Order Canceled'
            sql = f'''
                SELECT name
                FROM `tabUser`
                WHERE enabled = 1
                    AND company IN (
                        SELECT staffing_organization
                        FROM `tabClaim Order`
                        WHERE job_order = "{job_order}"
                            AND approved_no_of_workers > 0
                    )
            ''' if job_order_doc.resumes_required == 0 else f'''
                SELECT name
                FROM `tabUser`
                WHERE enabled = 1
                    AND company IN (
                        SELECT company
                        FROM `tabAssign Employee` tae
                        WHERE job_order = "{job_order}"
                            AND tag_status="Approved"
                    )
            '''
            staffing_list = [user[0] for user in frappe.db.sql(sql)]
            if staffing_list:
                staffing_list_app, staffing_list_mail = get_mail_list(list(set(staffing_list)),app_field=jo_modify_app,mail_field=jo_modify_mail)
                make_system_notification(staffing_list_app, message = msg, doctype = ORD, docname =  job_order, subject = subject)
                sendmail(emails = staffing_list_mail, message = msg, subject = subject, doctype = ORD, docname = job_order)
    except Exception as e:
        print(e, frappe.get_traceback())
