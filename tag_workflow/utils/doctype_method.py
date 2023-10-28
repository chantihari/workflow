import frappe
from frappe import _
import re
from .notification import ses_email_send
from frappe import enqueue, msgprint
from frappe.utils import (cint, flt, get_formatted_email, cstr, unique)
from erpnext.projects.doctype.timesheet.timesheet import get_activity_cost
from frappe.utils.global_search import update_global_search
from frappe.utils.password import update_password as _update_password
from hrms.hr.utils import validate_active_employee
from frappe.permissions import (
	add_user_permission,
	has_permission,
	set_user_permission_if_allowed,
)
# user method update
STANDARD_USERS = ("Guest", "Administrator")
Abbr = "Abbreviation is mandatory"

def validate_username(self):
    if not self.username and self.is_new() and self.first_name:
        self.username = frappe.scrub(self.first_name)

    if not self.username:
        return

    username = self.suggest_username()
    self.username = username

def suggest_username(self):
    def _check_suggestion(suggestion):
        if self.username != suggestion and not self.username_exists(suggestion):
            return suggestion
        return None

    # @firstname
    username = _check_suggestion(frappe.scrub(self.first_name))

    if not username:
        # @firstname_last_name
        username = _check_suggestion(frappe.scrub("{0} {1}".format(self.first_name, self.last_name or "")))

    return username


def send_login_mail(self, subject, template, add_args, now=None):
    """send mail with login details"""
    from frappe.utils.user import get_user_fullname
    from frappe.utils import get_url

    created_by = get_user_fullname(frappe.session['user'])
    if created_by == "Guest":
        created_by = "Administrator"

    args = {
            'first_name': self.first_name or self.last_name or "user",
            'user': self.name,
            'title': subject,
            'login_url': get_url(),
            'created_by': created_by
    }

    args.update(add_args)
    print(now)
    onboard = 0
    company, email = "", ""
    parent = frappe.db.get_value("Company", self.company, "parent_staffing")
    user_list = frappe.db.get_all("User", {"company": self.company}, "name")
    if(parent and (len(user_list) <= 1)):
        onboard = 1
        company = parent
        email = self.name
        subject = "Notification from TAG"
    else:
        subject = "Welcome to TAG! Account Verification"

    args.update({"onboard": onboard, "company": company, "email": email})

    sender = frappe.session.user not in STANDARD_USERS and get_formatted_email(frappe.session.user) or None
     # frappe.sendmail(recipients=self.email, sender=sender, subject=subject, template=template, args=args, header="", delayed=(not now) if now!=None else self.flags.delay_emails, retry=3)
    ses_email_send(emails=self.email,subject=subject,args=args,template=template,sender_full_name=sender,sender=sender)
# document method update
def raise_no_permission_to(self,perm_type):
    print(perm_type)
    """Raise `frappe.PermissionError`."""
    if(self.doctype not in ["Company", "Assign Employee", "Sales Invoice", "Job Site", "Item","File"]):
        frappe.flags.error_message = _('Insufficient Permission for {0}, {1}').format(self.doctype, self.owner)
        raise frappe.PermissionError

#validate_duplicate_user_id
def validate_duplicate_user_id(self):
    sql = """select name from `tabEmployee` where user_id = "{0}" and status = 'Active' and name != '{1}' """.format(self.user_id, self.name)
    employee = frappe.db.sql_list(sql)
    print(employee)


# abbr validation
def append_number_if_name_exists(doctype, value, fieldname="abbr", separator="-", filters=None):
    if not filters:
        filters = dict()
    filters.update({fieldname: value})
    if doctype=='Job Site':
        exists=frappe.db.sql('select name from `tabJob Site` where name like "%{0}%"'.format(value))
    else:
        exists = frappe.db.exists(doctype, filters)
    regex = "^{value}{separator}\\d+$".format(value=re.escape(value), separator=separator)
    
    if(exists):
        sql = """SELECT `{fieldname}` FROM `tab{doctype}` WHERE `{fieldname}` {regex_character} %s ORDER BY length({fieldname}) DESC, `{fieldname}` DESC LIMIT 1""".format(doctype=doctype, fieldname=fieldname, regex_character=frappe.db.REGEX_CHARACTER)
        last = frappe.db.sql(sql, regex)

        if last:
            count = str(cint(last[0][0].rsplit(separator, 1)[1]) + 1)
        else:
            count = "1"

        value = "{0}{1}{2}".format(value, separator, count)
    return value


