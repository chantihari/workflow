import frappe
from frappe import _


@frappe.whitelist()
def active_holiday_list(company_name,holiday_list_name,status,name):
    try:
        if status == "Active":
            frappe.db.sql("""UPDATE `tabHoliday List` SET status = '{0}' WHERE company = '{1}' and name != '{2}'""".format("Inactive",company_name,holiday_list_name))
            frappe.db.commit()
            frappe.db.set_value("Company",company_name,"default_holiday_list",name)

        else:
            frappe.db.sql("""UPDATE `tabCompany` set default_holiday_list = null WHERE name = '{0}' and default_holiday_list = '{1}'""".format(company_name,name))
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(e, "Holiday_list.py")

            

