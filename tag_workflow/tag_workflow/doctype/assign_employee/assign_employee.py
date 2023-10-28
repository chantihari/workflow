# Copyright (c) 2021, SourceFuse and contributors
# For license information, please see license.txt
import frappe
from frappe import _
import requests
import json
import googlemaps
from frappe.model.document import Document

jobOrder = "Job Order"
AEMP = "Assign Employee"


class AssignEmployee(Document):
    # pass
    def on_update(self):
        job_order = frappe.get_doc(jobOrder, self.job_order)
        create_pay_rate_comp_code_job_title(job_order, self)


distance_value = {"5 miles": 5, "10 miles": 10, "20 miles": 20, "50 miles": 50}


@frappe.whitelist()
def create_after_save_code_rate_title(this_doc):
    """
    This function creates a job title for a pay rate comp code after saving a document.

    :param this_doc: The parameter "this_doc" is likely a JSON string that contains information about a
    Assign Employee Doc. The function attempts to load this JSON string into a Python dictionary using the
    "json.loads()" method
    """
    pass


def get_souce(location=None):
    try:
        source = []
        if location:
            site = frappe.db.get_list(
                "Job Site",
                {"name": location},
                ["address", "city", "state", "zip"],
                ignore_permissions=True,
            )
            for s in site:
                source = [s["address"], s["city"], s["state"], str(s["zip"])]
        return ",".join(source)
    except Exception:
        return ",".join(source)


def get_dest(dest):
    try:
        street = dest["street_address"] if dest["street_address"] else ""
        city = dest["city"] if dest["city"] else ""
        state = dest["state"] if dest["state"] else ""
        ZIP = str(dest["zip"]) if dest["zip"] != 0 else ""
        return street + "," + city + "," + state + "," + ZIP
    except Exception as e:
        print(e)
        return ""


@frappe.whitelist()
def add_job_title(assign_emp_detail, job_order):
    frappe.enqueue(
        add_job_title_in_background,
        assign_emp_detail=assign_emp_detail,
        job_order=job_order,
        queue="default",
        is_async=True
    )


def add_job_title_to_profile(job_title, emp_data, negative_status):
    if not sum(negative_status):
        if not len(emp_data.employee_job_category):
            emp_data.job_category = job_title
        emp_data.append("employee_job_category", {"job_category": job_title})
        emp_data.save(ignore_permissions=True)
        adding_job_categories(emp_data)


@frappe.whitelist()
def adding_job_categories(emp_data):
    emp_category = emp_data.employee_job_category
    length = len(emp_category)
    title = ""
    job_categories_list = []
    for i in range(len(emp_category)):
        job_categories_list.append(emp_category[i].job_category)
        if not emp_category[i].job_category:
            length -= 1

        elif title == "":
            title = emp_category[i].job_category
    if length > 1:
        job_categories = title + " + " + str(length - 1)
    else:
        job_categories = title
    emp_data.job_categories = job_categories
    emp_data.job_title_filter = ",".join(job_categories_list)
    emp_data.save(ignore_permissions=True)


def check_distance(emp, distance, location):
    try:
        result, source = [], []
        tag_gmap_key = frappe.get_site_config().tag_gmap_key or ""
        if not tag_gmap_key:
            frappe.msgprint(_("GMAP api key not found"))
            return ()

        gmaps = googlemaps.Client(key=tag_gmap_key)
        source = get_souce(location)
        for e in emp:
            try:
                dest = get_dest(e)
                my_dist = gmaps.distance_matrix(source, dest)
                if (
                    my_dist["status"] == "OK"
                    and my_dist["rows"][0]["elements"][0]["distance"]
                ):
                    km = my_dist["rows"][0]["elements"][0]["distance"]["value"] / 1000
                    if km is not None and (
                        (km * 0.62137) <= distance_value[distance] or km == 0
                    ):
                        result.append((e["name"], e["employee_name"]))
            except Exception as e:
                print(e)
                continue
        return tuple(result)
    except Exception as e:
        print(e, "google")
        frappe.msgprint(e)
        return ()


