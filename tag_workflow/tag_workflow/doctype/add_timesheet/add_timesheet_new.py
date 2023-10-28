import frappe, datetime
from frappe import enqueue, _

jobOrder = "Job Order"
timesheet_time = "select to_time,from_time from `tabTimesheet Detail` where parent= "
from tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet import (
    get_datetime,
    get_child_time,
    check_old_timesheet,
    check_tip,
    check_day,
    sub_update_timesheet,
    get_billable_unbillable_ot,
)
from tag_workflow.utils.timesheet import (
    remove_job_title,
    unsatisfied_organization,
    do_not_return,
    no_show_org,
)
import json
date_format = "%Y-%m-%d"

@frappe.whitelist()
def check_timesheets(items, job_order, date, from_time, to_time):
    """
    The function `check_timesheets` checks if a timesheet is already available for a given employee, job
    order, date, and time frame.
    
    :param items: The `items` parameter is a JSON string that contains a list of items. Each item in the
    list represents a timesheet entry and has the following properties:
    :param job_order: The `job_order` parameter is the name or identifier of a job order. It is used to
    retrieve information about the job order from the database
    :param date: The `date` parameter represents the date for which the timesheets are being checked
    :param from_time: The `from_time` parameter is the starting time of the time frame for which you
    want to check the timesheets
    :param to_time: The `to_time` parameter is the end time of the time frame for which you want to
    check the timesheets
    :return: either a list of error messages or the string "success".
    """
    try:
        items = json.loads(items)
        msg = check_if_employee_assign(items, job_order) or []
        if msg:
            return msg

        job_doc = frappe.get_doc(jobOrder, {"name": job_order})
        posting_date = datetime.datetime.strptime(date, date_format).date()
        if not job_doc.from_date <= posting_date <= job_doc.to_date:
            return ["Date must be in between Job Order start date and end date for timesheets"]

        from_time, to_time = get_datetime(date, from_time, to_time)
        for item in items:
            child_from, child_to, _, _ = get_child_time(date, from_time, to_time, item["from_time"], item["to_time"])
            is_ok = check_old_timesheet(child_from, child_to, item["employee"], item["timesheet_value"])
            
            if is_ok:
                msg.append(f"Timesheet is already available for employee <b>{item['employee_name']}</b>(<b>{item['employee']}</b>) for the given date and time frame.")
        return msg if msg else "success"
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.log_error(e, "check_timesheets error")
        return "fail"


def check_if_employee_assign(items, job_order):
    try:
        sql = f"""
            SELECT employee
            FROM `tabAssign Employee Details` 
            WHERE parent IN 
            (SELECT name FROM 
            `tabAssign Employee`
            WHERE tag_status = "Approved" 
            AND 
            job_order = '{job_order}')
            UNION
            SELECT employee 
            FROM `tabReplaced Employee` 
            WHERE parent IN 
            (SELECT name 
            FROM `tabAssign Employee` 
            WHERE tag_status = "Approved" 
            AND 
            job_order = '{job_order}')
        """
        result = frappe.db.sql(sql, as_list=1)
        result = [r[0] for r in result]

        msg = [
            _(
                "Employee with ID <b>{0}</b> not assigned to this Job Order(<b>{1}</b>). Please fill the details correctly and re-submit timesheets"
            ).format(item["employee"], job_order)
            for item in items
            if item["employee"] not in result
        ]

        return msg
    except Exception as e:
        print(e, frappe.get_traceback())
        return False


@frappe.whitelist()
def create_new_timesheet(selected_items, job_order, date, from_time, to_time, break_from_time, break_to_time):
    """
    The function `create_new_timesheet` creates a new timesheet based on the selected items, job order,
    date, from time, and to time.
    
    :param selected_items: A list of selected items. It should be in JSON format
    :param job_order: The `job_order` parameter is the identifier of the job order for which the
    timesheet is being created. It is used to retrieve the job order document from the database
    :param date: The date parameter represents the date of the timesheet
    :param from_time: The "from_time" parameter in the "create_new_timesheet" function represents the
    starting time of the timesheet entry
    :param to_time: The "to_time" parameter in the "create_new_timesheet" function is the end time of
    the timesheet entry. It represents the time when the work for the selected item was completed
    :return: The function `create_new_timesheet` returns two values: `item_list` and `ts_name`.
    """
    try:
        job_doc = frappe.get_doc(jobOrder, job_order)
        selected_items = json.loads(selected_items)
        posting_date = datetime.datetime.strptime(date, date_format).date()
        ts_name = []
        item_list = []
        for index, item in enumerate(selected_items):
            frappe.publish_progress(
                percent=(index+1)/len(selected_items)*100,
                title=_("Creating Timesheets..."),
            )
            tip_amount = check_tip(item)
            last_sat = check_day(posting_date)
            emp_pay_rate = item["pay_rate"]
            child_from, child_to, break_from, break_to = get_child_time(
                date,
                from_time,
                to_time,
                item["from_time"],
                item["to_time"],
                item["break_from"] if "break_from" in item else None,
                item["break_to"] if "break_to" in item else None,
            )
            timesheet = timesheet_data(
                item,
                job_order,
                job_doc,
                tip_amount,
                break_from,
                break_to,
                posting_date,
                child_from,
                child_to,
                date,
                last_sat,
                emp_pay_rate,
            )
            ts_name.append(timesheet.name)
            item_list.append([item["name"], timesheet.name])
        enqueue(
            "tag_workflow.tag_workflow.doctype.add_timesheet.add_timesheet.draft_ts_time",
            start_time=from_time,
            end_time=to_time,
            break_from=break_from_time,
            break_to=break_to_time,
            job_order=job_order,
            date_of_ts=date,
            ts_name=ts_name,
            now=True,
        )
        return item_list
    except Exception as e:
        print(frappe.get_traceback())
        frappe.log_error(e, "Create New Timesheet Error")


