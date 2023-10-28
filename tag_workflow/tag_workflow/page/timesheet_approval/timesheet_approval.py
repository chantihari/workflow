import frappe
from frappe import _
import json, ast
from frappe.share import add_docshare as add
from tag_workflow.utils.timesheet import (
    approval_notification,
    denied_notification
)
from tag_workflow.tag_data import check_mandatory_field
from tag_workflow.tag_workflow.doctype.job_order.job_order import prepare_invoice
import ast
import json

jobOrder = "Job Order"


# -----------------------------#
def get_status(order, company, date):
    sheets = frappe.db.get_list(
        "Timesheet",
        {
            "job_order_detail": order,
            "employee_company": company,
            "date_of_timesheet": date,
        },
        "workflow_state",
    )
    status = [s["workflow_state"] for s in sheets]
    if "Approval Request" in status:
        return "Approval Request"
    elif "Denied" in status or "Open" in status:
        return "In Progress"
    elif "Approved" in status:
        return "Approved"


@frappe.whitelist()
def get_data(company, order):
    try:
        result = []
        if not frappe.db.exists("Company", {"name": company}):
            frappe.msgpprint(_("Company not found"))
            return []

        if not frappe.db.exists(
            "Employee", {"company": company, "user_id": frappe.session.user}
        ):
            frappe.msgprint(_("Company and Job Order info doesn't match with you"))
            return []

        job_order_status = frappe.db.get_value(jobOrder, order, "order_status")
        job_order_owner = frappe.db.get_value(jobOrder, order, "owner")
        user_company = frappe.db.get_value(
            "User", {"name": job_order_owner}, "organization_type"
        )
        if user_company == "Staffing":
            data = frappe.db.get_list(
                "Timesheet",
                {"job_order_detail": order, "employee_company": company},
                ["date_of_timesheet", "workflow_state", "job_order_detail", "name"],
                group_by="date_of_timesheet",
                order_by="creation asc",
            )
        else:
            data = frappe.db.get_list(
                "Timesheet",
                {
                    "job_order_detail": order,
                    "employee_company": company,
                    "workflow_state": ["not like", "%Open%"],
                },
                ["date_of_timesheet", "workflow_state", "job_order_detail", "name"],
                group_by="date_of_timesheet",
                order_by="creation asc",
            )

        for d in data:
            d.update({"order_status": job_order_status})
            status = get_status(order, company, d["date_of_timesheet"])
            d.update({"workflow_state": status})
            exported = frappe.db.get_list(
                "Timesheet",
                {
                    "job_order_detail": d["job_order_detail"],
                    "date_of_timesheet": d["date_of_timesheet"],
                },
                ["ts_exported"],
                pluck="ts_exported",
            )
            ts_exported = (
                "Yes" if len(set(exported)) == 1 and exported[0] == 1 else "No"
            )
            d.update({"ts_exported": ts_exported})
            result.append(d)

            if not frappe.db.exists(
                "DocShare",
                {
                    "user": frappe.session.user,
                    "share_name": d["name"],
                    "read": 1,
                    "write": 1,
                    "submit": 1,
                },
            ):
                add(
                    "Timesheet",
                    d.name,
                    user=frappe.session.user,
                    read=1,
                    write=1,
                    submit=1,
                    notify=0,
                    flags={"ignore_share_permission": 1},
                )
        return result
    except Exception as e:
        frappe.msgprint(e)


