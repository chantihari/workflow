''' QuickBooks sync with ERP '''

import json
import frappe
import traceback
from frappe import _
import requests, time
from quickbooks import QuickBooks
from intuitlib.client import AuthClient
from quickbooks.objects.item import Item
from requests_oauthlib import OAuth2Session
from quickbooks.objects.account import Account
from quickbooks.objects.invoice import Invoice
from quickbooks.objects.customer import Customer
from quickbooks.objects.base import CustomerMemo
from quickbooks.objects.base import Address, PhoneNumber, EmailAddress
from quickbooks.objects.detailline import SalesItemLine, SalesItemLineDetail

sale = "Sales Invoice"

@frappe.whitelist()
def callback(*args, **kwargs):
    try:
        company_id = kwargs.get("realmId")
        if(frappe.db.exists("Company", {"quickbooks_company_id": company_id})):
            company = frappe.get_doc("Company", {"quickbooks_company_id": company_id})
            company.refresh_token = ''
            company.code = kwargs.get("code")
            client_id = company.get_password('client_id')
            client_secret = company.get_password('client_secret')
            oauth = OAuth2Session(client_id=client_id, redirect_uri=company.redirect_url, scope=company.scope)
            token = oauth.fetch_token(token_url=company.token_endpoint, client_secret=client_secret, code=kwargs.get("code"))
            company.access_token = token["access_token"]
            company.refresh_token = token["refresh_token"]
            company.save()
            frappe.respond_as_web_page("Quickbooks Authentication", html="<script>window.close()</script>")
        else:
            frappe.throw(_("Company does not exists"))
    except Exception as e:
        frappe.msgprint(e)


def get_access_token(comp):
    client_id = comp.get_password('client_id')
    client_secret = comp.get_password('client_secret')
    try:
        oauth = OAuth2Session(client_id=client_id, redirect_uri=comp.redirect_url, scope=comp.scope)
        token = oauth.refresh_token(token_url=comp.token_endpoint, client_id=client_id, refresh_token=comp.refresh_token, client_secret=client_secret, code=comp.code)
        frappe.db.set_value("Company", comp.name, "access_token", token["access_token"])
        frappe.db.set_value("Company", comp.name, "refresh_token", token["refresh_token"])
        return token["access_token"]
    except Exception as e:
        frappe.log_error(e, "get_access_token")
        return ''



#------------check if quickbook auth or not and sync invoice------------#
@frappe.whitelist()
def auth_quickbook_and_sync(company, invoice):
    try:
        result = {"authorization_url": "", "invoice_id": "", "error": ""}
        com = frappe.get_doc("Company", company)
        client_id = com.get_password('client_id')
        client_secret = com.get_password('client_secret')
        if(not client_id or not client_secret or not com.quickbooks_company_id):
            frappe.msgprint(_("Please add <b>Client ID</b>, <b>Client Secret</b> and <b>QuickBook Company ID</b> in <b>{0}</b> profile").format(company))
        elif(not com.refresh_token and com.authorization_url):
            com.refresh_token, com.code, com.access_token, com.refresh_token, com.authorization_url = '', '', '', '', ''
            com.save()
            result['authorization_url'] = com.authorization_url
        elif(com.refresh_token):
            invoice = frappe.get_doc(sale, invoice)
            if(not invoice.quickbook_invoice_id):
                result = sync_invoice(invoice, result)
                frappe.db.set_value(sale, invoice.name, "quickbook_invoice_id", result['invoice_id'])
            else:
                result = sync_invoice(invoice, result, invoice.quickbook_invoice_id)
                if(invoice.quickbook_invoice_id != result['invoice_id']):
                    frappe.db.set_value(sale, invoice.name, "quickbook_invoice_id", result['invoice_id'])
        return result
    except Exception as e:
        frappe.log_error(e, "QuickBook auth")
        result['error'] = e
        return result

#check customer in Quickbook
def check_customer(customer, client):
    try:
        customers = Customer.filter(Active=True, GivenName=customer, qb=client)
        if not customers:
            cust = Customer()
            cust.CompanyName = customer
            cust.GivenName = customer

            if(frappe.db.exists("Company", customer)):
                _customer = frappe.get_doc("Company", customer, ignore_permissions=True)
                cust.BillAddr = Address()
                cust.BillAddr.Line1 = _customer.address or ''
                cust.BillAddr.Line2 = _customer.suite_or_apartment_no or ''
                cust.BillAddr.City = _customer.city or ''
                cust.BillAddr.CountrySubDivisionCode = _customer.state or ''
                cust.BillAddr.PostalCode = _customer.zip or ''

                cust.PrimaryPhone = PhoneNumber()
                cust.PrimaryPhone.FreeFormNumber = _customer.phone_no or ''

                cust.PrimaryEmailAddr = EmailAddress()
                cust.PrimaryEmailAddr.Address = _customer.email or ''

            cust.save(qb=client)
            return cust
        else:
            for c in customers:
                return c
    except Exception as e:
        frappe.log_error(e, "check_customer")


