import frappe
from frappe import _
import datetime
from dateutil.relativedelta import relativedelta
from frappe.model.mapper import get_mapped_doc
from frappe.share import add_docshare as add
from tag_workflow.tag_data import joborder_email_template
from tag_workflow.utils.notification import make_system_notification, get_mail_list

start = datetime.datetime.now().date() + relativedelta(day=1)
end = datetime.datetime.now().date() + relativedelta(day=31)
time_format = " 12:00:00"

#-----------------#
COM = "Company"
payment = "Payment Schedule"
taxes= "Sales Taxes and Charges"
team = "Sales Team"
SO = "Sales Invoice"

#-----------------------------------#
def set_missing_values(source, target, customer=None, ignore_permissions=True):
    if customer:
        target.customer = customer.name
        target.customer_name = customer.customer_name
    target.ignore_pricing_rule = 1
    target.flags.ignore_permissions = ignore_permissions
    target.run_method("set_missing_values")
    target.run_method("calculate_taxes_and_totals")

def make_sales_invoice(source_name, company, target_doc=None, ignore_permissions=True):
    def customer_doc(source_name):
        return frappe.get_doc("Customer", {"name": source_name})

    def update_item(company, source, doclist):
        total_amount = 0
        
        income_account, cost_center, default_expense_account, tag_charges = frappe.db.get_value("Company", company, ["default_income_account", "cost_center", "default_expense_account", "tag_charges"])

        sql = """ select grand_total from `tabSales Invoice` where docstatus = 1 and company = '{0}' and posting_date between '{1}' and '{2}' """.format(source, start, end)
        invoice = frappe.db.sql(sql, as_dict=1)

        for inv in invoice:
            total_amount += (inv.grand_total * tag_charges)/100
        
        item = {"item_name": "Service charges for "+str(source), "description": "Service", "uom": "Nos", "qty": 1, "stock_uom": "Nos", "conversion_factor": 1, "stock_qty": 1, "rate": total_amount, "amount": total_amount, "income_account": income_account, "cost_center": cost_center, "default_expense_account": default_expense_account}
        doclist.append("items", item)

    def make_invoice(source_name, target_doc):
        return get_mapped_doc(COM, source_name, {
            COM: {"doctype": SO, "validation": {"docstatus": ["=", 0]}},
            taxes: {"doctype": taxes, "add_if_empty": True},
            team: {"doctype": team, "add_if_empty": True},
            payment: {"doctype": payment,"add_if_empty": True}
        }, target_doc, set_missing_values, ignore_permissions=ignore_permissions)

    customer = customer_doc(source_name)
    doclist = make_invoice(source_name, target_doc)
    doclist.company = company
    update_item(company, source_name, doclist)
    set_missing_values(source_name, doclist, customer=customer, ignore_permissions=ignore_permissions)
    return doclist

@frappe.whitelist()
def make_invoice(source_name, target_doc=None):
    try:
        company = frappe.db.get_value("User", frappe.session.user, "company") or "TAG"
        sql = """ select name from `tabSales Invoice` where docstatus = 1 and company = '{0}' and posting_date between '{1}' and '{2}' """.format(source_name, start, end)
        invoice_list = frappe.db.sql(sql, as_dict=1)
        if(len(invoice_list) <= 0):
            frappe.msgprint(_("No Invoice found for <b>{0}</b> for current month").format(source_name))
            return 0
        else:
            return make_sales_invoice(source_name, company)
    except Exception as e:
        print(e)
        frappe.msgprint(frappe.get_traceback())


