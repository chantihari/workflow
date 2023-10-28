import frappe
from frappe import _
from frappe.share import add_docshare as add
import datetime
from pymysql.constants.ER import NO
from tag_workflow.utils.notification import sendmail, make_system_notification, get_mail_list
import json
from frappe.utils import time_diff_in_seconds
from frappe import enqueue
import ast
import re
# global #
JOB = "Job Order"
assignEmployee="Assign Employee"
TM_FT = "%Y-%m-%d %H:%M:%S"
timesheet_time= 'select to_time,from_time from `tabTimesheet Detail` where parent= '
noShow='No Show'
nonSatisfactory='Non Satisfactory'
pattern = r'[+<>^?#/\\]'
#----------------#
def validate_time_logs(self):
    for data in self.get("time_logs"):
        self.validate_overlap(data)
        self.set_project(data)
        self.validate_project(data)

@frappe.whitelist()
def send_timesheet_for_approval(employee, docname, company, job_order):
    try:
        sql = """ select parent from `tabHas Role` where role in ("Staffing Admin", "Staffing User") and parent in(select user_id from `tabEmployee` where user_id != '' and company = (select company from `tabEmployee` where name = '{0}')) """.format(employee)
        user_list = frappe.db.sql(sql, as_dict=1)
        staffing_user=[]

        for user in user_list:
            if not frappe.db.exists("User Permission",{"user": user.parent,"allow": "Timesheet","apply_to_all_doctypes":1, "for_value": docname}):
                add("Timesheet", docname, user=user.parent, read=1, write=1, submit=1, notify=0, flags={"ignore_share_permission": 1})
                perm_doc = frappe.get_doc(dict(doctype="User Permission",user=user.parent,allow="Timesheet",for_value=docname,apply_to_all_doctypes=1))
                perm_doc.save(ignore_permissions=True)
            if user.parent not in staffing_user:
                staffing_user.append(user.parent)

        today = datetime.date.today()
        msg = f'{company} has submitted a timesheet on {today} for {job_order} for approval. '
        subject = 'Timesheet For Approval'
        staffing_user_app, staffing_user_mail = get_mail_list(staffing_user,app_field='ts_send_app',mail_field='ts_send_mail')
        make_system_notification(staffing_user_app, msg, 'Timesheet', docname,subject)
        sendmail(emails=staffing_user_mail, message=msg, subject=subject, doctype='Timesheet', docname=docname)
        return True
    except Exception as e:
        frappe.log_error(e, "Job Order Approval")

#----------timesheet------------------#
@frappe.whitelist()
def get_timesheet_data(job_order, comp_type, date, timesheets_to_update=None):
    """
    The function `get_timesheet_data` retrieves timesheet data based on the job order, company type, and
    date provided.
    
    :param job_order: The job_order parameter is the identifier for a specific job order. It is used to
    retrieve data related to that job order from the database
    :param comp_type: The `comp_type` parameter is a string that represents the type of company. It can
    have the following values:
    :param date: The "date" parameter is the date for which you want to retrieve timesheet data
    :param timesheets_to_update: The `timesheets_to_update` parameter is an optional parameter that
    allows you to specify a list of timesheet names that you want to update. If this parameter is
    provided, the function will only return data for the specified timesheets. If this parameter is not
    provided, the function will return data for
    :return: a tuple containing two elements. The first element is a list of dictionaries representing
    timesheet data. The second element is a dictionary representing draft timesheet data.
    """
    try:
        jo = frappe.get_doc(JOB, job_order)

        company_type = 'Exclusive Hiring' if comp_type == 'Staffing' else comp_type

        if company_type in ["Hiring", "Exclusive Hiring"]:
            approved_cond = "AND aed.approved = 1" if jo.resumes_required == 1 and comp_type != 'Staffing' else ""
            sql = f"""
            SELECT aed.job_category, aed.job_start_time, aed.employee, aed.employee_name, "" as status, aed.pay_rate
            FROM `tabAssign Employee` AS ae
            INNER JOIN `tabAssign Employee Details` AS aed ON ae.name = aed.parent
            WHERE ae.job_order = "{job_order}" AND ae.tag_status = 'Approved' AND (aed.remove_employee = 0 OR (aed.remove_employee = 1 AND (aed.removed_by_hiring =1 AND DATE_FORMAT(aed.removed_by_hiring_date, '%Y-%m-%d') > '{date}'))) {approved_cond}
            """

            sql += f"""
            UNION ALL

            SELECT re.job_category, re.job_start_time, re.employee, re.employee_name, "Replaced" as status, re.pay_rate
            FROM `tabReplaced Employee` AS re
            INNER JOIN `tabAssign Employee` AS ae ON ae.name = re.parent
            WHERE ae.job_order = "{job_order}" AND ae.tag_status = 'Approved'
            
            UNION ALL
            
            SELECT ree.job_title, TIME_FORMAT(ree.start_time, '%H:%i'), ree.employee_id, ree.employee_name, "Removed" as status, ree.pay_rate
            FROM `tabRemoved Employee List` AS ree
            INNER JOIN `tabAssign Employee` AS ae ON ae.name = ree.parent
            LEFT JOIN `tabReplaced Employee` AS re ON ae.name = re.parent
            WHERE ae.job_order = "{job_order}" AND ae.tag_status = 'Approved'
                AND ree.order_status = 'Ongoing'
                AND (re.employee IS NULL OR re.employee NOT IN (
                        SELECT re2.employee
                        FROM `tabReplaced Employee` AS re2
                        INNER JOIN `tabAssign Employee` AS ae2 ON ae2.name = re2.parent
                        WHERE ae2.job_order = "{job_order}" AND ae2.tag_status = 'Approved'
                    ))
                AND ree.removed_by_hiring=0
            """

            data = frappe.db.sql(sql, as_dict=True)
            result = [
                {
                    "job_title": d['job_category'],
                    "start_time": d['job_start_time'].rjust(5, "0"),
                    "employee": d['employee'],
                    "employee_name": d["employee_name"],
                    "enter_time": "",
                    "exit_time": "",
                    "total_hours": 0.00,
                    "company": frappe.get_value("Employee", d['employee'], "company"),
                    "status": d["status"],
                    "timesheet_name": "",
                    "break_from": "",
                    "break_to": "",
                    "billing_amount": 0.00,
                    "tip": 0.00,
                    "overtime_hours": 0.00,
                    "overtime_rate": 0.00,
                    "pay_rate": d["pay_rate"]
                }
                for d in data
            ]
            add_rate_data(jo.multiple_job_titles, result)
            open_exist = frappe.db.sql('''
            SELECT TS.name AS name, employee, from_time, to_time, TS.job_name AS job_title,
            TD.start_time, TD.break_start_time AS break_from, TD.break_end_time AS break_to,
            TD.hours AS hours, tip, billing_amount, TD.extra_hours AS extra_hours,
            TD.extra_rate AS extra_rate, TS.no_show, TS.non_satisfactory,
            TS.dnr
            FROM `tabTimesheet` AS TS
            INNER JOIN `tabTimesheet Detail` AS TD ON TS.name = TD.parent
            WHERE job_order_detail = %s AND date_of_timesheet = %s
                AND TS.workflow_state = "Open"
            ORDER BY TS.name DESC
            ''', (job_order, date), as_dict=True)

            if(len(open_exist)):
                data1=exist_data(open_exist, result, timesheets_to_update)
                sql=f'''
                SELECT start_time, end_time, break_from, break_to FROM `tabDraft Time` WHERE date_of_ts="{date}"
                AND job_order="{job_order}" ORDER BY id desc
                '''
                draft_ts=frappe.db.sql(sql,as_dict=True)
                data1 = sort_data(data1)
                return data1, draft_ts, 1
            else:
                data1 = sort_data(result)
                return data1, {}, 0
        return []
    except Exception as e:
        print(e, frappe.get_traceback())
        return []