#create invoice in quickbook
def create_invoice(invoices, client, cust, result, request_id=None):
    try:
        if(request_id):
            INV = Invoice.filter(Id=request_id, qb=client)
            if(INV):
                invoice = INV[0]
            else:
                invoice = Invoice()
                invoice.DocNumber = invoices.name
        else:
            invoice = Invoice()
            invoice.DocNumber = invoices.name

        items = get_items(invoices)
        if(items):
            invoice.Line = []
            for i in items:
                line_detail = SalesItemLineDetail()
                line_detail.UnitPrice = i['rate']  # in dollars
                line_detail.Qty = i['qty']

                line = SalesItemLine()
                line.Amount = i['rate']*i['qty']  # in dollars
                line.Description = i['employee']
                line.SalesItemLineDetail = line_detail
                invoice.Line.append(line)

            invoice.TxnDate = str(invoices.posting_date)
            invoice.CustomerRef = cust.to_ref()
            invoice.CustomerMemo = CustomerMemo()
            invoice.CustomerMemo.value = "TAG Job Order: "+str(invoices.job_order)+", TAG Invoice: "+str(invoices.name)
            invoice.save(qb=client)
            result['invoice_id'] = invoice.to_dict()['Id']
        else:
            result['error'] = "<b>Can't Export/Update. Employee's Details are not found</b>"
        return result
    except Exception as e:
        frappe.log_error(e, "create_invoice")
        result['error'] = str(e)
        return result

#invoice items
def get_items(invoice):
    try:
        items = []
        employee = []
        for e in invoice.timesheets:
            if e.employee_name not in employee:
                employee.append(e.employee_name)

        items = merge_employees_data(invoice, employee)
        return items
    except Exception as e:
        frappe.log_error(e, "get_items")
        return []

def merge_employees_data(invoice, employee):
    try:
        items = []
        for e in employee:
            n_rate, n_qty, f_rate, o_rate, o_qty = 0, 0, 0, 0, 0
            for t in invoice.timesheets:
                if(e == t.employee_name):
                    n_rate, f_rate = t.per_hour_rate1, f_rate+t.flat_rate
                    bill_hour = t.billing_hours
                    if(t.overtime_hours > 0):
                        o_qty += o_qty+t.overtime_hours
                        o_rate = t.overtime_rate
                        bill_hour = t.billing_hours-t.overtime_hours
                    n_qty += bill_hour

            items.append({"employee": e+"(Standard)", "rate": n_rate, "qty": n_qty})
            if(f_rate > 0):
                items.append({"employee": e+"(Flat)", "rate": f_rate, "qty": 1})
            if(o_qty > 0):
                items.append({"employee": e+"(OT)", "rate": o_rate, "qty": o_qty})

        return items
    except Exception as e:
        frappe.log_error(e, "merge_employees_data")
        return []

def sync_invoice(invoice, result, request_id=None):
    try:
        print(invoice.company)
        company = frappe.get_doc("Company", invoice.company)
        client_id = company.get_password('client_id')
        client_secret = company.get_password('client_secret')
        #fetching access token from quickbook
        access_token = get_access_token(company)
        if(access_token):
            #Setting up an AuthClient
            qb_environment = frappe.get_site_config().qb_environment or 'sandbox'
            auth_client = AuthClient(client_id=client_id, client_secret=client_secret, access_token=access_token, environment=qb_environment, redirect_uri=company.redirect_url)
            client = QuickBooks(auth_client=auth_client, refresh_token=company.refresh_token, company_id=company.quickbooks_company_id)
            #checking customer in quickbook database
            cust = check_customer(invoice.customer, client)
            #create_invoice in quickbook
            result = create_invoice(invoice, client, cust, result, request_id)
        else:
            company.refresh_token, company.code, company.access_token, company.refresh_token, company.authorization_url = '', '', '', '', ''
            company.save()
            result['authorization_url'] = company.authorization_url
        return result
    except Exception as e:
        frappe.log_error(e, "sync_invoice")
        result['error'] = str(e)
        return result
