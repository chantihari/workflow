import frappe
from frappe import _


@frappe.whitelist()
def get_order_info(company1, com):
    try:
        cat, location, final_list = [], [], []
        sql = f"""SELECT name
            FROM `tabJob Order`
            WHERE '{frappe.utils.nowdate()}' BETWEEN from_date AND to_date
            AND name IN (
                SELECT DISTINCT job_order
                FROM `tabClaim Order`
                WHERE staffing_organization = "{company1}"
                AND approved_no_of_workers != 0
                UNION
                SELECT DISTINCT job_order
                FROM `tabAssign Employee`
                WHERE company = "{company1}"
                AND tag_status = 'Approved'
            )
            AND (cancellation_date IS NULL OR (cancellation_date IS NOT NULL AND cancellation_date >= '{frappe.utils.nowdate()}'))
            ORDER BY creation DESC;
        """
        job_orders = frappe.db.sql(sql)
        order_details = [jo[0] for jo in job_orders]
        if len(order_details) > 0:
            for j in order_details:
                data = check_claims(j, company1)
                for d in data:
                    categories = d.category.split("~")
                    cat += categories

                    if d not in final_list:
                        final_list.append(d)
                sql = "select job_site_name as name, lat, lng from `tabJob Site` where name = (select job_site from `tabJob Order` where name = '{}') and lat != '' and lng != ''".format(
                    j
                )
                data = frappe.db.sql(sql, as_dict=1)
                cat = list(set(cat))
                cat.sort()
                for d in data:
                    location.append([d["name"], float(d["lat"]), float(d["lng"]), j])
            value = {
                "location": location,
                "order": final_list,
                "org_type": com,
                "category": cat,
            }
            return value
    except Exception as e:
        print(e)
        frappe.msgprint(frappe.get_traceback())
        return {"location": [], "order": []}


@frappe.whitelist()
def order_info(name):
    try:
        result = []
        result = frappe.db.get_list(
            "Job Order",
            {"name": name},
            [
                "from_date",
                "to_date",
                "job_site",
                "total_no_of_workers",
                "extra_notes",
                "resumes_required",
                "require_staff_to_wear_face_mask",
            ],
        )
        sql = f"""
        SELECT
            jo.name, jo.from_date, jo.to_date, jo.job_site, jo.total_no_of_workers, jo.extra_notes, jo.resumes_required, jo.require_staff_to_wear_face_mask, jo.contact_email,
            GROUP_CONCAT(DISTINCT mjt.select_job ORDER BY mjt.no_of_workers DESC SEPARATOR '~') AS select_job
        FROM
            `tabJob Order` AS jo
        JOIN
            `tabMultiple Job Titles` AS mjt
            ON jo.name = mjt.parent
        WHERE
            jo.name = "{name}"
        GROUP BY
            jo.name
        """
        result = frappe.db.sql(sql, as_dict=1)
        return result
    except Exception as e:
        frappe.msgprint(e)


@frappe.whitelist()
def filter_category(company, com, category=None, order_by=None):
    try:
        location, order_detail, final_list = [], [], []
        order_detail = check_claim_assign_order(company)

        sql = filter_data(category, order_by)
        job_order = frappe.db.sql(sql, as_dict=1)
        for j in job_order:
            if j.name in order_detail:
                data = check_claims(j.name, company)
                for d in data:
                    if d not in final_list:
                        final_list.append(d)

                sql = f"""SELECT job_site_name AS name, lat, lng FROM `tabJob Site`
                WHERE name =
                (SELECT job_site FROM `tabJob Order` WHERE name = '{j.name}') AND lat != '' AND lng != ''"""
                data = frappe.db.sql(sql, as_dict=1)
                for d in data:
                    location.append(
                        [d["name"], float(d["lat"]), float(d["lng"]), j.name]
                    )

        value = {"location": location, "order": final_list, "org_type": com}
        return value
    except Exception as e:
        print(e)
        frappe.msgprint(frappe.get_traceback())
        return {"location": [], "order": []}