@frappe.whitelist()
def sort_data(data):
    try:
        emp = [i['employee'] for i in data]
        if len(emp)>1:
            sort_data=[]
            sort_ids = frappe.db.sql(f'''select name from tabEmployee where name in {tuple(emp)} order by company ASC, last_name ASC, first_name ASC''')
            for i in sort_ids:
                for j in data:
                    if i[0]==j['employee']:
                        sort_data.append(j)
            return sort_data
        else:
            return data
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.log_error(frappe.get_traceback(), "sort_data error")

#------------------------------------#
def get_child_time(posting_date, from_time, to_time, child_from=None, child_to=None):
    try:
        if(child_from and child_to):
            from_time = datetime.datetime.strptime((posting_date+" "+str(child_from)), TM_FT)
            to_time = datetime.datetime.strptime((posting_date+" "+str(child_to)), TM_FT)
            return from_time, to_time
        else:
            return from_time, to_time
    except Exception as e:
        print(e)
        return from_time, to_time

def check_old_timesheet(child_from, child_to, employee):
    try:
        sql = """select c.name, c.parent from `tabTimesheet Detail` c where (('{1}' >= c.from_time and '{1}' <= c.to_time) or ('{2}' >= c.from_time and '{2}' <= c.to_time) or ('{1}' <= c.from_time and '{2}' >= c.to_time)) and parent in (select name from `tabTimesheet` where employee = '{0}') """.format(employee, child_from, child_to)
        data = frappe.db.sql(sql, as_dict=1)
        return 1 if(len(data) > 0) else 0
    except Exception as e:
        print(e)
        return 0

def check_if_employee_assign(items): 
    try:
        is_employee = 1
        for item in items['items']:
            sql = """ select employee from `tabAssign Employee Details` where employee = '{0}' and parent in (select name from `tabAssign Employee` where tag_status = "Approved" and job_order = '{1}') """.format(item['employee'], items['job_order'])
            result = frappe.db.sql(sql, as_dict=1)
            if(len(result) == 0):
                frappe.msgprint(_("Employee with ID <b>{0}</b> not assigned to this Job Order(<b>{1}</b>). Please fill the details correctly.").format(item['employee'], items['job_order']))
                is_employee = 0
        return is_employee
    except Exception as e:
        frappe.msgprint(e)
        return False
        

@frappe.whitelist()
def remove_job_title(emp_doc_name,job_title):
    try:
        emp_doc=frappe.get_doc("Employee", emp_doc_name)
        if len(emp_doc.employee_job_category)!=0:
            for i in emp_doc.employee_job_category:
                if i.job_category==job_title:
                    emp_doc.remove(i)
                    emp_doc.save(ignore_permissions=True)

        job_category_remove(emp_doc)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(e, "remove job title error")

@frappe.whitelist()
def job_category_remove(emp_doc):
        if len(emp_doc.employee_job_category):
            emp_doc.job_category = emp_doc.employee_job_category[0].job_category
            emp_category = emp_doc.employee_job_category
            length = len(emp_category)
            title = '';	
            job_categories_list = []
            for i in range(len(emp_category)):
                job_categories_list.append(emp_category[i].job_category)
                if not emp_category[i].job_category:
                    length -= 1
                    
                elif title == '':
                    title = emp_category[i].job_category                  
            if length>1:
                job_categories = title + ' + ' + str(length-1)
            else:
                job_categories = title
            emp_doc.job_categories = job_categories
            emp_doc.job_title_filter = ",".join(job_categories_list)
            emp_doc.save(ignore_permissions=True)
        else:
            emp_doc.job_category = None
            emp_doc.job_categories = None
            emp_doc.save(ignore_permissions=True)

@frappe.whitelist()
def update_timesheet_data(data, company, company_type, user):
    try:
        added = 0
        if(company_type != "Hiring" and user != frappe.session.user):
            return

        data = json.loads(data)
        is_employee = check_if_employee_assign(data)
        if(is_employee == 0):
            return False

        job = frappe.get_doc(JOB, {"name": data['job_order']})
        posting_date = datetime.datetime.strptime(data['posting_date'], "%Y-%m-%d").date()
        if(posting_date >= job.from_date and posting_date <= job.to_date):
            from_time = datetime.datetime.strptime((data['posting_date']+" "+data['enter_time']), TM_FT)
            to_time = datetime.datetime.strptime((data['posting_date']+" "+data['exit_time']), TM_FT)
            for item in data['items']:
                child_from, child_to = get_child_time(data['posting_date'], from_time, to_time, item['enter_time'], item['exit_time'])
                is_ok = check_old_timesheet(child_from, child_to, item['employee'])
                if(is_ok == 0):
                    timesheet = frappe.get_doc(dict(doctype = "Timesheet", company=company, job_order_detail=data['job_order'], employee = item['employee'], from_date=job.from_date, to_date=job.to_date, job_name=job.select_job, per_hour_rate=job.per_hour, flat_rate=job.flat_rate,status_of_work_order = job.order_status,date_of_timesheet=data['posting_date']))
                    timesheet.append("time_logs", {
                        "activity_type": job.select_job,
                        "from_time": child_from,
                        "to_time": child_to,
                        "hrs": str(item['total_hours'])+" hrs",
                        "hours": float(item['total_hours']),
                        "is_billable": 1,
                        "billing_rate": job.per_hour,
                        "flat_rate": job.flat_rate
                    })
                    timesheet.insert(ignore_permissions=True)
                    timesheet.workflow_state = "Approval Request"
                    timesheet.save()
                    enqueue("tag_workflow.utils.timesheet.send_timesheet_for_approval", employee=item['employee'],docname=timesheet.name,company=company,job_order=data['job_order'])
                    added = 1
                else:
                    frappe.msgprint(_("Timesheet already filled for employee <b>{0}</b>(<b>{1}</b>) for given datetime").format(item["employee_name"],item['employee']))
        else:
            frappe.msgprint(_("Date must be in between Job Order start date and end date for timesheets"))

        return True if added == 1 else False
    except Exception as e:
        print(e)
        frappe.db.rollback()
        return False