def timesheet_data(
    item,
    job_order,
    job_doc,
    tip_amount,
    break_from,
    break_to,
    posting_date,
    child_from,
    child_to,
    date,
    last_sat,
    emp_pay_rate,
):
    """
    The function `timesheet_data` creates or updates a timesheet document with various details such as
    job order, job document, tip amount, break times, posting date, child times, date, last Saturday,
    employee pay rate, and more.
    
    :param item: A dictionary containing information about the timesheet item, such as employee, hours
    worked, bill rate, etc
    :param job_order: The job order is a unique identifier for a specific job or project. It helps to
    track and manage the tasks, resources, and timeline associated with that job
    :param job_doc: The `job_doc` parameter is a document that contains information about a job order.
    It is used to retrieve details such as the company, from_date, to_date, order_status, and other
    relevant information for creating a timesheet
    :param tip_amount: The tip amount is the additional amount of money given to the employee as a tip
    for their service
    :param break_from: The parameter "break_from" represents the start time of the break during the
    timesheet entry
    :param break_to: The parameter "break_to" represents the end time of a break during the timesheet
    entry
    :param posting_date: The date on which the timesheet is being posted
    :param child_from: The parameter "child_from" represents the starting time of the work shift for the
    employee
    :param child_to: The parameter `child_to` represents the end time of a task or activity in the
    timesheet
    :param date: The date parameter represents the date of the timesheet
    :param last_sat: The parameter "last_sat" is used to specify the date of the last Saturday. It is
    used in the calculation of overtime hours in the function
    :param emp_pay_rate: The `emp_pay_rate` parameter represents the pay rate of the employee
    :return: a Timesheet document.
    """
    (
        week_all_hours,
        all_job_hours,
        week_hiring_hours,
    ) = timesheet_billing_hours(
        job_doc=job_doc,
        timesheet_date=posting_date,
        last_sat=last_sat,
        employee=item["employee"],
        user=frappe.session.user,
        from_time=child_from,
    )
    cur_timesheet_hours = item["hours"]
    overtime_current_job_hours_val, todays_overtime_hours = overall_overtime(
        job_order_vals=job_doc,
        timesheet_date=posting_date,
        working_hours=cur_timesheet_hours,
        employee=item["employee"],
        from_time=child_from,
        last_sat=last_sat,
    )
    (
        overtime_hours,
        overtime_all_hours,
        overtime_hiring_hours,
        hiring_timesheet_oh,
    ) = sub_update_timesheet(cur_timesheet_hours, week_all_hours, week_hiring_hours)
    job_title_time = item["job_title_time"].split(", ")
    start_time = job_title_time[-1]
    job_title = ", ".join(job_title_time[:-1])
    if item["timesheet_value"] and len(item["timesheet_value"]) > 0:
        timesheet = frappe.get_doc("Timesheet", item["timesheet_value"])
        timesheet.set("time_logs", [])
    else:
        timesheet = frappe.get_doc(
            dict(
                doctype="Timesheet",
                company=job_doc.company,
                job_order_detail=job_order,
                employee=item["employee"],
                from_date=job_doc.from_date,
                to_date=job_doc.to_date,
                job_name=job_title,
                per_hour_rate=item["bill_rate"],
                flat_rate=item["flat_rate"],
                status_of_work_order=job_doc.order_status,
                date_of_timesheet=date,
                timesheet_hours=cur_timesheet_hours,
                total_weekly_hours=week_all_hours + cur_timesheet_hours,
                current_job_order_hours=all_job_hours + cur_timesheet_hours,
                overtime_timesheet_hours=overtime_hours,
                total_weekly_overtime_hours=overtime_all_hours,
                cuurent_job_order_overtime_hours=float(overtime_current_job_hours_val),
                total_weekly_hiring_hours=week_hiring_hours + cur_timesheet_hours,
                total_weekly_overtime_hiring_hours=overtime_hiring_hours,
                overtime_timesheet_hours1=hiring_timesheet_oh,
                billable_weekly_overtime_hours=overtime_hiring_hours,
                unbillable_weekly_overtime_hours=overtime_all_hours
                - overtime_hiring_hours,
                employee_pay_rate=emp_pay_rate,
                todays_overtime_hours=todays_overtime_hours,
            )
        )
    flat_rate = item["flat_rate"] + tip_amount
    timesheet = update_billing_payroll_details(
        timesheet_doc=timesheet,
        job_doc=job_doc,
        timesheet_date=posting_date,
        employee=item["employee"],
        working_hours=float(item["hours"]),
        total_flat_rate=flat_rate,
        per_hour=item["bill_rate"],
        from_time=child_from,
        last_sat=last_sat,
        emp_pay_rate=emp_pay_rate,
    )
    timesheet.append(
        "time_logs",
        {
            "activity_type": job_title,
            "start_time": start_time,
            "from_time": child_from,
            "to_time": child_to,
            "hrs": str(item["hours"]) + " hrs",
            "hours": float(item["hours"]),
            "is_billable": 1,
            "billing_rate": item["bill_rate"],
            "tip": tip_amount,
            "flat_rate": flat_rate,
            "break_start_time": break_from,
            "break_end_time": break_to,
            "extra_hours": float(item["overtime_hours"]),
            "extra_rate": float(item["overtime_rate"]),
            "pay_amount": timesheet.timesheet_payable_amount,
            "billing_amount": float(item["amount"]),
            "billing_hours": float(item["hours"])
        },
    )
    timesheet = add_status(timesheet, item["status"])
    if item["timesheet_value"] and len(item["timesheet_value"]) > 0:
        timesheet.save(ignore_permissions=True)
    else:
        timesheet.insert(ignore_permissions=True)
    return timesheet