@frappe.whitelist()
def get_employee(doctype, txt, searchfield, page_len, start, filters):
    try:
        emp_company = filters.get("emp_company")
        job_category = filters.get("job_category")
        company = filters.get("company")
        distance = filters.get("distance_radius")
        job_location = filters.get("job_location")
        job_order = filters.get("job_order")
        employee_lis = filters.get("employee_lis")
        all_employees = filters.get("all_employees")
        if not job_category:
            return tuple()
        lat, lng = frappe.db.get_value("Job Site", job_location, ["lat", "lng"])    
        for index, i in enumerate(employee_lis):
                if index >= 1:
                    value = value + "'" + "," + "'" + i
                else:
                    value = value + i
        value = ""
        redis = frappe.cache()

        return get_emps_all_cases(emp_company, job_order, distance, txt, company, value, lat, lng, redis, employee_lis, job_category, all_employees)
    except Exception:
        print(frappe.get_traceback())
        return tuple()


def get_emp_non_resume_required(emp_company, job_order, distance, txt, all_employees, company, value, lat, lng, redis, employee_lis,job_category):
    try:
        key = emp_company + "" + job_order + "" + distance

        if redis.hget(key, "emp") and not txt and all_employees == 1:
            return cache_data(redis, key, employee_lis)

        if all_employees:
            sql = """
                select * from(
                select name, employee_name,CONCAT(Round(
                3959 * Acos( Least(1.0,Cos( Radians({4}) )*Cos( Radians(lat) )*Cos( Radians(lng) - Radians ({5}) )+Sin( Radians({4}) )*Sin( Radians(lat)))),1), " miles") as `distance`
                from `tabEmployee`
                where company = '{0}' and status = 'Active'
                and name NOT IN (select e.employee from `tabAssign Employee Details` e inner join `tabAssign Employee` a where a.name = e.parent and e.approved=1 and a.job_order='{7}')
                and (lat!="" or lat is Null) and (lng!="" or lng is Null)
                and user_id is Null
                and name NOT IN (select parent from `tabBlocked Employees` where blocked_from = '{1}')
                and name NOT IN (select parent from `tabDNR`  where dnr = '{1}') 
                and (name NOT IN (select parent from `tabUnsatisfied Organization` where unsatisfied_organization_name = '{1}')) 
                and name NOT IN ('{2}') and (name like '%%{3}%%' or employee_name like  '%%{3}%%')) t
                where (`distance` < {6} or `distance` is NULL) order by `distance` is NULL,`distance`*1
                """.format(
                emp_company,
                company,
                value,
                "%s" % txt,
                lat,
                lng,
                distance_value[distance],
                job_order,
            )
        else:
            sql = """
                select * from(
                select name, employee_name,CONCAT(Round(
                3959 * Acos( Least(1.0,Cos( Radians({5}) )*Cos( Radians(lat) )*Cos( Radians(lng) - Radians ({6}) )+Sin( Radians({5}) )*Sin( Radians(lat)))),1), " miles") as `distance`
                from `tabEmployee`where company = '{0}'and status = 'Active' and zip!=0
                and lat!="" and lng!=""
                and name NOT IN (select e.employee from `tabAssign Employee Details` e inner join `tabAssign Employee` a where a.name = e.parent and e.approved=1 and a.job_order='{8}')
                and employee_name like '%%{4}%%' 
                and user_id is Null
                and name in (select parent from `tabJob Category` where job_category = '{1}'
                and parent NOT IN ('{3}')) 
                and name NOT IN (select parent from `tabBlocked Employees` where blocked_from = '{2}') 
                and name NOT IN (select parent from `tabDNR`  where dnr = '{2}') 
                and (name NOT IN (select parent from `tabUnsatisfied Organization` where unsatisfied_organization_name = '{2}'))and name NOT IN ('{3}')
                and (name like '%%{4}%%' or employee_name like  '%%{4}%%')) t
                where `distance` < {7} order by `distance`*1
                """.format(
                emp_company,
                job_category,
                company,
                value,
                "%s" % txt,
                lat,
                lng,
                distance_value[distance],
                job_order,
            )
        emp = frappe.db.sql(sql)
        save_data_in_redis(key, emp)
        return emp
    except Exception:
        print(frappe.get_traceback())
        return tuple()
    