@frappe.whitelist(allow_guest=True)
@frappe.validate_and_sanitize_search_inputs
def get_timesheet_employee(doctype, txt, searchfield, start, page_len, filters):
    job_order = filters.get('job_order')
    sql = f"""
    select employee, employee_name
    from `tabAssign Employee Details`
    where parent in (select name from `tabAssign Employee` where job_order = '{job_order}' and tag_status = "Approved")
    and (employee like "%%{str(txt)}%%" or employee_name like "%%{str(txt)}%%")
    UNION
    select DISTINCT employee, employee_name
    from `tabReplaced Employee`
    where parent in(select name from `tabAssign Employee` where job_order = '{job_order}' and tag_status = "Approved")
    and (employee like "%%{str(txt)}%%" or employee_name like "%%{str(txt)}%%")
    """
    return frappe.db.sql(sql)

@frappe.whitelist()
def notify_email_after_submit(job_order,employee, value, subject, company, employee_name, date,timesheet_name,job_title,event=None):
    try:
        sql = """ select user_id from `tabEmployee` where company = (select company from `tabEmployee` where name = '{0}') and user_id IS NOT NULL  """.format(employee)
        user_list = frappe.db.sql(sql, as_dict=1)
        if subject=='DNR':
            message=dnr_notification_after_submit(job_order,value,employee_name,subject,date,company,job_title)
        else:
            message=show_satisfactory_notification(job_order,value,employee_name,subject,date,company,employee,job_title)  
        users = []
        for user in user_list:
            users.append(user['user_id'])

        if users:
            staffing_user_app, staffing_user_mail = get_mail_list(users,app_field='ts_send_app',mail_field='ts_send_mail')
            if event:
                make_system_notification(staffing_user_app, message,JOB, job_order, subject)
            sendmail(staffing_user_mail, message, subject, "Timesheet", timesheet_name)
    except Exception as e:
        frappe.log_error(e, "Timesheet Email Error")
        frappe.throw(e)

@frappe.whitelist()
def notify_email(doc):
    try:
        sql = """ select user_id from `tabEmployee` where company = (select company from `tabEmployee` where name = '{0}') and user_id IS NOT NULL  """.format(doc.employee)
        user_list = frappe.db.sql(sql, as_dict=1)
        users = []
        for user in user_list:
            users.append(user['user_id'])
        if users:
            users_app, users_mail = get_mail_list(users,app_field='ts_send_app',mail_field='ts_send_mail')
        if doc.dnr:
            subject = "DNR"
            message=dnr_notification(doc.job_order_detail,doc.dnr,doc.employee_name,subject,doc.creation,doc.company,doc.employee,doc.job_name)
            if users:
                make_system_notification(users_app, message,JOB, doc.job_order_detail, subject)
                sendmail(users_mail, message, subject, "Timesheet", doc.name)
        if doc.no_show:
            message=show_satisfactory_notification(doc.job_order_detail,doc.non_satisfactory,doc.employee_name,subject,doc.creation,doc.company,doc.employee,doc.job_name)
            if users:
                make_system_notification(users_app, message, JOB, doc.job_order_detail, subject)
                sendmail(users_mail, message, noShow, "Timesheet", doc.name)
        if doc.non_satisfactory:
            subject = nonSatisfactory
            message=show_satisfactory_notification(doc.job_order_detail,doc.non_satisfactory,doc.employee_name,subject,doc.creation,doc.company,doc.employee,doc.job_name)
            if users:
                make_system_notification(users_app, message,JOB, doc.job_order_detail, subject)
                sendmail(users_mail, message, subject, "Timesheet", doc.name)
    except Exception as e:
        frappe.log_error(e, "Timesheet Email Error")
        frappe.throw(e)

#-------assign employee----------#
@frappe.whitelist()
def check_employee_editable(job_order, name, creation):
    try:
        is_editable = 0
        order = frappe.get_doc(JOB, job_order)
        time_format = TM_FT
        to_date = order.to_date#datetime.datetime.strptime(str(order.to_date), time_format)
        creation = datetime.datetime.strptime(str(creation[0:19]), time_format)
        today = datetime.datetime.now()

        if(today.date() >= to_date):
            return is_editable

        sql = """ select no_show, non_satisfactory, dnr from `tabTimesheet` where docstatus != 1 and job_order_detail = '{0}' and employee in (select employee from `tabAssign Employee Details` where parent = '{1}') """.format(job_order, name)
        emp_list = frappe.db.sql(sql, as_dict=1)
        for emp in emp_list:
            if(emp.no_show == 1 or emp.dnr == 1 or emp.non_satisfactory == 1):
                is_editable = 1

        return is_editable
    except Exception as e:
        print(e)
        is_editable = 1
        frappe.log_error(frappe.get_traceback(), "check_employee_editable")
        return is_editable

@frappe.whitelist()
def company_rating(hiring_company=None,staffing_company=None,ratings=None,job_order=None):
    try:
        staffing_company_rating(hiring_company=hiring_company,staffing_company=staffing_company,ratings=ratings,job_order=job_order)
        return 1
       
    except Exception as e:
        frappe.log_error(e, "Hiring Company Rating")
        frappe.throw(e)

@frappe.whitelist()
def rating_no_show(rating_no_show,invoice_name):
    try:
        if rating_no_show:
            rating_no_show=1
        else:
            rating_no_show=0
        frappe.db.sql('''update `tabSales Invoice` set rating_no_show="{}" where name="{}"'''.format(rating_no_show,invoice_name))
    except Exception as e:
        frappe.log_error(e, "Staffing Company Rating")
        frappe.throw(e)