def timesheet_billing_hours(
    job_doc, timesheet_date, last_sat, employee, user, from_time, timesheet=None
):
    """
    The function `timesheet_billing_hours` retrieves the total hours worked by an employee on different
    categories of jobs within a specified time period.
    
    :param job_doc: The `job_doc` parameter is a document that represents a job order. It contains
    information about the job, such as the job name, job details, and job dates
    :param timesheet_date: The date of the timesheet for which you want to calculate the billing hours
    :param last_sat: The parameter "last_sat" represents the date of the last Saturday
    :param employee: The employee parameter is the name of the employee for whom you want to calculate
    the billing hours
    :param user: The `user` parameter represents the email address of the user for whom the timesheet
    billing hours are being calculated
    :param from_time: The `from_time` parameter is the time until which the timesheet details should be
    considered
    :param timesheet: The `timesheet` parameter is the name of a specific timesheet
    :return: three values: week_all_hours, all_job_hours, and week_hiring_hours.
    """
    sql = f"\
        SELECT IFNULL(SUM(TS.total_hours), 0) AS total_hours FROM `tabTimesheet` AS TS, `tabTimesheet Detail` AS TD WHERE TS.name=TD.parent AND employee='{employee}' AND date_of_timesheet BETWEEN '{last_sat}' AND '{timesheet_date}' AND TS.name !='{timesheet}' AND TD.to_time<'{from_time}' AND TS.workflow_state!='Open' \
        UNION ALL \
        SELECT IFNULL(SUM(TS.total_hours), 0) AS total_hours FROM `tabTimesheet` AS TS, `tabTimesheet Detail` AS TD WHERE TS.name=TD.parent AND employee='{employee}' AND job_order_detail='{job_doc.name}' AND TS.name !='{timesheet}' AND date_of_timesheet BETWEEN '{job_doc.from_date}' AND '{timesheet_date}' AND TD.to_time<'{from_time}' AND TS.workflow_state!='Open' \
        UNION ALL \
        SELECT IFNULL(SUM(TS.total_hours), 0) AS total_hours FROM `tabTimesheet` AS TS, `tabTimesheet Detail` AS TD WHERE TS.name=TD.parent AND employee='{employee}' AND date_of_timesheet BETWEEN '{last_sat}' AND '{timesheet_date}' AND TS.name !='{timesheet}' AND TD.to_time<'{from_time}' AND TS.workflow_state!='Open' AND company IN (SELECT company FROM `tabEmployee` WHERE email= '{user}')"

    data = frappe.db.sql(sql, as_dict=1)

    week_all_hours = data[0]["total_hours"] or 0
    all_job_hours = data[1]["total_hours"] or 0
    week_hiring_hours = data[2]["total_hours"] or 0

    return week_all_hours, all_job_hours, week_hiring_hours


def all_week_jo(employee, jo, timesheet_date, from_time):
    """
    Get min and max date of timesheet where employee and job order is given and it is not in open state
    """
    sql = f" select min(date_of_timesheet) as min_date, max(date_of_timesheet) as max_date from `tabTimesheet` where employee='{employee}' and job_order_detail='{jo}' and workflow_state!='Open'"
    data = frappe.db.sql(sql, as_dict=1)
    d1 = data[0]["min_date"]
    d2 = timesheet_date
    if d1 and d2:
        last_saturday = check_day(d2)
        week_oh = 0
        day_name1 = d2.strftime("%A")
        if day_name1 != "Friday":
            last_sql = f" select sum(TS.total_hours) as total_hours from `tabTimesheet` as TS, `tabTimesheet Detail` as TD where TS.name=TD.parent and employee='{employee}' and date_of_timesheet between '{last_saturday}' and '{d2}' and job_order_detail='{jo}' and TD.to_time<'{from_time}' and TS.workflow_state!='Open' "
            last_data = frappe.db.sql(last_sql, as_dict=1)
            if (
                len(last_data) > 0
                and last_data[0]["total_hours"] is not None
                and last_data[0]["total_hours"] > 40
            ):
                week_oh += last_data[0]["total_hours"] - 40

        week_oh = sub_all_week_jo(week_oh, d1, d2, employee, jo, from_time)
        return week_oh
    else:
        week_oh = 0
        return week_oh


def sub_all_week_jo(week_oh, d1, d2, employee, jo, from_time):
    dates = [
        datetime.date.fromordinal(d_ord)
        for d_ord in range(d1.toordinal(), d2.toordinal() + 1)
        if (datetime.date.fromordinal(d_ord).weekday() == 4)
    ]

    if len(dates) > 0:
        for i in dates:
            last_sat = i - datetime.timedelta(days=i.weekday() + 2)

            week_sql = f" select sum(TS.total_hours) as total_hours from `tabTimesheet` as TS, `tabTimesheet Detail` as TD where TS.name=TD.parent and employee='{employee}' and date_of_timesheet between '{last_sat}' and '{i}' and job_order_detail='{jo}' and TD.to_time<'{from_time}' and TS.workflow_state!='Open' "
            week_data = frappe.db.sql(week_sql, as_dict=1)

            if (
                week_data[0]["total_hours"] is not None
                and week_data[0]["total_hours"] > 40
            ):
                oh = week_data[0]["total_hours"] - 40
                week_oh += oh
        return week_oh
    return week_oh