def get_emps_all_cases(emp_company, job_order, distance, txt, company, value, lat, lng, redis, employee_lis, job_category, all_employees):
    try:
        key = emp_company + "" + job_order + "" + (distance or "") + job_category + "_" +str(all_employees)
        if redis.hget(key, "emp") and not txt:
            return cache_data(redis, key, employee_lis)
        all_emp_cond = 'and name in (select parent from `tabJob Category` where job_category = "{0}" and parent NOT IN ("{1}"))'.format(job_category, value) if not all_employees else ''
        if distance is None:
            sql = """
                select * from (
                select name, employee_name,CONCAT(Round(
                3959 * Acos( Least(1.0,Cos( Radians({4}) )*Cos( Radians(lat) )*Cos( Radians(lng) - Radians ({5}) )+Sin( Radians({4}) )*Sin( Radians(lat)))),1), " miles") as `distance`
                from `tabEmployee`
                where company = '{0}' and status = 'Active'
                and name NOT IN (select e.employee from `tabAssign Employee Details` e inner join `tabAssign Employee` a where a.name = e.parent and e.approved=1 and a.job_order='{6}')
                and (lat!="" or lat is Null) and (lng!="" or lng is Null)
                and user_id is Null
                and name NOT IN (select parent from `tabBlocked Employees` where blocked_from = '{1}')
                and name NOT IN (select parent from `tabDNR`  where dnr = '{1}') 
                and (name NOT IN (select parent from `tabUnsatisfied Organization` where unsatisfied_organization_name = '{1}')) 
                and name NOT IN ('{2}') and (name like '%%{3}%%' or employee_name like  '%%{3}%%') {7}) t
                """.format(
                emp_company,
                company,
                value,
                "%s" % txt,
                lat,
                lng,
                job_order,
                all_emp_cond
            )
        else:
            sql = """
                select * from(
                select name, employee_name,CONCAT(Round(
                3959 * Acos( Least(1.0,Cos( Radians({5}) )*Cos( Radians(lat) )*Cos( Radians(lng) - Radians ({6}) )+Sin( Radians({5}) )*Sin( Radians(lat)))),1), " miles") as `distance`
                from `tabEmployee`where company = '{0}'and status = 'Active' and zip!=0
                and lat!="" and lng!=""
                and name NOT IN (select e.employee from `tabAssign Employee Details` e inner join `tabAssign Employee` a where a.name = e.parent and e.approved=1 and a.job_order='{8}')
                and employee_name like '%%{4}%%' 
                and user_id is Null
                and name NOT IN (select parent from `tabBlocked Employees` where blocked_from = '{2}') 
                and name NOT IN (select parent from `tabDNR`  where dnr = '{2}') 
                and (name NOT IN (select parent from `tabUnsatisfied Organization` where unsatisfied_organization_name = '{2}'))and name NOT IN ('{3}')
                and (name like '%%{4}%%' or employee_name like  '%%{4}%%') {1}) t
                where `distance` < {7} order by `distance`*1
                """.format(
                emp_company,
                all_emp_cond,
                company,
                value,
                "%s" % txt,
                lat,
                lng,
                distance_value[distance],
                job_order,
            )
        print(sql)
        emp = frappe.db.sql(sql)
        save_data_in_redis(key, emp)
        return emp
    except Exception:
        print(frappe.get_traceback())
        return tuple()


@frappe.whitelist()
def worker_data(job_order):
    sql = f"select total_no_of_workers,total_workers_filled from `tabJob Order` where name='{job_order}'"
    data = frappe.db.sql(sql, as_dict=True)
    return data


@frappe.whitelist()
def approved_workers(job_order, user_email):
    sql = f"select name, staffing_organization, notes, sum(approved_no_of_workers) as approved_no_of_workers from `tabClaim Order` where job_order='{job_order}' and staffing_organization in (select company from `tabEmployee` where user_id='{user_email}')  group by staffing_organization"
    data = frappe.db.sql(sql, as_dict=True)
    sql = """ select name from `tabAssign Employee` where job_order="{0}" and company= "{1}" """.format(
        job_order, data[0]["staffing_organization"]
    )
    my_assign_emp = frappe.db.sql(sql, as_list=1)
    if len(my_assign_emp) > 0:
        doc = frappe.get_doc(AEMP, my_assign_emp[0][0])
        if int(doc.claims_approved) != int(data[0]["approved_no_of_workers"]):
            frappe.db.set_value(
                AEMP,
                str(my_assign_emp[0][0]),
                "claims_approved",
                int(data[0]["approved_no_of_workers"]),
            )

    claim = frappe.db.sql(
        """ select notes from `tabClaim Order` where staffing_organization="{0}" and job_order="{1}" and notes !=''  order by modified desc """.format(
            data[0]["staffing_organization"], job_order
        ),
        as_dict=1,
    )
    if claim:
        data[0]["notes"] = claim[0]["notes"]
    return data