def validate_abbr(self):
    if not self.abbr:
        self.abbr = ''.join(c[0] for c in self.company_name.split()).upper()
    self.name = self.name.replace('"', "'")
    self.abbr = self.abbr.strip()

    if not self.abbr.strip():
        frappe.throw(_(Abbr))
    sql = """ select abbr from tabCompany where name != "{0}" and abbr = "{1}" """.format(self.name, self.abbr)
    if frappe.db.sql(sql):
        self.abbr = append_number_if_name_exists("Company", self.abbr, fieldname="abbr", separator="-", filters=None)

#-----navbar settings-------#
def validate_standard_navbar_items(self):
    doc_before_save = self.get_doc_before_save()
    print(doc_before_save)

#------crm contact------#
def create_contact(self):
    if not self.lead_name:
        self.set_full_name()
        self.set_lead_name()

    contact = frappe.new_doc("Contact")
    contact.update({
        "first_name": self.first_name or self.lead_name,
        "last_name": self.last_name,
        "salutation": self.salutation,
        "gender": self.gender,
        "job_title": self.job_title,
        "company_name": self.company_name,
        "email_address": self.email_id,
        "phone_number": self.phone_no
    })

    if self.company:
        contact.company = self.company
    else:
        contact.company = "TAG"

    if self.email_id:
        contact.append("email_ids", {
            "email_id": self.email_id,
            "is_primary": 1
        })

    if self.phone:
        contact.append("phone_nos", {
            "phone": self.phone_no,
            "is_primary_phone": 1
        })

    if self.mobile_no:
        contact.append("phone_nos", {
            "phone": self.mobile_no,
            "is_primary_mobile_no":1
        })
    contact.insert(ignore_permissions=True)
    contact.reload()  # load changes by hooks on contact
    return contact

#-------timesheet------#
def get_bill_cost(rate, data):
    bill_rate = flt(rate.get('billing_rate')) if flt(data.billing_rate) == 0 else data.billing_rate
    cost_rate = flt(rate.get('costing_rate')) if flt(data.costing_rate) == 0 else data.costing_rate
    return bill_rate, cost_rate

def update_cost(self):
    for data in self.time_logs:
        if data.activity_type or data.is_billable:
            rate = get_activity_cost(self.employee, data.activity_type)
            hours = data.billing_hours or 0
            costing_hours = data.billing_hours or data.hours or 0
            if rate and self.no_show == 0 and hours > 0:
                bill_rate, cost_rate = get_bill_cost(rate, data)
                data.billing_rate = bill_rate
                data.costing_rate = cost_rate
                data.billing_amount = self.timesheet_billable_amount
                data.payable_amount = self.timesheet_payable_amount
                data.costing_amount = data.costing_rate * costing_hours
                data.base_billing_amount = data.billing_amount
                data.extra_hours=self.overtime_timesheet_hours1
                if data.extra_hours == float(0):
                    data.extra_rate = float(0)
            else:
                data.billing_amount = 0.00
                data.base_billing_amount = 0.00

def validate_mandatory_fields(self):
    for data in self.time_logs:
        if not data.from_time and not data.to_time and self.replaced == 0 and self.no_show == 0:
            frappe.throw(_("Row {0}: From Time and To Time is mandatory.").format(data.idx))

        if not data.activity_type and self.employee:
            frappe.throw(_("Row {0}: Activity Type is mandatory.").format(data.idx))

def run_post_save_methods(self):
    self.get_doc_before_save()

    if self._action=="save":
        self.run_method("on_update")
    elif self._action=="submit":
        self.run_method("on_update")
        self.run_method("on_submit")
    elif self._action=="cancel":
        self.run_method("on_cancel")
        self.check_no_back_links_exist()
    elif self._action=="update_after_submit":
        self.run_method("on_update_after_submit")

    self.clear_cache()
    self.notify_update()

    if(self.doctype != "Timesheet"):
        update_global_search(self)

    self.save_version()
    self.run_method('on_change')

    if (self.doctype, self.name) in frappe.flags.currently_saving:
        frappe.flags.currently_saving.remove((self.doctype, self.name))
    self.latest = None