def overall_overtime(
    job_order_vals,
    timesheet_date,
    employee,
    working_hours,
    from_time,
    last_sat,
    timesheet=None,
):
    """Called multiple times"""
    """How to handle if timesheet is none when called from timesheet_data where timesheet is not even created yet."""
    hiring_company = job_order_vals.company
    sql = f"""\
        SELECT SUM(TS.total_hours) AS total_hours FROM `tabTimesheet` AS TS, `tabTimesheet Detail` AS TD WHERE TS.name=TD.parent AND employee='{employee}' AND (date_of_timesheet BETWEEN '{last_sat}' AND '{timesheet_date}') AND company='{hiring_company}' AND TS.name !='{timesheet}' AND job_order_detail='{job_order_vals.name}' AND TD.to_time<'{from_time}' AND TS.workflow_state!='Open' \
        UNION ALL
        SELECT SUM(TS.todays_overtime_hours) AS total_hours FROM `tabTimesheet` AS TS, `tabTimesheet Detail` AS TD WHERE TS.name=TD.parent AND employee='{employee}' AND (date_of_timesheet BETWEEN '{job_order_vals.from_date}' AND '{timesheet_date}') AND company='{hiring_company}' AND TS.name !='{timesheet}' AND job_order_detail='{job_order_vals.name}' AND TD.to_time<'{from_time}' AND TS.workflow_state!='Open'
    """
    result = frappe.db.sql(sql, as_dict=1)
    weekly_hours = result[0].total_hours if result[0].total_hours is not None else 0.00
    worked_time = float(weekly_hours) + float(working_hours)

    current_week_overtime = 0
    if weekly_hours <= 40:
        if (worked_time) <= 40:
            current_week_overtime = 0
        else:
            current_week_overtime = worked_time - 40
    else:
        current_week_overtime = working_hours
    current_timesheet_overtime_hours = (
        result[1].total_hours if result[1].total_hours is not None else 0.00
    )
    current_timesheet_overtime_hours = (
        current_timesheet_overtime_hours + current_week_overtime
    )
    return current_timesheet_overtime_hours, current_week_overtime


def update_billing_payroll_details(
    timesheet_doc,
    job_doc,
    timesheet_date,
    employee,
    working_hours,
    total_flat_rate,
    per_hour,
    from_time,
    last_sat,
    emp_pay_rate,
):
    (
        timesheet_billed_amount,
        timesheet_overtime_bill,
        total_job_amount,
        total_overtime_job_amount,
    ) = billing_details_data(
        timesheet_doc.name,
        job_doc,
        timesheet_date,
        employee,
        working_hours,
        total_flat_rate,
        per_hour,
        from_time,
        last_sat,
    )
    timesheet_doc.timesheet_billable_amount = timesheet_billed_amount
    timesheet_doc.timesheet_billable_overtime_amount = timesheet_overtime_bill
    timesheet_doc.total_job_order_amount = total_job_amount
    timesheet_doc.total_job_order_billable_overtime_amount_ = total_overtime_job_amount

    (
        timesheet_payable_amount,
        timesheet_ot_billable,
        timesheet_unbillable_ot,
        total_job_payable,
        total_job_billable_ot,
        total_unbillable_ot,
    ) = set_payroll_fields(
        emp_pay_rate,
        job_doc.company,
        employee,
        timesheet_doc.name,
        timesheet_date,
        working_hours,
        from_time,
        last_sat,
        job_doc,
    )
    timesheet_doc.timesheet_payable_amount = timesheet_payable_amount
    timesheet_doc.timesheet_billable_overtime_amount_staffing = timesheet_ot_billable
    timesheet_doc.timesheet_unbillable_overtime_amount = timesheet_unbillable_ot
    timesheet_doc.total_job_order_payable_amount = total_job_payable
    timesheet_doc.total_job_order_billable_overtime_amount = total_job_billable_ot
    timesheet_doc.total_job_order_unbillable_overtime_amount = total_unbillable_ot
    return timesheet_doc


@frappe.whitelist()
def set_payroll_fields(
    pay_rate,
    hiring_company,
    employee,
    timesheet,
    timesheet_date,
    today_hours,
    from_time,
    last_sat,
    job_order_vals,
):
    sql = f"""\
        SELECT SUM(TS.total_hours) AS data1, SUM(TS.timesheet_payable_amount) AS data2, SUM(TS.timesheet_billable_overtime_amount_staffing) AS data3 FROM `tabTimesheet` AS TS, `tabTimesheet Detail` AS TD WHERE TS.name=TD.parent AND employee='{employee}' AND (date_of_timesheet BETWEEN '{last_sat}' AND '{timesheet_date}') AND TS.name !='{timesheet}' AND TD.to_time<'{from_time}' AND TS.workflow_state!='Open' \
        UNION ALL \
        SELECT SUM(TS.total_hours), SUM(TS.timesheet_payable_amount), SUM(TS.timesheet_billable_overtime_amount_staffing) FROM `tabTimesheet` AS TS, `tabTimesheet Detail` AS TD WHERE TS.name=TD.parent AND employee='{employee}' AND (date_of_timesheet BETWEEN '{last_sat}' AND '{timesheet_date}') AND TS.name !='{timesheet}' AND company = '{hiring_company}' AND TD.to_time<'{from_time}' AND TS.workflow_state!='Open' \
        UNION ALL \
        SELECT SUM(TS.timesheet_payable_amount), SUM(TS.timesheet_billable_overtime_amount_staffing), SUM(TS.timesheet_unbillable_overtime_amount) FROM `tabTimesheet` AS TS, `tabTimesheet Detail` AS TD where TS.name=TD.parent AND employee='{employee}' AND job_order_detail='{job_order_vals.name}' AND TS.name !='{timesheet}' AND (date_of_timesheet between '{job_order_vals.from_date}' AND '{timesheet_date}') AND TD.to_time<'{from_time}' AND TS.workflow_state!='Open'
    """
    result = frappe.db.sql(sql, as_dict=1)

    total_weekly_hours = result[0].data1 if result[0].data1 is not None else 0.0
    worked_time = float(total_weekly_hours) + float(today_hours)
    if worked_time > 40:
        if total_weekly_hours <= 40:
            timesheet_payable_amount = (40 - total_weekly_hours) * pay_rate + 1.5 * (
                worked_time - 40
            ) * pay_rate
        else:
            timesheet_payable_amount = 1.5 * float(today_hours) * pay_rate
    else:
        timesheet_payable_amount = float(today_hours) * pay_rate

    total_hiring_weekly_hours = result[1].data1 if result[1].data1 is not None else 0.0
    timesheet_ot_billable, timesheet_unbillable_ot = get_billable_unbillable_ot(
        total_hiring_weekly_hours,
        total_weekly_hours,
        worked_time,
        today_hours,
        pay_rate,
    )

    total_job_payable = (
        result[2]["data1"] if result[2]["data1"] is not None else 0.00
    ) + timesheet_payable_amount
    total_job_billable_ot = (
        result[2]["data2"] if result[2]["data2"] is not None else 0.00
    ) + timesheet_ot_billable
    total_unbillable_ot = (
        result[2]["data2"] if result[2]["data2"] is not None else 0.00
    ) + timesheet_unbillable_ot

    return (
        timesheet_payable_amount,
        timesheet_ot_billable,
        timesheet_unbillable_ot,
        total_job_payable,
        total_job_billable_ot,
        total_unbillable_ot,
    )