@frappe.whitelist()
def check_old_value(name):
    try:
        return frappe.db.get_value(
            "Assign Employee Details",
            name,
            ["employee", "pay_rate", "job_start_time", "job_category"],
        )
    except Exception as e:
        frappe.msgprint(e)


@frappe.whitelist()
def check_emp_available(frm):
    try:
        data = json.loads(frm)
        company = data["company"]
        job_order = data["job_order"]
        emps = data["employee_details"]
        my_job = frappe.get_doc(jobOrder, job_order)
        job_start_date = my_job.from_date
        job_end_date = my_job.to_date
        pay_rate = check_pay_rate(data)
        data = f'select name,job_order from `tabAssign Employee` where company="{company}" and tag_status="Approved" and job_order in (select name from `tabJob Order` where order_status!="Completed" and ((from_date between "{job_start_date}" and "{job_end_date}") or (to_date between "{job_start_date}" and "{job_end_date}")  ))'
        my_dta = frappe.db.sql(data, as_dict=1)
        if my_dta:
            emp_lists = []
            for i in my_dta:
                check_emp = f'select employee,employee_name,parent from `tabAssign Employee Details` where parent="{i.name}"'
                my_emp_data = frappe.db.sql(check_emp, as_dict=1)
                for j in my_emp_data:
                    emp_lists.append(j)
            l = my_emp_work(emps, emp_lists)
            z = []
            for i in l:
                d1 = {}
                y = frappe.get_doc(AEMP, i[1])
                if y.job_order != job_order:
                    d1["job_order"] = y.job_order
                    d1["employee"] = i[0]
                    z.append(d1)
                else:
                    d1["job_order"] = 1
                    z.append(d1)
            return z, pay_rate
        else:
            return 1, pay_rate
    except Exception as e:
        frappe.error_log(e, "Check same order")


def my_emp_work(emps, my_emp_data):
    if emps and len(emps):
        l = []
        for i in emps:
            for k in my_emp_data:
                if i["employee"] in k.values():
                    l.append([k["employee_name"], k["parent"]])
        return l


@frappe.whitelist()
def validate_employee(doc, method):
    job_order = frappe.get_doc(jobOrder, doc.job_order)
    if job_order.is_repeat != 1:
        for employee in doc.employee_details:
            employee_doc = frappe.get_doc("Employee", employee.employee)
            if employee_doc.company != doc.company:
                frappe.throw(
                    "Employee does not belong to the Staffing Organization")
    user = frappe.get_doc("User", frappe.session.user)
    if not doc.is_new() and (
        user.tag_user_type == "Hiring Admin" or user.tag_user_type == "Hiring User"
    ):
        for employee in doc.employee_details:
            assign_emp = frappe.db.get_list(
                "Assign Employee Details",
                {"employee": employee.employee, "parent": doc.name},
                ["name"],
                ignore_permissions=True,
            )
            if assign_emp == []:
                frappe.throw("Insufficient permission to modify employee")


@frappe.whitelist()
def payrate_change(docname):
    try:
        sql = """select data from `tabVersion` where docname="{0}" order by modified DESC""".format(
            docname
        )
        data = frappe.db.sql(sql, as_list=1)
        if len(data) == 0:
            return "success"
        new_data = json.loads(data[0][0])
        doc = frappe.get_doc(AEMP, docname)
        free_redis(doc.company, doc.job_order)
        if (
            ("changed" not in new_data and "row_changed" not in new_data)
            or len(new_data["added"]) > 0
            or len(new_data["removed"]) > 0
        ):
            return "success"
        elif "row_changed" in new_data and len(new_data["row_changed"]) > 0:
            for i in new_data["row_changed"][0][3]:
                if i[0] == "employee_name":
                    return "success"
        return "failure"
    except Exception as e:
        print(e, frappe.get_traceback())


