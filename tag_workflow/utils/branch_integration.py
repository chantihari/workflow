import json
from datetime import datetime, date
import calendar
import frappe
from frappe import _
import requests

@frappe.whitelist()
def check_dob_ssn(emp_id=None, ssn=None, dob=None, doctype=None):
    if emp_id:
        emp_data = frappe.get_doc('Employee', emp_id)
        message = ''
        message+= f'Enable Branch for {emp_data.employee_name}.' if emp_data.opt_in==0 and not doctype else ''
        message+= check_ssn(emp_data, message)
        if emp_data.date_of_birth:
            today = date.today()
            age = today.year - emp_data.date_of_birth.year -((today.month, today.day) < (emp_data.date_of_birth.month, emp_data.date_of_birth.day))
            if age < 18:
                message += f'<hr>{emp_data.employee_name} must be 18+ to have a Branch account.' if message else f'{emp_data.employee_name} must be 18+ to have a Branch account.'
        return message
    else:
        return check_dob_ssn_contd(ssn, dob)

@frappe.whitelist()
def check_ssn(emp_data, message):
    all_emp = frappe.get_all('Employee', fields=['name'], filters={'name': ['!=', emp_data.name], 'account_number': ['is', 'set']})
    for emp in all_emp:
        emp_detail = frappe.get_doc('Employee',emp)
        if emp_detail.ssn and emp_data.ssn and emp_detail.get_password('ssn') == emp_data.get_password('ssn'):
            return f'<hr>SSN of {emp_data.employee_name} must be unique to have a Branch account.' if message else f'SSN of {emp_data.employee_name} must be unique to have a Branch account.'
    return ''