@frappe.whitelist()
def submit_timesheet(selected_items, date, job_order, from_time, to_time, company_type):
    try:
        """
        The `submit_timesheet` function takes in various parameters, processes the data, and returns a list
        of timesheets.
        
        :param selected_items: A JSON string containing the selected items for the timesheet submission
        :param date: The "date" parameter represents the date of the timesheet submission
        :param job_order: The `job_order` parameter is the identifier of the job order for which the
        timesheet is being submitted
        :param from_time: The `from_time` parameter is the starting time of the timesheet entry
        :param to_time: The `to_time` parameter is the end time of the timesheet entry. It represents the
        time when the work for that entry was completed
        :param company_type: The parameter "company_type" is used to specify the type of company for which
        the timesheet is being submitted. It is passed as an argument to the function "submit_timesheet"
        :return: a list of dictionaries called "timesheets".
        """
        timesheets = []
        selected_items = json.loads(selected_items)
        posting_date = datetime.datetime.strptime(date, date_format).date()
        job_doc = frappe.get_doc(jobOrder, job_order)
        for index, item in enumerate(selected_items):
            frappe.publish_progress(
                percent=(index+1)/len(selected_items)*100,
                title=_("Submitting Timesheets..."),
            )
            timesheet = frappe.get_doc("Timesheet", item["timesheet_value"])
            last_sat = check_day(posting_date)
            child_from, child_to, _break_from, _break_to = get_child_time(
                date,
                from_time,
                to_time,
                item["from_time"],
                item["to_time"],
                item["break_from"] if "break_from" in item else None,
                item["break_to"] if "break_to" in item else None,
            )
            staffing_own_timesheet(
                timesheet, company_type, last_sat, job_doc, timesheet.employee_pay_rate
            )
            job_title_time = item["job_title_time"].split(", ")
            job_title = ", ".join(job_title_time[:-1])
            timesheets.append(
                {
                    "employee": item["employee"],
                    "docname": timesheet.name,
                    "company": job_doc.company,
                    "job_title": job_title,
                    "employee_name": item["employee_name"],
                    "job_order": job_order,
                }
            )
            timesheet_already_exist = {
                'name': item["timesheet_value"],
                'employee_company': item["company"],
                'total_hours': item["hours"],
                'date_of_timesheet': date,
                'flat_rate': item["flat_rate"],
                'billing_rate': item["bill_rate"],
                'from_time': child_from,
                'activity_type': job_title,
                'start_time': job_title_time[1],
                'employee_pay_rate': item["pay_rate"]
            }
            ts_status_submit(timesheet, job_order)
            update_previous_timesheet(
                job_doc=job_doc,
                timesheet_date=posting_date,
                employee=item["employee"],
                timesheet_doc=timesheet,
                to_time=child_to,
                timesheet_already_exist=timesheet_already_exist,
            )
        return timesheets
    except Exception as e:
        print(e, frappe.get_traceback())


def add_status(timesheet, status):
    try:
        if status == "Non Satisfactory":
            timesheet.non_satisfactory = 1
            timesheet.no_show = 0
            timesheet.dnr = 0
            timesheet.replaced = 0
        elif status == "DNR":
            timesheet.dnr = 1
            timesheet.no_show = 0
            timesheet.non_satisfactory = 0
            timesheet.replaced = 0
        elif status == "No Show":
            timesheet.no_show = 1
            timesheet.dnr = 0
            timesheet.non_satisfactory = 0
            timesheet.replaced = 0
            for item in timesheet.time_logs:
                item.hours = 0
                item.is_billable = 0
                item.billing_rate = 0
                item.flat_rate = 0
                item.billing_amount = 0
        elif status == "Replaced":
            timesheet.replaced = 1
            timesheet.no_show = 0
            timesheet.dnr = 0
            timesheet.non_satisfactory = 0
            if item.hours <= 0:
                item.billing_rate = 0
                item.flat_rate = 0
                item.billing_amount = 0
        else:
            timesheet.replaced = 0
            timesheet.no_show = 0
            timesheet.dnr = 0
            timesheet.non_satisfactory = 0
        return timesheet
    except Exception:
        return timesheet