def check_pay_rate(data):
    try:
        bill_rates = {}
        pay_rates = {}
        for i in data["multiple_job_title_details"]:
            bill_rates[f'{i["select_job"]}~{i["job_start_time"]}'] = i["bill_rate"] or 0
            pay_rates[f'{i["select_job"]}~{i["job_start_time"]}'] = (
                i["employee_pay_rate"] or 0
            )

        emp_details = data["employee_details"]
        temp = {"bill_rate_data": []}
        employees = {}

        for i in emp_details:
            check_key_data_employees(bill_rates, pay_rates, i, temp, employees)

        if len(employees) > 0:
            temp["employees"] = employees
        return temp
    except Exception as e:
        frappe.log_error(e, "Check Pay Rate Pop Up Error")
        print(e, frappe.get_traceback())


def check_key_data_employees(bill_rates, pay_rates, i, temp, employees):
    key_data = {}
    key = f'{i["job_category"]}~{i["job_start_time"]+":00"}'
    if key in bill_rates:
        total_bill_rate_title = bill_rates[key]
        key_data["bill_rate"] = total_bill_rate_title
        emp_pay_rate = pay_rates[key]
        if float(emp_pay_rate) > total_bill_rate_title:
            key_data["emp_pay_rate"] = emp_pay_rate
        if float(i["pay_rate"]) > total_bill_rate_title:
            employees[i["employee_name"]] = i["pay_rate"]
        if key_data not in temp["bill_rate_data"]:
            temp["bill_rate_data"].append(key_data)


@frappe.whitelist()
def update_workers_filled(job_order_name):
    try:
        frappe.enqueue(
            "tag_workflow.tag_workflow.doctype.assign_employee.assign_employee.update_workers_filled_job",
            now=True,
            job_order_name=job_order_name,
        )
    except Exception as e:
        print(e, frappe.get_traceback())
        frappe.log_error(e, "Workers Update")


@frappe.whitelist()
def update_workers_filled_job(job_order_name):
    try:
        total_workers_filled = 0
        job = frappe.get_doc(jobOrder, job_order_name)
        if job.resumes_required == 0:
            emp_assigned = frappe.db.sql(
                'select count(employee_name) as total_emp_assigned from `tabAssign Employee Details` where parent in (select name from `tabAssign Employee` where job_order="{0}") and remove_employee=0;'.format(
                    job_order_name
                ),
                as_dict=1,
            )
            if len(emp_assigned):
                total_workers_filled = emp_assigned[0]["total_emp_assigned"]

            title_wise_workers_filled_sql = """select count(employee_name) as filled, job_category,job_start_time from `tabAssign Employee Details` 
                                            where parent in (select name from `tabAssign Employee` where job_order='{0}') and remove_employee=0 
                                            group by job_category,job_start_time;""".format(
                job_order_name
            )
        else:
            emp_assigned = frappe.db.sql(
                'select count(employee_name) as total_emp_assigned from `tabAssign Employee Details` where parent in (select name from `tabAssign Employee` where job_order="{0}") and remove_employee=0 and approved=1;'.format(
                    job_order_name
                ),
                as_dict=1,
            )
            if len(emp_assigned):
                total_workers_filled = emp_assigned[0]["total_emp_assigned"]

            title_wise_workers_filled_sql = """select count(employee_name) as filled, job_category,job_start_time from `tabAssign Employee Details` 
                                            where parent in (select name from `tabAssign Employee` where job_order='{0}') and remove_employee=0 and approved=1 
                                            group by job_category,job_start_time;""".format(
                job_order_name
            )

        title_wise_workers_filled = frappe.db.sql(
            title_wise_workers_filled_sql, as_dict=True
        )
        cases = []
        case_query = "update `tabMultiple Job Titles` SET worker_filled = "
        for each_title in title_wise_workers_filled:
            each_case = f"""WHEN select_job="{each_title['job_category']}" AND job_start_time like "%%{each_title['job_start_time']}%%" AND parent="{job_order_name}" THEN {each_title['filled']}"""
            cases.append(each_case)

        if cases:
            cases.insert(0, "CASE")
            cases.append(" ELSE 0")
            cases.append("END ")
            case_query += " ".join(cases)
            case_query += f'''where parent = "{job_order_name}"'''
            frappe.db.sql(case_query)
            frappe.db.commit()

        if int(total_workers_filled) != int(job.total_workers_filled):
            frappe.db.sql(
                'update `tabJob Order` set total_workers_filled={0} where name="{1}"'.format(
                    int(total_workers_filled), job_order_name
                )
            )
            frappe.db.commit()

    except Exception as e:
        frappe.log_error(e, "Workers Update Job")