#-------------------------------------Month Invoice---------------------#
@frappe.whitelist(allow_guest=False)
def make_month_invoice(frm):
    tag_company = frappe.db.get_value("User", frappe.session.user, "company") or "TAG"
    import json
    frm_value = json.loads(frm)
    months = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,"July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12}
    
    date = frm_value['month']
    year = frm_value['year']
    company = frm_value['company']
    get_month_digit = months[date]
    # get current month start date and end date
    current_month_str = str(year)+'-'+str(get_month_digit)+'-'+'01' 
    current_date = frappe.utils.getdate(current_month_str)

    first_day = frappe.utils.get_first_day(current_date)
   
    first = f"select creation from `tabSales Invoice`  where month = '{date}' and year = '{year}' and company = '{tag_company}' order by creation desc limit 1"
    sales_first_day = frappe.db.sql(first,as_dict=1)

    if sales_first_day:
        first_day = frappe.utils.getdate(sales_first_day[0]['creation'])

    last_day = frappe.utils.get_last_day(first_day)
    current_last_day = datetime.datetime.now().date()

    if current_last_day < last_day:
        last_day = current_last_day

    sql = f""" select name from `tabSales Invoice` where docstatus = 1 and company = '{company}' and posting_date between '{first_day}' and '{last_day}' and is_check_in_sales_invoice = 0 """
    invoice_list = frappe.db.sql(sql, as_dict=1)

    if(len(invoice_list) <= 0):
        frappe.msgprint(_("No Invoice found for <b>{0}</b> for current month from {1} to {2}").format(company,frappe.format(first_day, {'fieldtype': 'Date'}),frappe.format(last_day, {'fieldtype': 'Date'})))
        return 0
    else:
        return create_month_sales_invoice(company, tag_company,date,year,first_day,last_day)


def receiver_company_details(doclist, for_company, for_company_city, for_company_state, for_company_zip, for_company_billing, for_company_city_billing, for_company_state_billing, for_company_zip_billing, for_billing_address_check,accounts_receivable_name,accounts_receivable_rep_email,accounts_receivable_phone_number):
        if for_billing_address_check and for_company_billing:
            doclist.for_company = for_company_billing
            doclist.for_company_city = for_company_city_billing
            doclist.for_company_state = for_company_state_billing
            doclist.for_company_zip = for_company_zip_billing
        else:
            doclist.for_company = for_company
            doclist.for_company_city = for_company_city
            doclist.for_company_state = for_company_state
            doclist.for_company_zip = for_company_zip
            
        if for_billing_address_check:
            if len(accounts_receivable_name):
                doclist.accounts_receivable_name = accounts_receivable_name
            if len(accounts_receivable_rep_email):
                doclist.accounts_receivable_rep_email = accounts_receivable_rep_email
            if len(accounts_receivable_phone_number):
                doclist.accounts_receivable_phone_number = accounts_receivable_phone_number