@frappe.whitelist()
def staffing_own_timesheet(
    timesheet_doc, company_type, last_sat, job_doc, emp_pay_rate
):
    """
    The function updates the workflow state and other fields in the timesheet document based on the
    company type and calculates various values for billing and pay amounts.
    
    :param timesheet_doc: The timesheet document that needs to be processed
    :param company_type: The parameter `company_type` is a string that represents the type of company.
    It is used to determine whether the timesheet should be approved or not. If the company type is not
    "Staffing", the timesheet workflow state is set to "Approval Request"
    :param last_sat: The parameter `last_sat` is used to specify the date of the last Saturday. It is
    used in the `update_all_exist_timesheet` function to calculate the weekly hours and overtime hours
    for the timesheet
    :param job_doc: The `job_doc` parameter is the document or record of the job or project associated
    with the timesheet. It contains information such as the job name, client details, project duration,
    and other relevant details
    :param emp_pay_rate: The parameter `emp_pay_rate` represents the pay rate of the employee. It is
    used in the function to calculate various amounts related to the timesheet, such as billable amount,
    payable amount, overtime amount, etc
    """
    try:
        if company_type != "Staffing":
            frappe.db.sql(
                f"""
                UPDATE tabTimesheet SET workflow_state = "Approval Request"
                WHERE name="{timesheet_doc.name}"
            """
            )
            frappe.db.commit()
        else:
            flat_rate = timesheet_doc.time_logs[0].flat_rate
            hours = timesheet_doc.total_hours
            timesheet_date = timesheet_doc.date_of_timesheet
            from_time = timesheet_doc.time_logs[0].from_time
            timesheet_doc.save(ignore_permissions=True)
            d = update_all_exist_timesheet(
                timesheet_doc=timesheet_doc,
                timesheet=timesheet_doc.name,
                job_doc=job_doc,
                timesheet_date=timesheet_date,
                employee=timesheet_doc.employee,
                working_hours=hours,
                total_flat_rate=flat_rate,
                from_time=from_time,
                last_sat=last_sat,
                emp_pay_rate=emp_pay_rate,
            )
            frappe.db.sql(
                f"""
                UPDATE `tabTimesheet`
                SET docstatus = "1",
                    workflow_state = "Approved",
                    status = "Submitted",
                    timesheet_billable_amount = "{d[0][0]}",
                    timesheet_billable_overtime_amount = "{d[0][1]}",
                    total_job_order_amount = "{d[0][2]}",
                    total_job_order_billable_overtime_amount_ = "{d[0][3]}",
                    timesheet_hours = "{d[1][0]}",
                    total_weekly_hours = "{d[1][1]}",
                    current_job_order_hours = "{d[1][2][0]}",
                    overtime_timesheet_hours = "{d[1][3][0]}",
                    total_weekly_overtime_hours = "{d[1][4][0]}",
                    cuurent_job_order_overtime_hours = "{d[1][5][0]}",
                    total_weekly_hiring_hours = "{d[1][6][0]}",
                    total_weekly_overtime_hiring_hours = "{d[1][7][0]}",
                    overtime_timesheet_hours1 = "{d[1][8][0]}",
                    billable_weekly_overtime_hours = "{d[1][9][0]}",
                    unbillable_weekly_overtime_hours = "{d[1][10]}",
                    todays_overtime_hours = "{d[1][11]}",
                    timesheet_payable_amount = "{d[2][0]}",
                    timesheet_billable_overtime_amount_staffing = "{d[2][1]}",
                    timesheet_unbillable_overtime_amount = "{d[2][2]}",
                    total_job_order_payable_amount = "{d[2][3]}",
                    total_job_order_billable_overtime_amount = "{d[2][4]}",
                    total_job_order_unbillable_overtime_amount = "{d[2][5]}"
                WHERE name = "{timesheet_doc.name}"
            """
            )
            frappe.db.sql(
                f'UPDATE `tabTimesheet Detail` SET billing_amount="{d[0][0]}", pay_amount="{d[2][0]}" WHERE parent="{timesheet_doc.name}"'
            )
            frappe.db.commit()
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.log_error(e, "staffing_own_timesheet error")


def update_all_exist_timesheet(
    timesheet_doc,
    timesheet,
    job_doc,
    timesheet_date,
    employee,
    working_hours,
    total_flat_rate,
    from_time,
    last_sat,
    emp_pay_rate,
):
    timesheet_doc = update_billing_payroll_details(
        timesheet_doc,
        job_doc,
        timesheet_date,
        employee,
        working_hours,
        total_flat_rate,
        timesheet_doc.time_logs[0].billing_rate,
        from_time,
        last_sat,
        emp_pay_rate,
    )
    (
        week_all_hours,
        all_job_hours,
        week_hiring_hours,
    ) = timesheet_billing_hours(
        job_doc=job_doc,
        timesheet_date=timesheet_date,
        employee=employee,
        user=frappe.session.user,
        timesheet=timesheet,
        from_time=from_time,
        last_sat=last_sat,
    )
    cur_timesheet_hours = working_hours
    current_job_order_overtime_hours, todays_overtime_hours = overall_overtime(
        job_order_vals=job_doc,
        timesheet_date=timesheet_date,
        working_hours=working_hours,
        employee=employee,
        from_time=from_time,
        timesheet=timesheet,
        last_sat=last_sat,
    )
    (
        overtime_hours,
        overtime_all_hours,
        overtime_hiring_hours,
        hiring_timesheet_oh,
    ) = sub_update_timesheet(cur_timesheet_hours, week_all_hours, week_hiring_hours)
    timesheet_hours = cur_timesheet_hours
    total_weekly_hours = week_all_hours + cur_timesheet_hours
    current_job_order_hours = (all_job_hours + cur_timesheet_hours,)
    overtime_timesheet_hours = (overtime_hours,)
    total_weekly_overtime_hours = (overtime_all_hours,)
    current_job_order_overtime_hours = (float(current_job_order_overtime_hours),)
    total_weekly_hiring_hours = (week_hiring_hours + cur_timesheet_hours,)
    total_weekly_overtime_hiring_hours = (overtime_hiring_hours,)
    overtime_timesheet_hours1 = (hiring_timesheet_oh,)
    billable_weekly_overtime_hours = (overtime_hiring_hours,)
    unbillable_weekly_overtime_hours = overtime_all_hours - overtime_hiring_hours
    data2 = [
        timesheet_hours,
        total_weekly_hours,
        current_job_order_hours,
        overtime_timesheet_hours,
        total_weekly_overtime_hours,
        current_job_order_overtime_hours,
        total_weekly_hiring_hours,
        total_weekly_overtime_hiring_hours,
        overtime_timesheet_hours1,
        billable_weekly_overtime_hours,
        unbillable_weekly_overtime_hours,
        todays_overtime_hours,
    ]
    return data2