#---------------------------------------------------------#
def check_islatest(self):
    modified = frappe.db.sql("""select value from tabSingles where doctype=%s and field='modified' for update""", self.doctype)
    modified = modified and modified[0][0]
    if modified and modified != cstr(self._original_modified):
        return True, modified
    return False, modified

def check_ismodify(self):
    tmp = frappe.db.sql("""select modified, docstatus from `tab{0}` where name = %s for update""".format(self.doctype), self.name, as_dict=True)
    if not tmp:
        frappe.throw(_("Record does not exist"))
    else:
        tmp = tmp[0]

    modified = cstr(tmp.modified)
    if modified and modified != cstr(self._original_modified):
        return True, tmp, modified
    return False, tmp, modified

def check_if_latest(self):
		"""Checks if `modified` timestamp provided by document being updated is same as the
		`modified` timestamp in the database. If there is a different, the document has been
		updated in the database after the current copy was read. Will throw an error if
		timestamps don't match.

		Will also validate document transitions (Save > Submit > Cancel) calling
		`self.check_docstatus_transition`."""

		self.load_doc_before_save(raise_exception=True)

		self._action = "save"
		previous = self._doc_before_save

		# previous is None for new document insert
		if not previous:
			self.check_docstatus_transition(0)
			return

		if cstr(previous.modified) != cstr(self._original_modified) and self.doctype not in ["Company", "Employee", "Job Order", "Assign Employee", "User", "Lead", "Timesheet", "Employee Onboarding", "Contract", "Claim Order"]:
			frappe.msgprint(
				_("Error: Document has been modified after you have opened it")
				+ (f" ({previous.modified}, {self.modified}). ")
				+ _("Please refresh to get the latest document."),
				raise_exception=frappe.TimestampMismatchError,
			)

		if not self.meta.issingle:
			self.check_docstatus_transition(previous.docstatus)
#-----------------------------------------------------#
@frappe.whitelist()
def checkingjobsite(job_site):
    job_site = job_site.strip()
    if not job_site.strip():
        frappe.throw(_(Abbr))
    sql = "select job_site from `tabJob Site` where job_site like '%{0}%' order by name desc ".format(job_site)
    if frappe.db.sql(sql):
        return append_number_if_name_exists("Job Site", job_site, fieldname="job_site", separator="-", filters=None)
    return job_site

@frappe.whitelist()
def checkingdesignation_name(designation_name):
    designation_name = designation_name.strip()
    if not designation_name.strip():
        frappe.throw(_(Abbr))
    sql = "select designation_name from `tabDesignation` where designation_name = '{0}' ".format(designation_name)
    if frappe.db.sql(sql):
        return append_number_if_name_exists("Designation", designation_name, fieldname="designation_name", separator="-", filters=None)
    return designation_name 

@frappe.whitelist()
def checkingjobtitle_name(job_titless):
    job_titless = job_titless.strip()
    if not job_titless.strip():
        frappe.throw(_(Abbr))
    sql = "select job_titless from `tabItem` where job_titless = '{0}' ".format(job_titless)
    if frappe.db.sql(sql):
        return append_number_if_name_exists("Item", job_titless, fieldname="job_titless", separator="-", filters=None)
    return job_titless

@frappe.whitelist()
def check_company_type(company):
    org_type = frappe.db.sql("SELECT organization_type  from tabCompany where LOWER(name) = LOWER('{0}')".format(company.lower()),as_dict=1)
    return org_type

@frappe.whitelist()
def get_staffing_company_data():
    company_type = "Staffing"
    get_user = frappe.db.sql ("select role_profile_name from `tabUser` where name='{0}'".format(frappe.session.user),as_dict=1)
    if get_user[0]['role_profile_name'] == "Staffing Admin":
        sql = frappe.db.sql("select company_name from `tabCompany` where modified_by = '{0}' and organization_type='{1}'".format(frappe.session.user,company_type))
        if len(sql) == 1:
            data = list(sql)
            return  data
        else:
            blankdata=tuple(' ',)
            data = list(sql)
            data.insert(0,blankdata)
            return  data
    else:
        sql = frappe.db.sql("select company_name from `tabCompany` where organization_type = '{0}'".format(company_type))
        blankdata=tuple(' ',)
        data = list(sql)
        data.insert(0,blankdata)
        return  data