# -----------------------------------------------#
@frappe.whitelist()
def get_child_data(order, timesheet=None, date=None):
    """
    The function `get_child_data` retrieves timesheet data based on the given order and date, and
    returns the result as a list of dictionaries.

    :param order: The "order" parameter is used to specify the job order detail for which you want to
    retrieve the child data from the Timesheet
    :param timesheet: The `timesheet` parameter is used to specify the name of the timesheet for which
    you want to retrieve child data. It is an optional parameter and can be set to `None` if not
    required
    :param date: The `date` parameter is used to filter the timesheets based on a specific date. If a
    date is provided, the function will retrieve timesheets that have a matching `date_of_timesheet`
    value. If no date is provided or if the value is "null", the function will retrieve all
    :return: a list of dictionaries containing various data related to timesheets.
    """
    try:
        result = []
        company = frappe.db.get_value(
            "Timesheet", {"name": timesheet}, "employee_company"
        )
        job_order_owner = frappe.db.get_value(jobOrder, order, "owner")
        user_company = frappe.db.get_value(
            "User", {"name": job_order_owner}, "organization_type"
        )
        if user_company == "Staffing":
            if date != "null":
                sql = f"""
                    SELECT t.job_name, t.workflow_state, t.name, t.employee, t.employee_name, t.no_show,
                    t.non_satisfactory, t.dnr, t.replaced, t.date_of_timesheet, t.ts_exported
                    c.start_time, c.from_time, c.to_time, c.break_start_time, c.break_end_time, c.hours
                    FROM `tabTimesheet` t INNER JOIN `tabTimesheet Detail` c ON t.name = c.parent
                    LEFT JOIN tabEmployee e ON t.name=e.name
                    WHERE t.job_order_detail = '{order}' AND t.date_of_timesheet = '{date}' AND t.employee_company = "{company}"
                    ORDER BY SUBSTRING_INDEX(t.job_name, '-', 1),
                    CAST(SUBSTRING_INDEX(t.job_name, '-', -1) AS UNSIGNED),
                    e.last_name, e.first_name
                """
            else:
                sql = f"""
                    SELECT t.job_name, t.workflow_state, t.name, t.employee, t.employee_name,
                    t.no_show, t.non_satisfactory, t.dnr, t.replaced, t.date_of_timesheet, t.ts_exported
                    c.start_time, c.from_time, c.to_time, c.break_start_time, c.break_end_time, c.hours
                    FROM `tabTimesheet` t INNER JOIN `tabTimesheet Detail` c ON t.name = c.parent
                    LEFT JOIN tabEmployee e ON t.name=e.name
                    WHERE t.job_order_detail = '{order}' AND t.employee_company = "{company}"
                    ORDER BY SUBSTRING_INDEX(t.job_name, '-', 1), CAST(SUBSTRING_INDEX(t.job_name, '-', -1) AS UNSIGNED)
                    e.last_name, e.first_name
                """
        else:
            if date != "null":
                sql = f"""
                    SELECT t.job_name, t.workflow_state, t.name, t.employee, t.employee_name, t.no_show,
                    t.non_satisfactory, t.dnr, t.replaced, t.date_of_timesheet, t.ts_exported,
                    c.start_time, c.from_time, c.to_time, c.break_start_time, c.break_end_time, c.hours
                    from `tabTimesheet` t INNER JOIN `tabTimesheet Detail` c ON t.name = c.parent
                    LEFT JOIN tabEmployee e ON e.name = t.employee
                    WHERE t.job_order_detail = '{order}' AND t.date_of_timesheet = '{date}' AND t.employee_company = "{company}" AND t.workflow_state!='Open'
                    ORDER BY SUBSTRING_INDEX(t.job_name, '-', 1), CAST(SUBSTRING_INDEX(t.job_name, '-', -1) AS UNSIGNED),
                    e.last_name, e.first_name
                """
            else:
                sql = f"""
                    select t.job_name, t.workflow_state, t.name, t.employee, t.employee_name, t.no_show,
                    t.non_satisfactory, t.dnr, t.replaced, t.date_of_timesheet, t.ts_exported
                    c.start_time, c.from_time, c.to_time, c.break_start_time, c.break_end_time, c.hours
                    FROM `tabTimesheet` t INNER JOIN `tabTimesheet Detail` c ON t.name = c.parent
                    LEFT JOIN tabEmoployee e ON e.name=t.employee
                    WHERE t.job_order_detail = '{order}' AND t.employee_company = "{company}" AND t.workflow_state!='Open'
                    ORDER BY SUBSTRING_INDEX(t.job_name, '-', 1), CAST(SUBSTRING_INDEX(t.job_name, '-', -1) AS UNSIGNED)
                """

        data = frappe.db.sql(sql, as_dict=1)
        for d in data:
            from_time = ":".join(str(d["from_time"]).split(" ").pop().split(":")[:-1])
            to_time = ":".join(str(d["to_time"]).split(" ").pop().split(":")[:-1])
            break_start = ":".join(
                str(d["break_start_time"]).split(" ").pop().split(":")[:-1]
            )
            break_end = ":".join(
                str(d["break_end_time"]).split(" ").pop().split(":")[:-1]
            )
            start_time = ":".join(
                str(d["start_time"]).split(" ").pop().split(":")[:-1]
            ).rjust(5, "0")

            state = employee_status(d)

            result.append(
                {
                    "employee": d["employee"],
                    "employee_name": d["employee_name"],
                    "from_time": from_time,
                    "to_time": to_time,
                    "break_start": break_start,
                    "break_end": break_end,
                    "name": d["name"],
                    "hours": d["hours"],
                    "workflow_state": d["workflow_state"],
                    "state": state,
                    "ts_exported": d["ts_exported"],
                    "job_title": d["job_name"],
                    "start_time": start_time,
                }
            )

            if not frappe.db.exists(
                "DocShare",
                {
                    "user": frappe.session.user,
                    "share_name": d["name"],
                    "read": 1,
                    "write": 1,
                    "submit": 1,
                },
            ):
                add(
                    "Timesheet",
                    d["name"],
                    user=frappe.session.user,
                    read=1,
                    write=1,
                    submit=1,
                    notify=0,
                    flags={"ignore_share_permission": 1},
                )
        return result
    except Exception as e:
        frappe.msgprint(e)