@frappe.whitelist()
def staffing_company_rating(hiring_company,staffing_company,ratings,job_order):
    ratings = ast.literal_eval(ratings)
    if ratings['Rating'] not in [i / 10 for i in range(1, 11)]:
        frappe.throw("Invalid rating.")
    doc = frappe.new_doc('Company Review')
    doc.staffing_company=staffing_company
    doc.hiring_company=hiring_company
    doc.job_order=job_order
    doc.rating=ratings['Rating']
    doc.staffing_ratings=ratings['Rating']*5
    if 'Comment' in ratings.keys():
        doc.comments=re.sub(pattern, '', ratings['Comment'])
    doc.save(ignore_permissions=True)

    sql = '''select user_id from `tabEmployee` where company = '{}' and user_id IS NOT NULL '''.format(staffing_company)
    staff_member = frappe.db.sql(sql, as_list=1)
    for staff in staff_member:
        add("Company Review", doc.name, staff[0], read=1, write = 0, share = 0, everyone = 0,notify = 1, flags={"ignore_share_permission": 1})

    sql = ''' select average_rating from `tabCompany` where name = '{}' '''.format(staffing_company)
    company_rate = frappe.db.sql(sql, as_list=1)
    if (len(company_rate)==0 or company_rate[0][0]==None):
        doc=frappe.get_doc('Company',staffing_company)
        doc.average_rating=str(ratings['Rating']*5)
        doc.save()
    else:
        sql = ''' select staffing_ratings from `tabCompany Review` where staffing_company='{}' '''.format(staffing_company)
        average_rate = frappe.db.sql(sql, as_list=1)
        if average_rate[0][0]!=None:
            rating=[float(i[0]) for i in average_rate]
            doc=frappe.get_doc('Company',staffing_company)
            avg_rating=round(sum(rating)/len(rating), 1)
            doc.average_rating=str(avg_rating)
            doc.save()
    return "success"
@frappe.whitelist()
def approval_notification(job_order=None,staffing_company=None,date=None,hiring_company=None,timesheet_name=None,timesheet_approved_time=None,current_time=None):
    try:
        sql = ''' select select_job,job_site,creation from `tabJob Order` where name='{}' '''.format(job_order)
        job_order_data = frappe.db.sql(sql,as_dict=1)
        job_location=job_order_data[0].job_site
        subject='Timesheet Approval'
        msg=f'{staffing_company} has approved the {timesheet_name} timesheet for {job_order} at {job_location}'
        user_list=frappe.db.sql(''' select user_id from `tabEmployee` where company='{}' and user_id IS NOT NULL'''.format(hiring_company),as_list=1)        
        hiring_user = [hiring_user[0] for hiring_user in user_list]
        hiring_user_app, hiring_user_mail = get_mail_list(hiring_user,app_field='ts_approved_app',mail_field='ts_approved_mail')
        make_system_notification(hiring_user_app,msg,'Timesheet',timesheet_name,subject)
        sql = """ UPDATE `tabTimesheet` SET approval_notification = 0 where name="{0}" """.format(timesheet_name)
        frappe.db.sql(sql)
        frappe.db.commit()
        sendmail(emails=hiring_user_mail, message=msg, subject=subject, doctype='Timesheet', docname=timesheet_name)
        # frappe.enqueue("tag_workflow.utils.notification.sendmail",emails=hiring_user_mail, message=msg, subject=subject, doctype='Timesheet', docname=timesheet_name)
    except Exception as e:
        frappe.log_error(e, "Timesheet Approved")
        frappe.throw(e)


def unsatisfied_organization(emp_doc_name,company,job_order):
    try:
        emp_doc=frappe.get_doc("Employee", emp_doc_name)
        emp_doc.append('unsatisfied_from', {
            'unsatisfied_organization_name': company,
            'job_order':job_order,
            'date':datetime.datetime.now()
        })
        emp_doc.save(ignore_permissions=True)
        frappe.db.commit()
        assign_emp_doc=f"""select name from `tabAssign Employee` where job_order='{job_order}' and company='{emp_doc.company}' """
        data=frappe.db.sql(assign_emp_doc,as_dict=True)
        assign_doc=frappe.get_doc(assignEmployee,data[0].name)
        assign_doc.append('replaced_employees', {
            'employee_name': emp_doc.name,
            "employee_status": nonSatisfactory
        })
        assign_doc.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(e, "unsatisfied error")


def dnr_notification(job_order,value,employee_name,subject,date,company,employee,job_title):
    sql = ''' select from_date,job_start_time,to_date from `tabJob Order` where name='{}' '''.format(job_order)
    data=frappe.db.sql(sql, as_dict=1)
    start_date=data[0].from_date
    end_date=data[0].to_date
    today = datetime.date.today()
    to_time=data[0].job_start_time
    time_object = datetime.datetime.strptime(str(to_time), '%H:%M:%S').time()
    time_diff=time_diff_in_seconds(str(datetime.datetime.now().time()),str(time_object))
    if int(value) ==1 and subject == 'DNR':
        emp_doc = frappe.get_doc('Employee', employee)
        employee_dnr(company,emp_doc,job_order)
        remove_job_title(emp_doc,job_title)
    
    elif int(value) == 0 and subject == 'DNR':
         emp_doc = frappe.get_doc('Employee', employee)
         removing_dnr_employee(company,emp_doc,job_order)

    if(today<=end_date and today-start_date==0 and (time_diff/60/60 < 2)):
        if(int(value)):
            message = f'<b>{employee_name}</b> has been marked as <b>{subject}</b> for work order <b>{job_order}</b> on <b>{date}</b> with <b>{company}</b>. There is time to substitute this employee for today’s work order {datetime.date.today()}'
        else:
            message = f'<b>{employee_name}</b> has been unmarked as <b>{subject}</b> for work order <b>{job_order}</b> on <b>{date}</b> with <b>{company}</b>.'
        return message

    else:
        if(int(value)):
            message = f'<b>{employee_name}</b> has been marked as <b>{subject}</b> for work order <b>{job_order}</b> on <b>{date}</b> with <b>{company}</b>. There is time to substitute this employee for tomorrow’s work order {datetime.date.today()}'
        else:
            message = f'<b>{employee_name}</b> has been unmarked as <b>{subject}</b> for work order <b>{job_order}</b> on <b>{date}</b> with <b>{company}</b>.'
        return message
        
def show_satisfactory_notification(job_order,value,employee_name,subject,date,company,employee,job_title):
    if(int(value)):
        message = f'<b>{employee_name}</b> has been marked as <b>{subject}</b> for work order <b>{job_order}</b> on <b>{date}</b> with <b>{company}</b>.'
    else:
        message = f'<b>{employee_name}</b> has been unmarked as <b>{subject}</b> for work order <b>{job_order}</b> on <b>{date}</b> with <b>{company}</b>.'
    
    if subject == nonSatisfactory:
        if int(value)==1:
            emp_doc = frappe.get_doc('Employee', employee)
            employee_unsatisfactory(company,emp_doc,job_order)
            remove_job_title(employee,job_title)
        else:
            emp_doc = frappe.get_doc('Employee', employee)
            removing_unsatisfied_employee(company,emp_doc,job_order)

    no_show(job_order,value,subject,company,employee,job_title)     
    return message