def update_previous_timesheet(
    job_doc,
    timesheet_date,
    employee,
    timesheet_doc,
    to_time,
    timesheet_already_exist=None,
):
    if timesheet_already_exist["name"] and len(timesheet_already_exist) > 0:
        sql = f"""
        UPDATE tabTimesheet SET docstatus="0", workflow_state="Approval Request", status="Draft"
        WHERE name="{timesheet_already_exist}"
        AND workflow_state !='Approved'
        """
        frappe.db.sql(sql)
        frappe.db.commit()
        timesheet_exist = [timesheet_already_exist]
        update_timesheet_exist(job_doc.name, timesheet_date, employee, timesheet_exist)
    job_order_last_dat = job_doc.to_date
    all_timesheet = f"""
    SELECT TS.name, TS.total_hours, TS.date_of_timesheet, TD.flat_rate, TD.billing_rate, TD.from_time, TS.employee_pay_rate
    FROM `tabTimesheet` AS TS , `tabTimesheet Detail` AS TD
    WHERE TS.name=TD.parent AND employee="{employee}" AND date_of_timesheet between "{timesheet_date}"
    AND "{job_order_last_dat}" AND TS.name !="{timesheet_doc.name}" AND TD.from_time>"{to_time}"
    AND TS.workflow_state="Approval Request"
    ORDER BY TD.from_time
    """
    timesheet_exist = frappe.db.sql(all_timesheet, as_dict=True)
    if len(timesheet_exist):
        frappe.enqueue(
            update_timesheet_exist,
            job_doc_name=job_doc.name,
            timesheet_date=timesheet_date,
            employee=employee,
            timesheet_exist=timesheet_exist,
            queue="long",
            is_async=True,
        )


def update_timesheet_exist(job_doc_name, timesheet_date, employee, timesheet_exist):
    job_doc = frappe.get_doc(jobOrder, job_doc_name)
    for i in timesheet_exist:
        flat_rate = i["flat_rate"]
        per_hour = i["billing_rate"]
        hours = i["total_hours"]
        timeshet_date = i["date_of_timesheet"]
        last_sat = check_day(timesheet_date)
        from_time = i["from_time"]
        d = update_all_exist_timesheet(
            timesheet_doc=i["name"],
            job_doc=job_doc,
            timesheet_date=timeshet_date,
            employee=employee,
            working_hours=hours,
            total_flat_rate=flat_rate,
            per_hour_rate=per_hour,
            from_time=from_time,
            last_sat=last_sat,
            emp_pay_rate=i["employee_pay_rate"],
        )
        frappe.db.sql(
            f"""
            UPDATE `tabTimesheet`
            SET timesheet_billable_amount="{d[0][0]}",
                timesheet_billable_overtime_amount="{d[0][1]}",
                total_job_order_amount="{d[0][2]}",
                total_job_order_billable_overtime_amount_="{d[0][3]}",
                timesheet_hours="{d[1][0]}",
                total_weekly_hours="{d[1][1]}",
                current_job_order_hours="{d[1][2][0]}",
                overtime_timesheet_hours="{d[1][3][0]}",
                total_weekly_overtime_hours="{d[1][4][0]}",
                cuurent_job_order_overtime_hours="{d[1][5][0]}",
                total_weekly_hiring_hours="{d[1][6][0]}",
                total_weekly_overtime_hiring_hours="{d[1][7][0]}",
                overtime_timesheet_hours1="{d[1][8][0]}",
                billable_weekly_overtime_hours="{d[1][9][0]}",
                unbillable_weekly_overtime_hours="{d[1][10]}",
                todays_overtime_hours="{d[1][11]}",
                timesheet_payable_amount="{d[2][0]}",
                timesheet_billable_overtime_amount_staffing="{d[2][1]}",
                timesheet_unbillable_overtime_amount="{d[2][2]}",
                total_job_order_payable_amount="{d[2][3]}",
                total_job_order_billable_overtime_amount="{d[2][4]}",
                total_job_order_unbillable_overtime_amount="{d[2][5]}"
            WHERE name="{i["name"]}"
        """
        )
        frappe.db.sql(
            f'UPDATE `tabTimesheet Detail` SET billing_amount="{d[0][0]}", pay_amount="{d[2][0]}" where parent="{i["name"]}"'
        )
        frappe.db.commit()