@frappe.whitelist()
def update_notes(name, notes, job_order, company):
    try:
        frappe.db.sql(
            """ UPDATE `tabAssign Employee` SET notes ="{0}" where job_order="{1}" and company="{2}" """.format(
                notes, job_order, company
            )
        )
        frappe.db.commit()
        frappe.publish_realtime(event="sync_data", doctype=AEMP, docname=name)
    except Exception as e:
        print(e)


def cache_data(redis, key, employee_lis):
    try:
        data = redis.hget(key, "emp")
        if len(data) > 0:
            for d in data:
                if d[0] in employee_lis:
                    data.remove(d)
            redis.hset(key, "emp", data)
            return data
    except Exception as e:
        frappe.log_error(e, "cache_data_error")


def save_data_in_redis(key, emp):
    try:
        redis = frappe.cache()
        if len(emp) and redis.hget(key, "emp") == None:
            redis.hset(key, "emp", list(emp))
    except Exception as e:
        frappe.log_error(e, "store_data _error")


@frappe.whitelist()
def free_redis(company, job_order):
    try:
        redis = frappe.cache()
        distances = ["5 miles", "10 miles", "20 miles", "50 miles"]
        for d in distances:
            key = company + "" + job_order + "" + d
            if redis.hget(key, "emp"):
                redis.hdel(key, "emp")
    except Exception as e:
        frappe.log_error(e, "redis error")


@frappe.whitelist()
def add_notes(company, job_order):
    try:
        return frappe.db.sql(
            """ select notes from `tabAssign Employee` where job_order="{0}" and company="{1}" and notes!=""  limit 1 """.format(
                job_order, company
            ),
            as_dict=1,
        )
    except Exception as e:
        print(e)


@frappe.whitelist()
def add_job_title_in_background(assign_emp_detail, job_order):
    """
    The function `add_job_title_in_background` adds job titles to employee profiles in the background
    based on the assigned employee details and the status of the job order.
    
    :param docname: The `docname` parameter is the name of the document in the "Assign Employee" table
    that you want to add a job title in the backgroadd_job_title_in_backgroundund for
    :param assign_emp_detail: The `assign_emp_detail` parameter is a JSON string that contains details
    about the employees and their assigned job categories. It is expected to be in the following format:
    """
    try:
        assign_emp_detail = json.loads(assign_emp_detail)
        status = frappe.db.get_value("Job Order", job_order, ["order_status"])
        emp_assigned = [emp["employee"] for emp in assign_emp_detail]
        categories_sql = f"SELECT parent, job_category FROM `tabJob Category` WHERE parent='{emp_assigned[0]}'" if len(emp_assigned)==1 else f"SELECT parent, job_category from `tabJob Category` WHERE parent in {tuple(emp_assigned)}"
        categories = frappe.db.sql(categories_sql, as_list=1)

        if status != "Completed":
            for emp in assign_emp_detail:
                try:
                    job_title = emp['job_category']
                    print([emp["name"], job_title] not in categories, emp["employee"], job_title)
                    if [emp["employee"], job_title] not in categories:
                        emp_data = frappe.get_doc("Employee", emp['employee'])
                        check_status_sql = f"""
                            SELECT COUNT(*) FROM `tabDNR` WHERE parent='{emp['employee']}' AND job_order='{job_order}'
                            UNION ALL
                            SELECT COUNT(*) FROM `tabNo Show List` WHERE parent='{emp['employee']}' AND job_order='{job_order}'
                            UNION ALL
                            SELECT COUNT(*) FROM `tabUnsatisfied Organization` WHERE parent='{emp['employee']}' AND job_order='{job_order}'
                        """
                        negative_status = frappe.db.sql(check_status_sql, as_list=True)
                        negative_status = [int(a[0]) for a in negative_status]
                        add_job_title_to_profile(job_title, emp_data, negative_status)
                        frappe.db.commit()
                except Exception:
                    pass
    except Exception as e:
        frappe.log_error(e, 'add_job_title_in_background error')