def employee_unsatisfactory(company,emp_doc,job_order):
    if len(emp_doc.unsatisfied_from)>0:
        for i in emp_doc.unsatisfied_from:
            if(i.unsatisfied_organization_name == company):
                return
    frappe.enqueue(unsatisfied_organization, emp_doc.name,company,job_order, is_async=True, queue="long")


def removing_unsatisfied_employee(company,emp_doc,job_order):
    if len(emp_doc.unsatisfied_from)!=0:
        for i in emp_doc.unsatisfied_from:
            if i.unsatisfied_organization_name == company and i.job_order==job_order:
                remove_row = i
        assign_emp_doc=f"""select name from `tabAssign Employee` where job_order='{job_order}' and company='{emp_doc.company}' """
        data=frappe.db.sql(assign_emp_doc,as_dict=True)
        assign_doc=frappe.get_doc(assignEmployee,data[0].name)
        for y in assign_doc.replaced_employees:
            if y.employee_name == emp_doc.name and y.employee_status==nonSatisfactory:
                removed_row = y
       
        emp_doc.remove(remove_row)
        emp_doc.save(ignore_permissions=True)
        assign_doc.remove(removed_row)
        assign_doc.save(ignore_permissions=True)


@frappe.whitelist()
def assigned_job_order(doctype,txt,searchfield,page_len,start,filters):
    try:
        company=filters.get('company')
        today = datetime.datetime.now()

        sql = ''' select name from `tabJob Order` where company = '{0}' and from_date<'{1}' and name in (select job_order from `tabAssign Employee` where hiring_organization = '{0}')'''.format(company,today)
        return frappe.db.sql(sql)
    except Exception as e:
        frappe.log_error(e, "Job Order For Timesheet")
        frappe.throw(e)

@frappe.whitelist()
def jb_ord_dispute_comment_box(comment,job_order):
    try:
        comment = json.loads(comment)
        if comment:
            job_order_doc = frappe.get_doc(JOB,job_order)
            if job_order_doc.dispute_comment:
                job_order_doc.dispute_comment += '\n' +'-'*15 + '\n'+ comment['Comment']
            else:
                job_order_doc.dispute_comment = comment['Comment']

            job_order_doc.flags.ignore_mandatory = True
            job_order_doc.save(ignore_permissions=True)

            return True
    except Exception as e:
        frappe.log_error(e, "Dispute Message")
        frappe.throw(e)


@frappe.whitelist()
def hiring_company_rating(hiring_company=None,staffing_company=None,ratings=None,job_order=None,timesheet=None):
    try:
        timesheet_doc=frappe.get_doc('Timesheet', timesheet)
        user_company_name=frappe.db.get_value("User", frappe.session.user, "company")
        if timesheet_doc.employee_company!=user_company_name:
            frappe.throw('Logged in user does not belong to the Timesheet Staffing Company')
        elif timesheet_doc.job_order_detail!=job_order:
            frappe.throw('Timesheet '+timesheet_doc.name+' does not belong to the Job Order '+job_order)
        ratings = json.loads(ratings)
        if ratings['Rating'] not in [i / 10 for i in range(1, 11)]:
            frappe.throw("Invalid rating.")
        doc = frappe.new_doc('Hiring Company Review')
        doc.staffing_company=staffing_company
        doc.hiring_company=hiring_company
        doc.job_order=job_order
        doc.rating=ratings['Rating']
        doc.rating_hiring=ratings['Rating']*5
        if 'Comment' in ratings.keys():
            doc.comments=re.sub(pattern, '', ratings['Comment'])
        doc.save(ignore_permissions=True)
        sql = ''' select user_id from `tabEmployee` where company = '{}' and user_id IS NOT NULL '''.format(hiring_company)
        hiring_member = frappe.db.sql(sql, as_list=1)
        for name in hiring_member:
            add("Hiring Company Review", doc.name, name[0], read=1, write = 0, share = 0, everyone = 0,notify = 1, flags={"ignore_share_permission": 1})
        company_rate=frappe.db.sql(''' select average_rating from `tabCompany` where name='{}' '''.format(hiring_company),as_list=1)
        if (len(company_rate)==0 or company_rate[0][0]==None):
            doc=frappe.get_doc('Company',hiring_company)
            doc.average_rating=str(ratings['Rating']*5)
            doc.save()
        else:
            sql = ''' select rating_hiring from `tabHiring Company Review` where hiring_company = '{}' '''.format(hiring_company)
            average_rate = frappe.db.sql(sql, as_list=1)
            if average_rate[0][0]!=None:
                rating=[float(i[0]) for i in average_rate]
                doc=frappe.get_doc('Company',hiring_company)
                avg_rating=round(sum(rating)/len(rating),1)
                doc.average_rating=str(avg_rating)
                doc.save()
        return "success"
    except Exception as e:
        frappe.log_error(e, "Hiring Company Rating")
        frappe.throw(e)



@frappe.whitelist()
def staffing_emp_rating(employee,id,up,down,job_order,comment,timesheet_name):
    try:
        rating = 1
        if int(down):
            rating = 0
        parent = frappe.get_doc(JOB, job_order)
        parent.append('employee_rating', {
            'employee_name': employee +'-'+ id,
            'rating':  rating,
            'comment': comment if comment else ''
        })
        parent.flags.ignore_mandatory = True
        parent.save(ignore_permissions=True)
        timesheet = frappe.get_doc('Timesheet',timesheet_name)
        timesheet.is_employee_rating_done = 1
        timesheet.flags.ignore_mandatory = True
        timesheet.save(ignore_permissions=True)
        return True
    except Exception as e:
        frappe.log_error(e, "Staffing Employee Rating")
        frappe.throw(e)


def employee_dnr(company,emp_doc,job_order):
    if len(emp_doc.dnr_employee_list) == 0:
        do_not_return(emp_doc.name,company,job_order)
    else:
        for i in emp_doc.dnr_employee_list:
            if i.dnr == company:
                return
        do_not_return(emp_doc.name,company,job_order)
            
      
def removing_dnr_employee(company,emp_doc,job_order):
    if len(emp_doc.dnr_employee_list)!=0:
        for i in emp_doc.dnr_employee_list:
            if i.dnr == company and i.job_order==job_order:
                remove_row = i
        emp_doc.remove(remove_row)
        emp_doc.save(ignore_permissions=True)
           
   