def update_all_exist_timesheet(
    timesheet_doc,
    job_doc,
    timesheet_date,
    employee,
    working_hours,
    total_flat_rate,
    per_hour_rate,
    from_time,
    last_sat,
    emp_pay_rate,
):
    data = billing_details_data(
        timesheet_doc,
        job_doc,
        timesheet_date,
        employee,
        working_hours,
        total_flat_rate,
        per_hour_rate,
        from_time,
        last_sat,
    )
    (
        week_all_hours,
        all_job_hours,
        week_hiring_hours,
    ) = timesheet_billing_hours(
        job_doc=job_doc,
        timesheet_date=timesheet_date,
        last_sat=last_sat,
        employee=employee,
        user=frappe.session.user,
        timesheet=timesheet_doc,
        from_time=from_time,
    )
    cur_timesheet_hours = working_hours
    cuurent_job_order_overtime_hours, todays_overtime_hours = overall_overtime(
        job_order_vals=job_doc,
        timesheet_date=timesheet_date,
        working_hours=working_hours,
        employee=employee,
        from_time=from_time,
        last_sat=last_sat,
        timesheet=timesheet_doc,
    )
    (
        overtime_hours,
        overtime_all_hours,
        overtime_hiring_hours,
        hiring_timesheet_oh,
    ) = sub_update_timesheet(cur_timesheet_hours, week_all_hours, week_hiring_hours)
    timesheet_hours = cur_timesheet_hours
    total_weekly_hours = week_all_hours + cur_timesheet_hours
    current_job_order_hours = (all_job_hours + cur_timesheet_hours,)
    overtime_timesheet_hours = (overtime_hours,)
    total_weekly_overtime_hours = (overtime_all_hours,)
    cuurent_job_order_overtime_hours = (float(cuurent_job_order_overtime_hours),)
    total_weekly_hiring_hours = (week_hiring_hours + cur_timesheet_hours,)
    total_weekly_overtime_hiring_hours = (overtime_hiring_hours,)
    overtime_timesheet_hours1 = (hiring_timesheet_oh,)
    billable_weekly_overtime_hours = (overtime_hiring_hours,)
    unbillable_weekly_overtime_hours = overtime_all_hours - overtime_hiring_hours
    data2 = [
        timesheet_hours,
        total_weekly_hours,
        current_job_order_hours,
        overtime_timesheet_hours,
        total_weekly_overtime_hours,
        cuurent_job_order_overtime_hours,
        total_weekly_hiring_hours,
        total_weekly_overtime_hiring_hours,
        overtime_timesheet_hours1,
        billable_weekly_overtime_hours,
        unbillable_weekly_overtime_hours,
        todays_overtime_hours,
    ]
    data3 = set_payroll_fields(
        emp_pay_rate,
        job_doc.company,
        employee,
        timesheet_doc,
        timesheet_date,
        working_hours,
        from_time,
        last_sat,
        job_doc,
    )
    data3 = list(data3)
    return data, data2, data3


def billing_details_data(
    timesheet,
    job_order_vals,
    timesheet_date,
    employee,
    working_hours,
    total_flat_rate,
    per_hour_rate,
    from_time,
    last_sat,
):
    per_rate = per_hour_rate
    flat_rate = total_flat_rate
    hiring_company = job_order_vals.company
    sql = f"""
    SELECT IFNULL(SUM(TS.total_hours), 0), IFNULL(SUM(TS.timesheet_billable_amount), 0) FROM `tabTimesheet` AS TS,
    `tabTimesheet Detail` AS TD
    WHERE TS.name=TD.parent AND employee='{employee}' AND (date_of_timesheet BETWEEN '{last_sat}' AND '{timesheet_date}')
    AND company='{hiring_company}' AND TS.name !='{timesheet}' AND TD.to_time<'{from_time}' AND TS.workflow_state!='Open'
    UNION ALL
    SELECT IFNULL(SUM(TS.timesheet_billable_amount), 0), IFNULL(SUM(TS.timesheet_billable_overtime_amount), 0) FROM `tabTimesheet` AS TS,
    `tabTimesheet Detail` AS TD WHERE TS.name=TD.parent AND employee='{employee}' AND job_order_detail='{job_order_vals.name}'
    AND TS.name !='{timesheet}' AND (date_of_timesheet between '{job_order_vals.from_date}' AND '{timesheet_date}')
    AND TD.to_time<'{from_time}' and TS.workflow_state!='Open'
    """
    data = frappe.db.sql(sql)
    weekly_hours = data[0][0]
    worked_time = float(weekly_hours) + float(working_hours)
    if weekly_hours <= 40:
        if (worked_time) <= 40:
            timesheet_billed_amount = (float(working_hours) * per_rate) + flat_rate
            timesheet_overtime_bill = 0.00
        else:
            extra_hours = worked_time - 40
            timesheet_billed_amount = (
                ((working_hours - extra_hours) * per_rate)
                + (1.5 * per_rate * extra_hours)
                + flat_rate
            )
            timesheet_overtime_bill = 1.5 * per_rate * extra_hours
    else:
        timesheet_billed_amount = (1.5 * per_rate * working_hours) + flat_rate
        timesheet_overtime_bill = 1.5 * per_rate * working_hours

    total_job_amount = data[1][0] + timesheet_billed_amount
    total_overtime_job_amount = data[1][1] + timesheet_overtime_bill
    return (
        timesheet_billed_amount,
        timesheet_overtime_bill,
        total_job_amount,
        total_overtime_job_amount,
    )


def ts_status_submit(timesheet, job_order):
    try:
        employee = timesheet.employee
        company = timesheet.company
        if timesheet.non_satisfactory:
            enqueue(
                unsatisfied_organization,
                emp_doc_name=employee,
                company=company,
                job_order=job_order,
            )
            enqueue(
                remove_job_title,
                emp_doc_name=timesheet.employee,
                job_title=timesheet.job_name,
                queue="long",
                is_async=True,
            )
        elif timesheet.dnr:
            enqueue(
                do_not_return,
                emp_doc_name=employee,
                company=company,
                job_order=job_order,
                now=True,
            )
            enqueue(
                remove_job_title,
                emp_doc_name=employee,
                job_title=timesheet.job_name,
                queue="long",
                is_async=True,
            )
        elif timesheet.no_show:
            enqueue(
                no_show_org,
                emp_doc_name=employee,
                company=company,
                job_order=job_order,
                queue="long",
                is_async=True,
            )
            enqueue(
                remove_job_title,
                emp_doc_name=employee,
                job_title=timesheet.job_name,
                queue="long",
                is_async=True,
            )
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.log_error(e, "ts_status_submit error")