def create_month_sales_invoice(source_name, company,month,year,first_day,last_day, target_doc=None, ignore_permissions=True):
    def customer_doc(source_name):
        return frappe.get_doc("Customer", {"name": source_name})

    def update_item(company, source, doclist,first_day,last_day):
        try:
            total_amount = 0
            grand_total = 0
            
            income_account,cost_center,default_expense_account,creater_company,creater_city,creater_state,creater_zip,_ = frappe.db.get_value("Company", company,["default_income_account", "cost_center", "default_expense_account","address","city","state","zip","tag_charges"])
            for_company,for_company_city,for_company_state,for_company_zip,for_company_billing,for_company_city_billing,for_company_state_billing,for_company_zip_billing,staff_tag_charge,for_billing_address_check,accounts_receivable_name,accounts_receivable_rep_email,accounts_receivable_phone_number = frappe.db.get_value("Company",source,["address","city","state","zip","complete_address_billing","city_billing","state_billing","zip_billing","tag_charges","display_account_receivables_on_invoices","accounts_receivable_name","accounts_receivable_rep_email","accounts_receivable_phone_number"])

            sql = """ select grand_total from `tabSales Invoice` where docstatus = 1 and company = '{0}' and posting_date between '{1}' and '{2}' and is_check_in_sales_invoice = 0 """.format(source, first_day, last_day)
            invoice = frappe.db.sql(sql, as_dict=1)

            for inv in invoice:
                total_amount += (inv.grand_total * staff_tag_charge)/100
                grand_total += inv.grand_total
            
            item = {"item_name": "Service charges for "+str(source), "description": "Service", "uom": "Nos", "qty": 1, "stock_uom": "Nos", "conversion_factor": 1, "stock_qty": 1, "rate": total_amount, "amount": total_amount, "income_account": income_account, "cost_center": cost_center, "default_expense_account": default_expense_account}
            doclist.append("items", item)

            doclist.tag_charge1 = staff_tag_charge
            doclist.tag_grand_total1 = grand_total
            doclist.total_billing_amount_premium = total_amount

            # tag company detail based on billing details flag from settings page
            doclist.creater_company = creater_company
            doclist.creater_city = creater_city
            doclist.creater_state = creater_state
            doclist.creater_zip = creater_zip

            # staffing company detail based on billing details flag from settings page
            receiver_company_details(doclist, for_company, for_company_city, for_company_state, for_company_zip, for_company_billing, for_company_city_billing, for_company_state_billing, for_company_zip_billing, for_billing_address_check,accounts_receivable_name,accounts_receivable_rep_email,accounts_receivable_phone_number)
        except Exception as e:
            print(e)
            frappe.log_error(e,'create month sales invoice update item')

    def update_salesinvoice_list(company, doclist,first_day,last_day):
        try:
            sql = f""" select name,company,job_order,total_billing_hours,total_billing_amount from `tabSales Invoice` where docstatus = 1 and company = '{company}' and posting_date between '{first_day}' and '{last_day}' and is_check_in_sales_invoice = 0 """
            salesinvoice_data = frappe.db.sql(sql, as_dict=True)

            for d in salesinvoice_data:
                update_salesinvoice_is_check_in_sales_invoice(d.name)
                if d.job_order:
                    joborder = frappe.db.sql(f'''select company,select_job,from_date,to_date,rate from `tabJob Order` where name = "{d.job_order}"''', as_dict=True)
                
                    activity = {"sales_invoice_id":d.name,"job_order_id":d.job_order,"start_date":joborder[0].from_date,"end_date":joborder[0].to_date,"job_title":joborder[0].select_job,"total_hours":d.total_billing_hours,"total_amount":d.total_billing_amount}
                    doclist.append("sales_invoice_data", activity)
        except Exception as e:
            print(e)
            frappe.log_error(e,'update sales invoice list')

    def make_invoice(source_name, target_doc):
        return get_mapped_doc(COM, source_name, {
            COM: {"doctype": SO, "validation": {"docstatus": ["=", 0]}},
            taxes: {"doctype": taxes, "add_if_empty": True},
            team: {"doctype": team, "add_if_empty": True},
            payment: {"doctype": payment,"add_if_empty": True}
        }, target_doc, set_missing_values, ignore_permissions=ignore_permissions)

    customer = customer_doc(source_name)
    doclist = make_invoice(source_name, target_doc)

    doclist.company = company
    doclist.month = month
    doclist.year = year
    doclist.first_day = first_day
    doclist.last_day = last_day
    doclist.title = customer.name+" "+doclist.month+" "+doclist.year
    update_item(company, source_name, doclist,first_day,last_day)
    update_salesinvoice_list(source_name, doclist,first_day,last_day)
    set_missing_values(source_name, doclist, customer=customer, ignore_permissions=ignore_permissions)
    doclist.save()
    doclist.submit()
    # sharing  list of staffing user
    sql = ''' select name from `tabUser` where company='{}' and tag_user_type = "Staffing Admin" '''.format(source_name)
    user_list = frappe.db.sql(sql, as_dict=1)

    users = [l.name for l in user_list]
    for usr in users:
        add("Sales Invoice", doclist.name, usr, read=1, write = 0, share = 0, everyone = 0, flags={"ignore_share_permission": 1})
    if(users):
        msg = f'{company} has submitted a Monthly invoice for {month}-{year}'
        subject = " Monthly Invoice Submitted"
        make_system_notification(users, msg, SO, doclist.name, subject)
        link = frappe.utils.get_url_to_form(SO, doclist.name)
        joborder_email_template(subject = subject,content = msg,recipients = users,link=link)
    return doclist.name


def update_salesinvoice_is_check_in_sales_invoice(name):
    try:
        sql = """ UPDATE `tabSales Invoice` SET `tabSales Invoice`.is_check_in_sales_invoice = 1 where name = "{}" """.format(name)
        frappe.db.sql(sql)
        frappe.db.commit()
    except Exception as e:
        frappe.error_log(e,'update failed is_check_in_sales_invoice')


#----------------due date---------------#
@frappe.whitelist()
def get_due_date(posting_date, party_type, party, company=None, bill_date=None):
    try:
        due_date = None
        if(posting_date):
            due_date = frappe.utils.add_to_date(posting_date, days=30)
        return due_date
    except Exception as e:
        frappe.msgprint(e)