@frappe.whitelist()
def get_jobtitle_list_assign_employee(
    doctype, txt, searchfield, page_len, start, filters
):
    """
    The above code is a Python function that retrieves job titles based on certain filters.
    """

    try:
        if int(filters["resume_required"]):
            sql = f"""select DISTINCT(select_job) from (
                        SELECT q1.job_category, q1.job_start_time, q1.approved_emps, q2.select_job, q2.no_of_workers
                        FROM (
                        SELECT select_job, job_start_time, no_of_workers
                        FROM `tabMultiple Job Titles`
                        WHERE parent = '{filters['job_order']}'
                        ) AS q2
                        left JOIN (
                        SELECT job_category, job_start_time, SUM(approved) AS approved_emps
                        FROM `tabAssign Employee Details`
                        WHERE parent IN (
                            SELECT name FROM `tabAssign Employee`
                            WHERE job_order = '{filters['job_order']}' and tag_status="Approved"
                        )
                        GROUP BY job_category, job_start_time
                        ) AS q1 ON q1.job_start_time = q2.job_start_time and q2.select_job = q1.job_category
                        ) q3 where (q3.no_of_workers > q3.approved_emps or q3.approved_emps IS NULL) and select_job like "%%{str(txt)}%%"
                """
        else:
            sql = f"""select DISTINCT(job_titles) from `tabIndustry Types Job Titles` 
                    where job_titles in (select select_job from `tabMultiple Job Titles` where parent='{filters['job_order']}')                     
                    and job_titles in (SELECT mul.job_title from `tabClaim Order` co join `tabMultiple Job Title Claim` as mul on mul.parent=co.name 
                    where co.staffing_organization = '{filters['company']}'
                    and co.job_order = '{filters['job_order']}' and  mul.approved_no_of_workers>0)
                    and job_titles like "%%{str(txt)}%%"
                """
        job_category = frappe.db.sql(sql)
        return job_category
    except Exception as e:
        frappe.log_error(e, "Getting Job Title Error")


@frappe.whitelist()
def get_start_time_list_assign_employee(resume_required, job_order, company):
    """
    The above code is a Python function that retrieves a list of start times based on certain
    conditions.
    """

    if int(resume_required):
        sql = f"""select distinct(start_time) from (
                    SELECT q1.job_category, q1.job_start_time, q1.approved_emps, q2.select_job, q2.no_of_workers, q2.job_start_time as start_time
                    FROM (
                    SELECT select_job, job_start_time, no_of_workers
                    FROM `tabMultiple Job Titles`
                    WHERE parent = '{job_order}'
                    ) AS q2
                    left JOIN (
                    SELECT job_category, job_start_time, SUM(approved) AS approved_emps
                    FROM `tabAssign Employee Details`
                    WHERE parent IN (
                        SELECT name FROM `tabAssign Employee`
                        WHERE job_order = '{job_order}' and tag_status="Approved"
                    )
                    GROUP BY job_category, job_start_time
                    ) AS q1 ON q1.job_start_time = q2.job_start_time and q2.select_job = q1.job_category
                    ) q3 where q3.no_of_workers > q3.approved_emps or q3.approved_emps IS NULL 
            """
    else:
        sql = f"""select DISTINCT(job_start_time) from `tabMultiple Job Titles` 
                    where parent='{job_order}'
                    and select_job in (SELECT mul.job_title from `tabClaim Order` co join `tabMultiple Job Title Claim` as mul on mul.parent=co.name 
                    where co.staffing_organization = '{company}'
                    and co.job_order = '{job_order}' and  mul.approved_no_of_workers>0)
            """
    start_times = frappe.db.sql(sql)
    times = [":".join((str(x[0]).split(":"))[:-1]) for x in start_times if x]
    return times


@frappe.whitelist()
def multiple_job_title_details(job_order,resume_required, staffing_company=None):
    try:
        my_data = multiple_job_titles_sql_query(job_order,resume_required,staffing_company)

        if len(my_data) == 0:
            return "No Record"
        else:
            from tag_workflow.tag_workflow.doctype.claim_order.claim_order import (get_pay_rate_class_code)
            jo_doc = frappe.get_doc(jobOrder, job_order)
            for each_data in my_data:
                pay_rate = get_pay_rate_class_code(jo_doc.as_json(), staffing_company)
                if pay_rate[each_data["select_job"]].get('emp_pay_rate'):
                    each_data.update({"pay_rate": pay_rate[each_data["select_job"]]['emp_pay_rate']})
            return my_data
    except Exception as e:
        print(frappe.get_traceback())
        frappe.log_error(e, "Getting Job Title Details Error")