def filter_data(category, order_by):
    sql = None
    if category and order_by:
        sql = f"""
        SELECT DISTINCT parent AS name FROM `tabMultiple Job Titles`
        WHERE category="{category}" AND parent IN
        (SELECT JO.name FROM `tabJob Order` as JO
        WHERE "{frappe.utils.nowdate()}" BETWEEN JO.from_date AND JO.to_date
        AND JO.company_type="{order_by}")
        ORDER BY creation DESC
        """
    elif category:
        sql = f"""
        SELECT DISTINCT parent AS name FROM `tabMultiple Job Titles`
        WHERE category="{category}" AND parent IN
        (SELECT JO.name FROM `tabJob Order` as JO
        WHERE "{frappe.utils.nowdate()}" BETWEEN JO.from_date AND JO.to_date)
        ORDER BY creation DESC
        """
    elif order_by:
        sql = f"""
        SELECT name FROM `tabJob Order`
        WHERE "{frappe.utils.nowdate()}" BETWEEN from_date AND to_date
        AND company_type="{order_by}"
        ORDER BY creation DESC
        """
    return sql


def check_claims(j, company1):
    doc = frappe.get_doc("Job Order", j)
    if doc.resumes_required == 0:
        sql = f"""
            SELECT
                jo.name, jo.from_date, jo.to_date, jo.total_no_of_workers, jo.estimated_hours_per_day, jo.per_hour, jo.job_start_time,
                GROUP_CONCAT(DISTINCT mjt.category ORDER BY mjt.category SEPARATOR '~') AS category,
                GROUP_CONCAT(DISTINCT mjt.select_job ORDER BY mjt.no_of_workers DESC SEPARATOR '~') AS select_job,
                (
                    SELECT SUM(co.approved_no_of_workers)
                    FROM `tabClaim Order` AS co
                    WHERE jo.name = co.job_order AND co.staffing_organization="{company1}"
                ) AS approved_workers
            FROM
                `tabJob Order` AS jo
            JOIN
                `tabMultiple Job Titles` AS mjt
                ON jo.name = mjt.parent
            WHERE
                jo.name = "{j}"
            GROUP BY
                jo.name
        """
        data = frappe.db.sql(sql, as_dict=1)
    else:
        sql = f"""
            SELECT
                jo.name, jo.from_date, jo.to_date, jo.total_no_of_workers, jo.estimated_hours_per_day, jo.per_hour, jo.job_start_time,
                GROUP_CONCAT(DISTINCT mjt.category ORDER BY mjt.category SEPARATOR '~') AS category,
                GROUP_CONCAT(DISTINCT mjt.select_job ORDER BY mjt.no_of_workers DESC SEPARATOR '~') AS select_job,
                (
                    SELECT COUNT(approved)
                    FROM `tabAssign Employee Details`
                    WHERE approved = 1
                    AND removed_by_hiring = 0
                    AND parent IN (
                        SELECT name
                        FROM `tabAssign Employee`
                        WHERE job_order = "{j}"
                        AND company = "{company1}"
                        AND tag_status = "Approved"
                    )
                ) AS approved_workers
            FROM
                `tabJob Order` AS jo
            JOIN
                `tabMultiple Job Titles` AS mjt
                ON jo.name = mjt.parent
            WHERE
                jo.name = "{j}"
            GROUP BY
                jo.name
        """
        data = frappe.db.sql(sql, as_dict=1)
    return data


def check_claim_assign_order(company):
    sql = f"""
    ((SELECT DISTINCT job_order FROM `tabClaim Order` WHERE staffing_organization = "{company}" and approved_no_of_workers != 0 order by creation desc)
    UNION
    (SELECT DISTINCT job_order FROM `tabAssign Employee`where company = "{company}" and tag_status = "Approved"))
    """
    job_orders = frappe.db.sql(sql)
    return [jo[0] for jo in job_orders]