@frappe.whitelist()
def check_dob_ssn_contd(ssn, date_of_birth):
    message = ''
    if ssn:
        ssn_duplicate = False
        all_emp = frappe.get_all('Employee', fields=['name'], filters={'account_number': ['is', 'set']})
        for emp in all_emp:
            emp_detail = frappe.get_doc('Employee',emp)
            if emp_detail.ssn and emp_detail.get_password('ssn') == ssn:
                ssn_duplicate = True
                break
        if ssn_duplicate:
            message += 'SSN must be unique to have a Branch account.'
    if date_of_birth:
        date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d')
        today = date.today()
        age = today.year - date_of_birth.year -((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
        if age < 18:
            message+='<hr>Employee must be 18+ to have a Branch account.' if message else 'Employee must be 18+ to have a Branch account.'
    return message

@frappe.whitelist()
def get_employee_data(emp_id, company):
    try:
        emp_data = frappe.get_doc('Employee', emp_id)
        if emp_data.opt_in == 1:
            if emp_data.account_number:
                return None
            else:
                return check_fields(emp_data) if check_fields(emp_data) else create_wallet(emp_data, company)
        else:
            return check_fields(emp_data) if check_fields(emp_data) else None
    except Exception as e:
        frappe.log_error('Branch: Get Employee Data Error', e)

def check_fields(emp_data):
    message = "<b>Please fill the below fields to create wallet in Branch:</b>"
    fields = {"First Name": emp_data.first_name, "Last Name": emp_data.last_name, "Street Address": emp_data.street_address, "City": emp_data.city, "State": emp_data.state, "Zip": emp_data.zip, "Date of Birth": emp_data.date_of_birth, "SSN": emp_data.sssn, "Contact Number": emp_data.contact_number, "Email": emp_data.email}
    for i in fields:
        if not fields[i]:
            message = message + '<br>' + '<span>&bull;</span> '+i
    warning = check_dob_ssn(emp_data.name)
    if message != "<b>Please fill the below fields to create wallet in Branch:</b>":
        message+= '<hr>'+warning if warning else ''
        return message
    elif warning:
        return warning
    else:
        return None

def state_abbr(state):
    state_list = {
        'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA', 'Canal Zone': 'CZ',
        'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'District of Columbia': 'DC', 'Florida': 'FL',
        'Georgia': 'GA', 'Guam': 'GU', 'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN',
        'Iowa': 'IA', 'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
        'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT',
        'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC',
        'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Puerto Rico': 'PR', 'Rhode Island': 'RI',
        'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
        'Virgin Islands': 'VI', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
    }
    if state in state_list.keys():
        return state_list[state]
    else:
        return ''


@frappe.whitelist()
def create_wallet(emp_data, company):
    try:
        company_details = frappe.get_doc('Company', company)
        decrypted_org_id = company_details.get_password('branch_org_id')
        decrypted_api_key = company_details.get_password('branch_api_key')
        data = {
            "first_name": emp_data.first_name,
            "last_name": emp_data.last_name,
            "address":{
                "address_1": emp_data.street_address,
                "address_2": emp_data.suite_or_apartment_no if emp_data.suite_or_apartment_no else '',
                "city": emp_data.city,
                "state": state_abbr(emp_data.state),
                "postal_code": emp_data.zip if len(emp_data.zip) ==5 else emp_data.zip[:5]
            },
            "date_of_birth": emp_data.date_of_birth.strftime("%Y-%m-%d"),
            "ssn": emp_data.get_password("ssn"),
            "phone_number":emp_data.contact_number,
            "email_address":emp_data.email,
            "create_employee":True,
        }
        branch_url= f"https://sandbox.branchapp.com/v1/organizations/{decrypted_org_id}/employees/{emp_data.name}/wallets"
        response = requests.post(url=branch_url, data=json.dumps(data), headers={'apikey': decrypted_api_key, 'Content-Type': 'application/json'})
        content = json.loads(response.content)
        if response.status_code == 201:
            frappe.msgprint(_(f"Branch wallet has been successfully created for the employee <b>{emp_data.name}: {emp_data.employee_name}</b>"))
            return content["account_number"]
        else:
            frappe.msgprint(_(f"Error {response.status_code}: {content['message']}"))
            return "Error"
    except Exception as e:
        frappe.log_error('Branch: Create Wallet Error', e)

@frappe.whitelist()
def get_wallet_data(emp_id):
    try:
        emp_data = frappe.get_doc('Employee', emp_id)
        if emp_data.account_number:
            company_details = frappe.get_doc('Company', emp_data.company)
            decrypted_org_id = company_details.get_password('branch_org_id')
            decrypted_api_key = company_details.get_password('branch_api_key')
            branch_url= f"https://sandbox.branchapp.com/v1/organizations/{decrypted_org_id}/employees/{emp_data.name}/wallet"
            response = requests.get(url=branch_url, headers={'apikey': decrypted_api_key})
            content = json.loads(response.content)
            if response.status_code == 200:
                result = {'acc_no': content['account_number'], 'card_status': 'True' if content['has_activated_card'] else 'False'}
                result = get_remaining_result(result, content['status'], content['reason_code'], content['reason'])

                utc = datetime.strptime(content['time_created'], '%Y-%m-%dT%H:%M:%SZ')
                create_time = datetime.fromtimestamp(calendar.timegm(utc.timetuple()))
                result['time_created'] = create_time.strftime('%m-%d-%Y %H:%M')
                return result
            else:
                return f"<b>Error {response.status_code}:</b>"
        else:
            return 'No Data'
    except Exception as e:
        frappe.log_error('Branch: Get Wallet Data Error', e)

def acc_status_label(status):
    status_label = {
        "CREATED": "A Wallet has been created",
        "FAILED": "A failure occurred during wallet creation",
        "CLOSED": "A Wallet has been closed",
        "NOT_CREATED": "A Wallet has not yet been created",
        "PENDING": "We are attempting to create the wallet. It is not yet available for disbursing funds",
        "UNCLAIMED": "A wallet has been created and is able to receive funds through the API, but the employee has not signed up with Branch yet",
        "ACTIVE": "A wallet has been created for an employee and they are in control of it"
    }
    return status_label[status] if status in status_label else ''

def reason_code_label(code):
    labels = {
        "ADDITIONAL_DOCS_REQ": "Branch was not able to confirm identity with the information provided the user will have to provide additional documentation, like drivers license, in order get a wallet on Branch",
        "FRAUD_CHECK_REQ": "Branch is performing checks to ensure that the user is not linked in any way to fraudulent activity. Once finished, this user's wallet will be activated. Until then, the wallet that was created for the user will not be able to be funded in any way",
        "CONFIRMED_FRAUD": "Branch determined this user to behave in fraudulent activities and will not be allowed to have a wallet on the platform. The wallet created for them will remain closed.",
        "DENIED": "For one reason or another, the user has been denied access to the platform",
        "ERROR": "A system error occurred, please try again"
    }
    return labels[code] if code in labels else ''

def get_remaining_result(result, status, reason_code, reason):
    if status:
        result['acc_status']= status.replace('_', ' ')
        result['acc_status_label'] = acc_status_label(status)

    if reason_code:
        result['reason_code'] = reason_code.replace('_', ' ')
        result['reason_code_label'] = reason_code_label(reason_code)

    if reason:
        result['reason'] = reason.replace('_', ' ')

    return result