def do_not_return(emp_doc_name,company,job_order):
    try:
        emp_doc = frappe.get_doc("Employee",emp_doc_name)
        emp_doc.append('dnr_employee_list',{'dnr':company,'job_order':job_order,'date':datetime.datetime.now()})
        emp_doc.save(ignore_permissions = True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(e, "do not return error")

@frappe.whitelist()
def denied_notification(job_order,hiring_company,staffing_company,timesheet_name):
    try:
        sql = ''' select select_job,job_site,creation from `tabJob Order` where name='{}' '''.format(job_order)
        job_order_data = frappe.db.sql(sql,as_dict=1)
        job_location=job_order_data[0].job_site
        subject='Timesheet Denied'
        msg=f'{staffing_company} has denied the {timesheet_name} timesheet for {job_order} at {job_location}'
        user_list=frappe.db.sql(''' select user_id from `tabEmployee` where company='{}' and user_id IS NOT NULL '''.format(hiring_company),as_list=1)        
        hiring_user = [hiring_user[0] for hiring_user in user_list]
        hiring_user_app, hiring_user_mail = get_mail_list(hiring_user,app_field='ts_deny_app',mail_field='ts_deny_mail')
        make_system_notification(hiring_user_app,msg,'Timesheet',timesheet_name,subject)
        sendmail(emails=hiring_user_mail, message=msg, subject=subject, doctype='Timesheet', docname=timesheet_name)
        # frappe.enqueue("tag_workflow.utils.notification.sendmail",emails=hiring_user_mail, message=msg, subject=subject, doctype='Timesheet', docname=timesheet_name, queue="long", timeout=12000)
    except Exception as e:
        frappe.log_error(e, "Timesheet Denied")
        frappe.throw(e)

@frappe.whitelist(allow_guest=False)
def timesheet_dispute_comment_box(comment, timesheet, user):
    """
    The function `timesheet_dispute_comment_box` adds a comment to a timesheet and updates its workflow
    state to "Denied" if the user has sufficient permissions.
    
    :param comment: The `comment` parameter is a JSON string that contains the comment to be added to
    the timesheet dispute
    :param timesheet: The "timesheet" parameter is the ID of the timesheet document that the comment is
    being added to
    :param user: The "user" parameter represents the user who is making the dispute comment
    :return: a boolean value, either True or None.
    """
    try:
        comment = json.loads(comment)
        if comment:
            timesheet_doc = frappe.get_doc('Timesheet',timesheet) #timesheet
            if user!=frappe.session.user or not frappe.has_permission(timesheet_doc, "read", throw=False):
                frappe.throw('Insufficient Permission for User ' + user)
            if timesheet_doc.dispute:
                timesheet_doc.dispute += '<br>' +'-'*15 + '<br>'+ comment['Comment']
            else:
                timesheet_doc.dispute = comment['Comment']
            timesheet_doc.workflow_state = 'Denied'
            timesheet_doc.flags.ignore_mandatory = True
            timesheet_doc.save(ignore_permissions=True)
            return True
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.log_error(e, "Dispute Message")
        frappe.throw(e)

@frappe.whitelist()
def job_name(doctype,txt,searchfield,page_len,start,filters):
    try:
        job=filters.get('job_name')
        sql = ''' select select_job from `tabMultiple Job Title` where parent="{0}"'''.format(job)
        return frappe.db.sql(sql)
    except Exception as e:
        frappe.log_error(e, "Job Order For Timesheet")
        frappe.throw(e)


def no_show(job_order,value,subject,company,employee,job_title):
    print('no_show'*200)
    if subject==noShow:
        if int(value)==0:
            emp_doc = frappe.get_doc('Employee', employee)
            removing_no_show(company,emp_doc,job_order)
        else:
            emp_doc = frappe.get_doc('Employee', employee)
            employee_no_show(company,emp_doc,job_order)
            remove_job_title(employee,job_title)


def employee_no_show(company,emp_doc,job_order):
    print('Inside employee_no_show'*200)
    if len(emp_doc.no_show)>0:
        for i in emp_doc.no_show:
            if(i.no_show_company == company and i.job_order==job_order):
                return
    frappe.enqueue(no_show_org, emp_doc.name, company, job_order, is_async=True, queue="long")


@frappe.whitelist()
def no_show_org(emp_doc_name,company,job_order):
    try:
        emp_doc=frappe.get_doc("Employee", emp_doc_name)
        emp_doc.append('no_show', {
            'no_show_company': company,
            'job_order':job_order,
            'date':datetime.datetime.now()
        })
        emp_doc.save(ignore_permissions=True)
        assign_emp_doc=f"""select name from `tabAssign Employee` where job_order='{job_order}' and company='{emp_doc.company}' """
        data=frappe.db.sql(assign_emp_doc,as_dict=True)
        assign_doc=frappe.get_doc(assignEmployee,data[0].name)
        assign_doc.append('replaced_employees', {
            'employee_name': emp_doc.name,
            "employee_status": noShow
        })
        assign_doc.save(ignore_permissions=True)
        print('Done')
        frappe.db.commit()
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.log_error(e, "no show org error")


def removing_no_show(company,emp_doc,job_order):
    if len(emp_doc.no_show)!=0:
        for i in emp_doc.no_show:
            if i.no_show_company == company and i.job_order==job_order:
                remove_row = i
        assign_emp_doc=f"""select name from `tabAssign Employee` where job_order='{job_order}' and company='{emp_doc.company}' """
        data=frappe.db.sql(assign_emp_doc,as_dict=True)
        assign_doc=frappe.get_doc(assignEmployee,data[0].name)
        for y in assign_doc.replaced_employees:
            if y.employee_name == emp_doc.name and y.employee_status==noShow:
                removed_row = y
       
        emp_doc.remove(remove_row)
        emp_doc.save(ignore_permissions=True)
        assign_doc.remove(removed_row)
        assign_doc.save(ignore_permissions=True)
    
@frappe.whitelist()
def submit_staff_timesheet(jo, timesheet_date, employee,timesheet,date,company,dnr,job_title):
    print('Here'*500)
    timesheet_exist=[{'name':timesheet}]
    enqueue("tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet.update_timesheet_exist", now=True,jo=jo, timesheet_date=timesheet_date, employee=employee,timesheet=timesheet,timesheet_exist=timesheet_exist)
    t_time=frappe.db.sql(timesheet_time+"'"+timesheet+"'",as_dict=1)
    to_time=t_time[0].to_time
    timesheet_status_data=f'update `tabTimesheet` set docstatus="1",workflow_state="Approved",status="Submitted" where name="{timesheet}"'                       
    frappe.db.sql(timesheet_status_data)
    frappe.db.commit()
    emp_doc=frappe.get_doc('Employee',employee)
    if int(dnr)==1:
        notify_email_after_submit(job_order=jo,employee=emp_doc.employee, value=1, subject="DNR", company=company, employee_name=emp_doc.employee_name, date=date,timesheet_name=timesheet, event='timesheet', job_title=job_title)
    
    enqueue("tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet.update_previous_timesheet", now=True,jo=jo, timesheet_date=timesheet_date, employee=employee,timesheet=timesheet,to_time=to_time,save=0)
    return "success"

def dnr_notification_after_submit(job_order,value,employee_name,subject,date,company, job_title):
    sql = ''' select from_date,job_start_time,to_date from `tabJob Order` where name='{}' '''.format(job_order)
    data=frappe.db.sql(sql, as_dict=1)
    start_date=data[0].from_date
    end_date=data[0].to_date
    today = datetime.date.today()
    to_time=data[0].job_start_time
    time_object = datetime.datetime.strptime(str(to_time), '%H:%M:%S.%f').time()
    time_diff=time_diff_in_seconds(str(datetime.datetime.now().time()),str(time_object))
    enqueue(do_not_return, emp_doc_name=employee_name, company=company, job_order=job_order, queue="long", is_async=True)
    enqueue(remove_job_title, emp_doc_name=employee_name, job_title = job_title, queue="long", is_async=True)
    if(today<=end_date and today-start_date==0 and (time_diff/60/60 < 2)):
        if(int(value)):
            message = f'<b>{employee_name}</b> has been marked as <b>{subject}</b> for work order <b>{job_order}</b> on <b>{date}</b> with <b>{company}</b>. There is time to substitute this employee for today’s work order {datetime.date.today()}'
        else:
            message = f'<b>{employee_name}</b> has been unmarked as <b>{subject}</b> for work order <b>{job_order}</b> on <b>{date}</b> with <b>{company}</b>.'
        return message

    else:
        if(int(value)):
            message = f'<b>{employee_name}</b> has been marked as <b>{subject}</b> for work order <b>{job_order}</b> on <b>{date}</b> with <b>{company}</b>. There is time to substitute this employee for tomorrow’s work order {datetime.date.today()}'
        else:
            message = f'<b>{employee_name}</b> has been unmarked as <b>{subject}</b> for work order <b>{job_order}</b> on <b>{date}</b> with <b>{company}</b>.'
        return message
        
def exist_data(open_exist,data1,timesheets_to_update):
    for i in open_exist:
        for j in range(len(data1)):
            start_time_str = str(i['start_time'])
            formatted_start_time = datetime.datetime.strptime(start_time_str, '%H:%M:%S').strftime('%I:%M')
            if i['employee']==data1[j]['employee'] and i['job_title']==data1[j]['job_title'] and formatted_start_time==data1[j]['start_time']:
                data1[j]["enter_time"]=str(i['from_time']).split(' ')[1]
                data1[j]["exit_time"]=str(i['to_time']).split(' ')[1]
                data1[j]["total_hours"]=i['hours']
                data1[j]["break_from"]=str(i['break_from']) if i['break_from'] else ""
                data1[j]["break_to"]=str(i['break_to']) if i['break_to'] else ""
                data1[j]["billing_amount"]=i['billing_amount']
                data1[j]["tip"]=i['tip']
                data1[j]["timesheet_name"]=i['name']
                data1[j]["overtime_hours"]=i['extra_hours']
                data1[j]["overtime_rate"]=i['extra_rate']
                status=emp_status(i,data1,j)
                data1[j]["status"]=status
    data1=check_selected_values(data1,timesheets_to_update)
    return data1
def emp_status(i,data1,j):
    if data1[j]['status'] == 'Replaced':
        return 'Replaced'
    elif data1[j]['status']=='Removed':
        return 'Removed'
    else:
        status=''
        if i['dnr']==1:
            status='DNR'
        if i['no_show']==1:
            return noShow
        if i['non_satisfactory']==1:
            status=nonSatisfactory
        return status

@frappe.whitelist()
def checking_same_values_timesheet(user_selected_timesheet):
    try:
        new_timesheet_list=ast.literal_eval(user_selected_timesheet)
        new_timesheet_list_data=tuple(new_timesheet_list)
        if(len(new_timesheet_list_data)>1):
            timeseheets_status=frappe.db.sql('select workflow_state,job_order_detail,date_of_timesheet from `tabTimesheet` where name in {0} '.format(new_timesheet_list_data),as_dict=1)
        else:
            timeseheets_status=frappe.db.sql('select workflow_state,job_order_detail,date_of_timesheet from `tabTimesheet` where name="{0}"'.format(new_timesheet_list_data[0]),as_dict=1)
        job_order=timeseheets_status[0]['job_order_detail']
        timesheet_date=timeseheets_status[0]['date_of_timesheet']
        for i in timeseheets_status:
            if i['workflow_state']!='Open':
                return 'Different Status'
            elif i['job_order_detail']!=job_order:
                return 'Different Job Order'
            elif i['date_of_timesheet']!=timesheet_date:
                return 'Different Job Order Dates'
        return new_timesheet_list,job_order,timesheet_date
    except Exception as e:
        frappe.log_error(e,'Cheching Same timesheets details')

def check_selected_values(data1,timesheets_to_update):
    if(timesheets_to_update):
        timesheet_exi=timesheets_to_update.split(',')
        data2=[]
        for i in range(len(timesheet_exi)):
            for j in range(len(data1)):
                if(data1[j]['timesheet_name']==timesheet_exi[i]):
                    data2.append(data1[j])
        return data2
    else:
        return data1

@frappe.whitelist()
def csv_data(ts_list):
    """
    The function `csv_data` processes a list of timesheet IDs, retrieves relevant data from the
    database, and returns a success message along with the processed data or a failure message with the
    names of companies that could not be found in the database.
    It prepares data for Staff Complete Export Timesheet functionality.
    
    :param ts_list: The `ts_list` parameter is a list of Timesheet names
    :return: a tuple containing two values. The first value is either 'Success' or 'Failure', indicating
    the status of the function. The second value is either a list of data or a string.
    """
    try:
        ts_list=ast.literal_eval(ts_list)
        ts_data, exported_ts, company = [], [], []
        for ts in ts_list:
            ts_details = frappe.get_doc('Timesheet', ts)
            office_code, comp_id = frappe.db.get_value('Company', {'name': ts_details.employee_company}, ['office_code', 'comp_id'])
            if office_code and ts_details.workflow_state=='Approved':
                exported_ts.append(ts_details.name)
                pos_code = get_pos_id(ts_details.job_order_detail, ts_details.job_name)
                hiring_comp, emp_id, date_of_ts, ts_hours =  comp_id, ts_details.employee, ts_details.date_of_timesheet.strftime('%m-%d-%Y'), ts_details.total_hours
                from_time, to_time, pay_rate, bill_rate, job_order = ts_details.time_logs[0].from_time.strftime("%m-%d-%Y %H:%M"), ts_details.time_logs[0].to_time.strftime("%m-%d-%Y %H:%M"), ts_details.employee_pay_rate, ts_details.per_hour_rate, ts_details.job_order_detail
                if ts_details.todays_overtime_hours==0:
                    ts_data = no_ot_data(ts_details, ts_data, office_code, hiring_comp, emp_id, date_of_ts, pos_code, ts_hours, from_time, to_time, pay_rate, bill_rate, job_order)
                else:
                    ts_data = ot_data(ts_details, ts_data, office_code, hiring_comp, emp_id, date_of_ts, pos_code, ts_hours, from_time, to_time, pay_rate, bill_rate, job_order)
            elif not office_code:
                company.append(ts_details.employee_company)
        if len(exported_ts)>0:
            sql = f'''UPDATE `tabTimesheet` SET ts_exported = 1 WHERE name in {tuple(exported_ts)}''' if len(exported_ts)>1 else f'''UPDATE `tabTimesheet` SET ts_exported = 1 WHERE name in ("{exported_ts[0]}")'''
            frappe.db.sql(sql)
            frappe.db.commit()
        if len(company)==0:
            return 'Success', ts_data
        else:
            company = list(set(company))
            return 'Failure', ' and '.join(filter(None, [', '.join(company[:-1])] + company[-1:]))
    except Exception as e:
        print('csv_data Error', frappe.get_traceback())
        frappe.log_error(e, 'csv_data Error')

@frappe.whitelist()
def no_ot_data(ts_details, ts_data, office_code, hiring_comp, emp_id, date_of_ts, pos_code, ts_hours, from_time, to_time, pay_rate, bill_rate, job_order):
    try:
        if ts_details.timesheet_billable_amount == 0 and ts_details.no_show==0 and ts_details.time_logs[0].extra_hours>0:
            ts_data.append([hiring_comp, emp_id, 'REG', date_of_ts, pos_code, round(ts_hours-ts_details.time_logs[0].extra_hours, 2), round(ts_hours-ts_details.time_logs[0].extra_hours,2), office_code, from_time, to_time, round(pay_rate,2), round(bill_rate,2), job_order, '', '', 'TAG', '', ''])
            ts_data.append([hiring_comp, emp_id, 'OT', date_of_ts, pos_code, round(ts_details.time_logs[0].extra_hours,2), round(ts_details.time_logs[0].extra_hours,2), office_code, from_time, to_time, round(pay_rate*1.5,2), round(bill_rate,2), job_order, '', '', 'TAG', '', ''])
        else:
            if ts_details.timesheet_unbillable_overtime_amount > 0:
                unbillable_hours=ts_details.timesheet_unbillable_overtime_amount/(1.5*pay_rate)
                ts_data.append([hiring_comp, emp_id, 'REG', date_of_ts, pos_code, round(ts_hours,2), round(ts_hours,2), office_code, from_time, to_time, round(pay_rate,2), round(bill_rate,2), job_order, '', '', 'TAG', '', ''])
                ts_data.append([hiring_comp, emp_id, 'OT', date_of_ts, pos_code, round(unbillable_hours,2), round(unbillable_hours,2), office_code, from_time, to_time, round(pay_rate*1.5,2), round(bill_rate,2), job_order, '', '', 'TAG', '', ''])
            else:
                ts_data.append([hiring_comp, emp_id, 'REG', date_of_ts, pos_code, round(ts_hours,2), round(ts_hours,2), office_code, from_time, to_time, round(pay_rate,2), round(bill_rate,2), job_order, '', '', 'TAG', '', ''])
        return ts_data
    except Exception as e:
        print('no_ot_data Error', frappe.get_traceback())
        frappe.log_error(e, 'no_ot_data Error')

@frappe.whitelist()
def ot_data(ts_details, ts_data, office_code, hiring_comp, emp_id, date_of_ts, pos_code, ts_hours, from_time, to_time, pay_rate, bill_rate, job_order):
    try:
        if ts_hours==ts_details.todays_overtime_hours:
            ts_data.append([hiring_comp, emp_id, 'OT', date_of_ts, pos_code, round(ts_details.todays_overtime_hours,2), round(ts_details.todays_overtime_hours,2), office_code, from_time, to_time, round(pay_rate*1.5,2), round(bill_rate*1.5,2), job_order, '', '', 'TAG', '', ''])
        else:
            ts_data.append([hiring_comp, emp_id, 'REG', date_of_ts, pos_code, round(ts_hours-ts_details.todays_overtime_hours,2), round(ts_hours-ts_details.todays_overtime_hours,2), office_code, from_time, to_time, round(pay_rate,2), round(bill_rate,2), job_order, '', '', 'TAG', '', ''])
            ts_data.append([hiring_comp, emp_id, 'OT', date_of_ts, pos_code, round(ts_details.todays_overtime_hours,2), round(ts_details.todays_overtime_hours,2), office_code, from_time, to_time, round(pay_rate*1.5,2), round(bill_rate*1.5,2), job_order, '', '', 'TAG', '', ''])
        return ts_data
    except Exception as e:
        print('ot_data Error', frappe.get_traceback())
        frappe.log_error(e, 'ot_data Error')

@frappe.whitelist()
def get_pos_id(job_order, pos_code):
    """
    The function `get_pos_id` retrieves the item ID of a job title based on the job order and position
    code provided, or returns the first 15 characters of the position code if no item ID is found.
    
    :param job_order: The `job_order` parameter is the name of a job order. It is used to retrieve the
    job site associated with the job order
    :param pos_code: The `pos_code` parameter is a code that represents a job position
    :return: The function `get_pos_id` returns the `pos_id` value if it exists in the database query
    result, otherwise it returns the first 15 characters of the `pos_code` parameter.
    """
    try:
        job_site = frappe.db.get_value(JOB, {"name": job_order}, ["job_site"])
        pos_id = frappe.db.sql(f'''select item_id from `tabIndustry Types Job Titles` where parent= "{job_site}" and job_titles="{pos_code}"''', as_list=1)
        return pos_id[0][0] if pos_id else pos_code[:15]
    except Exception as e:
        print('get_pos_id Error', frappe.get_traceback())
        frappe.log_error(e, 'get_pos_id Error')

@frappe.whitelist()
def add_rate_data(multiple_job_titles, result):
    try:
        for row in multiple_job_titles:
            for res in result:
                time = datetime.datetime.strptime(str(row.job_start_time), "%H:%M:%S")
                if row.select_job == res["job_title"] and time.strftime("%H:%M") == res["start_time"]:
                    res["bill_rate"] = row.per_hour
                    res["flat_rate"] = row.flat_rate
    except Exception as e:
        print(e, frappe.get_traceback())