@frappe.whitelist()
def get_hiring_company_data():
    company_type = "Hiring"
    sql = frappe.db.sql("select company_name from `tabCompany` where organization_type = '{0}'".format(company_type))
    blankdata=tuple(' ',)
    data = list(sql)
    data.insert(0,blankdata)
    return  data

@frappe.whitelist()
def check_payrates_data(name):
    sql = frappe.db.sql("select name from `tabPay Rates` where name='{0}' and job_order is not null ".format(name))
    if sql:
        return True
    return False

def send_password_notification(self, new_password):
    try:
        if self.flags.in_insert and self.name not in STANDARD_USERS:
            if new_password:
                # new password given, no email required
                _update_password(
                    user=self.name, pwd=new_password, logout_all_sessions=self.logout_all_sessions
                )

            if not self.flags.no_welcome_mail and cint(self.send_welcome_email):
                self.send_welcome_mail_to_user()
                self.flags.email_sent = 1
                if frappe.session.user != "Guest":
                    msgprint(_("Welcome email sent"))
        else:
            self.email_new_password(new_password)

    except frappe.OutgoingEmailError:
        # email server not set, don't send email
        self.log_error("Unable to send new password notification")

#------------------------------------------SalarySlip-----------------------------------------#

def calculate_total_for_salary_slip_based_on_timesheet(self):
    ttl_amount = 0
    if self.timesheets:
        self.total_working_hours = 0
        for timesheet in self.timesheets:
            if timesheet.working_hours:
                self.total_working_hours += timesheet.working_hours
                ttl_amount += timesheet.pay_amounts

    wages_amount = self.total_working_hours * self.hour_rate
    self.base_hour_rate = flt(self.hour_rate) * flt(self.exchange_rate)
    salary_component = frappe.db.get_value('Salary Structure', {'name': self.salary_structure}, 'salary_component')
    if self.earnings:
        for i, earning in enumerate(self.earnings):
            if earning.salary_component == salary_component:
                self.earnings[i].amount = wages_amount
            self.gross_pay += self.earnings[i].amount
    self.net_pay = flt(self.gross_pay) - flt(self.total_deduction)
    if(self.salary_structure == "Temporary Employees_"+self.company):
        self.net_pay = ttl_amount
        self.gross_pay = ttl_amount
    
    


def set_time_sheet(self):
    if self.salary_slip_based_on_timesheet:
        self.set("timesheets", [])
        timesheets = frappe.db.sql(""" select * from `tabTimesheet` where employee = %(employee)s and start_date BETWEEN %(start_date)s AND %(end_date)s and (status = 'Submitted' or
            status = 'Billed')""", {'employee': self.employee, 'start_date': self.start_date, 'end_date': self.end_date}, as_dict=1)

        for data in timesheets:
            self.append('timesheets', {
                'time_sheet': data.name,
                'working_hours': data.total_hours,
                'pay_rate': data.employee_pay_rate,
                'job_order': data.job_order_detail,
                'pay_amounts':data.total_job_order_payable_amount

            })

def salary_slip_validate(self):
    self.currency = frappe.db.get_value('Global Defaults','Global Defaults',"default_currency")
    self.status = self.get_status()
    validate_active_employee(self.employee)
    self.validate_dates()
    self.check_existing()
    if not self.salary_slip_based_on_timesheet:
        self.get_date_details()

    if not (len(self.get("earnings")) or len(self.get("deductions"))):
        # get details from salary structure
        self.get_emp_and_working_day_details()
    else:
        self.get_working_days_details(lwp = self.leave_without_pay)

    self.calculate_net_pay()
    self.compute_year_to_date()
    self.compute_month_to_date()
    self.compute_component_wise_year_to_date()
    self.add_leave_balances()
    if self.salary_structure == "Temporary Employees_"+self.company:
        self.set_totals()
    

    if frappe.db.get_single_value("Payroll Settings", "max_working_hours_against_timesheet"):
        max_working_hours = frappe.db.get_single_value("Payroll Settings", "max_working_hours_against_timesheet")
        if self.salary_slip_based_on_timesheet and (self.total_working_hours > int(max_working_hours)):
            frappe.msgprint(_("Total working hours should not be greater than max working hours {0}").
                            format(max_working_hours), alert=True)