@frappe.whitelist()
def multiple_job_titles_sql_query(job_order,resume_required,staffing_company):
    query_patch=""
    if int(resume_required) == 0:
        query_patch = f" and staffing_organization = '{staffing_company}'"
    sql = f"""
                SELECT
                mul.select_job,
                mul.category,
                mul.no_of_workers,
                mul.worker_comp_code,
                mul.rate,
                mul.job_start_time,
                mul.estimated_hours_per_day,
                mul.per_hour,
                mul.flat_rate,
                mul.worker_filled,
                sum(mjc.approved_no_of_workers) as approved_no_of_workers
            FROM
                `tabMultiple Job Titles` mul
            LEFT JOIN
                `tabJob Order` jo ON mul.parent = jo.name
            LEFT JOIN
                (
                    SELECT
                        approved_no_of_workers,
                        job_title,
                        start_time
                    FROM
                        `tabMultiple Job Title Claim`
                    WHERE
                        parent IN (
                            SELECT
                                name
                            FROM
                                `tabClaim Order`
                            WHERE
                                job_order = '{job_order}' {query_patch}
                        )
                ) mjc ON mul.select_job = mjc.job_title AND mul.job_start_time = mjc.start_time
            WHERE
                jo.name = '{job_order}'
                group by mul.select_job,mul.job_start_time;
        """
    my_data = frappe.db.sql(sql, as_dict=True)
    return my_data


@frappe.whitelist()
def create_pay_rate_comp_code_job_title(job_order, assign_employee):
    """
    This function creates pay rate, staff compensation code, and job title for a assign employee based on
    job order details in a background job.

    :param job_order: The job order is a JSON object that contains information about a job order
    :param assign_employee: The parameter `assign_employee` is a JSON object that contains information about a
    assign employee, including the staffing organization, multiple job titles, and other relevant details
    """
    try:
        job_site = job_order.job_site
        staffing_company = assign_employee.company
        hiring_company = job_order.company
        for index, row in enumerate(assign_employee.multiple_job_title_details):
            job_title, industry_type = (
                row.select_job,
                job_order.multiple_job_titles[index].category,
            )
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
                "tag_workflow.tag_workflow.doctype.claim_order.claim_order.create_staff_comp_code_new",
                row=row,
                job_title=job_title,
                job_site=job_site,
                industry_type=industry_type,
                staffing_company=staffing_company,
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
    except Exception as e:
        print(e, frappe.get_traceback(),
              "create_pay_rate_comp_code_job_title Error")


@frappe.whitelist()
def validate_approved_workers(job_order, staff_company):
    """
    The above code is executing a SQL query to fetch data from the database. It selects the
    job_title, start_time, and the sum of approved_no_of_workers from the 'Multiple Job Title Claim'
    table. It then joins this table with the 'Claim Order' table based on the parent field. The
    query filters the data based on the staffing_organization and job_order values. Finally, it
    groups the data by job_title.
    """

    sql = f""" SELECT mul.job_title, mul.start_time ,sum(mul.approved_no_of_workers) as approved_no_of_workers from `tabMultiple Job Title Claim` mul 
        left join `tabClaim Order`  as co on mul.parent=co.name 
        where co.staffing_organization = "{staff_company}"
        and co.job_order = "{job_order}" group by mul.job_title, mul.start_time"""
    data = frappe.db.sql(sql, as_dict=True)

    approved_job_titles = {}
    for i in data:
        approved_job_titles[
            f'{i["job_title"]}~{":".join(str(i["start_time"]).split(":")[:-1])}'
        ] = (i["approved_no_of_workers"] or 0)

    return approved_job_titles

@frappe.whitelist()
def check_removed_employee(docname):
    try:
        sql = """select data from `tabVersion` where docname="{0}" order by modified DESC""".format(docname)
        data = frappe.db.sql(sql, as_list=1)

        if not data:
            return []

        new_data = json.loads(data[0][0])
        removed_emp_rows = []

        if new_data.get('row_changed'):
            for i in new_data.get('row_changed'):
                if i[0] == "employee_details" and any(j[0] == "remove_employee" and j[2] == 1 for j in i[3]):
                    removed_emp_rows.append(i[1] + 1)

        return removed_emp_rows
    except Exception as e:
        print(e, frappe.get_traceback())