# ------------------------------------------#
@frappe.whitelist()
def approve_timesheets(timesheet, action):
    try:
        data = []
        emp_with_insuficient_details = []
        timesheets = json.loads(timesheet)
        for t in timesheets:
            doc = frappe.get_doc("Timesheet", t)
            emp_fields = check_mandatory_field(doc.employee, 1, "1")
            empty_field_str = ""
            for field in emp_fields:
                empty_field_str += ", " + field.title()
                empty_field_str = empty_field_str.replace("_", " ")
            if emp_fields == "success":
                frappe.db.set_value("Timesheet", t, "workflow_state", action)
                frappe.db.set_value("Timesheet", t, "status", "Submitted")
                frappe.db.set_value("Timesheet", t, "docstatus", 1)
                data.append({"date": doc.date_of_timesheet, "timesheet": t})
            else:
                empty_field_str = empty_field_str[1:]
                emp_with_insuficient_details.append(
                    [doc.employee_name.title(), empty_field_str]
                )
            approval_notification(
                job_order=doc.job_order_detail,
                staffing_company=doc.employee_company,
                date=None,
                hiring_company=doc.company,
                timesheet_name=doc.name,
                timesheet_approved_time=doc.modified,
                current_time=frappe.utils.now(),
            )
        return (
            data[0] if (len(data) > 0) else {"date": "", "timesheet": ""},
            emp_with_insuficient_details,
            len(timesheets),
        )
    except Exception as e:
        frappe.throw(e)


@frappe.whitelist()
def deny_timesheet(data, count):
    try:
        result = []
        data = json.loads(data)
        count = ast.literal_eval(count)
        for c in range(0, len(count)):
            tm = "timesheet" + str(c)
            res = "reason" + str(c)
            if tm in data.keys():
                doc = frappe.get_doc(
                    "Timesheet", {"name": data[tm]}, ignore_permissions=True
                )
                frappe.db.set_value("Timesheet", data[tm], "workflow_state", "Denied")
                frappe.db.set_value("Timesheet", data[tm], "status", "Denied")
                if res in data.keys():
                    if doc.dispute:
                        frappe.db.set_value(
                            "Timesheet",
                            data[tm],
                            "dispute",
                            doc.dispute + "<br>" + "-" * 15 + "<br>" + data[res],
                        )
                    else:
                        frappe.db.set_value("Timesheet", data[tm], "dispute", data[res])
                result.append({"date": doc.date_of_timesheet, "timesheet": doc.name})
                denied_notification(
                    job_order=doc.job_order_detail,
                    staffing_company=doc.employee_company,
                    hiring_company=doc.company,
                    timesheet_name=doc.name,
                )
        return result[0] if (len(result) > 0) else {"date": "", "timesheet": ""}
    except Exception as e:
        frappe.msgprint(e)


# Employee Status
def employee_status(d):
    status = []
    state = ""
    if d.dnr == 1:
        status.append("DNR")
    if d.non_satisfactory == 1:
        status.append("Non Satisfactory")
    if d.no_show == 1:
        status.append("No Show")
    if len(status) > 0:
        state = ",".join(status)
    if d.replaced == 1:
        state = "Replaced"
    return state


@frappe.whitelist()
def get_selected_ts(checkbox_values):
    try:
        ts_list = []
        values = ast.literal_eval(checkbox_values)
        for i in values:
            if "_" in i:
                ts = frappe.db.get_list(
                    "Timesheet",
                    {
                        "date_of_timesheet": i.split("_")[1],
                        "job_order_detail": i.split("_")[0],
                    },
                    ["name"],
                    pluck="name",
                )
                for t in ts:
                    ts_list.append(t)
            elif "TS" in i:
                ts_list.append(i)
        return ts_list
    except Exception as e:
        frappe.log_error(e, "get_selected_ts Error")

@frappe.whitelist(allow_guest=False)
def make_invoice(job_order, staffing_company):
    try:
        if frappe.db.get_value("User", frappe.session.user, "company") != staffing_company:
            frappe.throw("Insufficient Permission for user ", frappe.session.user)
        len_sql = f'''
            SELECT name, total_billable_amount, total_billable_hours, no_show, non_satisfactory, dnr
            FROM `tabTimesheet` where job_order_detail = '{job_order}'
            AND docstatus = 1 AND employee_company="{staffing_company}" AND is_check_in_sales_invoice = 0
            ORDER BY creation
        '''
        timesheet = frappe.db.sql(len_sql, as_dict=1)
        if len(timesheet) < 1:
            frappe.msgprint(
                _(f"Either Invoice For Timesheet OR No Approved Timesheet found for this Job Order(<b>{job_order}</b>)")
            )
        else:
            return prepare_invoice(staffing_company, job_order, timesheet)
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.log_error(e, "make_invoice Error")