def update_user_permissions(self):
    try:
        if not self.create_user_permission: return
        if not has_permission('User Permission', ptype='write', raise_exception=False): return
        employee_user_permission_exists = frappe.db.exists('User Permission', {
            'allow': 'Employee',
            'for_value': self.name,
            'user': self.user_id
		})
        if employee_user_permission_exists: return
        user_type= frappe.db.get_value('User',{'name':self.user_id},'tag_user_type') or None
        if not user_type:
            add_user_permission("Employee", self.name, self.user_id)
            set_user_permission_if_allowed("Company", self.company, self.user_id)
    except Exception as e:
        frappe.log_error(e,'update_permission_error')


def get_data_as_docs(self):
    def format_column_name(df):
        return "`tab{0}`.`{1}`".format(df.parent, df.fieldname)
    filters = self.export_filters
    if self.meta.is_nested_set():
        order_by = "`tab{0}`.`lft` ASC".format(self.doctype)
    else:
        order_by = "`tab{0}`.`creation` DESC".format(self.doctype)

    parent_fields = [
        format_column_name(df) for df in self.fields if df.parent == self.doctype
    ]
    company = "Temporary Assistance Guru LLC"
    if self.doctype == "Employee":
        parent_data = frappe.db.sql("select * from `tabEmployee` where email='JDoe@example.com' and company='{0}'".format(company),as_dict=1)
    elif self.doctype == "Contact":
        contact_data  = frappe.db.sql("select * from `tabContact` where email_address='JDoe@example.com' and owner_company='{0}'".format(company),as_dict=1)
        del_key = 'name'
        for data in contact_data:
            if del_key in data:
                del data[del_key]
        parent_data = contact_data
    else:
        parent_data = frappe.db.get_list(
                self.doctype,
                filters=filters,
                fields=["name"] + parent_fields,
                limit_page_length=self.export_page_length,
                order_by=order_by,
                as_list=0,
            )
    parent_names = [p.name for p in parent_data]
    child_data = {}
    for key in self.exportable_fields:
        if key == self.doctype:
            continue
        child_table_df = self.meta.get_field(key)
        child_table_doctype = child_table_df.options
        child_fields = ["name", "idx", "parent", "parentfield"] + list(
            set(
                [format_column_name(df) for df in self.fields if df.parent == child_table_doctype]
            )
        )
        data = frappe.db.get_list(
            child_table_doctype,
            filters={
                "parent": ("in", parent_names),
                "parentfield": child_table_df.fieldname,
                "parenttype": self.doctype,
            },
            fields=child_fields,
            order_by="idx asc",
            as_list=0,
        )
        child_data[key] = data

    grouped_children_data = self.group_children_data_by_parent(child_data)
    for doc in parent_data:
        related_children_docs = grouped_children_data.get(doc.name, {})
        yield {**doc, **related_children_docs}


def validate_employee_roles(doc,method):
	# called via User hook
	print(method)
	if "Employee" in [d.role for d in doc.get("roles")]:
		if not frappe.db.get_value("Employee", {"user_id": doc.name}):
			doc.get("roles").remove(doc.get("roles", {"role": "Employee"})[0])

def create_task_and_notify_user(self):
    # create the task for the given project and assign to the concerned person
    if self.holiday_list:
        holiday_list = self.get_holiday_list()

    for activity in self.activities:
        if activity.task:
            continue
        
        values = {
            "doctype": "Task",
            "project": self.project,
            "subject": activity.activity_name + " : " + self.employee_name,
            "description": activity.description,
            "department": self.department,
            "company": self.company,
            "task_weight": activity.task_weight			
        }

        if self.holiday_list:
            dates = self.get_task_dates(activity, holiday_list)
            values["exp_start_date"] = dates[0]
            values["exp_end_date"] = dates[1]

        task = frappe.get_doc(values).insert(ignore_permissions=True)
        activity.db_set("task", task.name)

        users = [activity.user] if activity.user else []
        if activity.role:
            user_list = frappe.db.sql_list(
                """
                SELECT
                    DISTINCT(has_role.parent)
                FROM
                    `tabHas Role` has_role
                        LEFT JOIN `tabUser` user
                            ON has_role.parent = user.name
                WHERE
                    has_role.parenttype = 'User'
                        AND user.enabled = 1
                        AND has_role.role = %s
            """,
                activity.role,
            )
            users = unique(users + user_list)

            if "Administrator" in users:
                users.remove("Administrator")

        # assign the task the users
        if users:
            self.assign_task_to_users(task, users)
